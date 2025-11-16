# Quick Start - GitHub + DigitalOcean Deployment

## 1️⃣ Create GitHub Repository (5 minutes)

```powershell
# In PowerShell on Windows

# Navigate to project
cd "k:\Dai Trader"

# Initialize git
git init
git add .
git commit -m "Initial commit"

# Go to https://github.com/new
# Create a PRIVATE repository named "dai-trader"
# Then run (replace YOUR_USERNAME):

git remote add origin https://github.com/YOUR_USERNAME/dai-trader.git
git branch -M main
git push -u origin main
```

## 2️⃣ Create DigitalOcean Droplet (3 minutes)

1. Go to https://cloud.digitalocean.com
2. Click **Create** → **Droplets**
3. Select:
   - **Ubuntu 22.04 LTS**
   - **Basic Plan - $6/month** (1GB RAM)
   - **Any datacenter** (NY recommended)
   - Add SSH key or use password
4. Click **Create Droplet**
5. Copy the IP address shown

## 3️⃣ Deploy to Server (10 minutes)

```bash
# SSH into your droplet (replace YOUR_IP)
ssh root@YOUR_IP

# Run these commands one by one:
apt-get update
apt-get install -y git python3.11 python3.11-venv python3-pip

# Clone your repo (replace YOUR_USERNAME)
git clone https://github.com/YOUR_USERNAME/dai-trader.git
cd dai-trader

# Setup environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Add your Alpaca API keys, then Ctrl+X, Y, Enter

# Setup auto-start service
cp deploy/dai-trader.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable dai-trader
systemctl start dai-trader

# Check if running
systemctl status dai-trader
```

## 4️⃣ Verify It's Working

```bash
# View live logs
journalctl -u dai-trader -f

# You should see:
# - Bot initializing
# - Connecting to Alpaca
# - Checking market status
# - Scanning watchlist
```

## ✅ Done!

Your bot is now running 24/7 on DigitalOcean!

### Common Commands:

```bash
# View logs
journalctl -u dai-trader -f

# Restart bot
systemctl restart dai-trader

# Stop bot
systemctl stop dai-trader

# Update code (after pushing to GitHub)
cd ~/dai-trader
git pull
systemctl restart dai-trader
```

### Access your server anytime:
```bash
ssh root@YOUR_IP
```

**Cost**: $6/month  
**Uptime**: 24/7 (runs even when your PC is off)  
**Updates**: Push to GitHub, pull on server, restart service

See `DEPLOYMENT.md` for detailed guide!
