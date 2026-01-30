# Solana Soldier - Product Requirements Document

## Original Problem Statement
Create a Telegram bot called "Solana Soldier" for Solana cryptocurrency arbitrage trading that:
- Creates Solana wallets per user and sends private keys
- Tracks whale wallets in real-time
- Executes trades with $2 profit target in under 2 minutes
- Has admin credit system with /setcredits command
- Users pay £100/day via crypto (SOL, ETH, BTC)
- Reports trades via Telegram with easy button UI
- Integrates with Jupiter DEX for swaps
- Implements rug detection algorithm

## User Personas
1. **Crypto Trader** - Wants automated arbitrage trading without manual monitoring
2. **Admin (@memecorpofficial)** - Manages user credits and verifies payments
3. **Whale Tracker** - Uses bot to monitor whale wallet activities

## Core Requirements (Static)
- Telegram bot integration with inline keyboard buttons
- Solana wallet creation using solders library
- Whale wallet tracking (9 wallets configured)
- Credit system for user access
- Payment verification system (SOL/ETH/BTC)
- Web dashboard for monitoring
- Jupiter DEX integration for trades
- Rug detection algorithm
- Automated trading logic

## What's Been Implemented

### Phase 1 (2026-01-30)
- ✅ Telegram bot with commands: /start, /wallet, /newwallet, /balance, /setcredits, /whales, /pay, /help
- ✅ Inline keyboard buttons for navigation
- ✅ Solana wallet creation with private key generation
- ✅ MongoDB models for Users, Wallets, Trades, WhaleActivities, Payments
- ✅ API endpoints for stats, users, trades, payments, whales, SOL price
- ✅ Admin credit management system
- ✅ Payment request flow with admin notification
- ✅ Landing page and dashboard

### Phase 2 (2026-01-30)
- ✅ **Jupiter DEX Integration** - JupiterDEX class with quote, swap transaction, and execution methods
- ✅ **Rug Detection Algorithm** - RugDetector class checking:
  - Low liquidity (<$5,000)
  - High creator holdings (>50%)
  - Low holder count (<50)
  - Token age (<24 hours)
  - Mint/freeze authority enabled
  - Top holder concentration (>80%)
  - Known rugger addresses
- ✅ **Whale Monitor** - WhaleMonitor class with real-time polling
- ✅ **Auto Trader** - AutoTrader class with:
  - Signal processing from whale activity
  - Confidence calculation
  - Position management
  - Exit monitoring
- ✅ **Trending Token Scanner** - TrendingTokenScanner using DexScreener API
- ✅ **New Telegram Commands**: /trending, /rugcheck, /trade, /positions
- ✅ **New API Endpoints**: /trending-tokens, /new-pairs, /rugcheck, /trading-stats, /execute-trade
- ✅ **Dashboard Updates**: New tabs for Trending, Rugcheck, Whales, Trading Engine stats

## Architecture
```
/app/backend/
├── server.py           # FastAPI + Telegram bot
├── trading_engine.py   # Jupiter DEX, Rug Detection, Whale Monitor, Auto Trader
└── .env               # Configuration

/app/frontend/
└── src/App.js         # React dashboard with 7 tabs
```

## Prioritized Backlog
### P0 (Completed)
- [x] Jupiter DEX integration
- [x] Rug detection algorithm
- [x] Whale monitoring
- [x] Automated trading logic

### P1 (Next)
- [ ] Live trade execution with actual funds
- [ ] Helius RPC integration for faster queries
- [ ] Real-time websocket whale monitoring
- [ ] Profit tracking per position

### P2 (Future)
- [ ] PumpFun API integration
- [ ] Trade history export
- [ ] Performance analytics charts
- [ ] Multi-wallet support per user

## Configuration
- Admin: @memecorpofficial
- Admin Chat: -4993252670
- Daily Access: £100
- Profit Target: $2/trade
- Max Trade Time: 120 seconds
- Payment Addresses:
  - SOL: TXFm5oQQ4Qp51tMkPgdqSESYdQaN6hqQkpoZidWMdSy
  - ETH: 0x125FeD6C4A538aaD4108cE5D598628DC42635Fe9
  - BTC: bc1p3red8wgfa9k2qyhxxj9vpnehvy29ld63lg5t6kfvrcy6lz7l9mhspyjk3k

## Notes
- Solscan API returns 401 - may need API key renewal
- DexScreener API used as fallback for trending tokens
- Jupiter DEX swaps are SIMULATED for safety - real execution requires wallet funding
