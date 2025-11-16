# Dai Trader - DigitalOcean Deployment Guide

Complete guide to deploy your autonomous trading bot on DigitalOcean using GitHub.

## 📋 Prerequisites

1. DigitalOcean account ([Get $200 credit](https://m.do.co/c/))
2. GitHub account
3. Alpaca API keys ([Get free paper trading keys](https://alpaca.markets))

## 🚀 Step-by-Step Deployment

### Step 1: Create GitHub Repository

```powershell
# In your local project directory (k:\Dai Trader)

# Initialize git (if not already done)
git init

# Create .gitignore to exclude sensitive files
# (already created in project)

# Add all files
git add .

# Commit
git commit -m "Initial commit - Dai Trader bot"

# Create a new repository on GitHub:
# 1. Go to https://github.com/new
# 2. Name it "dai-trader" (or whatever you prefer)
# 3. Make it PRIVATE (important for security)
# 4. Don't initialize with README (we already have one)
# 5. Click "Create repository"

# Link your local repo to GitHub (replace YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/dai-trader.git
git branch -M main
git push -u origin main
```

### Step 2: Create DigitalOcean Droplet

1. **Login to DigitalOcean**
   - Go to https://cloud.digitalocean.com

2. **Create Droplet**
   - Click "Create" → "Droplets"
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic
   - **CPU Options**: Regular (Disk type: SSD)
   - **Size**: $6/month (1GB RAM, 1 vCPU) - Perfect for this bot
   - **Datacenter**: Choose closest to you (New York for US East)
   - **Authentication**: SSH Key (recommended) or Password
   - **Hostname**: dai-trader-bot

3. **Wait for Droplet Creation** (1-2 minutes)

4. **Note your Droplet's IP address** (shown in dashboard)

### Step 3: Initial Server Setup

```powershell
# SSH into your droplet (replace YOUR_IP with actual IP)
ssh root@YOUR_IP

# If using password, enter it when prompted
# If using SSH key, it should connect automatically
```

Once connected to your server:

```bash
# Download and run the setup script
wget https://raw.githubusercontent.com/YOUR_USERNAME/dai-trader/main/deploy/digitalocean_setup.sh
chmod +x digitalocean_setup.sh
./digitalocean_setup.sh
```

This will install:
- Python 3.11
- Git
- TA-Lib (technical analysis library)
- All system dependencies

### Step 4: Deploy Your Bot

```bash
# Clone your repository
git clone https://github.com/YOUR_USERNAME/dai-trader.git
cd dai-trader

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Create environment file from example
cp .env.example .env

# Edit configuration with your API keys
nano .env
```

**In nano editor:**
- Add your Alpaca API keys
- Set `ALPACA_PAPER=True` for testing
- Configure your watchlist and strategy
- Press `Ctrl+X`, then `Y`, then `Enter` to save

### Step 5: Test Your Bot

```bash
# Test the connection
python examples.py
# Choose option 2 to verify Alpaca connection

# Run a quick backtest
python -c "from backtester import Backtester; bt = Backtester('momentum', 10000); bt.run_backtest(['AAPL'], '2024-01-01')"

# Test the bot (Ctrl+C to stop after verification)
python trading_bot.py
```

### Step 6: Set Up as System Service (Auto-Start)

This makes your bot run automatically and restart if it crashes:

```bash
# Copy service file to systemd
sudo cp deploy/dai-trader.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable dai-trader

# Start the service
sudo systemctl start dai-trader

# Check status
sudo systemctl status dai-trader
```

### Step 7: Monitor Your Bot

```bash
# View live logs
sudo journalctl -u dai-trader -f

# Check if running
sudo systemctl status dai-trader

# Restart bot
sudo systemctl restart dai-trader

# Stop bot
sudo systemctl stop dai-trader
```

## 🔄 Updating Your Bot

When you make changes locally and want to deploy:

**On your local machine:**
```powershell
git add .
git commit -m "Description of changes"
git push origin main
```

**On your DigitalOcean droplet:**
```bash
cd ~/dai-trader
./deploy/update.sh
```

Or manually:
```bash
cd ~/dai-trader
git pull origin main
source venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart dai-trader
```

## 📊 Monitoring & Maintenance

### View Logs
```bash
# Real-time logs
sudo journalctl -u dai-trader -f

# Last 100 lines
sudo journalctl -u dai-trader -n 100

# Logs from today
sudo journalctl -u dai-trader --since today

# Save logs to file
sudo journalctl -u dai-trader > dai-trader-logs.txt
```

### Check Performance
```bash
# SSH into droplet
ssh root@YOUR_IP

# Check bot status
sudo systemctl status dai-trader

# View database
cd ~/dai-trader
source venv/bin/activate
python examples.py
# Choose option 4 for database stats
```

### System Resources
```bash
# CPU and memory usage
htop

# Disk space
df -h

# Network usage
vnstat
```

## 🔒 Security Best Practices

### 1. Secure SSH Access
```bash
# Disable password authentication (use SSH keys only)
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd
```

### 2. Set Up Firewall
```bash
# Enable UFW firewall
sudo ufw allow OpenSSH
sudo ufw enable
sudo ufw status
```

### 3. Regular Updates
```bash
# Update system weekly
sudo apt-get update
sudo apt-get upgrade -y
```

### 4. Environment Variables Security
- Never commit `.env` file to GitHub (already in `.gitignore`)
- Use DigitalOcean Secrets for sensitive data (optional)

## 💰 Cost Breakdown

| Service | Cost | Purpose |
|---------|------|---------|
| DigitalOcean Droplet (1GB) | $6/month | Runs your bot 24/7 |
| Alpaca Paper Trading | FREE | Testing |
| Alpaca Live Trading | FREE | No commissions |
| GitHub Private Repo | FREE | Code storage |
| **Total (Testing)** | **$6/month** | |

## 🆘 Troubleshooting

### Bot won't start
```bash
# Check logs for errors
sudo journalctl -u dai-trader -n 50

# Test manually
cd ~/dai-trader
source venv/bin/activate
python trading_bot.py
```

### Import errors
```bash
cd ~/dai-trader
source venv/bin/activate
pip install -r requirements.txt --upgrade --force-reinstall
```

### Can't connect to Alpaca
```bash
# Verify API keys
cat .env | grep ALPACA

# Test connection
python examples.py
# Choose option 2
```

### High CPU usage
- This is normal during market hours (9:30 AM - 4:00 PM ET)
- If constantly high, check logs for errors

### Out of memory
- Upgrade to 2GB droplet ($12/month)
- Or optimize watchlist (fewer symbols)

## 📱 Optional: Set Up Alerts

### Email Alerts (via SendGrid - Free tier)
```bash
pip install sendgrid

# Add to .env:
# SENDGRID_API_KEY=your_key
# ALERT_EMAIL=your@email.com
```

### SMS Alerts (via Twilio)
```bash
pip install twilio

# Add to .env:
# TWILIO_ACCOUNT_SID=your_sid
# TWILIO_AUTH_TOKEN=your_token
# ALERT_PHONE=+1234567890
```

## 🎯 Next Steps

1. ✅ Deploy to DigitalOcean
2. ✅ Test with paper trading ($0 virtual money)
3. ✅ Run for 1-2 months to verify strategy
4. ✅ Monitor performance and adjust settings
5. ✅ When confident, switch to live trading ($500 minimum)

## 📞 Quick Reference Commands

```bash
# Start bot
sudo systemctl start dai-trader

# Stop bot
sudo systemctl stop dai-trader

# Restart bot
sudo systemctl restart dai-trader

# View logs
sudo journalctl -u dai-trader -f

# Update code
cd ~/dai-trader && git pull && sudo systemctl restart dai-trader

# Check status
sudo systemctl status dai-trader

# SSH to server
ssh root@YOUR_IP
```

---

**Remember**: Always test with paper trading first! Your bot will run 24/5 (Monday-Friday, market hours) automatically on DigitalOcean.
