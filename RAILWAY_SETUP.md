# 🚂 Railway Deployment - Step by Step Guide for Solana Soldier

## STEP 1: Push Code to GitHub First
Before deploying to Railway, you need your code on GitHub.

In Emergent:
1. Click the **"Save to Github"** button in the chat
2. Create a new repository named `solana-soldier`
3. Make it **Private** (recommended for security)
4. Click Save

---

## STEP 2: Create Railway Project

1. Go to **https://railway.app/new**
2. Click **"Deploy from GitHub repo"**
3. Select your `solana-soldier` repository
4. Railway will start importing

---

## STEP 3: Add MongoDB Database

1. In your Railway project, click **"+ New"** button
2. Select **"Database"**
3. Choose **"Add MongoDB"**
4. Railway auto-creates the database and MONGO_URL variable

---

## STEP 4: Configure Backend Service

1. Click on your main service (the GitHub one)
2. Go to **"Settings"** tab
3. Set these values:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

---

## STEP 5: Add Environment Variables

1. Click on your service → **"Variables"** tab
2. Click **"+ New Variable"** and add each one:

```
DB_NAME = solana_soldier
TELEGRAM_BOT_TOKEN = 8553687931:AAFZ87vcHiVsbrRRhcgX3fFe0D9zos-2JLM
HELIUS_API_KEY = 5963c03a-3441-4c7a-816f-4a307b412439
SOLSCAN_API_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjcmVhdGVkQXQiOjE3MzYyNzMyNTg2NjQsImVtYWlsIjoic2hpYmFybXkwMTFAZ21haWwuY29tIiwiYWN0aW9uIjoidG9rZW4tYXBpIiwiYXBpVmVyc2lvbiI6InYyIiwiaWF0IjoxNzM2MjczMjU4fQ.u-LrpYwKCQ6FGu6Ha8iAoTrT94yGGJYn0SW7IOULEEM
ADMIN_CHAT_ID = -4993252670
ADMIN_USERNAME = @memecorpofficial
PAYMENT_SOL_ADDRESS = TXFm5oQQ4Qp51tMkPgdqSESYdQaN6hqQkpoZidWMdSy
PAYMENT_ETH_ADDRESS = 0x125FeD6C4A538aaD4108cE5D598628DC42635Fe9
PAYMENT_BTC_ADDRESS = bc1p3red8wgfa9k2qyhxxj9vpnehvy29ld63lg5t6kfvrcy6lz7l9mhspyjk3k
DAILY_ACCESS_PRICE_GBP = 100
LIVE_TRADING_ENABLED = true
AUTO_TRADE_ON_WHALE_SIGNAL = true
CORS_ORIGINS = *
```

3. **IMPORTANT**: Also add the MongoDB reference:
   - Click **"+ New Variable"**
   - Name: `MONGO_URL`
   - Click **"Reference"** → Select your MongoDB service → `MONGO_URL`

---

## STEP 6: Deploy!

1. Railway auto-deploys when you add variables
2. Wait 2-3 minutes for build to complete
3. Click **"Settings"** → Look for your **Public URL** (e.g., `solana-soldier-production.up.railway.app`)

---

## STEP 7: Verify It's Working

1. Visit: `https://YOUR-URL.railway.app/api/`
   - Should show: `{"status": "online"}`

2. Visit: `https://YOUR-URL.railway.app/api/system-status`
   - Should show trading status

3. Test your Telegram bot - send `/start` to @Cfsolanasoldier_bot

---

## 🎉 DONE! Your bot is now running 24/7 on Railway!

## Troubleshooting

**Bot not responding?**
- Check logs in Railway dashboard
- Verify TELEGRAM_BOT_TOKEN is correct

**MongoDB error?**
- Make sure MONGO_URL references the Railway MongoDB service

**Build failed?**
- Check the "Deployments" tab for error logs
