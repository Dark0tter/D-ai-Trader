#!/bin/bash
# DigitalOcean Droplet Setup Script
# Run this once after creating your Ubuntu droplet

echo "=========================================="
echo "Dai Trader - DigitalOcean Setup"
echo "=========================================="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3.11
echo "Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3-pip
sudo apt-get install -y python3.11-dev build-essential

# Install git
echo "Installing Git..."
sudo apt-get install -y git

# Install system dependencies for TA-Lib
echo "Installing TA-Lib dependencies..."
sudo apt-get install -y wget
cd /tmp
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ~

# Clone your repository
echo "=========================================="
echo "Setup complete! Now run:"
echo "git clone https://github.com/YOUR_USERNAME/dai-trader.git"
echo "cd dai-trader"
echo "python3.11 -m venv venv"
echo "source venv/bin/activate"
echo "pip install -r requirements.txt"
echo "cp .env.example .env"
echo "nano .env  # Add your Alpaca API keys"
echo "=========================================="
