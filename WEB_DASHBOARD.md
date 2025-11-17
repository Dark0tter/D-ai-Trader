# Web Dashboard Setup Guide

Complete guide to deploying the Dai Trader web dashboard on your DigitalOcean server.

## 🚀 Quick Deploy

SSH into your server and run these commands:

```bash
cd ~/dai-trader
git pull
source venv/bin/activate
pip install flask flask-cors
python3 web_dashboard.py
```

Then access: **http://YOUR_SERVER_IP:5000**

Default password: `dai-trader-2025`

---

## 📋 Full Production Setup

### Step 1: Pull Latest Code

```bash
cd ~/dai-trader
git pull
```

### Step 2: Install Dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Environment (Optional)

Create or edit your `.env` file to add dashboard settings:

```bash
nano .env
```

Add these lines:

```bash
# Web Dashboard Settings
DASHBOARD_PASSWORD=your-secure-password-here
DASHBOARD_PORT=5000
DASHBOARD_HOST=0.0.0.0
```

### Step 4: Install as System Service

```bash
# Copy service file
sudo cp deploy/dai-trader-web.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable dai-trader-web

# Start the service
sudo systemctl start dai-trader-web
```

### Step 5: Check Status

```bash
# View service status
sudo systemctl status dai-trader-web

# View live logs
sudo journalctl -u dai-trader-web -f
```

---

## 🌐 Domain Name Setup

### Option 1: Use IP Address Directly
Access: `http://159.65.247.84:5000`

### Option 2: Setup Domain with SSL

1. **Point your domain to server:**
   - Add A record: `@` → `159.65.247.84`
   - Add A record: `dashboard` → `159.65.247.84`

2. **Install Nginx:**
```bash
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx -y
```

3. **Create Nginx config:**
```bash
sudo nano /etc/nginx/sites-available/dai-trader
```

Paste this configuration (replace `yourdomain.com`):

```nginx
server {
    listen 80;
    server_name yourdomain.com dashboard.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

4. **Enable the site:**
```bash
sudo ln -s /etc/nginx/sites-available/dai-trader /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

5. **Get SSL certificate:**
```bash
sudo certbot --nginx -d yourdomain.com -d dashboard.yourdomain.com
```

Now access: **https://yourdomain.com** 🔒

---

## 📱 Features

Your dashboard includes:

### Real-Time Monitoring
- ✅ Live portfolio value updates (every 10 seconds)
- ✅ Current positions with P&L
- ✅ Recent trade history
- ✅ Performance charts

### AI Learning Stats
- 🧠 States learned
- 🧠 AI win rate
- 🧠 Average reward
- 🧠 Exploration rate

### Account Overview
- 💰 Portfolio value
- 💰 Cash available
- 💰 Buying power
- 💰 Active positions

### Trading Metrics
- 📊 Total trades
- 📊 Win rate
- 📊 Total P&L
- 📊 Average P&L per trade

### Live Logs
- 📝 Real-time bot activity
- 📝 Trade executions
- 📝 AI learning updates

---

## 🔐 Security

### Change Default Password

Edit the systemd service file:

```bash
sudo nano /etc/systemd/system/dai-trader-web.service
```

Change this line:
```
Environment="DASHBOARD_PASSWORD=your-secure-password-123"
```

Restart the service:
```bash
sudo systemctl daemon-reload
sudo systemctl restart dai-trader-web
```

### Firewall Setup

```bash
# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow dashboard port (if not using Nginx)
sudo ufw allow 5000/tcp

# Enable firewall
sudo ufw enable
```

---

## 🛠️ Management Commands

### Start/Stop Dashboard

```bash
# Start
sudo systemctl start dai-trader-web

# Stop
sudo systemctl stop dai-trader-web

# Restart
sudo systemctl restart dai-trader-web

# Status
sudo systemctl status dai-trader-web
```

### View Logs

```bash
# Live logs
sudo journalctl -u dai-trader-web -f

# Last 100 lines
sudo journalctl -u dai-trader-web -n 100

# Today's logs
sudo journalctl -u dai-trader-web --since today
```

### Update Dashboard

```bash
cd ~/dai-trader
git pull
sudo systemctl restart dai-trader-web
```

---

## 📊 API Endpoints

The dashboard provides these API endpoints:

- `GET /api/status` - Account and positions
- `GET /api/trades` - Recent trades
- `GET /api/performance` - Performance metrics
- `GET /api/ai-stats` - AI learning statistics
- `GET /api/logs` - Recent log entries

---

## 🐛 Troubleshooting

### Dashboard won't start

```bash
# Check logs
sudo journalctl -u dai-trader-web -n 50

# Test manually
cd ~/dai-trader
source venv/bin/activate
python3 web_dashboard.py
```

### Can't access from browser

```bash
# Check if running
sudo systemctl status dai-trader-web

# Check if port is open
sudo netstat -tulpn | grep 5000

# Check firewall
sudo ufw status
```

### Database errors

```bash
# Ensure main bot created the database
sudo systemctl status dai-trader

# Check database file exists
ls -la ~/dai-trader/trading_bot.db
```

---

## 🎨 Customization

### Change Port

Edit `.env` or service file:
```
DASHBOARD_PORT=8080
```

### Change Host (bind to specific IP)

```
DASHBOARD_HOST=127.0.0.1  # Local only
DASHBOARD_HOST=0.0.0.0    # All interfaces (default)
```

---

## 📱 Mobile Access

The dashboard is fully responsive and works great on mobile devices!

Simply access the same URL from your phone or tablet.

---

## 🔄 Auto-Updates

The dashboard auto-refreshes every 10 seconds to show:
- Latest portfolio values
- New positions
- Recent trades
- Updated AI stats
- Fresh logs

---

## ✨ Next Steps

1. ✅ Deploy dashboard
2. ✅ Setup domain name (optional)
3. ✅ Configure SSL (optional)
4. ✅ Change default password
5. ✅ Bookmark your dashboard URL
6. ✅ Monitor your AI trader from anywhere!

---

**Need help?** Check the logs or test manually with `python3 web_dashboard.py`

Happy trading! 🚀📈
