# Solana Soldier - Deployment Guide

## Railway Deployment

### Step 1: Create Railway Account
1. Go to https://railway.app
2. Sign up with GitHub

### Step 2: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Connect your GitHub and select the repository

### Step 3: Add MongoDB
1. In your project, click "New" → "Database" → "Add MongoDB"
2. Railway will auto-create MONGO_URL

### Step 4: Configure Environment Variables
Go to your service → Variables tab and add:

```
# Required
MONGO_URL=<auto-filled by Railway MongoDB>
DB_NAME=solana_soldier
TELEGRAM_BOT_TOKEN=8553687931:AAFZ87vcHiVsbrRRhcgX3fFe0D9zos-2JLM
HELIUS_API_KEY=5963c03a-3441-4c7a-816f-4a307b412439
SOLSCAN_API_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3MzYyNzMyNTg2NjQsImVtYWlsIjoic2hpYmFybXkwMTFAZ21haWwuY29tIiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzM2MjczMjU4fQ.u-LrpYwKCQ6FGu6Ha8iAoTrT94yGGJYn0SW7IOULEEM

# Admin Config
ADMIN_CHAT_ID=-4993252670
ADMIN_USERNAME=@memecorpofficial

# Payment Addresses
PAYMENT_SOL_ADDRESS=TXFm5oQQ4Qp51tMkPgdqSESYdQaN6hqQkpoZidWMdSy
PAYMENT_ETH_ADDRESS=0x125FeD6C4A538aaD4108cE5D598628DC42635Fe9
PAYMENT_BTC_ADDRESS=bc1p3red8wgfa9k2qyhxxj9vpnehvy29ld63lg5t6kfvrcy6lz7l9mhspyjk3k
DAILY_ACCESS_PRICE_GBP=100

# Trading Config
LIVE_TRADING_ENABLED=true
AUTO_TRADE_ON_WHALE_SIGNAL=true

# CORS (set to your frontend URL after deployment)
CORS_ORIGINS=*
```

### Step 5: Deploy
Railway auto-deploys on push to main branch.

---

## Render Deployment

### Step 1: Create Render Account
1. Go to https://render.com
2. Sign up with GitHub

### Step 2: Create Backend Service
1. Click "New" → "Web Service"
2. Connect your GitHub repo
3. Configure:
   - **Name**: solana-soldier-api
   - **Root Directory**: backend
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

### Step 3: Create Frontend Service
1. Click "New" → "Static Site"
2. Connect same repo
3. Configure:
   - **Name**: solana-soldier-frontend
   - **Root Directory**: frontend
   - **Build Command**: `yarn install && yarn build`
   - **Publish Directory**: build

### Step 4: Add MongoDB (Render doesn't have built-in MongoDB)
Use MongoDB Atlas:
1. Go to https://mongodb.com/atlas
2. Create free cluster
3. Get connection string
4. Add to Render environment variables

### Step 5: Environment Variables (Render Dashboard)
Add same variables as Railway (see above)

Plus for frontend:
```
REACT_APP_BACKEND_URL=https://solana-soldier-api.onrender.com
```

---

## Post-Deployment Checklist

- [ ] Verify MongoDB connection
- [ ] Test Telegram bot responds to /start
- [ ] Check /api/system-status endpoint
- [ ] Verify whale WebSocket connection
- [ ] Test a trade with small amount

## Troubleshooting

### Bot not responding
- Check TELEGRAM_BOT_TOKEN is correct
- Verify no other instance is running (conflict error)

### MongoDB connection failed
- Check MONGO_URL format
- Verify IP whitelist (Atlas: allow 0.0.0.0/0 for Render/Railway)

### WebSocket disconnecting
- Helius WebSocket may timeout - auto-reconnect is implemented
- Check HELIUS_API_KEY is valid
