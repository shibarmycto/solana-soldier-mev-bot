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
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, ConversationHandler, MessageHandler, filters
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

# Import new modules
from faucet_miner import SolanaSoldiersArmy, CRYPTO_FAUCETS
from nft_aggregator import NFTAggregator

# Conversation states for multi-step interactions
SELECTING_TRADE_AMOUNT, CONFIRMING_TRADE = range(2)

# Trade amount options (in USD)
TRADE_AMOUNTS = [2, 5, 10, 25, 50, 100, 250, 500]

# Cost for deploying Solana Soldiers (in credits)
SOLDIERS_COST = 50

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

# New systems
soldiers_army: Optional[SolanaSoldiersArmy] = None
nft_aggregator: Optional[NFTAggregator] = None

# Store active trading users (telegram_id -> keypair)
active_trading_users: Dict[int, Dict] = {}

# Store user trade settings (telegram_id -> {profit_target, trade_amount_usd, stop_loss_pct})
user_trade_settings: Dict[int, Dict] = {}

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

class UserTrackedWalletModel(BaseModel):
    """Wallets that users add to track"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_telegram_id: int
    wallet_address: str
    label: Optional[str] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

# Admin usernames who get free access
ADMIN_USERNAMES = [
    "memecorpofficial",
    # Add more admin usernames here
]

def is_admin_user(username: str) -> bool:
    """Check if user is an admin"""
    if not username:
        return False
    return username.lower() in [a.lower() for a in ADMIN_USERNAMES]

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

# Dynamic API keys storage (can be updated by admin)
api_keys_config = {
    "solscan": SOLSCAN_API_KEY,
    "helius": HELIUS_API_KEY
}

async def get_whale_transactions(wallet_address: str):
    """Fetch transactions from a whale wallet using Solscan API with fallback"""
    # Try Solscan Pro API first
    solscan_key = api_keys_config.get("solscan", SOLSCAN_API_KEY)
    
    if solscan_key:
        try:
            # Correct header format: Authorization: API_KEY
            headers = {"Authorization": solscan_key}
            async with httpx.AsyncClient() as http_client:
                response = await http_client.get(
                    f"https://pro-api.solscan.io/v2.0/account/transfer",
                    params={"address": wallet_address, "page_size": 20},
                    headers=headers,
                    timeout=15
                )
                if response.status_code == 200:
                    logger.info(f"Solscan API success for {wallet_address[:8]}...")
                    return response.json()
                elif response.status_code == 401:
                    logger.warning(f"Solscan API 401 Unauthorized - check API key")
                else:
                    logger.warning(f"Solscan API returned {response.status_code}")
        except Exception as e:
            logger.error(f"Solscan API error: {e}")
    
    # Fallback to Helius for transaction data
    helius_key = api_keys_config.get("helius", HELIUS_API_KEY)
    if helius_key:
        try:
            async with httpx.AsyncClient() as http_client:
                response = await http_client.post(
                    f"https://api.helius.xyz/v0/addresses/{wallet_address}/transactions",
                    params={"api-key": helius_key},
                    json={"limit": 20},
                    timeout=15
                )
                if response.status_code == 200:
                    logger.info(f"Helius fallback success for {wallet_address[:8]}...")
                    data = response.json()
                    # Transform Helius format to match expected structure
                    return {"data": data, "source": "helius"}
        except Exception as e:
            logger.error(f"Helius fallback error: {e}")
    
    return {"data": []}

async def test_solscan_api(api_key: str = None) -> dict:
    """Test if Solscan API key is working"""
    key = api_key or api_keys_config.get("solscan", SOLSCAN_API_KEY)
    test_wallet = "74YhGgHA3x1jcL2TchwChDbRVVXvzSxNbYM6ytCukauM"
    
    try:
        headers = {"Authorization": key}
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(
                f"https://pro-api.solscan.io/v2.0/account/transfer",
                params={"address": test_wallet, "page_size": 1},
                headers=headers,
                timeout=10
            )
            return {
                "status": "ok" if response.status_code == 200 else "error",
                "status_code": response.status_code,
                "message": "API key is valid" if response.status_code == 200 else f"API returned {response.status_code}"
            }
    except Exception as e:
        return {"status": "error", "status_code": 0, "message": str(e)}

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
    
    # Check if user is admin
    user_is_admin = is_admin_user(username)
    
    try:
        # Use telegram-specific db connection
        tg_db = get_telegram_db()
        
        # Check/create user in database
        existing_user = await tg_db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
        if not existing_user:
            # New user - give admins unlimited credits
            new_user = UserModel(
                telegram_id=telegram_id, 
                username=username,
                is_admin=user_is_admin,
                credits=999999 if user_is_admin else 0.0
            )
            await tg_db.users.insert_one(new_user.model_dump())
        else:
            # Update existing user admin status if they became admin
            if user_is_admin and not existing_user.get('is_admin'):
                await tg_db.users.update_one(
                    {"telegram_id": telegram_id},
                    {"$set": {"is_admin": True, "credits": 999999}}
                )
    except Exception as e:
        logger.error(f"DB error in start_command: {e}")
    
    # Different menu for admins
    if user_is_admin:
        keyboard = [
            [InlineKeyboardButton("💳 Create Wallet", callback_data="create_wallet"),
             InlineKeyboardButton("💰 My Balance", callback_data="balance")],
            [InlineKeyboardButton("🐋 Whale Watch (Admin)", callback_data="whale_watch_admin"),
             InlineKeyboardButton("📊 My Trades", callback_data="my_trades")],
            [InlineKeyboardButton("➕ Add Wallet to Track", callback_data="add_wallet"),
             InlineKeyboardButton("👥 Manage Users", callback_data="manage_users")],
            [InlineKeyboardButton("⚙️ Settings", callback_data="settings"),
             InlineKeyboardButton("📞 Support", callback_data="support")]
        ]
        admin_badge = "👑 *ADMIN MODE* 👑\n"
    else:
        keyboard = [
            [InlineKeyboardButton("💳 Create Wallet", callback_data="create_wallet"),
             InlineKeyboardButton("💰 My Balance", callback_data="balance")],
            [InlineKeyboardButton("➕ Add Wallet to Track", callback_data="add_wallet"),
             InlineKeyboardButton("📊 My Trades", callback_data="my_trades")],
            [InlineKeyboardButton("💵 Buy Access (£100/day)", callback_data="buy_access"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
            [InlineKeyboardButton("📞 Support", callback_data="support")]
        ]
        admin_badge = ""
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""
🎖️ *SOLANA SOLDIER* 🎖️
━━━━━━━━━━━━━━━━━━━━━
{admin_badge}
Welcome, {username}! 

I'm your automated Solana arbitrage trading bot.

*Features:*
• 🐋 Track whale wallets in real-time
• ⚡ Execute trades in under 2 minutes
• 💰 Target $2 profit per trade
• 🛡️ Anti-rug protection built-in
• ➕ Add your own wallets to track

*Quick Start:*
1. Create a wallet
2. {'Start trading! (Admin - Free Access)' if user_is_admin else 'Buy daily access (£100)'}
3. Add wallets to track

Select an option below:
"""
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /wallet command - show wallet info"""
    telegram_id = update.effective_user.id
    
    wallets = await get_telegram_db().wallets.find(
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
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
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
    await get_telegram_db().wallets.insert_one(wallet.model_dump())
    
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
    
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    wallets = await get_telegram_db().wallets.find(
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
    trades = await get_telegram_db().trades.find(
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
    result = await get_telegram_db().users.update_one(
        {"username": target_username},
        {"$set": {"credits": amount}}
    )
    
    if result.modified_count > 0:
        await update.message.reply_text(f"✅ Set {amount} credits for @{target_username}")
        
        # Notify user
        user = await get_telegram_db().users.find_one({"username": target_username}, {"_id": 0})
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
    """Handle /whales command - show user's tracked wallets (preset wallets only for admin)"""
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    user_is_admin = is_admin_user(username)
    
    tg_db = get_telegram_db()
    
    # Get user's custom tracked wallets
    user_wallets = await tg_db.user_tracked_wallets.find(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    ).to_list(50)
    
    whale_text = "🐋 *YOUR TRACKED WALLETS* 🐋\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Show user's custom wallets
    if user_wallets:
        whale_text += "*Your Wallets:*\n"
        for i, w in enumerate(user_wallets, 1):
            label = w.get('label', 'Unlabeled')
            addr = w.get('wallet_address', '')
            whale_text += f"{i}. `{addr[:8]}...{addr[-8:]}`\n   _{label}_\n"
        whale_text += "\n"
    else:
        whale_text += "_No custom wallets added yet._\n\n"
    
    # Only show preset wallets to admins
    if user_is_admin:
        whale_text += f"*🔒 Preset Wallets (Admin Only):*\n"
        for i, wallet in enumerate(WHALE_WALLETS[:5], 1):
            whale_text += f"{i}. `{wallet[:8]}...{wallet[-8:]}`\n"
        whale_text += f"\n...and {len(WHALE_WALLETS) - 5} more preset\n"
    
    whale_text += "\n💡 Use /addwallet to track a new wallet"
    
    await update.message.reply_text(whale_text, parse_mode='Markdown')

