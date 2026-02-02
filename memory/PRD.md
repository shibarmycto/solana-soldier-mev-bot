# Solana Soldier - Product Requirements Document

## Original Problem Statement
Create a Telegram bot called "Solana Soldier" for Solana cryptocurrency arbitrage trading with:
- Real-time whale wallet tracking
- Automated trading on whale signals
- $2 profit target per trade in under 2 minutes
- Jupiter DEX integration for swaps
- Rug detection algorithm
- Helius RPC for fast blockchain queries
- WebSocket real-time monitoring

## User Personas
1. **Crypto Trader** - Uses automated trading following whale signals
2. **Admin (@memecorpofficial)** - Manages user credits and verifies payments
3. **Whale Tracker** - Monitors whale wallet activities in real-time

## What's Been Implemented

### Phase 1 - Core Bot (2026-01-30)
- ✅ Telegram bot with commands and inline keyboard UI
- ✅ Solana wallet creation with private key generation
- ✅ MongoDB models and CRUD operations
- ✅ Admin credit management system
- ✅ Payment portal (SOL/ETH/BTC)
- ✅ Web dashboard

### Phase 2 - Trading Engine (2026-01-30)
- ✅ Jupiter DEX Integration (quote, swap, execute)
- ✅ Rug Detection Algorithm (7 risk checks)
- ✅ Whale Monitor with polling
- ✅ Trending Token Scanner (DexScreener)
- ✅ New commands: /trending, /rugcheck, /trade, /positions

### Phase 3 - Live Trading & WebSocket (2026-01-30)
- ✅ **Helius RPC Integration** - Fast blockchain queries
- ✅ **Helius WebSocket** - Real-time transaction monitoring
- ✅ **Live Trade Execution** - Via Jupiter DEX with Helius
- ✅ **Auto-Trade on Whale Signal** - Automatic execution when whale buys
- ✅ **Position Monitoring** - Exit on profit target or timeout
- ✅ New commands: /autotrade, /stopautotrade, /status
- ✅ New API: /system-status, /wallet-balance

## System Status
```
Live Trading: ENABLED ✅
Auto-Trade on Whale: ENABLED ✅
Helius RPC: CONNECTED ✅
WebSocket: CONNECTED ✅
Whale Wallets: 9 SUBSCRIBED ✅
```

## Trading Parameters
- Min Profit Target: $2 USD
- Max Trade Time: 120 seconds
- Max Trade per Signal: 0.5 SOL
- Slippage: 1.5%
- Gas Reserve: 0.01 SOL

## Architecture
```
/app/backend/
├── server.py           # FastAPI + Telegram bot + API
├── trading_engine.py   # Helius RPC, WebSocket, Jupiter, Rug Detection
└── .env               # Configuration

Key Components:
- HeliusRPC: Fast blockchain queries
- HeliusWebSocket: Real-time tx monitoring
- JupiterDEX: Trade execution
- RugDetector: Token safety checks
- WhaleMonitorWebSocket: Real-time whale tracking
- LiveAutoTrader: Automated trading logic
```

## Telegram Commands
| Command | Description |
|---------|-------------|
| /start | Start bot with menu |
| /wallet | View wallets |
| /newwallet | Create new wallet |
| /balance | Check balance |
| /trade <token> <sol> | Manual trade |
| /autotrade <sol> | Enable auto-trading |
| /stopautotrade | Disable auto-trading |
| /positions | View active positions |
| /trending | Trending tokens |
| /rugcheck <token> | Check token safety |
| /whales | View tracked whales |
| /status | System status |
| /pay | Buy daily access |
| /help | Help menu |
| /setcredits @user amt | (Admin) Set credits |

## Configuration
- Admin: @memecorpofficial
- Admin Chat: -4993252670
- Daily Access: £100
- Helius API: 5963c03a-3441-4c7a-816f-4a307b412439

## Payment Addresses
- SOL: TXFm5oQQ4Qp51tMkPgdqSESYdQaN6hqQkpoZidWMdSy
- ETH: 0x125FeD6C4A538aaD4108cE5D598628DC42635Fe9
- BTC: bc1p3red8wgfa9k2qyhxxj9vpnehvy29ld63lg5t6kfvrcy6lz7l9mhspyjk3k

