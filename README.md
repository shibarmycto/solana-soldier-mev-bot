# Multi-Purpose Bot Collection

This repository contains multiple bots including the Solana Soldier MEV Bot and the Claude Remote Assistant Bot.

## Solana Soldier MEV Bot

A sophisticated MEV (Maximal Extractable Value) bot for the Solana blockchain that identifies and executes profitable trading opportunities such as arbitrage, JIT ladder protection, and front-running.

### Solana Bot Features

- **Real-time Mempool Monitoring**: Monitors Solana mempool for profitable opportunities
- **Multiple MEV Strategies**: 
  - Arbitrage between different DEXs
  - JIT ladder protection
  - Front-running opportunities
- **High-Frequency Execution**: Optimized for speed to capture MEV opportunities
- **Priority Fee Management**: Uses dynamic fee calculation for transaction inclusion
- **Risk Management**: Built-in safeguards to minimize losses

### Solana Bot Prerequisites

- Python 3.8+
- Solana account with sufficient SOL for transaction fees
- Access to a Solana RPC endpoint (recommended: QuickNode, Alchemy, or own node)

### Solana Bot Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd solana-soldier-mev-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Solana Bot Configuration

1. Set up your environment variables:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:
```env
RPC_URL=https://api.mainnet-beta.solana.com
PRIVATE_KEY=your_private_key_here
PRIORITY_FEE_CAP=0.01  # Max priority fee in SOL
MIN_PROFIT_THRESHOLD=0.001  # Minimum profit threshold (0.1%)
```

### Solana Bot Usage

To run the bot:

```bash
python solana_soldier_mev_bot.py
```

## Claude Remote Assistant Bot

An advanced Telegram bot that integrates with Anthropic's Claude AI to provide remote device control and automation capabilities.

### Claude Bot Features
- AI-powered conversations using Anthropic Claude
- Remote device control (Android, iOS, PC)
- Job application automation
- Form filling assistance
- Multi-platform messaging integration
- Secure session management

### Railway Deployment

Both bots are configured for easy deployment on Railway.app:

1. **Prerequisites**:
   - For Claude Bot: Telegram Bot Token (from @BotFather) and Anthropic Claude API Key
   - For Solana Bot: Solana account with SOL for transaction fees

2. **Quick Deploy**:
   - The project includes `railway.json` for automatic configuration (in claude-remote-assistant/)
   - Required environment variables are pre-defined
   - Dockerfile included for containerized deployment

3. **To Deploy Claude Bot**:
   - Fork this repository
   - Connect to Railway.app
   - Set required environment variables
   - Deploy with one click

See `claude-remote-assistant/RUNNING_ON_RAILWAY.md` for detailed deployment instructions.

## Architecture

- `solana_soldier_mev_bot.py`: Main Solana bot implementation
- `claude-remote-assistant/`: Claude Remote Assistant Bot directory
- `requirements.txt`: Python dependencies
- `Procfile`: Railway deployment configuration (now points to Claude bot)
- `.env.example`: Environment variable template

## Risk Disclaimer

MEV strategies carry substantial risks including:
- Smart contract vulnerabilities
- Market volatility
- Network congestion
- Regulatory changes
- Potential losses exceeding profits

Use at your own risk. This software is provided as-is without warranty.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

MIT