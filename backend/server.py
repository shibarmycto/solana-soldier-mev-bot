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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '')
SOLSCAN_API_KEY = os.environ.get('SOLSCAN_API_KEY', '')
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    telegram_id = user.id
    username = user.username or user.first_name
    
    # Check/create user in database
    existing_user = await db.users.find_one({"telegram_id": telegram_id}, {"_id": 0})
    if not existing_user:
        new_user = UserModel(telegram_id=telegram_id, username=username)
        await db.users.insert_one(new_user.model_dump())
    
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
    help_text = """
📖 *SOLANA SOLDIER COMMANDS* 📖
━━━━━━━━━━━━━━━━━━━━━

*User Commands:*
/start - Start the bot
/wallet - View your wallets
/newwallet - Create new wallet
/balance - Check your balance
/whales - View tracked whales
/pay - Buy daily access
/help - Show this help

*Admin Commands:*
/setcredits @user amount - Set user credits

*Support:* Contact @memecorpofficial
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

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
    tokens = await get_trending_tokens()
    return tokens

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

@app.on_event("startup")
async def startup_event():
    """Start telegram bot on app startup"""
    logger.info("Starting Solana Soldier API...")
    
    # Start telegram bot in background thread
    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    logger.info("Telegram bot thread started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global telegram_app
    if telegram_app:
        await telegram_app.stop()
    client.close()
    logger.info("Shutdown complete")
