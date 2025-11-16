#!/bin/bash
# Quick deployment script for updates
# Run this whenever you push updates to GitHub

echo "Deploying latest changes..."

# Pull latest code
git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt --upgrade

# Restart the service
sudo systemctl restart dai-trader

echo "Deployment complete!"
echo "Check status: sudo systemctl status dai-trader"
echo "View logs: sudo journalctl -u dai-trader -f"
