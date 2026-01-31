#!/bin/bash

echo "Telegram Group Responder Bot"
echo "=============================="

# Check if config.json exists
if [ ! -f "config.json" ]; then
    echo "Error: config.json not found!"
    echo "Please create a config.json file with your bot token."
    echo "See README.md for instructions."
    exit 1
fi

# Check if the bot token has been updated
TOKEN=$(grep -o '"bot_token": "[^"]*"' config.json | cut -d'"' -f4)
if [ "$TOKEN" = "YOUR_BOT_TOKEN_HERE" ]; then
    echo "Error: Please update config.json with your actual bot token!"
    echo "Replace 'YOUR_BOT_TOKEN_HERE' with your real bot token."
    exit 1
fi

echo "Starting the Telegram bot..."
echo "Press Ctrl+C to stop the bot"
echo ""

python3 telegram_group_responder.py