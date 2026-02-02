# 🎖️ Solana Soldier - MEV Trading Bot

A Telegram-based Solana arbitrage trading bot that tracks whale wallets and executes quick trades for profit.

![Solana Soldier](https://img.shields.io/badge/Solana-Soldier-14F195?style=for-the-badge&logo=solana)
![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![React](https://img.shields.io/badge/React-18+-61DAFB?style=for-the-badge&logo=react)

## Features

### 🐋 Whale Tracking
- Real-time monitoring of 9+ whale wallets via Helius WebSocket
- Instant notifications on whale activity
- Customizable wallet tracking per user

### ⚡ Auto-Trading
- Quick in/out trades ($2-$500 configurable)
- Stop-loss protection
- Rug-pull detection via Jupiter DEX
- P&L tracking and reporting

### 🤖 Solana Soldiers (AI Faucet Mining)
- Deploy AI agents to mine 48+ crypto faucets
- Auto proxy rotation
- 24-hour mining sessions
- Progress reports

### 🖼️ NFT Aggregator
- Trending collections from Magic Eden & OpenSea
- Floor price tracking
- Collection analytics

### 👑 Admin Panel
- User management
- API key configuration
- Trade monitoring
- Broadcast messaging

## Tech Stack

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: React 18, TailwindCSS
- **Database**: MongoDB
- **Blockchain**: Solana (solders, Jupiter DEX, Helius RPC)
- **Bot**: python-telegram-bot

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MongoDB
- Telegram Bot Token
- Helius API Key

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/solana-soldier.git
cd solana-soldier

# Backend setup
cd backend
cp .env.example .env
# Edit .env with your credentials
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001

# Frontend setup (new terminal)
cd frontend
cp .env.example .env
# Edit .env with backend URL
yarn install
yarn start
```

## Telegram Commands

| Category | Commands |
|----------|----------|
| **Wallet** | `/start` `/wallet` `/newwallet` `/balance` `/exportwallets` |
| **Trading** | `/quicktrade` `/trade` `/autotrade` `/stopautotrade` `/positions` `/pnl` |
| **Whales** | `/whales` `/addwallet` `/removewallet` |
| **Market** | `/trending` `/rugcheck` `/nft` `/nfttrending` |
| **Soldiers** | `/soldiers` `/missionstatus` `/stopmission` |
| **Leaderboard** | `/leaderboard` `/myrank` |
| **Admin** | `/adminpanel` `/setcredits` `/apikeys` `/setapi` `/broadcast` |

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Railway and Render deployment guides.

## Environment Variables

### Backend (.env)
```
MONGO_URL=mongodb://...
DB_NAME=solana_soldier
TELEGRAM_BOT_TOKEN=...
HELIUS_API_KEY=...
SOLSCAN_API_KEY=...
LIVE_TRADING_ENABLED=true
AUTO_TRADE_ON_WHALE_SIGNAL=true
```

### Frontend (.env)
```
REACT_APP_BACKEND_URL=https://your-api.com
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/` | Health check |
| `GET /api/system-status` | Trading system status |
| `GET /api/stats` | Bot statistics |
| `GET /api/leaderboard` | Top traders |
| `GET /api/api-status` | External API status |
| `GET /api/trending-tokens` | Trending tokens |
| `GET /api/nft/trending/{chain}` | Trending NFTs |

## License

MIT License - see LICENSE file

## Support

Contact: @memecorpofficial on Telegram
