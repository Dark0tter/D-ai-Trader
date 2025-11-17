#!/bin/bash
# Quick Deployment Script for D-ai-Trader
# Run this on your DigitalOcean droplet

echo "=========================================="
echo "D-ai-Trader Deployment Script"
echo "=========================================="

# Update system
apt-get update
apt-get upgrade -y

# Install Python and dependencies
apt-get install -y python3.11 python3.11-venv python3-pip git wget build-essential

# Clone repository
cd ~
git clone https://github.com/Dark0tter/D-ai-Trader.git
cd D-ai-Trader

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file
cp .env.example .env

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   nano .env"
echo ""
echo "2. Add these values:"
echo "   ALPACA_API_KEY=PKKNLPP2J5V6TASWPFWYTFMAZT"
echo "   ALPACA_SECRET_KEY=4UmLF9CgdLrQZHMXHp9rLhBv1recXfoLEJsZJujCVcFL"
echo ""
echo "3. Setup auto-start service:"
echo "   cp deploy/dai-trader.service /etc/systemd/system/"
echo "   systemctl daemon-reload"
echo "   systemctl enable dai-trader"
echo "   systemctl start dai-trader"
echo ""
echo "4. Check status:"
echo "   systemctl status dai-trader"
echo "   journalctl -u dai-trader -f"
echo "=========================================="