## Tracked Whale Wallets
1. 74YhGgHA3x1jcL2TchwChDbRVVXvzSxNbYM6ytCukauM
2. 2KUCqnm5c49wqG9cUyDiv9fVs12EMmNtBsrKpVZzLovd
3. EthJwgUrj8drTsUZxFt13uBpQeMv3E1ceDyGAseNaxeh
4. CkVqgWTBdZSbiaycU5K1M3JttKdAyjTwRbfZXoFugo65
5. 7NTV2q79Ee4gqTH1KS52u14BA7GDvDUZmkzd7xE3Kxci
6. 6cFuSvQS7WU689HSnQufHnghrxkY6qpiq4qKLyUfD86B
7. H3DvA7eCqKmGmQmb1wTUmhXLQwAjt7ckmH7GPhoCtUQB
8. AUFxnVLsKkkupjCY4kmA5ZDH8c4HgK7CZ4FYw1VcXpn8
9. 32r5qvmNTtmp7jAEfgPsF9dtBzcgUWDt6t5JyEaD3Kf1

### Phase 4 - Bot Restoration & Privacy Features (2026-02-01)
- ✅ **Bot Restoration** - Fixed bot crash after user code corruption
- ✅ **Frontend Fix** - Fixed WHALE_WALLETS undefined error
- ✅ **Admin/User Roles** - Admin distinction implemented
- ✅ **User Wallet Tracking** - /addwallet, /removewallet, /whales commands
- ✅ **Privacy Features** - Preset whale wallets hidden from regular users
- ✅ **Free Admin Access** - Admins automatically get unlimited credits

### Phase 5 - Major Features Update (2026-02-02)
- ✅ **Profit Leaderboard** - /leaderboard, /myrank commands
- ✅ **Admin Panel** - /adminpanel, /allusers, /alltrades, /broadcast commands
- ✅ **Quick Trade ($2-$500)** - /quicktrade with button selection for trade amounts
- ✅ **Solana Soldiers AI Faucet Mining** (50 credits):
  - 48 crypto faucets across 20+ chains
  - Auto proxy rotation
  - Multi-agent deployment (5/10/20 agents)
  - 24-hour mining sessions
  - Progress reports every 6 hours
- ✅ **NFT Aggregator** - /nft, /nfttrending (Magic Eden, OpenSea)
- ✅ **Real-time Trade Reports** - Auto notifications on trades
- ✅ **Full Command List** - 35+ Telegram commands

## Full Command List
| Category | Commands |
|----------|----------|
| Wallet | /start /wallet /newwallet /balance /exportwallets |
| Trading | /quicktrade /trade /autotrade /stopautotrade /stoploss /positions /mytrades /pnl |
| Whales | /whales /addwallet /removewallet |
| Market | /trending /rugcheck /nft /nfttrending |
| Soldiers | /soldiers /missionstatus /stopmission |
| Leaderboard | /leaderboard /myrank |
| Payments | /pay /credits |
| Other | /status /settings /help /commands |
| Admin | /setcredits /allusers /alltrades /adminpanel /broadcast |

## Testing Status
- ✅ Backend: 100% pass rate (31+ tests passed)
- ✅ Frontend: 100% pass rate (landing page + dashboard)
- ✅ Telegram Bot: All 38+ commands registered
- ✅ Faucet Mining: 48 faucets (SIMULATED claims)
- ✅ NFT Aggregator: Magic Eden & OpenSea integration
- ✅ API Management: /apikeys, /setapi, /testapi commands

## API Status
- ⚠️ **Solscan Pro API**: Key valid but requires PAID TIER upgrade at solscan.io
- ✅ **Helius RPC**: Working (used as fallback for whale data)

## MOCKED/SIMULATED Features
- ⚠️ **Faucet Claims**: Simulated with 70% success rate (not real claims)
- Real faucets require captcha solving and can ban IPs

## Next Steps (P1)
- [ ] Fix Solscan API 401 error (whale data)
- [ ] Dashboard real-time updates via WebSocket
- [ ] Re-add bot to admin group chat (bot was kicked)