async def addwallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addwallet command - add a wallet to track"""
    telegram_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Usage: /addwallet <wallet_address> [label]\n\nExample:\n`/addwallet 7NTV2q79Ee4gqTH1KS52u14BA7GDvDUZmkzd7xE3Kxci Whale1`",
            parse_mode='Markdown'
        )
        return
    
    wallet_address = args[0]
    label = " ".join(args[1:]) if len(args) > 1 else "Unlabeled"
    
    # Validate wallet address (basic check)
    if len(wallet_address) < 32 or len(wallet_address) > 50:
        await update.message.reply_text("❌ Invalid wallet address. Please enter a valid Solana address.")
        return
    
    tg_db = get_telegram_db()
    
    # Check if already tracking
    existing = await tg_db.user_tracked_wallets.find_one({
        "user_telegram_id": telegram_id,
        "wallet_address": wallet_address,
        "is_active": True
    })
    
    if existing:
        await update.message.reply_text("❌ You're already tracking this wallet.")
        return
    
    # Add wallet
    tracked_wallet = UserTrackedWalletModel(
        user_telegram_id=telegram_id,
        wallet_address=wallet_address,
        label=label
    )
    await tg_db.user_tracked_wallets.insert_one(tracked_wallet.model_dump())
    
    await update.message.reply_text(
        f"✅ *Wallet Added!*\n\nAddress: `{wallet_address[:12]}...`\nLabel: {label}\n\nUse /whales to view your tracked wallets.",
        parse_mode='Markdown'
    )

async def removewallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removewallet command - remove a tracked wallet"""
    telegram_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text("Usage: /removewallet <wallet_address>")
        return
    
    wallet_address = args[0]
    tg_db = get_telegram_db()
    
    result = await tg_db.user_tracked_wallets.update_one(
        {"user_telegram_id": telegram_id, "wallet_address": wallet_address},
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count > 0:
        await update.message.reply_text(f"✅ Wallet `{wallet_address[:12]}...` removed from tracking.", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Wallet not found in your tracked list.")

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

*💰 WALLET COMMANDS:*
/start - Start the bot
/wallet - View your wallets
/newwallet - Create new wallet
/balance - Check your balance
/exportwallets - Export wallet keys

*📊 TRADING COMMANDS:*
/quicktrade - Start trading (choose amount $2-$500)
/trade \<token\> \<amount\> - Manual trade
/autotrade \<sol\> \<stoploss%\> - Enable auto-trade
/stopautotrade - Disable auto-trading
/stoploss \<percent\> - Set stop-loss %
/positions - View active positions
/mytrades - Your trade history
/pnl - View P&L report

*🐋 WHALE TRACKING:*
/whales - View tracked whales
/addwallet \<addr\> [label] - Track a wallet
/removewallet \<addr\> - Stop tracking wallet

*📈 MARKET DATA:*
/trending - Trending tokens
/rugcheck \<token\> - Check token safety
/nft [collection] - NFT data
/nfttrending - Trending NFTs

*🤖 SOLANA SOLDIERS (50 Credits):*
/soldiers - Deploy faucet mining agents
/missionstatus - Check mining progress
/stopmission - Cancel mining session

*🏆 LEADERBOARD:*
/leaderboard - Top traders
/myrank - Your ranking

*💳 PAYMENTS:*
/pay - Buy daily access (£100)
/credits - Check credits

*⚙️ OTHER:*
/status - System status
/settings - Your settings
/help - Show this help
/commands - List all commands

*👑 ADMIN COMMANDS:*
/setcredits @user amount - Set user credits
/allusers - View all users
/alltrades - View all trades
/adminpanel - Admin dashboard
/broadcast \<msg\> - Send to all users

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
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user or user.get('credits', 0) <= 0:
        await update.message.reply_text("❌ You need credits to enable auto-trading. Use /pay to buy access.")
        return
    
    # Get user's wallet
    wallet = await get_telegram_db().wallets.find_one(
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
    trades = await get_telegram_db().trades.find(
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
    
    trades = await get_telegram_db().trades.find(
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
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user or user.get('credits', 0) <= 0:
        await update.message.reply_text("❌ You need credits to trade. Use /pay to buy access.")
        return
    
    # Get user's wallet
    wallet = await get_telegram_db().wallets.find_one(
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
                await get_telegram_db().trades.insert_one(trade_record.model_dump())
                
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
            await get_telegram_db().trades.insert_one(trade_record.model_dump())
            
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
        await get_telegram_db().users.update_one(
            {"telegram_id": telegram_id},
            {"$inc": {"credits": -1}}
        )
        
    except Exception as e:
        logger.error(f"Trade error: {e}")
        await update.message.reply_text(f"❌ Trade failed: {str(e)[:100]}")

async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /positions command - show active positions"""
    telegram_id = update.effective_user.id
    
    trades = await get_telegram_db().trades.find(
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
    await get_telegram_db().whale_activities.insert_one(whale_activity.model_dump())
    
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

# ============== NEW COMMANDS ==============

async def quicktrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quicktrade - Start trading with selectable amount ($2-$500)"""
    telegram_id = update.effective_user.id
    
    # Check user credits
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user or user.get('credits', 0) <= 0:
        await update.message.reply_text("❌ You need credits to trade. Use /pay to buy access.")
        return
    
    # Check wallet
    wallet = await get_telegram_db().wallets.find_one(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    )
    if not wallet:
        await update.message.reply_text("❌ No wallet found. Use /newwallet to create one first.")
        return
    
    # Get wallet balance
    balance_sol = 0
    if helius_rpc:
        balance_sol = await helius_rpc.get_balance(wallet['public_key'])
    
    sol_price = await get_sol_price()
    balance_usd = balance_sol * sol_price
    
    # Create trade amount selection buttons
    keyboard = []
    row = []
    for i, amount in enumerate(TRADE_AMOUNTS):
        if balance_usd >= amount:
            row.append(InlineKeyboardButton(f"${amount}", callback_data=f"trade_amount_{amount}"))
        else:
            row.append(InlineKeyboardButton(f"${amount} ❌", callback_data=f"trade_amount_insufficient_{amount}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_main")])
    
    await update.message.reply_text(
        f"""
⚡ *QUICK TRADE* ⚡
━━━━━━━━━━━━━━━━━━━━━

*Your Balance:*
• {balance_sol:.4f} SOL (~${balance_usd:.2f})

*Select Trade Amount:*
Choose how much USD value to trade per signal.

Higher amounts = Higher potential profit (and risk)!

*Current Settings:*
• Stop-Loss: {DEFAULT_STOP_LOSS_PCT*100:.0f}%
• Max Trade Time: {MAX_TRADE_TIME_SECONDS}s

Select your trade amount below:
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /leaderboard - Show top traders by profit"""
    tg_db = get_telegram_db()
    
    # Aggregate trades by user to get total profit
    pipeline = [
        {"$group": {
            "_id": "$user_telegram_id",
            "total_profit": {"$sum": "$profit_usd"},
            "total_trades": {"$sum": 1},
            "successful_trades": {
                "$sum": {"$cond": [{"$eq": ["$status", "COMPLETED"]}, 1, 0]}
            }
        }},
        {"$sort": {"total_profit": -1}},
        {"$limit": 10}
    ]
    
    leaderboard_data = await tg_db.trades.aggregate(pipeline).to_list(10)
    
    # Get usernames
    leaderboard_text = "🏆 *PROFIT LEADERBOARD* 🏆\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    for i, entry in enumerate(leaderboard_data):
        user = await tg_db.users.find_one({"telegram_id": entry["_id"]}, {"_id": 0, "username": 1})
        username = user.get("username", "Anonymous") if user else "Anonymous"
        
        win_rate = (entry["successful_trades"] / entry["total_trades"] * 100) if entry["total_trades"] > 0 else 0
        profit = entry["total_profit"]
        
        medal = medals[i] if i < len(medals) else f"{i+1}."
        profit_sign = "+" if profit >= 0 else ""
        
        leaderboard_text += f"{medal} *@{username}*\n"
        leaderboard_text += f"    💰 {profit_sign}${profit:.2f} | 📊 {entry['total_trades']} trades | ✅ {win_rate:.0f}%\n\n"
    
    if not leaderboard_data:
        leaderboard_text += "_No trades yet. Be the first to trade!_"
    
    await update.message.reply_text(leaderboard_text, parse_mode='Markdown')

async def myrank_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myrank - Show user's ranking"""
    telegram_id = update.effective_user.id
    tg_db = get_telegram_db()
    
    # Get user's stats
    user_trades = await tg_db.trades.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0, "profit_usd": 1, "status": 1}
    ).to_list(10000)
    
    total_profit = sum(t.get('profit_usd', 0) for t in user_trades)
    total_trades = len(user_trades)
    successful = sum(1 for t in user_trades if t.get('status') == 'COMPLETED')
    win_rate = (successful / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate rank
    pipeline = [
        {"$group": {
            "_id": "$user_telegram_id",
            "total_profit": {"$sum": "$profit_usd"}
        }},
        {"$sort": {"total_profit": -1}}
    ]
    
    all_traders = await tg_db.trades.aggregate(pipeline).to_list(1000)
    rank = 1
    for trader in all_traders:
        if trader["_id"] == telegram_id:
            break
        rank += 1
    
    total_traders = len(all_traders)
    
    rank_text = f"""
🎖️ *YOUR TRADING RANK* 🎖️
━━━━━━━━━━━━━━━━━━━━━

*Rank:* #{rank} of {total_traders} traders

*Your Stats:*
• Total Profit: ${total_profit:.2f}
• Total Trades: {total_trades}
• Successful: {successful}
• Win Rate: {win_rate:.1f}%

{'🏆 *TOP 10 TRADER!*' if rank <= 10 else '📈 Keep trading to climb the ranks!'}
"""
    
    await update.message.reply_text(rank_text, parse_mode='Markdown')

async def soldiers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /soldiers - Deploy Solana Soldiers faucet mining agents"""
    telegram_id = update.effective_user.id
    
    # Check credits
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    credits = user.get('credits', 0) if user else 0
    
    if credits < SOLDIERS_COST:
        await update.message.reply_text(
            f"""
🤖 *SOLANA SOLDIERS* 🤖
━━━━━━━━━━━━━━━━━━━━━

Deploy AI agents to mine crypto from 50+ faucets automatically for 24 hours!

*Cost:* {SOLDIERS_COST} credits
*Your Credits:* {credits:.0f}

❌ *Insufficient Credits*

Use /pay to buy more credits.
""",
            parse_mode='Markdown'
        )
        return
    
    # Show deployment options
    keyboard = [
        [InlineKeyboardButton("🚀 Deploy 5 Soldiers (50 credits)", callback_data="deploy_soldiers_5")],
        [InlineKeyboardButton("💪 Deploy 10 Soldiers (50 credits)", callback_data="deploy_soldiers_10")],
        [InlineKeyboardButton("⚔️ Deploy 20 Soldiers (50 credits)", callback_data="deploy_soldiers_20")],
        [InlineKeyboardButton("❌ Cancel", callback_data="back_main")]
    ]
    
    faucet_stats = soldiers_army.get_faucet_stats() if soldiers_army else {"total_faucets": 50, "mainnet_faucets": 10, "testnet_faucets": 40}
    
    await update.message.reply_text(
        f"""
🤖 *SOLANA SOLDIERS - FAUCET MINERS* 🤖
━━━━━━━━━━━━━━━━━━━━━

Deploy AI agents to automatically claim crypto from faucets!

*Available Faucets:* {faucet_stats['total_faucets']}
• Mainnet: {faucet_stats['mainnet_faucets']} faucets
• Testnet: {faucet_stats['testnet_faucets']} faucets

*Supported Chains:*
SOL, ETH, MATIC, BNB, AVAX, FTM, DOGE, LTC, and more!

*Features:*
• 🔄 Auto proxy rotation
• 🤖 Multi-agent deployment
• 📊 Hourly progress reports
• 🔑 Wallet creation for each chain
• ⏰ 24-hour mining session

*Cost:* {SOLDIERS_COST} credits (24h)
*Your Credits:* {credits:.0f} ✅

Select deployment option:
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def missionstatus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /missionstatus - Check mining progress"""
    telegram_id = update.effective_user.id
    
    if not soldiers_army:
        await update.message.reply_text("❌ Soldiers system not initialized.")
        return
    
    session = await soldiers_army.get_session_status(telegram_id)
    
    if not session or session.status != "active":
        await update.message.reply_text(
            """
📊 *MISSION STATUS* 📊

No active mining session.

Use /soldiers to deploy agents!
""",
            parse_mode='Markdown'
        )
        return
    
    earnings_text = "\n".join([
        f"  • {amt:.6f} {curr}" 
        for curr, amt in session.total_earned.items()
    ]) or "  _Mining in progress..._"
    
    success_rate = (session.faucets_successful / session.faucets_attempted * 100) if session.faucets_attempted > 0 else 0
    
    await update.message.reply_text(
        f"""
📊 *MISSION STATUS* 📊
━━━━━━━━━━━━━━━━━━━━━

*Session:* `{session.session_id[:15]}...`
*Status:* 🟢 Active
*Expires:* {session.expires_at[:16]}

*Agents:* {session.agents_deployed} deployed

*Progress:*
• Faucets Attempted: {session.faucets_attempted}
• Successful Claims: {session.faucets_successful}
• Success Rate: {success_rate:.1f}%

*Earnings So Far:*
{earnings_text}

Use /stopmission to cancel.
""",
        parse_mode='Markdown'
    )

async def stopmission_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stopmission - Cancel mining session"""
    telegram_id = update.effective_user.id
    
    if not soldiers_army:
        await update.message.reply_text("❌ Soldiers system not initialized.")
        return
    
    success = await soldiers_army.cancel_session(telegram_id)
    
    if success:
        await update.message.reply_text("✅ Mission cancelled. Final report will be sent shortly.")
    else:
        await update.message.reply_text("❌ No active mission to cancel.")

async def mytrades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mytrades - Show user's trade history with details"""
    telegram_id = update.effective_user.id
    
    trades = await get_telegram_db().trades.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(20)
    
    if not trades:
        await update.message.reply_text("📊 No trades yet. Start trading to see history!")
        return
    
    text = "📊 *YOUR TRADE HISTORY* 📊\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    total_profit = 0
    for t in trades[:10]:
        status_icon = "✅" if t.get('status') == 'COMPLETED' else "❌" if t.get('status') == 'FAILED' else "⏳"
        profit = t.get('profit_usd', 0)
        total_profit += profit
        profit_text = f"+${profit:.2f}" if profit >= 0 else f"-${abs(profit):.2f}"
        
        token = t.get('token_symbol', t.get('token_address', 'UNKNOWN')[:8])
        
        text += f"{status_icon} *{t['trade_type']}* {t.get('amount_sol', 0):.4f} SOL\n"
        text += f"   Token: {token} | P&L: {profit_text}\n"
        text += f"   _{t['created_at'][:16]}_\n\n"
    
    text += f"━━━━━━━━━━━━━━━━━━━━━\n"
    text += f"*Total P&L:* ${total_profit:.2f}\n"
    text += f"*Total Trades:* {len(trades)}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def nft_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /nft - NFT collection info"""
    args = context.args
    
    if not nft_aggregator:
        await update.message.reply_text("❌ NFT aggregator not initialized.")
        return
    
    if not args:
        # Show trending NFTs
        collections = await nft_aggregator.get_trending_collections("solana", limit=10)
        
        text = "🖼️ *TRENDING NFTs (Solana)* 🖼️\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for i, c in enumerate(collections[:10], 1):
            verified = "✅" if c.verified else ""
            text += f"{i}. *{c.name}* {verified}\n"
            text += f"   Floor: {c.floor_price:.2f} {c.currency} | Vol: {c.volume_24h:.0f}\n\n"
        
        text += "\nUse `/nft <collection>` for details"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        # Search for specific collection
        query = " ".join(args)
        collections = await nft_aggregator.search_collections(query, "solana")
        
        if collections:
            c = collections[0]
            text = nft_aggregator.format_collection_summary(c)
            await update.message.reply_text(text, parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ Collection '{query}' not found.")

async def nfttrending_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /nfttrending - Show trending NFT collections"""
    if not nft_aggregator:
        await update.message.reply_text("❌ NFT aggregator not initialized.")
        return
    
    keyboard = [
        [InlineKeyboardButton("🟣 Solana", callback_data="nft_trending_solana"),
         InlineKeyboardButton("🔵 Ethereum", callback_data="nft_trending_ethereum")]
    ]
    
    await update.message.reply_text(
        "🖼️ *NFT TRENDING* 🖼️\n\nSelect blockchain:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def adminpanel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /adminpanel - Admin dashboard"""
    username = update.effective_user.username
    
    if not is_admin_user(username):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    tg_db = get_telegram_db()
    
    # Gather stats
    total_users = await tg_db.users.count_documents({})
    total_wallets = await tg_db.wallets.count_documents({"is_active": True})
    total_trades = await tg_db.trades.count_documents({})
    pending_payments = await tg_db.payments.count_documents({"status": "PENDING_VERIFICATION"})
    
    trades = await tg_db.trades.find({}, {"_id": 0, "profit_usd": 1}).to_list(10000)
    total_profit = sum(t.get('profit_usd', 0) for t in trades)
    
    # Recent activity
    recent_trades = await tg_db.trades.find({}, {"_id": 0}).sort("created_at", -1).to_list(5)
    
    keyboard = [
        [InlineKeyboardButton("👥 All Users", callback_data="admin_users"),
         InlineKeyboardButton("📊 All Trades", callback_data="admin_trades")],
        [InlineKeyboardButton("💳 Payments", callback_data="admin_payments"),
         InlineKeyboardButton("🐋 Whale Logs", callback_data="admin_whale_logs")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")]
    ]
    
    await update.message.reply_text(
        f"""
👑 *ADMIN PANEL* 👑
━━━━━━━━━━━━━━━━━━━━━

*System Overview:*
• Users: {total_users}
• Active Wallets: {total_wallets}
• Total Trades: {total_trades}
• Total Profit: ${total_profit:.2f}
• Pending Payments: {pending_payments}

*Trading Status:*
• Live Trading: {'🟢 ON' if LIVE_TRADING_ENABLED else '🔴 OFF'}
• Auto-Trade: {'🟢 ON' if AUTO_TRADE_ON_WHALE_SIGNAL else '🔴 OFF'}
• Active Traders: {len(active_trading_users)}

*Recent Activity:*
{chr(10).join([f"• {t['trade_type']} {t.get('amount_sol', 0):.3f} SOL - {t['status']}" for t in recent_trades[:3]]) or 'No recent trades'}

Select an option:
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def allusers_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /allusers - Admin view all users"""
    username = update.effective_user.username
    
    if not is_admin_user(username):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    users = await get_telegram_db().users.find({}, {"_id": 0}).to_list(100)
    
    text = "👥 *ALL USERS* 👥\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for u in users[:20]:
        badge = "👑" if u.get('is_admin') else "👤"
        credits = u.get('credits', 0)
        username_str = u.get('username', 'unknown')
        text += f"{badge} @{username_str} | {credits:.0f} credits | ID: {u.get('telegram_id')}\n"
    
    text += f"\n*Total:* {len(users)} users"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def alltrades_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /alltrades - Admin view all trades"""
    username = update.effective_user.username
    
    if not is_admin_user(username):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    trades = await get_telegram_db().trades.find({}, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    text = "📊 *ALL TRADES* 📊\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for t in trades[:15]:
        status_icon = "✅" if t.get('status') == 'COMPLETED' else "❌" if t.get('status') == 'FAILED' else "⏳"
        profit = t.get('profit_usd', 0)
        text += f"{status_icon} User {t['user_telegram_id']} | {t['trade_type']} {t.get('amount_sol', 0):.3f} SOL | P&L: ${profit:.2f}\n"
    
    total_profit = sum(t.get('profit_usd', 0) for t in trades)
    text += f"\n━━━━━━━━━━━━━━━━━━━━━\n*Total Trades:* {len(trades)}\n*Total P&L:* ${total_profit:.2f}"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /broadcast - Admin send message to all users"""
    username = update.effective_user.username
    
    if not is_admin_user(username):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    users = await get_telegram_db().users.find({}, {"_id": 0, "telegram_id": 1}).to_list(10000)
    
    sent = 0
    failed = 0
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user['telegram_id'],
                text=f"📢 *ANNOUNCEMENT*\n\n{message}\n\n_- Solana Soldier Team_",
                parse_mode='Markdown'
            )
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.1)  # Rate limiting
    
    await update.message.reply_text(f"✅ Broadcast sent to {sent} users. Failed: {failed}")

async def commands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /commands - List all available commands"""
    commands_text = """
📋 *ALL COMMANDS* 📋
━━━━━━━━━━━━━━━━━━━━━

*💰 WALLET:*
/start /wallet /newwallet /balance /exportwallets

*📊 TRADING:*
/quicktrade /trade /autotrade /stopautotrade
/stoploss /positions /mytrades /pnl

*🐋 WHALES:*
/whales /addwallet /removewallet

*📈 MARKET:*
/trending /rugcheck /nft /nfttrending

*🤖 SOLDIERS:*
/soldiers /missionstatus /stopmission

*🏆 LEADERBOARD:*
/leaderboard /myrank

*💳 PAYMENTS:*
/pay /credits

*⚙️ OTHER:*
/status /settings /help /commands

*👑 ADMIN:*
/setcredits /allusers /alltrades
/adminpanel /broadcast
/apikeys /setapi /testapi
"""
    await update.message.reply_text(commands_text, parse_mode='Markdown')

async def apikeys_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /apikeys - Admin view API key status"""
    username = update.effective_user.username
    
    if not is_admin_user(username):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    # Test each API
    solscan_status = await test_solscan_api()
    
    solscan_key = api_keys_config.get("solscan", "")
    helius_key = api_keys_config.get("helius", "")
    
    solscan_masked = f"{solscan_key[:20]}...{solscan_key[-10:]}" if len(solscan_key) > 30 else solscan_key[:10] + "..."
    helius_masked = f"{helius_key[:8]}...{helius_key[-4:]}" if len(helius_key) > 12 else helius_key[:6] + "..."
    
    status_icon = "✅" if solscan_status["status"] == "ok" else "❌"
    
    await update.message.reply_text(
        f"""
🔑 *API KEYS STATUS* 🔑
━━━━━━━━━━━━━━━━━━━━━

*Solscan Pro API:*
Key: `{solscan_masked}`
Status: {status_icon} {solscan_status['message']}

*Helius RPC:*
Key: `{helius_masked}`
Status: ✅ Connected

*Commands:*
• `/setapi solscan <key>` - Update Solscan API
• `/setapi helius <key>` - Update Helius API
• `/testapi solscan` - Test Solscan connection
""",
        parse_mode='Markdown'
    )

async def setapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setapi - Admin set API keys"""
    username = update.effective_user.username
    
    if not is_admin_user(username):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            """
*Usage:* `/setapi <service> <api_key>`

*Services:*
• `solscan` - Solscan Pro API
• `helius` - Helius RPC API

*Example:*
`/setapi solscan eyJhbGciOiJIUzI1NiIs...`
""",
            parse_mode='Markdown'
        )
        return
    
    service = args[0].lower()
    new_key = args[1]
    
    if service not in ["solscan", "helius"]:
        await update.message.reply_text("❌ Invalid service. Use `solscan` or `helius`.")
        return
    
    # Test the new key before saving
    if service == "solscan":
        test_result = await test_solscan_api(new_key)
        if test_result["status"] != "ok":
            await update.message.reply_text(
                f"❌ *API Key Test Failed*\n\nStatus: {test_result['status_code']}\nMessage: {test_result['message']}\n\nKey was NOT updated.",
                parse_mode='Markdown'
            )
            return
    
    # Update the key
    old_key = api_keys_config.get(service, "")
    api_keys_config[service] = new_key
    
    # Also update in database for persistence
    await get_telegram_db().config.update_one(
        {"key": f"api_key_{service}"},
        {"$set": {"value": new_key, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    
    await update.message.reply_text(
        f"""
✅ *API Key Updated!*

*Service:* {service.upper()}
*Old Key:* `{old_key[:15]}...` (masked)
*New Key:* `{new_key[:15]}...` (masked)

The new key is now active.
""",
        parse_mode='Markdown'
    )
    
    logger.info(f"Admin {username} updated {service} API key")

async def testapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /testapi - Test API connection"""
    username = update.effective_user.username
    
    if not is_admin_user(username):
        await update.message.reply_text("❌ Admin access required.")
        return
    
    args = context.args
    service = args[0].lower() if args else "solscan"
    
    await update.message.reply_text(f"🔄 Testing {service.upper()} API...")
    
    if service == "solscan":
        result = await test_solscan_api()
        status_icon = "✅" if result["status"] == "ok" else "❌"
        
        await update.message.reply_text(
            f"""
{status_icon} *Solscan API Test*

*Status Code:* {result['status_code']}
*Result:* {result['message']}

{'API is working correctly!' if result['status'] == 'ok' else 'API test failed. Check your key with /setapi'}
""",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("Currently only `solscan` test is supported.")

async def credits_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /credits - Check credits balance"""
    telegram_id = update.effective_user.id
    
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    credits = user.get('credits', 0) if user else 0
    
    await update.message.reply_text(
        f"""
💳 *YOUR CREDITS* 💳

*Balance:* {credits:.0f} credits

*Credit Usage:*
• Trading: 1 credit per trade
• Soldiers (24h): {SOLDIERS_COST} credits

Use /pay to buy more credits (£100 = 10,000 credits)
""",
        parse_mode='Markdown'
    )

async def exportwallets_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /exportwallets - Export all wallet private keys"""
    telegram_id = update.effective_user.id
    
    wallets = await get_telegram_db().wallets.find(
        {"user_telegram_id": telegram_id},
        {"_id": 0}
    ).to_list(100)
    
    if not wallets:
        await update.message.reply_text("❌ No wallets found.")
        return
    
    text = "🔐 *YOUR WALLETS* 🔐\n━━━━━━━━━━━━━━━━━━━━━\n\n"
    text += "⚠️ *SAVE SECURELY - DELETE THIS MESSAGE AFTER*\n\n"
    
    for i, w in enumerate(wallets, 1):
        status = "🟢 Active" if w.get('is_active') else "🔴 Inactive"
        text += f"*Wallet {i}:* {status}\n"
        text += f"Public: `{w['public_key']}`\n"
        text += f"Private: `{w['private_key_encrypted']}`\n\n"
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings - User settings"""
    telegram_id = update.effective_user.id
    
    user_settings = user_trade_settings.get(telegram_id, {
        'profit_target': MIN_PROFIT_USD,
        'stop_loss_pct': DEFAULT_STOP_LOSS_PCT * 100,
        'trade_amount_usd': 2
    })
    
    keyboard = [
        [InlineKeyboardButton(f"💰 Trade Amount: ${user_settings.get('trade_amount_usd', 2)}", callback_data="settings_trade_amount")],
        [InlineKeyboardButton(f"🎯 Profit Target: ${user_settings.get('profit_target', MIN_PROFIT_USD)}", callback_data="settings_profit_target")],
        [InlineKeyboardButton(f"🛡️ Stop-Loss: {user_settings.get('stop_loss_pct', DEFAULT_STOP_LOSS_PCT*100):.0f}%", callback_data="settings_stop_loss")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_main")]
    ]
    
    await update.message.reply_text(
        """
⚙️ *YOUR SETTINGS* ⚙️
━━━━━━━━━━━━━━━━━━━━━

Configure your trading parameters:
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

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
        await get_telegram_db().wallets.insert_one(wallet.model_dump())
        
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
        user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
        wallets = await get_telegram_db().wallets.find(
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
        # For regular users - show their tracked wallets
        tg_db = get_telegram_db()
        user_wallets = await tg_db.user_tracked_wallets.find(
            {"user_telegram_id": telegram_id, "is_active": True},
            {"_id": 0}
        ).to_list(10)
        
        whale_text = "🐋 *YOUR TRACKED WALLETS* 🐋\n\n"
        if user_wallets:
            for w in user_wallets:
                label = w.get('label', 'Unlabeled')
                addr = w.get('wallet_address', '')
                whale_text += f"• `{addr[:12]}...` _{label}_\n"
        else:
            whale_text += "_No wallets tracked yet._\n"
        
        whale_text += "\n💡 Use /addwallet to track a wallet"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
        await query.edit_message_text(
            whale_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "whale_watch_admin":
        # Admin view - show preset wallets
        whale_text = "🐋 *ADMIN - PRESET WHALE WALLETS* 🐋\n\n"
        for i, wallet in enumerate(WHALE_WALLETS, 1):
            whale_text += f"{i}. `{wallet[:8]}...{wallet[-8:]}`\n"
        
        whale_text += f"\n*Total:* {len(WHALE_WALLETS)} wallets monitored 24/7"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
        await query.edit_message_text(
            whale_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "add_wallet":
        await query.edit_message_text(
            """
➕ *ADD WALLET TO TRACK* ➕

To add a wallet, use the command:
`/addwallet <address> [label]`

*Example:*
`/addwallet 7NTV2q79Ee4gqTH1KS52u14BA7GDvDUZmkzd7xE3Kxci MyWhale`

Use /whales to view your tracked wallets.
Use /removewallet <address> to remove.
""",
            parse_mode='Markdown'
        )
    
    elif data == "manage_users":
        # Admin only
        username = query.from_user.username
        if not is_admin_user(username):
            await query.edit_message_text("❌ Admin access required.")
            return
        
        tg_db = get_telegram_db()
        users = await tg_db.users.find({}, {"_id": 0}).to_list(20)
        
        text = "👥 *USER MANAGEMENT* 👥\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        text += f"*Total Users:* {len(users)}\n\n"
        
        for u in users[:10]:
            is_admin = u.get('is_admin', False)
            credits = u.get('credits', 0)
            badge = "👑" if is_admin else "👤"
            text += f"{badge} @{u.get('username', 'unknown')} - {credits:.0f} credits\n"
        
        text += "\n*Commands:*\n/setcredits @user amount"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "my_trades":
        trades = await get_telegram_db().trades.find(
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
        await get_telegram_db().payments.insert_one(payment.model_dump())
        
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
        await get_telegram_db().wallets.update_many(
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
    
    # ============== NEW CALLBACK HANDLERS ==============
    
    elif data.startswith("trade_amount_"):
        # User selected a trade amount
        if "insufficient" in data:
            await query.answer("❌ Insufficient balance for this amount!", show_alert=True)
            return
        
        amount_usd = int(data.replace("trade_amount_", ""))
        
        # Store user's selected amount
        if telegram_id not in user_trade_settings:
            user_trade_settings[telegram_id] = {}
        user_trade_settings[telegram_id]['trade_amount_usd'] = amount_usd
        
        # Show confirmation with Start Trade button
        keyboard = [
            [InlineKeyboardButton("🚀 START TRADING", callback_data=f"confirm_start_trade_{amount_usd}")],
            [InlineKeyboardButton("⚙️ Change Stop-Loss", callback_data="change_stop_loss")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_quicktrade")]
        ]
        
        sol_price = await get_sol_price()
        amount_sol = amount_usd / sol_price
        
        await query.edit_message_text(
            f"""
⚡ *CONFIRM TRADE SETTINGS* ⚡
━━━━━━━━━━━━━━━━━━━━━

*Trade Amount:* ${amount_usd} (~{amount_sol:.4f} SOL)
*Stop-Loss:* {DEFAULT_STOP_LOSS_PCT*100:.0f}%
*Profit Target:* ${MIN_PROFIT_USD}
*Max Time:* {MAX_TRADE_TIME_SECONDS}s

The bot will:
1. 🐋 Monitor whale wallets 24/7
2. 🔍 Detect new token buys
3. 🛡️ Run rug-check
4. ⚡ Execute quick in/out trades
5. 💰 Exit at ${MIN_PROFIT_USD}+ profit or stop-loss

Press START to begin auto-trading!
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data.startswith("confirm_start_trade_"):
        # User confirmed - start trading
        amount_usd = int(data.replace("confirm_start_trade_", ""))
        
        # Get wallet and check balance
        wallet = await get_telegram_db().wallets.find_one(
            {"user_telegram_id": telegram_id, "is_active": True},
            {"_id": 0}
        )
        
        if not wallet:
            await query.edit_message_text("❌ No wallet found. Use /newwallet first.")
            return
        
        sol_price = await get_sol_price()
        amount_sol = amount_usd / sol_price
        
        # Check balance
        if helius_rpc:
            balance = await helius_rpc.get_balance(wallet['public_key'])
            if balance < amount_sol + 0.01:
                await query.edit_message_text(
                    f"❌ Insufficient balance.\n\nRequired: {amount_sol + 0.01:.4f} SOL\nAvailable: {balance:.4f} SOL\n\nFund your wallet:\n`{wallet['public_key']}`",
                    parse_mode='Markdown'
                )
                return
        
        # Create keypair and add to active traders
        try:
            keypair = Keypair.from_base58_string(wallet['private_key_encrypted'])
        except:
            keypair = Keypair.from_bytes(base58.b58decode(wallet['private_key_encrypted']))
        
        active_trading_users[telegram_id] = {
            'keypair': keypair,
            'trade_amount': amount_sol,
            'trade_amount_usd': amount_usd,
            'stop_loss_pct': DEFAULT_STOP_LOSS_PCT,
            'wallet_public_key': wallet['public_key'],
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        
        keyboard = [
            [InlineKeyboardButton("📊 View Positions", callback_data="view_positions")],
            [InlineKeyboardButton("🛑 STOP TRADING", callback_data="stop_auto_trade")]
        ]
        
        await query.edit_message_text(
            f"""
🚀 *AUTO-TRADING ACTIVATED!* 🚀
━━━━━━━━━━━━━━━━━━━━━

*Settings:*
• Trade Amount: ${amount_usd} ({amount_sol:.4f} SOL)
• Stop-Loss: {DEFAULT_STOP_LOSS_PCT*100:.0f}%
• Profit Target: ${MIN_PROFIT_USD}

*Status:* 🟢 LIVE

Your bot is now monitoring {len(WHALE_WALLETS)} whale wallets.
You'll receive real-time notifications for every trade!

Trade reports will be sent automatically.
""",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Send confirmation to user
        logger.info(f"✅ User {telegram_id} started auto-trading with ${amount_usd}")
    
    elif data == "stop_auto_trade":
        if telegram_id in active_trading_users:
            del active_trading_users[telegram_id]
            await query.edit_message_text(
                "🛑 *AUTO-TRADING STOPPED*\n\nYour bot has stopped trading. Use /quicktrade to start again.",
                parse_mode='Markdown'
            )
        else:
            await query.answer("No active trading session.", show_alert=True)
    
    elif data == "view_positions":
        if auto_trader:
            positions = await auto_trader.get_active_positions()
            if positions:
                text = "📊 *ACTIVE POSITIONS* 📊\n\n"
                for p in positions[:5]:
                    text += f"• {p.get('token_symbol', 'UNKNOWN')}: {p.get('amount_sol', 0):.4f} SOL\n"
                    text += f"  Entry: ${p.get('entry_price', 0):.6f} | Current: ${p.get('current_price', 0):.6f}\n\n"
            else:
                text = "📊 *POSITIONS* 📊\n\nNo active positions. Waiting for whale signals..."
        else:
            text = "📊 No positions data available."
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_trading")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "back_quicktrade":
        # Go back to trade amount selection
        wallet = await get_telegram_db().wallets.find_one(
            {"user_telegram_id": telegram_id, "is_active": True},
            {"_id": 0}
        )
        balance_sol = 0
        if wallet and helius_rpc:
            balance_sol = await helius_rpc.get_balance(wallet['public_key'])
        
        sol_price = await get_sol_price()
        balance_usd = balance_sol * sol_price
        
        keyboard = []
        row = []
        for i, amount in enumerate(TRADE_AMOUNTS):
            if balance_usd >= amount:
                row.append(InlineKeyboardButton(f"${amount}", callback_data=f"trade_amount_{amount}"))
            else:
                row.append(InlineKeyboardButton(f"${amount} ❌", callback_data=f"trade_amount_insufficient_{amount}"))
            if len(row) == 4:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="back_main")])
        
        await query.edit_message_text(
            f"⚡ *QUICK TRADE* ⚡\n\n*Balance:* {balance_sol:.4f} SOL (~${balance_usd:.2f})\n\nSelect trade amount:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif data == "back_trading":
        if telegram_id in active_trading_users:
            keyboard = [
                [InlineKeyboardButton("📊 View Positions", callback_data="view_positions")],
                [InlineKeyboardButton("🛑 STOP TRADING", callback_data="stop_auto_trade")]
            ]
            await query.edit_message_text(
                "🚀 *AUTO-TRADING ACTIVE* 🚀\n\nYour bot is monitoring whales.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "Use /quicktrade to start trading.",
                parse_mode='Markdown'
            )
    
    elif data.startswith("deploy_soldiers_"):
        num_agents = int(data.replace("deploy_soldiers_", ""))
        
        # Check credits
        user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
        credits = user.get('credits', 0) if user else 0
        
        if credits < SOLDIERS_COST:
            await query.answer("❌ Insufficient credits!", show_alert=True)
            return
        
        # Deduct credits
        await get_telegram_db().users.update_one(
            {"telegram_id": telegram_id},
            {"$inc": {"credits": -SOLDIERS_COST}}
        )
        
        # Deploy soldiers
        if soldiers_army:
            await query.edit_message_text("🚀 *DEPLOYING SOLDIERS...*\n\nInitializing proxy pool and agents...", parse_mode='Markdown')
            session = await soldiers_army.deploy_soldiers(telegram_id, num_agents=num_agents, duration_hours=24)
            
            await query.edit_message_text(
                f"""
🤖 *SOLDIERS DEPLOYED!* 🤖
━━━━━━━━━━━━━━━━━━━━━

*Session:* `{session.session_id[:20]}...`
*Agents:* {num_agents} deployed
*Duration:* 24 hours
*Faucets:* {len(CRYPTO_FAUCETS)} targets

Your soldiers are now mining crypto!

Use /missionstatus to check progress.
""",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("❌ Soldiers system not available.")
    
    elif data.startswith("nft_trending_"):
        chain = data.replace("nft_trending_", "")
        
        if nft_aggregator:
            collections = await nft_aggregator.get_trending_collections(chain, limit=10)
            
            text = f"🖼️ *TRENDING NFTs ({chain.upper()})* 🖼️\n━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            for i, c in enumerate(collections[:10], 1):
                verified = "✅" if c.verified else ""
                text += f"{i}. *{c.name}* {verified}\n"
                text += f"   Floor: {c.floor_price:.4f} {c.currency} | Vol 24h: {c.volume_24h:.2f}\n\n"
            
            keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_main")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await query.edit_message_text("❌ NFT aggregator not available.")
    
    elif data == "admin_users":
        if not is_admin_user(query.from_user.username):
            await query.answer("❌ Admin only!", show_alert=True)
            return
        
        users = await get_telegram_db().users.find({}, {"_id": 0}).to_list(50)
        text = "👥 *ALL USERS* 👥\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for u in users[:20]:
            badge = "👑" if u.get('is_admin') else "👤"
            text += f"{badge} @{u.get('username', 'unknown')} | {u.get('credits', 0):.0f} credits\n"
        text += f"\n*Total:* {len(users)} users"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "admin_trades":
        if not is_admin_user(query.from_user.username):
            await query.answer("❌ Admin only!", show_alert=True)
            return
        
        trades = await get_telegram_db().trades.find({}, {"_id": 0}).sort("created_at", -1).to_list(20)
        text = "📊 *ALL TRADES* 📊\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for t in trades[:15]:
            status = "✅" if t.get('status') == 'COMPLETED' else "❌" if t.get('status') == 'FAILED' else "⏳"
            text += f"{status} User {t['user_telegram_id']} | {t['trade_type']} {t.get('amount_sol', 0):.3f} SOL | ${t.get('profit_usd', 0):.2f}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "admin_payments":
        if not is_admin_user(query.from_user.username):
            await query.answer("❌ Admin only!", show_alert=True)
            return
        
        payments = await get_telegram_db().payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(20)
        text = "💳 *PAYMENTS* 💳\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for p in payments[:15]:
            status = "✅" if p.get('status') == 'VERIFIED' else "⏳"
            text += f"{status} User {p['user_telegram_id']} | £{p.get('amount_gbp', 0)} | {p.get('crypto_type', 'N/A')}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "admin_whale_logs":
        if not is_admin_user(query.from_user.username):
            await query.answer("❌ Admin only!", show_alert=True)
            return
        
        activities = await get_telegram_db().whale_activities.find({}, {"_id": 0}).sort("detected_at", -1).to_list(20)
        text = "🐋 *WHALE LOGS* 🐋\n━━━━━━━━━━━━━━━━━━━━━\n\n"
        for a in activities[:10]:
            text += f"• {a.get('action', 'N/A')} | {a.get('token_symbol', 'N/A')} | {a.get('detected_at', '')[:16]}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    
    elif data == "admin_back":
        # Go back to admin panel
        keyboard = [
            [InlineKeyboardButton("👥 All Users", callback_data="admin_users"),
             InlineKeyboardButton("📊 All Trades", callback_data="admin_trades")],
            [InlineKeyboardButton("💳 Payments", callback_data="admin_payments"),
             InlineKeyboardButton("🐋 Whale Logs", callback_data="admin_whale_logs")],
        ]
        await query.edit_message_text(
            "👑 *ADMIN PANEL* 👑\n\nSelect an option:",
            reply_markup=InlineKeyboardMarkup(keyboard),
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
    total_users = await get_telegram_db().users.count_documents({})
    active_wallets = await get_telegram_db().wallets.count_documents({"is_active": True})
    total_trades = await get_telegram_db().trades.count_documents({})
    
    trades = await get_telegram_db().trades.find({}, {"_id": 0, "profit_usd": 1}).to_list(10000)
    total_profit = sum(t.get('profit_usd', 0) for t in trades)
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    whale_today = await get_telegram_db().whale_activities.count_documents({
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
    users = await get_telegram_db().users.find({}, {"_id": 0}).to_list(1000)
    return {"users": users}

@api_router.get("/users/{telegram_id}")
async def get_user(telegram_id: int):
    """Get specific user"""
    user = await get_telegram_db().users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    wallets = await get_telegram_db().wallets.find(
        {"user_telegram_id": telegram_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    trades = await get_telegram_db().trades.find(
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
    activities = await get_telegram_db().whale_activities.find(
        {},
        {"_id": 0}
    ).sort("detected_at", -1).to_list(100)
    return {"activities": activities}

@api_router.get("/trades")
async def get_trades():
    """Get all trades"""
    trades = await get_telegram_db().trades.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return {"trades": trades}

@api_router.get("/payments")
async def get_payments():
    """Get all payments"""
    payments = await get_telegram_db().payments.find({}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"payments": payments}

@api_router.get("/sol-price")
async def get_sol_price_endpoint():
    """Get current SOL price"""
    price = await get_sol_price()
    return {"price_usd": price}

@api_router.post("/whale-activities")
async def create_whale_activity(activity: WhaleActivityModel):
    """Record a whale activity"""
    await get_telegram_db().whale_activities.insert_one(activity.model_dump())
    return {"status": "created", "id": activity.id}

class SetCreditsRequest(BaseModel):
    telegram_id: int
    credits: float

@api_router.post("/admin/set-credits")
async def admin_set_credits(request: SetCreditsRequest):
    """Admin endpoint to set user credits"""
    result = await get_telegram_db().users.update_one(
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
    wallet = await get_telegram_db().wallets.find_one(
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
    await get_telegram_db().trades.insert_one(trade.model_dump())
    
    return {"status": "queued", "trade_id": trade.id}

@api_router.get("/trading-stats")
async def get_trading_stats():
    """Get trading statistics"""
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    
    total_trades = await get_telegram_db().trades.count_documents({})
    trades_today = await get_telegram_db().trades.count_documents({"created_at": {"$gte": today.isoformat()}})
    
    all_trades = await get_telegram_db().trades.find({}, {"_id": 0, "profit_usd": 1, "status": 1}).to_list(10000)
    total_profit = sum(t.get('profit_usd', 0) for t in all_trades)
    completed = sum(1 for t in all_trades if t.get('status') == 'COMPLETED')
    failed = sum(1 for t in all_trades if t.get('status') == 'FAILED')
    
    whale_activities_today = await get_telegram_db().whale_activities.count_documents({
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
    trades = await get_telegram_db().trades.find(
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

@api_router.get("/leaderboard")
async def get_leaderboard():
    """Get profit leaderboard"""
    tg_db = get_telegram_db()
    
    pipeline = [
        {"$group": {
            "_id": "$user_telegram_id",
            "total_profit": {"$sum": "$profit_usd"},
            "total_trades": {"$sum": 1},
            "successful_trades": {
                "$sum": {"$cond": [{"$eq": ["$status", "COMPLETED"]}, 1, 0]}
            }
        }},
        {"$sort": {"total_profit": -1}},
        {"$limit": 20}
    ]
    
    leaderboard = await tg_db.trades.aggregate(pipeline).to_list(20)
    
    # Enrich with usernames
    results = []
    for entry in leaderboard:
        user = await tg_db.users.find_one({"telegram_id": entry["_id"]}, {"_id": 0, "username": 1})
        results.append({
            "telegram_id": entry["_id"],
            "username": user.get("username", "Anonymous") if user else "Anonymous",
            "total_profit": entry["total_profit"],
            "total_trades": entry["total_trades"],
            "successful_trades": entry["successful_trades"],
            "win_rate": (entry["successful_trades"] / entry["total_trades"] * 100) if entry["total_trades"] > 0 else 0
        })
    
    return {"leaderboard": results}

@api_router.get("/admin/dashboard")
async def get_admin_dashboard():
    """Get admin dashboard data"""
    tg_db = get_telegram_db()
    
    total_users = await tg_db.users.count_documents({})
    total_wallets = await tg_db.wallets.count_documents({"is_active": True})
    total_trades = await tg_db.trades.count_documents({})
    pending_payments = await tg_db.payments.count_documents({"status": "PENDING_VERIFICATION"})
    
    trades = await tg_db.trades.find({}, {"_id": 0, "profit_usd": 1, "status": 1}).to_list(10000)
    total_profit = sum(t.get('profit_usd', 0) for t in trades)
    successful = sum(1 for t in trades if t.get('status') == 'COMPLETED')
    
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_trades = await tg_db.trades.count_documents({"created_at": {"$gte": today.isoformat()}})
    today_signups = await tg_db.users.count_documents({"created_at": {"$gte": today.isoformat()}})
    
    return {
        "total_users": total_users,
        "total_wallets": total_wallets,
        "total_trades": total_trades,
        "total_profit_usd": total_profit,
        "pending_payments": pending_payments,
        "active_traders": len(active_trading_users),
        "successful_trades": successful,
        "win_rate": (successful / total_trades * 100) if total_trades > 0 else 0,
        "today_trades": today_trades,
        "today_signups": today_signups,
        "live_trading_enabled": LIVE_TRADING_ENABLED,
        "auto_trade_enabled": AUTO_TRADE_ON_WHALE_SIGNAL,
        "tracked_whales": len(WHALE_WALLETS)
    }

@api_router.get("/faucets")
async def get_faucets():
    """Get available crypto faucets"""
    if soldiers_army:
        return {
            "faucets": soldiers_army.get_faucet_list(),
            "stats": soldiers_army.get_faucet_stats()
        }
    return {"faucets": [], "stats": {}}

@api_router.get("/mining-sessions")
async def get_mining_sessions():
    """Get all mining sessions"""
    sessions = await get_telegram_db().mining_sessions.find({}, {"_id": 0}).sort("started_at", -1).to_list(100)
    return {"sessions": sessions}

@api_router.get("/nft/trending/{chain}")
async def get_nft_trending(chain: str = "solana"):
    """Get trending NFT collections"""
    if nft_aggregator:
        collections = await nft_aggregator.get_trending_collections(chain, limit=20)
        return {"collections": [
            {
                "name": c.name,
                "symbol": c.symbol,
                "marketplace": c.marketplace,
                "chain": c.chain,
                "floor_price": c.floor_price,
                "currency": c.currency,
                "volume_24h": c.volume_24h,
                "listed_count": c.listed_count,
                "verified": c.verified
            } for c in collections
        ]}
    return {"collections": []}

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
        
        # Add handlers - Original commands
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
        telegram_app.add_handler(CommandHandler("addwallet", addwallet_command))
        telegram_app.add_handler(CommandHandler("removewallet", removewallet_command))
        
        # New commands
        telegram_app.add_handler(CommandHandler("quicktrade", quicktrade_command))
        telegram_app.add_handler(CommandHandler("leaderboard", leaderboard_command))
        telegram_app.add_handler(CommandHandler("myrank", myrank_command))
        telegram_app.add_handler(CommandHandler("soldiers", soldiers_command))
        telegram_app.add_handler(CommandHandler("missionstatus", missionstatus_command))
        telegram_app.add_handler(CommandHandler("stopmission", stopmission_command))
        telegram_app.add_handler(CommandHandler("mytrades", mytrades_command))
        telegram_app.add_handler(CommandHandler("nft", nft_command))
        telegram_app.add_handler(CommandHandler("nfttrending", nfttrending_command))
        telegram_app.add_handler(CommandHandler("adminpanel", adminpanel_command))
        telegram_app.add_handler(CommandHandler("allusers", allusers_command))
        telegram_app.add_handler(CommandHandler("alltrades", alltrades_command))
        telegram_app.add_handler(CommandHandler("broadcast", broadcast_command))
        telegram_app.add_handler(CommandHandler("commands", commands_command))
        telegram_app.add_handler(CommandHandler("credits", credits_command))
        telegram_app.add_handler(CommandHandler("exportwallets", exportwallets_command))
        telegram_app.add_handler(CommandHandler("settings", settings_command))
        
        # Callback handler
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
    global soldiers_army, nft_aggregator
    
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
    
    # Initialize Solana Soldiers (Faucet Mining)
    soldiers_army = SolanaSoldiersArmy(db=get_telegram_db(), telegram_notify=telegram_notify_user)
    logger.info(f"✅ Solana Soldiers initialized ({len(CRYPTO_FAUCETS)} faucets)")
    
    # Initialize NFT Aggregator
    nft_aggregator = NFTAggregator()
    logger.info("✅ NFT Aggregator initialized")
    
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
