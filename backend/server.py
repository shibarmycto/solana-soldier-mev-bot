from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import asyncio
import httpx
import base58
from solders.keypair import Keypair
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import threading
import json

# Import trading engine components
from trading_engine import (
    JupiterDEX, 
    RugDetector, 
    HeliusRPC,
    HeliusWebSocket,
    WhaleMonitorWebSocket,
    LiveAutoTrader,
    TrendingTokenScanner,
    TradeSignal,
    TradeResult,
    WSOL_MINT,
    MIN_PROFIT_USD,
    MAX_TRADE_TIME_SECONDS,
    LIVE_TRADING_ENABLED,
    AUTO_TRADE_ON_WHALE_SIGNAL,
    LAMPORTS_PER_SOL,
    MAX_TRADE_SOL,
    MIN_TRADE_SOL,
    DEFAULT_STOP_LOSS_PCT
)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
SOLSCAN_API_KEY = os.environ.get('SOLSCAN_API_KEY', '')
HELIUS_API_KEY = os.environ.get('HELIUS_API_KEY', '')
ADMIN_CHAT_ID = os.environ.get('ADMIN_CHAT_ID', '')
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', '@memecorpofficial')
PAYMENT_SOL_ADDRESS = os.environ.get('PAYMENT_SOL_ADDRESS', '')
PAYMENT_ETH_ADDRESS = os.environ.get('PAYMENT_ETH_ADDRESS', '')
PAYMENT_BTC_ADDRESS = os.environ.get('PAYMENT_BTC_ADDRESS', '')
DAILY_ACCESS_PRICE_GBP = float(os.environ.get('DAILY_ACCESS_PRICE_GBP', '100'))

# Whale wallets to track
WHALE_WALLETS = [
    "74YhGgHA3x1jcL2TchwChDbRVVXvzSxNbYM6ytCukauM",
    "2KUCqnm5c49wqG9cUyDiv9fVs12EMmNtBsrKpVZzLovd",
    "EthJwgUrj8drTsUZxFt13uBpQeMv3E1ceDyGAseNaxeh",
    "CkVqgWTBdZSbiaycU5K1M3JttKdAyjTwRbfZXoFugo65",
    "7NTV2q79Ee4gqTH1KS52u14BA7GDvDUZmkzd7xE3Kxci",
    "6cFuSvQS7WU689HSnQufHnghrxkY6qpiq4qKLyUfD86B",
    "H3DvA7eCqKmGmQmb1wTUmhXLQwAjt7ckmH7GPhoCtUQB",
    "AUFxnVLsKkkupjCY4kmA5ZDH8c4HgK7CZ4FYw1VcXpn8",
    "32r5qvmNTtmp7jAEfgPsF9dtBzcgUWDt6t5JyEaD3Kf1"
]

# Create the main app
app = FastAPI(title="Solana Soldier Bot API")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize trading components (will be set in startup)
jupiter_dex: Optional[JupiterDEX] = None
rug_detector: Optional[RugDetector] = None
whale_monitor: Optional[WhaleMonitorWebSocket] = None
auto_trader: Optional[LiveAutoTrader] = None
trending_scanner: Optional[TrendingTokenScanner] = None
helius_rpc: Optional[HeliusRPC] = None
whale_monitor_task: Optional[asyncio.Task] = None

# Store active trading users (telegram_id -> keypair)
active_trading_users: Dict[int, Dict] = {}

# Pydantic Models
class UserModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    telegram_id: int
    username: Optional[str] = None
    credits: float = 0.0
    is_admin: bool = False
    subscription_expires: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WalletModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_telegram_id: int
    public_key: str
    private_key_encrypted: str
    balance_sol: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True

class TradeModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_telegram_id: int
    wallet_public_key: str
    token_address: str
    token_symbol: Optional[str] = None
    trade_type: str  # "BUY" or "SELL"
    amount_sol: float
    amount_tokens: float = 0.0
    price_at_trade: float = 0.0
    profit_usd: float = 0.0
    status: str = "PENDING"  # PENDING, COMPLETED, FAILED
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class WhaleActivityModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    whale_address: str
    token_address: str
    token_symbol: Optional[str] = None
    action: str  # "CREATE", "BUY", "SELL", "BURN"
    amount: float = 0.0
    market_cap: float = 0.0
    detected_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class PaymentModel(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_telegram_id: int
    amount_gbp: float
    crypto_type: str  # SOL, ETH, BTC
    crypto_amount: float
    tx_hash: Optional[str] = None
    status: str = "PENDING"
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# API Response Models
class StatsResponse(BaseModel):
    total_users: int
    active_wallets: int
    total_trades: int
    total_profit_usd: float
    whale_activities_today: int

class UserStatsResponse(BaseModel):
    telegram_id: int
    username: Optional[str]
    credits: float
    wallet_count: int
    trade_count: int
    total_profit: float

# Utility Functions
def create_solana_wallet():
    """Create a new Solana wallet"""
    keypair = Keypair()
    public_key = str(keypair.pubkey())
    private_key = base58.b58encode(bytes(keypair)).decode('utf-8')
    return public_key, private_key

async def get_sol_price():
    """Get current SOL price in USD"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
                timeout=10
            )
            data = response.json()
            return data.get('solana', {}).get('usd', 200)
    except Exception as e:
        logger.error(f"Error fetching SOL price: {e}")
        return 200  # Default fallback price

async def get_whale_transactions(wallet_address: str):
    """Fetch transactions from a whale wallet using Solscan API"""
    try:
        headers = {"token": SOLSCAN_API_KEY}
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"https://pro-api.solscan.io/v2.0/account/transfer",
                params={"address": wallet_address, "page_size": 20},
                headers=headers,
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return {"data": []}
    except Exception as e:
        logger.error(f"Error fetching whale transactions: {e}")
        return {"data": []}

async def get_trending_tokens():
    """Fetch trending tokens from pump.fun/dexscreener"""
    try:
        async with httpx.AsyncClient() as http_client:
            # Try DexScreener API for trending Solana tokens
            response = await http_client.get(
                "https://api.dexscreener.com/latest/dex/tokens/So11111111111111111111111111111111111111112",
                timeout=15
            )
            if response.status_code == 200:
                return response.json()
            return {"pairs": []}
    except Exception as e:
        logger.error(f"Error fetching trending tokens: {e}")
        return {"pairs": []}

# Telegram Bot Handlers
telegram_app = None
telegram_db = None  # Separate DB connection for telegram thread

def get_telegram_db():
    """Get MongoDB connection for telegram thread"""
    global telegram_db
    if telegram_db is None:
        from motor.motor_asyncio import AsyncIOMotorClient
        telegram_client = AsyncIOMotorClient(mongo_url)
        telegram_db = telegram_client[os.environ['DB_NAME']]
    return telegram_db

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    telegram_id = user.id
    username = user.username or user.first_name
    
    try:
        # Use telegram-specific db connection
        tg_db = get_telegram_db()
        
        # Check/create user in database
        existing_user = await tg_db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
        if not existing_user:
            new_user = UserModel(telegram_id=telegram_id, username=username)
            await tg_db.users.insert_one(new_user.model_dump())
    except Exception as e:
        logger.error(f"DB error in start_command: {e}")
    
    keyboard = [
        [InlineKeyboardButton("💳 Create Wallet", callback_data="create_wallet"),
         InlineKeyboardButton("💰 My Balance", callback_data="balance")],
        [InlineKeyboardButton("🐋 Whale Watch", callback_data="whale_watch"),
         InlineKeyboardButton("📊 My Trades", callback_data="my_trades")],
        [InlineKeyboardButton("💵 Buy Access (£100/day)", callback_data="buy_access"),
         InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📞 Support", callback_data="support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎖️ *SOLANA SOLDIER* 🎖️
━━━━━━━━━━━━━━━━━━━━━

Welcome, {username}! 

I'm your automated Solana arbitrage trading bot.

*Features:*
• 🐋 Track whale wallets in real-time
• ⚡ Execute trades in under 2 minutes
• 💰 Target $2 profit per trade
• 🛡️ Anti-rug protection built-in
• 📊 100+ trades per day capability

*Quick Start:*
1. Create a wallet
2. Buy daily access (£100)
3. Start earning!

Select an option below:
"""
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wallet command - show wallet info"""
    telegram_id = update.effective_user.id
    
    wallets = await db.wallets.find(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    ).to_list(10)
    
    if not wallets:
        await update.message.reply_text(
            "❌ You don't have any wallets yet.\nUse /newwallet to create one.",
            parse_mode='Markdown'
        )
        return
    
    wallet_text = "🔐 *Your Wallets:*\n\n"
    for i, w in enumerate(wallets, 1):
        wallet_text += f"*Wallet {i}:*\n`{w['public_key']}`\n💰 Balance: {w.get('balance_sol', 0):.4f} SOL\n\n"
    
    await update.message.reply_text(wallet_text, parse_mode='Markdown')

async def newwallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /newwallet command - create new wallet"""
    telegram_id = update.effective_user.id
    
    # Check user credits/subscription
    user = await db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user:
        await update.message.reply_text("❌ Please /start the bot first.")
        return
    
    # Create wallet
    public_key, private_key = create_solana_wallet()
    
    wallet = WalletModel(
        user_telegram_id=telegram_id,
        public_key=public_key,
        private_key_encrypted=private_key  # In production, encrypt this!
    )
    await db.wallets.insert_one(wallet.model_dump())
    
    # Send private key securely
    await update.message.reply_text(
        f"""
🔐 *NEW WALLET CREATED* 🔐
━━━━━━━━━━━━━━━━━━━━━

*Public Key:*
`{public_key}`

*Private Key (SAVE THIS SECURELY!):*
`{private_key}`

⚠️ *IMPORTANT:*
• Save your private key somewhere safe
• Never share it with anyone
• This message will not be shown again

💡 Fund this wallet with SOL to start trading!
""",
        parse_mode='Markdown'
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /balance command"""
    telegram_id = update.effective_user.id
    
    user = await db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    wallets = await db.wallets.find(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    ).to_list(10)
    
    if not user:
        await update.message.reply_text("❌ Please /start the bot first.")
        return
    
    total_sol = sum(w.get('balance_sol', 0) for w in wallets)
    sol_price = await get_sol_price()
    total_usd = total_sol * sol_price
    
    # Get trade stats
    trades = await db.trades.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0}
    ).to_list(1000)
    
    total_profit = sum(t.get('profit_usd', 0) for t in trades)
    
    balance_text = f"""
💰 *YOUR BALANCE* 💰
━━━━━━━━━━━━━━━━━━━━━

*Credits:* {user.get('credits', 0):.2f}
*Wallets:* {len(wallets)}
*Total SOL:* {total_sol:.4f} (~${total_usd:.2f})

*Trading Stats:*
📊 Total Trades: {len(trades)}
💵 Total Profit: ${total_profit:.2f}

*Subscription:*
{'✅ Active' if user.get('subscription_expires') else '❌ Inactive - Buy access to trade!'}
"""
    await update.message.reply_text(balance_text, parse_mode='Markdown')

async def setcredits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setcredits command (admin only)"""
    admin_id = update.effective_user.id
    admin_username = update.effective_user.username
    
    # Check if admin
    if f"@{admin_username}" != ADMIN_USERNAME and str(admin_id) != ADMIN_CHAT_ID.replace("-", ""):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # Parse command: /setcredits @username 10000
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /setcredits @username amount")
        return
    
    target_username = args[0].replace("@", "")
    try:
        amount = float(args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount.")
        return
    
    # Find and update user
    result = await db.users.update_one(
        {"username": target_username},
        {"$set": {"credits": amount}}
    )
    
    if result.modified_count > 0:
        await update.message.reply_text(f"✅ Set {amount} credits for @{target_username}")
        
        # Notify user
        user = await db.users.find_one({"username": target_username}, {"_id": 0})
        if user:
            try:
                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                await bot.send_message(
                    chat_id=user['telegram_id'],
                    text=f"🎉 *Credits Updated!*\n\nYou now have *{amount}* credits.\n\nAdmin: {ADMIN_USERNAME}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error notifying user: {e}")
    else:
        await update.message.reply_text(f"❌ User @{target_username} not found.")

async def whales_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /whales command - show tracked whales"""
    whale_text = "🐋 *TRACKED WHALE WALLETS* 🐋\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for i, wallet in enumerate(WHALE_WALLETS[:5], 1):
        whale_text += f"{i}. `{wallet[:8]}...{wallet[-8:]}`\n"
    
    whale_text += f"\n...and {len(WHALE_WALLETS) - 5} more\n\n💡 These wallets are monitored 24/7 for trading opportunities."
    
    await update.message.reply_text(whale_text, parse_mode='Markdown')

async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pay command - show payment options"""
    keyboard = [
        [InlineKeyboardButton("🟣 Pay with SOL", callback_data="pay_sol")],
        [InlineKeyboardButton("🔵 Pay with ETH", callback_data="pay_eth")],
        [InlineKeyboardButton("🟠 Pay with BTC", callback_data="pay_btc")],
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    pay_text = f"""
💳 *BUY DAILY ACCESS* 💳
━━━━━━━━━━━━━━━━━━━━━

*Price:* £100 / day

Choose your payment method:

*Benefits:*
• 🐋 Real-time whale tracking
• ⚡ Automated trading execution
• 💰 $2 profit target per trade
• 🛡️ Anti-rug protection
• 📊 100+ trades per day

Select payment option below:
"""
    await update.message.reply_text(pay_text, reply_markup=reply_markup, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    live_status = "🟢 LIVE" if LIVE_TRADING_ENABLED else "🔴 OFF"
    auto_status = "🟢 ON" if AUTO_TRADE_ON_WHALE_SIGNAL else "🔴 OFF"
    
    help_text = f"""
📖 *SOLANA SOLDIER COMMANDS* 📖
━━━━━━━━━━━━━━━━━━━━━

*Trading Status:*
Live Trading: {live_status}
Auto-Trade on Whale: {auto_status}
Min Trade: {MIN_TRADE_SOL} SOL
Default Stop-Loss: {DEFAULT_STOP_LOSS_PCT*100:.0f}%

*User Commands:*
/start - Start the bot
/wallet - View your wallets
/newwallet - Create new wallet
/balance - Check your balance
/whales - View tracked whales
/trending - See trending tokens
/rugcheck \<token\> - Check token safety
/trade \<token\> \<amount\> - Execute trade

*Auto-Trading:*
/autotrade \<sol\> \<stoploss%\> - Enable auto-trade
/stopautotrade - Disable auto-trading
/stoploss \<percent\> - Set stop-loss %
/positions - View active positions
/pnl - View P&L report
/trades - Trade history

*Other:*
/pay - Buy daily access
/status - System status
/help - Show this help

*Admin Commands:*
/setcredits @user amount - Set user credits

*Support:* Contact @memecorpofficial
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /autotrade command - enable auto trading on whale signals"""
    telegram_id = update.effective_user.id
    args = context.args
    
    # Default trade amount and stop-loss
    trade_amount = MIN_TRADE_SOL
    stop_loss_pct = DEFAULT_STOP_LOSS_PCT
    
    if args:
        try:
            trade_amount = float(args[0])
            if len(args) > 1:
                stop_loss_pct = float(args[1]) / 100  # Convert percentage to decimal
        except ValueError:
            await update.message.reply_text(f"Usage: /autotrade <sol_amount> [stop_loss_%]\nExample: /autotrade 0.05 15\n\nMin trade: {MIN_TRADE_SOL} SOL")
            return
    
    # Enforce minimum trade
    if trade_amount < MIN_TRADE_SOL:
        trade_amount = MIN_TRADE_SOL
    
    # Enforce stop-loss bounds
    if stop_loss_pct < 0.01:
        stop_loss_pct = 0.01
    elif stop_loss_pct > 0.50:
        stop_loss_pct = 0.50
    
    # Check user credits
    user = await db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user or user.get('credits', 0) <= 0:
        await update.message.reply_text("❌ You need credits to enable auto-trading. Use /pay to buy access.")
        return
    
    # Get user's wallet
    wallet = await db.wallets.find_one(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    )
    if not wallet:
        await update.message.reply_text("❌ No wallet found. Use /newwallet to create one.")
        return
    
    # Check balance
    if helius_rpc:
        balance = await helius_rpc.get_balance(wallet['public_key'])
        if balance < trade_amount + 0.01:
            await update.message.reply_text(
                f"❌ Insufficient balance for auto-trading.\nRequired: {trade_amount + 0.01:.4f} SOL\nAvailable: {balance:.4f} SOL\n\nFund your wallet:\n`{wallet['public_key']}`",
                parse_mode='Markdown'
            )
            return
    
    # Recreate keypair
    try:
        private_key = wallet.get('private_key_encrypted')
        keypair = Keypair.from_bytes(base58.b58decode(private_key))
    except Exception as e:
        await update.message.reply_text(f"❌ Error loading wallet: {str(e)[:50]}")
        return
    
    # Register for auto-trading
    active_trading_users[telegram_id] = {
        'keypair': keypair,
        'trade_amount': trade_amount,
        'stop_loss_pct': stop_loss_pct,
        'wallet_public_key': wallet['public_key'],
        'enabled_at': datetime.now(timezone.utc).isoformat()
    }
    
    await update.message.reply_text(
        f"""
🤖 *AUTO-TRADING ENABLED* 🤖
━━━━━━━━━━━━━━━━━━━━━

Your bot will now automatically trade when whales buy tokens!

*Settings:*
• Trade Amount: {trade_amount} SOL per signal
• Stop-Loss: {stop_loss_pct*100:.0f}%
• Wallet: `{wallet['public_key'][:16]}...`
• Profit Target: ${MIN_PROFIT_USD}/trade
• Max Trade Time: {MAX_TRADE_TIME_SECONDS}s

⚠️ *IMPORTANT:*
• Real SOL will be used for trades
• Stop-loss will auto-sell if loss exceeds {stop_loss_pct*100:.0f}%
• Use /stoploss to change stop-loss
• Use /stopautotrade to disable

Good luck! 🚀
""",
        parse_mode='Markdown'
    )
    
    logger.info(f"User {telegram_id} enabled auto-trading with {trade_amount} SOL, SL: {stop_loss_pct*100:.0f}%")

async def stopautotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopautotrade command - disable auto trading"""
    telegram_id = update.effective_user.id
    
    if telegram_id in active_trading_users:
        del active_trading_users[telegram_id]
        await update.message.reply_text("✅ Auto-trading disabled. You will no longer receive automatic trades.")
        logger.info(f"User {telegram_id} disabled auto-trading")
    else:
        await update.message.reply_text("ℹ️ Auto-trading was not enabled for your account.")

async def pnl_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /pnl command - show P&L report"""
    telegram_id = update.effective_user.id
    
    # Get user's trades from database
    trades = await db.trades.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    if not trades:
        await update.message.reply_text("📊 No trades found. Use /autotrade to start trading!")
        return
    
    # Calculate P&L stats
    total_pnl = sum(t.get('pnl_usd', 0) for t in trades)
    total_trades = len(trades)
    winning = sum(1 for t in trades if t.get('pnl_usd', 0) > 0)
    losing = sum(1 for t in trades if t.get('pnl_usd', 0) < 0)
    win_rate = (winning / total_trades * 100) if total_trades else 0
    
    # Recent trades
    recent = trades[:5]
    recent_text = ""
    for t in recent:
        pnl = t.get('pnl_usd', 0)
        emoji = "🟢" if pnl >= 0 else "🔴"
        recent_text += f"{emoji} {t.get('token_address', '')[:8]}... ${pnl:+.2f}\n"
    
    pnl_emoji = "💰" if total_pnl >= 0 else "📉"
    
    await update.message.reply_text(
        f"""
{pnl_emoji} *P&L REPORT* {pnl_emoji}
━━━━━━━━━━━━━━━━━━━━━

*Total P&L:* {'+' if total_pnl >= 0 else ''}${total_pnl:.2f}
*Total Trades:* {total_trades}
*Winning:* {winning} 🟢
*Losing:* {losing} 🔴
*Win Rate:* {win_rate:.0f}%

*Recent Trades:*
{recent_text}

Use /trades for full history.
""",
        parse_mode='Markdown'
    )

async def stoploss_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stoploss command - set stop loss percentage"""
    telegram_id = update.effective_user.id
    args = context.args
    
    if not args:
        current_sl = active_trading_users.get(telegram_id, {}).get('stop_loss_pct', DEFAULT_STOP_LOSS_PCT)
        await update.message.reply_text(
            f"*Current Stop-Loss:* {current_sl*100:.0f}%\n\nUsage: /stoploss <percentage>\nExample: /stoploss 10 (for 10% stop-loss)",
            parse_mode='Markdown'
        )
        return
    
    try:
        stop_loss_pct = float(args[0]) / 100  # Convert percentage to decimal
        if stop_loss_pct < 0.01 or stop_loss_pct > 0.50:
            await update.message.reply_text("❌ Stop-loss must be between 1% and 50%")
            return
    except ValueError:
        await update.message.reply_text("❌ Invalid percentage. Use a number like 10 or 15")
        return
    
    if telegram_id in active_trading_users:
        active_trading_users[telegram_id]['stop_loss_pct'] = stop_loss_pct
        await update.message.reply_text(
            f"✅ Stop-loss updated to *{stop_loss_pct*100:.0f}%*\n\nYour positions will auto-sell if value drops by this amount.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Auto-trading not enabled. Use /autotrade first, then set stop-loss.")

async def trades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trades command - show trade history"""
    telegram_id = update.effective_user.id
    
    trades = await db.trades.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    if not trades:
        await update.message.reply_text("📊 No trades found.")
        return
    
    text = "📊 *TRADE HISTORY* 📊\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for t in trades[:10]:
        status = t.get('status', 'UNKNOWN')
        pnl = t.get('pnl_usd', 0)
        pnl_pct = t.get('pnl_pct', 0)
        
        if status == "CLOSED":
            emoji = "🟢" if pnl >= 0 else "🔴"
            text += f"{emoji} `{t.get('token_address', '')[:8]}...`\n"
            text += f"   Entry: ${t.get('entry_value_usd', 0):.2f} → Exit: ${t.get('exit_value_usd', 0):.2f}\n"
            text += f"   P&L: {'+' if pnl >= 0 else ''}${pnl:.2f} ({pnl_pct:+.1f}%)\n\n"
        elif status == "OPEN":
            text += f"🟡 `{t.get('token_address', '')[:8]}...` (OPEN)\n"
            text += f"   Entry: ${t.get('entry_value_usd', 0):.2f}\n\n"
        else:
            text += f"⚪ `{t.get('token_address', '')[:8]}...` ({status})\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command - show system status"""
    telegram_id = update.effective_user.id
    
    # Check if user is admin
    admin_username = update.effective_user.username
    is_admin = f"@{admin_username}" == ADMIN_USERNAME
    
    user_auto_enabled = telegram_id in active_trading_users
    user_trade_amount = active_trading_users.get(telegram_id, {}).get('trade_amount', 0)
    
    status_text = f"""
📊 *SYSTEM STATUS* 📊
━━━━━━━━━━━━━━━━━━━━━

*Trading Engine:*
• Live Trading: {'🟢 ENABLED' if LIVE_TRADING_ENABLED else '🔴 DISABLED'}
• Auto-Trade on Whale: {'🟢 ON' if AUTO_TRADE_ON_WHALE_SIGNAL else '🔴 OFF'}
• Helius RPC: {'🟢 Connected' if helius_rpc else '🔴 Not Connected'}
• Jupiter DEX: {'🟢 Ready' if jupiter_dex else '🔴 Not Ready'}

*Your Settings:*
• Auto-Trading: {'🟢 ENABLED (' + str(user_trade_amount) + ' SOL)' if user_auto_enabled else '🔴 DISABLED'}

*Active Users:* {len(active_trading_users)}
*Tracked Whales:* {len(WHALE_WALLETS)}
"""
    
    if is_admin:
        status_text += f"""
*Admin Info:*
• Active Trading Users: {len(active_trading_users)}
• Users: {[uid for uid in active_trading_users.keys()]}
"""
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def trending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trending command - show trending tokens"""
    await update.message.reply_text("🔍 Scanning for trending tokens...")
    
    try:
        if trending_scanner:
            tokens = await trending_scanner.get_trending_tokens()
            
            if tokens:
                text = "🔥 *TRENDING TOKENS* 🔥\n━━━━━━━━━━━━━━━━━━━━━\n\n"
                for i, t in enumerate(tokens[:10], 1):
                    price_change = t.get('price_change_24h', 0)
                    emoji = "🟢" if price_change > 0 else "🔴"
                    text += f"{i}. *{t['symbol']}* {emoji}\n"
                    text += f"   💲 ${t['price_usd']:.6f}\n"
                    text += f"   📈 {price_change:+.2f}%\n"
                    text += f"   💧 ${t['liquidity_usd']:,.0f}\n\n"
                
                text += "_Use /rugcheck <address> to check safety_"
                await update.message.reply_text(text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ No trending tokens found")
        else:
            await update.message.reply_text("❌ Trending scanner not initialized")
    except Exception as e:
        logger.error(f"Trending command error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)[:100]}")

async def rugcheck_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /rugcheck command - check token safety"""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /rugcheck <token_address>")
        return
    
    token_address = args[0]
    await update.message.reply_text(f"🔍 Checking token safety...\n`{token_address[:20]}...`", parse_mode='Markdown')
    
    try:
        if rug_detector:
            result = await rug_detector.check_token(token_address)
            
            safety_emoji = "✅" if result.is_safe else "⚠️"
            risk_bar = "🟢" * int((1 - result.risk_score) * 5) + "🔴" * int(result.risk_score * 5)
            
            text = f"""
{safety_emoji} *RUG CHECK RESULT* {safety_emoji}
━━━━━━━━━━━━━━━━━━━━━

*Token:* `{token_address[:20]}...`
*Status:* {'SAFE' if result.is_safe else 'RISKY'}
*Risk Score:* {result.risk_score:.0%} {risk_bar}

"""
            if result.warnings:
                text += "*⚠️ Warnings:*\n"
                for w in result.warnings[:5]:
                    text += f"• {w}\n"
            
            details = result.details
            if details:
                text += f"\n*📊 Details:*\n"
                if 'liquidity_usd' in details:
                    text += f"• Liquidity: ${details['liquidity_usd']:,.2f}\n"
                if 'holder_count' in details:
                    text += f"• Holders: {details['holder_count']}\n"
                if 'creator_holdings_pct' in details:
                    text += f"• Creator Holdings: {details['creator_holdings_pct']*100:.1f}%\n"
                if 'age_hours' in details:
                    text += f"• Age: {details['age_hours']:.1f} hours\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ Rug detector not initialized")
    except Exception as e:
        logger.error(f"Rugcheck error: {e}")
        await update.message.reply_text(f"❌ Error checking token: {str(e)[:100]}")

async def trade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /trade command - execute a trade"""
    telegram_id = update.effective_user.id
    args = context.args
    
    if len(args) < 2:
        await update.message.reply_text("Usage: /trade <token_address> <amount_sol>")
        return
    
    token_address = args[0]
    try:
        amount_sol = float(args[1])
    except ValueError:
        await update.message.reply_text("❌ Invalid amount")
        return
    
    # Check user subscription/credits
    user = await db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user or user.get('credits', 0) <= 0:
        await update.message.reply_text("❌ You need credits to trade. Use /pay to buy access.")
        return
    
    # Get user's wallet
    wallet = await db.wallets.find_one(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    )
    if not wallet:
        await update.message.reply_text("❌ No wallet found. Use /newwallet to create one.")
        return
    
    await update.message.reply_text(f"⏳ Processing trade...\n\nToken: `{token_address[:20]}...`\nAmount: {amount_sol} SOL", parse_mode='Markdown')
    
    try:
        # First, rug check
        if rug_detector:
            rug_result = await rug_detector.check_token(token_address)
            if not rug_result.is_safe:
                warnings_text = "\n".join(f"• {w}" for w in rug_result.warnings[:3])
                await update.message.reply_text(
                    f"⚠️ *TRADE BLOCKED - RUG RISK*\n\nRisk Score: {rug_result.risk_score:.0%}\n\n{warnings_text}",
                    parse_mode='Markdown'
                )
                return
        
        # Check if live trading is enabled
        if LIVE_TRADING_ENABLED and jupiter_dex and helius_rpc:
            # Get user's private key from wallet
            private_key = wallet.get('private_key_encrypted')
            if not private_key:
                await update.message.reply_text("❌ Wallet private key not found. Create a new wallet.")
                return
            
            # Recreate keypair
            keypair = Keypair.from_bytes(base58.b58decode(private_key))
            
            # Check balance via Helius
            balance = await helius_rpc.get_balance(wallet['public_key'])
            if balance < amount_sol + 0.01:  # Need extra for gas
                await update.message.reply_text(
                    f"❌ Insufficient balance.\nRequired: {amount_sol + 0.01:.4f} SOL\nAvailable: {balance:.4f} SOL\n\nFund your wallet: `{wallet['public_key']}`",
                    parse_mode='Markdown'
                )
                return
            
            # Execute LIVE trade
            await update.message.reply_text("🚀 *Executing LIVE trade...*", parse_mode='Markdown')
            
            amount_lamports = int(amount_sol * LAMPORTS_PER_SOL)
            result = await jupiter_dex.execute_swap(
                keypair=keypair,
                input_mint=WSOL_MINT,
                output_mint=token_address,
                amount_lamports=amount_lamports
            )
            
            if result.success:
                # Record successful trade
                trade_record = TradeModel(
                    user_telegram_id=telegram_id,
                    wallet_public_key=wallet['public_key'],
                    token_address=token_address,
                    trade_type="BUY",
                    amount_sol=amount_sol,
                    status="COMPLETED"
                )
                await db.trades.insert_one(trade_record.model_dump())
                
                await update.message.reply_text(
                    f"""
✅ *LIVE TRADE EXECUTED* ✅
━━━━━━━━━━━━━━━━━━━━━

*Signature:* `{result.signature[:20]}...`
*Token:* `{token_address[:16]}...`
*Amount:* {amount_sol} SOL
*Status:* COMPLETED

[View on Solscan](https://solscan.io/tx/{result.signature})
""",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"❌ Trade failed: {result.error}")
        else:
            # Simulated trade (live trading disabled)
            trade_record = TradeModel(
                user_telegram_id=telegram_id,
                wallet_public_key=wallet['public_key'],
                token_address=token_address,
                trade_type="BUY",
                amount_sol=amount_sol,
                status="SIMULATED"
            )
            await db.trades.insert_one(trade_record.model_dump())
            
            await update.message.reply_text(
                f"""
✅ *TRADE SIMULATED* ✅
━━━━━━━━━━━━━━━━━━━━━

*Trade ID:* `{trade_record.id[:8]}...`
*Token:* `{token_address[:16]}...`
*Amount:* {amount_sol} SOL
*Status:* SIMULATED

⚠️ Live trading: {'ENABLED' if LIVE_TRADING_ENABLED else 'DISABLED'}
Fund wallet to enable live trades.
""",
                parse_mode='Markdown'
            )
        
        # Deduct credits
        await db.users.update_one(
            {"telegram_id": telegram_id},
            {"$inc": {"credits": -1}}
        )
        
    except Exception as e:
        logger.error(f"Trade error: {e}")
        await update.message.reply_text(f"❌ Trade failed: {str(e)[:100]}")

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /positions command - show active positions"""
    telegram_id = update.effective_user.id
    
    trades = await db.trades.find(
        {"user_telegram_id": telegram_id, "status": {"$in": ["PENDING", "ACTIVE", "SIMULATED"]}},
        {"_id": 0}
    ).to_list(20)
    
    if not trades:
        await update.message.reply_text("📊 No active positions.\n\nUse /trade <token> <amount> to open one.")
        return
    
    text = "📊 *ACTIVE POSITIONS* 📊\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    for t in trades:
        text += f"*{t['trade_type']}* `{t['token_address'][:12]}...`\n"
        text += f"  Amount: {t['amount_sol']:.4f} SOL\n"
        text += f"  Status: {t['status']}\n"
        text += f"  Time: {t['created_at'][:16]}\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def whale_activity_callback(activity: Dict):
    """Callback when whale activity is detected - triggers auto trades"""
    logger.info(f"🐋 Whale activity detected: {activity}")
    
    # Store in database
    whale_activity = WhaleActivityModel(
        whale_address=activity['whale_address'],
        token_address=activity.get('token_address', ''),
        token_symbol=activity.get('token_symbol', 'UNKNOWN'),
        action=activity.get('action', 'UNKNOWN'),
        amount=activity.get('amount', 0),
        detected_at=datetime.now(timezone.utc).isoformat()
    )
    await db.whale_activities.insert_one(whale_activity.model_dump())
    
    # Notify admin chat
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        text = f"""
🐋 *WHALE ALERT* 🐋

*Wallet:* `{activity['whale_address'][:12]}...`
*Action:* {activity.get('action', 'UNKNOWN')}
*Token:* {activity.get('token_symbol', 'UNKNOWN')}
*Amount:* {activity.get('amount', 0):.4f}

[View on Solscan](https://solscan.io/tx/{activity.get('signature', '')})
"""
        await bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=text,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to notify whale activity: {e}")
    
    # AUTO-TRADE: Execute trades for all active trading users
    if AUTO_TRADE_ON_WHALE_SIGNAL and activity.get('action') == 'BUY':
        logger.info(f"🚀 Auto-trade triggered for {len(active_trading_users)} users")
        
        for telegram_id, user_data in active_trading_users.items():
            try:
                keypair = user_data.get('keypair')
                trade_amount = user_data.get('trade_amount', MIN_TRADE_SOL)
                stop_loss_pct = user_data.get('stop_loss_pct', DEFAULT_STOP_LOSS_PCT)
                
                if keypair and auto_trader:
                    # Execute auto trade with stop-loss
                    result = await auto_trader.process_whale_signal(
                        activity=activity,
                        user_keypair=keypair,
                        user_telegram_id=telegram_id,
                        trade_amount_sol=trade_amount,
                        stop_loss_pct=stop_loss_pct
                    )
                    
                    if result and result.success:
                        logger.info(f"✅ Auto-trade successful for user {telegram_id}")
                    
            except Exception as e:
                logger.error(f"Auto-trade error for user {telegram_id}: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    telegram_id = query.from_user.id
    
    if data == "create_wallet":
        public_key, private_key = create_solana_wallet()
        wallet = WalletModel(
            user_telegram_id=telegram_id,
            public_key=public_key,
            private_key_encrypted=private_key
        )
        await db.wallets.insert_one(wallet.model_dump())
        
        await query.edit_message_text(
            f"""
🔐 *WALLET CREATED!* 🔐

*Public Key:*
`{public_key}`

*Private Key:*
`{private_key}`

⚠️ Save your private key securely!
""",
            parse_mode='Markdown'
        )
    
    elif data == "balance":
        user = await db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
        wallets = await db.wallets.find(
            {"user_telegram_id": telegram_id, "is_active": True},
            {"_id": 0}
        ).to_list(10)
        
        total_sol = sum(w.get('balance_sol', 0) for w in wallets)
        credits = user.get('credits', 0) if user else 0
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
        
        await query.edit_message_text(
            f"""
💰 *YOUR BALANCE* 💰

*Credits:* {credits:.2f}
*Wallets:* {len(wallets)}
*Total SOL:* {total_sol:.4f}
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "whale_watch":
        whale_text = "🐋 *WHALE WATCH* 🐋\n\n"
        for wallet in WHALE_WALLETS[:5]:
            whale_text += f"• `{wallet[:12]}...`\n"
        whale_text += f"\n+{len(WHALE_WALLETS)-5} more wallets tracked"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
        await query.edit_message_text(
            whale_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "my_trades":
        trades = await db.trades.find(
            {"user_telegram_id": telegram_id},
            {"_id": 0}
        ).to_list(10)
        
        if trades:
            trade_text = "📊 *RECENT TRADES* 📊\n\n"
            for t in trades[:5]:
                trade_text += f"• {t['trade_type']} {t.get('amount_sol', 0):.4f} SOL - {t['status']}\n"
        else:
            trade_text = "📊 *TRADES* 📊\n\nNo trades yet. Buy access to start trading!"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
        await query.edit_message_text(
            trade_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "buy_access":
        keyboard = [
            [InlineKeyboardButton("🟣 SOL", callback_data="pay_sol"),
             InlineKeyboardButton("🔵 ETH", callback_data="pay_eth"),
             InlineKeyboardButton("🟠 BTC", callback_data="pay_btc")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ]
        await query.edit_message_text(
            f"""
💳 *BUY ACCESS - £100/day* 💳

Choose payment method:
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "pay_sol":
        keyboard = [[InlineKeyboardButton("✅ I've Paid", callback_data="confirm_payment_sol"),
                     InlineKeyboardButton("🔙 Back", callback_data="buy_access")]]
        await query.edit_message_text(
            f"""
🟣 *PAY WITH SOL* 🟣

Send £100 worth of SOL to:
`{PAYMENT_SOL_ADDRESS}`

After payment, click "I've Paid" and our admin will verify within 24h.

*Admin Contact:* {ADMIN_USERNAME}
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "pay_eth":
        keyboard = [[InlineKeyboardButton("✅ I've Paid", callback_data="confirm_payment_eth"),
                     InlineKeyboardButton("🔙 Back", callback_data="buy_access")]]
        await query.edit_message_text(
            f"""
🔵 *PAY WITH ETH* 🔵

Send £100 worth of ETH to:
`{PAYMENT_ETH_ADDRESS}`

After payment, click "I've Paid".

*Admin Contact:* {ADMIN_USERNAME}
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "pay_btc":
        keyboard = [[InlineKeyboardButton("✅ I've Paid", callback_data="confirm_payment_btc"),
                     InlineKeyboardButton("🔙 Back", callback_data="buy_access")]]
        await query.edit_message_text(
            f"""
🟠 *PAY WITH BTC* 🟠

Send £100 worth of BTC to:
`{PAYMENT_BTC_ADDRESS}`

After payment, click "I've Paid".

*Admin Contact:* {ADMIN_USERNAME}
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith("confirm_payment_"):
        crypto_type = data.replace("confirm_payment_", "").upper()
        username = query.from_user.username or query.from_user.first_name
        
        # Save payment request
        payment = PaymentModel(
            user_telegram_id=telegram_id,
            amount_gbp=100,
            crypto_type=crypto_type,
            crypto_amount=0,
            status="PENDING_VERIFICATION"
        )
        await db.payments.insert_one(payment.model_dump())
        
        # Notify admin
        try:
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            await bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"""
🔔 *NEW PAYMENT REQUEST* 🔔

User: @{username} (ID: {telegram_id})
Amount: £100
Crypto: {crypto_type}

Please verify and use:
/setcredits @{username} 10000
""",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error notifying admin: {e}")
        
        await query.edit_message_text(
            f"""
✅ *PAYMENT SUBMITTED* ✅

Your payment request has been sent to admin for verification.

*Transaction ID:* {payment.id[:8]}...
*Status:* Pending Verification

You'll receive a notification once verified.

*Admin Contact:* {ADMIN_USERNAME}
""",
            parse_mode='Markdown'
        )
    
    elif data == "settings":
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete Wallet", callback_data="delete_wallet")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
        ]
        await query.edit_message_text(
            "⚙️ *SETTINGS* ⚙️\n\nManage your account:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "delete_wallet":
        # Deactivate user's wallets
        await db.wallets.update_many(
            {"user_telegram_id": telegram_id},
            {"$set": {"is_active": False}}
        )
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
        await query.edit_message_text(
            "✅ All wallets deleted. Use /newwallet to create a fresh one.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "support":
        await query.edit_message_text(
            f"""
📞 *SUPPORT* 📞

Contact our admin for any issues:
{ADMIN_USERNAME}

Or send a message here and we'll respond ASAP!
""",
            parse_mode='Markdown'
        )
    
    elif data == "back_main":
        keyboard = [
            [InlineKeyboardButton("💳 Create Wallet", callback_data="create_wallet"),
             InlineKeyboardButton("💰 My Balance", callback_data="balance")],
            [InlineKeyboardButton("🐋 Whale Watch", callback_data="whale_watch"),
             InlineKeyboardButton("📊 My Trades", callback_data="my_trades")],
            [InlineKeyboardButton("💵 Buy Access (£100/day)", callback_data="buy_access"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        ]
        await query.edit_message_text(
            "🎖️ *SOLANA SOLDIER* 🎖️\n\nSelect an option:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )

# API Endpoints
@api_router.get("/")
async def root():
    return {"message": "Solana Soldier API", "status": "online"}

@api_router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get overall bot statistics"""
    total_users = await db.users.count_documents({})
    active_wallets = await db.wallets.count_documents({"is_active": True})
    total_trades = await db.trades.count_documents({})
    
    trades = await db.trades.find({}, {"_id": 0, "profit_usd": 1}).to_list(10000)
    total_profit = sum(t.get('profit_usd', 0) for t in trades)
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    whale_today = await db.whale_activities.count_documents({
        "detected_at": {"$gte": today.isoformat()}
    })
    
    return StatsResponse(
        total_users=total_users,
        active_wallets=active_wallets,
        total_trades=total_trades,
        total_profit_usd=total_profit,
        whale_activities_today=whale_today
    )

@api_router.get("/users")
async def get_users():
    """Get all users"""
    users = await db.users.find({}, {"_id": 0}).to_list(1000)
    return {"users": users}

@api_router.get("/users/{telegram_id}")
async def get_user(telegram_id: int):
    """Get specific user"""
    user = await db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    wallets = await db.wallets.find(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    trades = await db.trades.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0}
    ).to_list(1000)
    
    return {
        "user": user,
        "wallets": wallets,
        "trades": trades,
        "total_profit": sum(t.get('profit_usd', 0) for t in trades)
    }

@api_router.get("/whales")
async def get_whales():
    """Get tracked whale wallets"""
    return {"whales": WHALE_WALLETS}

@api_router.get("/whale-activities")
async def get_whale_activities():
    """Get recent whale activities"""
    activities = await db.whale_activities.find(
        {},
        {"_id": 0}
    ).sort("detected_at", -1).to_list(100)
    return {"activities": activities}

@api_router.get("/trades")
async def get_trades():
    """Get all trades"""
    trades = await db.trades.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"trades": trades}

@api_router.get("/payments")
async def get_payments():
    """Get all payments"""
    payments = await db.payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"payments": payments}

@api_router.get("/sol-price")
async def get_sol_price_endpoint():
    """Get current SOL price"""
    price = await get_sol_price()
    return {"price_usd": price}

@api_router.post("/whale-activities")
async def create_whale_activity(activity: WhaleActivityModel):
    """Record a whale activity"""
    await db.whale_activities.insert_one(activity.model_dump())
    return {"status": "created", "id": activity.id}

class SetCreditsRequest(BaseModel):
    telegram_id: int
    credits: float

@api_router.post("/admin/set-credits")
async def admin_set_credits(request: SetCreditsRequest):
    """Admin endpoint to set user credits"""
    result = await db.users.update_one(
        {"telegram_id": request.telegram_id},
        {"$set": {"credits": request.credits}}
    )
    if result.modified_count > 0:
        return {"status": "success", "credits": request.credits}
    raise HTTPException(status_code=404, detail="User not found")

@api_router.get("/trending-tokens")
async def get_trending_tokens_endpoint():
    """Get trending Solana tokens"""
    if trending_scanner:
        tokens = await trending_scanner.get_trending_tokens()
        return {"tokens": tokens}
    return {"tokens": []}

@api_router.get("/new-pairs")
async def get_new_pairs_endpoint():
    """Get newly created Solana pairs"""
    if trending_scanner:
        pairs = await trending_scanner.get_new_pairs()
        return {"pairs": pairs}
    return {"pairs": []}

@api_router.post("/rugcheck/{token_address}")
async def rugcheck_endpoint(token_address: str):
    """Check if a token is safe to trade"""
    if not rug_detector:
        raise HTTPException(status_code=503, detail="Rug detector not initialized")
    
    result = await rug_detector.check_token(token_address)
    return {
        "token_address": token_address,
        "is_safe": result.is_safe,
        "risk_score": result.risk_score,
        "warnings": result.warnings,
        "details": result.details
    }

@api_router.get("/active-positions")
async def get_active_positions():
    """Get all active trading positions"""
    if auto_trader:
        positions = await auto_trader.get_active_positions()
        return {"positions": positions}
    return {"positions": []}

class ExecuteTradeRequest(BaseModel):
    user_telegram_id: int
    token_address: str
    amount_sol: float
    trade_type: str = "BUY"

@api_router.post("/execute-trade")
async def execute_trade_endpoint(request: ExecuteTradeRequest):
    """Execute a trade (admin/API use)"""
    # Get user's wallet
    wallet = await db.wallets.find_one(
        {"user_telegram_id": request.user_telegram_id, "is_active": True},
        {"_id": 0}
    )
    if not wallet:
        raise HTTPException(status_code=404, detail="No wallet found for user")
    
    # Create trade record
    trade = TradeModel(
        user_telegram_id=request.user_telegram_id,
        wallet_public_key=wallet['public_key'],
        token_address=request.token_address,
        trade_type=request.trade_type,
        amount_sol=request.amount_sol,
        status="QUEUED"
    )
    await db.trades.insert_one(trade.model_dump())
    
    return {"status": "queued", "trade_id": trade.id}

@api_router.get("/trading-stats")
async def get_trading_stats():
    """Get trading statistics"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_trades = await db.trades.count_documents({})
    trades_today = await db.trades.count_documents({"created_at": {"$gte": today.isoformat()}})
    
    all_trades = await db.trades.find({}, {"_id": 0, "profit_usd": 1, "status": 1}).to_list(10000)
    total_profit = sum(t.get('profit_usd', 0) for t in all_trades)
    completed = sum(1 for t in all_trades if t.get('status') == 'COMPLETED')
    failed = sum(1 for t in all_trades if t.get('status') == 'FAILED')
    
    whale_activities_today = await db.whale_activities.count_documents({
        "detected_at": {"$gte": today.isoformat()}
    })
    
    return {
        "total_trades": total_trades,
        "trades_today": trades_today,
        "total_profit_usd": total_profit,
        "completed_trades": completed,
        "failed_trades": failed,
        "success_rate": (completed / total_trades * 100) if total_trades > 0 else 0,
        "whale_activities_today": whale_activities_today,
        "min_profit_target": MIN_PROFIT_USD,
        "max_trade_time_seconds": MAX_TRADE_TIME_SECONDS,
        "live_trading_enabled": LIVE_TRADING_ENABLED,
        "auto_trade_enabled": AUTO_TRADE_ON_WHALE_SIGNAL,
        "active_auto_traders": len(active_trading_users),
        "tracked_whales": len(WHALE_WALLETS)
    }

@api_router.get("/system-status")
async def get_system_status():
    """Get overall system status"""
    return {
        "status": "online",
        "live_trading_enabled": LIVE_TRADING_ENABLED,
        "auto_trade_on_whale_signal": AUTO_TRADE_ON_WHALE_SIGNAL,
        "helius_rpc_connected": helius_rpc is not None,
        "jupiter_dex_ready": jupiter_dex is not None,
        "whale_monitor_active": whale_monitor is not None,
        "active_trading_users": len(active_trading_users),
        "tracked_whale_wallets": len(WHALE_WALLETS),
        "min_profit_target_usd": MIN_PROFIT_USD,
        "min_trade_sol": MIN_TRADE_SOL,
        "max_trade_sol": MAX_TRADE_SOL,
        "max_trade_time_seconds": MAX_TRADE_TIME_SECONDS
    }

@api_router.get("/wallet-balance/{address}")
async def get_wallet_balance(address: str):
    """Get wallet SOL balance via Helius"""
    if not helius_rpc:
        raise HTTPException(status_code=503, detail="Helius RPC not initialized")
    
    balance = await helius_rpc.get_balance(address)
    return {"address": address, "balance_sol": balance}

@api_router.get("/pnl-stats")
async def get_pnl_stats():
    """Get overall P&L statistics"""
    if auto_trader:
        stats = await auto_trader.get_pnl_stats()
        return stats
    return {
        "total_pnl_usd": 0,
        "total_trades": 0,
        "winning_trades": 0,
        "losing_trades": 0,
        "win_rate": 0,
        "active_positions": 0
    }

@api_router.get("/user-pnl/{telegram_id}")
async def get_user_pnl(telegram_id: int):
    """Get P&L for a specific user"""
    trades = await db.trades.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0}
    ).to_list(1000)
    
    total_pnl = sum(t.get('pnl_usd', 0) for t in trades)
    total_trades = len(trades)
    winning = sum(1 for t in trades if t.get('pnl_usd', 0) > 0)
    losing = sum(1 for t in trades if t.get('pnl_usd', 0) < 0)
    
    return {
        "telegram_id": telegram_id,
        "total_pnl_usd": total_pnl,
        "total_trades": total_trades,
        "winning_trades": winning,
        "losing_trades": losing,
        "win_rate": (winning / total_trades * 100) if total_trades else 0
    }

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Telegram Bot Runner
def run_telegram_bot():
    """Run telegram bot in a separate thread"""
    async def main():
        global telegram_app
        telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CommandHandler("wallet", wallet_command))
        telegram_app.add_handler(CommandHandler("newwallet", newwallet_command))
        telegram_app.add_handler(CommandHandler("balance", balance_command))
        telegram_app.add_handler(CommandHandler("setcredits", setcredits_command))
        telegram_app.add_handler(CommandHandler("whales", whales_command))
        telegram_app.add_handler(CommandHandler("pay", pay_command))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("trending", trending_command))
        telegram_app.add_handler(CommandHandler("rugcheck", rugcheck_command))
        telegram_app.add_handler(CommandHandler("trade", trade_command))
        telegram_app.add_handler(CommandHandler("positions", positions_command))
        telegram_app.add_handler(CommandHandler("autotrade", autotrade_command))
        telegram_app.add_handler(CommandHandler("stopautotrade", stopautotrade_command))
        telegram_app.add_handler(CommandHandler("stoploss", stoploss_command))
        telegram_app.add_handler(CommandHandler("pnl", pnl_command))
        telegram_app.add_handler(CommandHandler("trades", trades_command))
        telegram_app.add_handler(CommandHandler("status", status_command))
        telegram_app.add_handler(CallbackQueryHandler(button_callback))
        
        logger.info("Starting Telegram bot...")
        await telegram_app.initialize()
        await telegram_app.start()
        await telegram_app.updater.start_polling(drop_pending_updates=True)
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())

async def telegram_notify_user(telegram_id: int, message: str):
    """Send notification to a user via Telegram"""
    try:
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Failed to notify user {telegram_id}: {e}")

async def start_whale_monitor():
    """Start whale monitoring in background using WebSocket"""
    global whale_monitor
    if whale_monitor:
        await whale_monitor.start()

@app.on_event("startup")
async def startup_event():
    """Start telegram bot and trading components on app startup"""
    global jupiter_dex, rug_detector, whale_monitor, auto_trader, trending_scanner, helius_rpc, whale_monitor_task
    
    logger.info("=" * 50)
    logger.info("🎖️ SOLANA SOLDIER API STARTING 🎖️")
    logger.info("=" * 50)
    
    # Initialize Helius RPC
    helius_rpc = HeliusRPC(HELIUS_API_KEY)
    logger.info(f"✅ Helius RPC initialized (API key: {HELIUS_API_KEY[:8]}...)")
    
    # Initialize trading components
    jupiter_dex = JupiterDEX(helius_rpc)
    rug_detector = RugDetector(SOLSCAN_API_KEY, helius_rpc)
    trending_scanner = TrendingTokenScanner()
    
    logger.info("✅ Jupiter DEX initialized")
    logger.info("✅ Rug Detector initialized")
    logger.info("✅ Trending Scanner initialized")
    
    # Initialize whale monitor with WebSocket
    whale_monitor = WhaleMonitorWebSocket(
        whale_wallets=WHALE_WALLETS,
        helius_api_key=HELIUS_API_KEY,
        on_whale_activity=whale_activity_callback,
        helius_rpc=helius_rpc
    )
    
    # Initialize auto trader
    auto_trader = LiveAutoTrader(
        jupiter=jupiter_dex,
        rug_detector=rug_detector,
        helius_rpc=helius_rpc,
        db=db,
        telegram_notify=telegram_notify_user,
        min_profit_usd=MIN_PROFIT_USD,
        max_trade_sol=MAX_TRADE_SOL
    )
    
    logger.info("✅ Auto Trader initialized")
    logger.info(f"   - Live Trading: {'ENABLED' if LIVE_TRADING_ENABLED else 'DISABLED'}")
    logger.info(f"   - Auto-Trade on Whale: {'ENABLED' if AUTO_TRADE_ON_WHALE_SIGNAL else 'DISABLED'}")
    logger.info(f"   - Min Profit Target: ${MIN_PROFIT_USD}")
    logger.info(f"   - Max Trade: {MAX_TRADE_SOL} SOL")
    
    # Start whale monitor in background
    whale_monitor_task = asyncio.create_task(start_whale_monitor())
    logger.info(f"✅ Whale Monitor started (tracking {len(WHALE_WALLETS)} wallets)")
    
    # Start telegram bot in background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    logger.info("✅ Telegram bot thread started")
    
    logger.info("=" * 50)
    logger.info("🚀 SOLANA SOLDIER READY FOR ACTION! 🚀")
    logger.info("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global telegram_app, jupiter_dex, rug_detector, whale_monitor, trending_scanner, helius_rpc, whale_monitor_task
    
    logger.info("Shutting down Solana Soldier...")
    
    # Stop whale monitor
    if whale_monitor:
        await whale_monitor.close()
    
    if whale_monitor_task:
        whale_monitor_task.cancel()
    
    # Close trading components
    if jupiter_dex:
        await jupiter_dex.close()
    if rug_detector:
        await rug_detector.close()
    if trending_scanner:
        await trending_scanner.close()
    if helius_rpc:
        await helius_rpc.close()
    
    if telegram_app:
        await telegram_app.stop()
    
    client.close()
    logger.info("Shutdown complete")
