# Solana Soldier - Product Requirements Document

## Original Problem Statement
Create a Telegram bot called "Solana Soldier" for Solana cryptocurrency arbitrage trading that:
- Creates Solana wallets per user and sends private keys
- Tracks whale wallets in real-time
- Executes trades with $2 profit target in under 2 minutes
- Has admin credit system with /setcredits command
- Users pay £100/day via crypto (SOL, ETH, BTC)
- Reports trades via Telegram with easy button UI

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

## What's Been Implemented (2026-01-30)
### Backend (FastAPI)
- ✅ Telegram bot with commands: /start, /wallet, /newwallet, /balance, /setcredits, /whales, /pay, /help
- ✅ Inline keyboard buttons for navigation
- ✅ Solana wallet creation with private key generation
- ✅ MongoDB models for Users, Wallets, Trades, WhaleActivities, Payments
- ✅ API endpoints for stats, users, trades, payments, whales, SOL price
- ✅ Admin credit management system
- ✅ Payment request flow with admin notification

### Frontend (React)
- ✅ Landing page with branding and features
- ✅ Dashboard with stats cards and tabs
- ✅ Whale wallet display
- ✅ Pricing section with payment options
- ✅ Real-time SOL price display

### Integrations
- ✅ Telegram Bot API (python-telegram-bot 21.0)
- ✅ Solscan API for whale tracking
- ✅ CoinGecko API for SOL price
- ✅ MongoDB for data storage

## Prioritized Backlog
### P0 (Critical)
- [ ] Implement actual trading execution logic
- [ ] Connect to Solana DEX (Raydium/Jupiter) for trades
- [ ] Real-time whale transaction monitoring

### P1 (High Priority)
- [ ] Automated trade execution based on whale activity
- [ ] Profit calculation and tracking
- [ ] Gas fee estimation and management
- [ ] Token burn detection

### P2 (Medium Priority)
- [ ] PumpFun trending token integration
- [ ] Trade history export
- [ ] Performance analytics dashboard
- [ ] Multi-wallet support per user

## Next Tasks
1. Integrate Jupiter/Raydium DEX API for actual trades
2. Implement real-time whale transaction websocket monitoring
3. Add automated trade execution logic with profit targets
4. Build rug detection algorithm
5. Add Helius RPC for faster blockchain queries

## Configuration
- Admin: @memecorpofficial
- Admin Chat: -4993252670
- Daily Access: £100
- Payment Addresses:
  - SOL: TXFm5oQQ4Qp51tMkPgdqSESYdQaN6hqQkpoZidWMdSy
  - ETH: 0x125FeD6C4A538aaD4108cE5D598628DC42635Fe9
  - BTC: bc1p3red8wgfa9k2qyhxxj9vpnehvy29ld63lg5t6kfvrcy6lz7l9mhspyjk3k
