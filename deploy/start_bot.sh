#!/bin/bash
# Start the trading bot service

echo "Starting Dai Trader Bot..."

# Navigate to project directory
cd /root/dai-trader

# Activate virtual environment
source venv/bin/activate

# Run the bot
python trading_bot.py
