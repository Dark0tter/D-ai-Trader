# Dashboard Enhancement Deployment Guide

## Updates Included

### ✅ 1. Responsive Scrolling
- **Horizontal scroll** on tables for small screens
- **Touch-friendly** scrolling on mobile devices
- **Responsive breakpoints** for tablets and phones
- **Custom scrollbars** for better UX

### ✅ 2. User Controls
- **Safe Mode Toggle** - Enable/disable automatic risk reduction
- **Bot Start/Stop** - Control trading bot from dashboard
- **Risk Level Selector** - Conservative, Moderate, or Aggressive
- **AI Learning Toggle** - Enable/disable reinforcement learning
- **Alerts Toggle** - Control notifications
- **Emergency Stop** - Immediately close all positions and halt trading

### ✅ 3. Security Features
- **HTTPS/SSL** - Encrypted connections via Let's Encrypt
- **Rate Limiting** - 200/day, 50/hour, 10/minute on login
- **Secure Headers** - HSTS, X-Frame-Options, CSP, etc.
- **Constant-time Password Comparison** - Prevents timing attacks
- **Session Management** - Secure, persistent sessions
- **CORS Protection** - Configurable allowed origins

### ✅ 4. Domain Support
- **Custom Domain** - Professional branded URL
- **Nginx Reverse Proxy** - Production-grade web server
- **Auto SSL Renewal** - Certbot automatic certificate updates
- **Gzip Compression** - Faster page loads

## Deployment Steps

### Step 1: Commit and Push Changes

```powershell
cd "K:\Dai Trader"
git add .
git commit -m "Add responsive dashboard with user controls and security

Features:
- Responsive scrolling for all screen sizes
- User control toggles (Safe Mode, Risk Level, Bot Control)
- Security: HTTPS, rate limiting, secure headers
- Domain setup with Nginx and SSL
- Emergency stop button
- Real-time safe mode status display"
git push
```

### Step 2: Connect to Server

```powershell
ssh root@159.65.247.84
# Password: I2T2CMFP,qa
```

### Step 3: Pull Updates

```bash
cd /root/dai-trader
git pull
```

### Step 4: Install New Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install flask-limiter for rate limiting
pip install flask-limiter

# Verify installation
pip list | grep flask
```

### Step 5: Update Environment Variables (Optional)

```bash
# Edit .env file
nano .env

# Add these optional settings:
# DASHBOARD_PASSWORD=your-secure-password-here
# ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
# DASHBOARD_SECRET_KEY=generate-with-secrets.token_hex(32)

# Save: Ctrl+O, Enter, Ctrl+X
```

### Step 6: Restart Dashboard Service

```bash
sudo systemctl restart dai-trader-web
sudo systemctl status dai-trader-web

# Check logs
sudo journalctl -u dai-trader-web -f
```

### Step 7: Domain Setup (If you have a domain)

**First, configure DNS:**
1. Go to your domain registrar (GoDaddy, Namecheap, etc.)
2. Add A record: `@` → `159.65.247.84`
3. Add A record: `www` → `159.65.247.84`
4. Wait 5-60 minutes for DNS propagation

**Verify DNS:**
```bash
# Check if domain resolves to your server
dig yourdomain.com
nslookup yourdomain.com
```

**Run domain setup script:**
```bash
cd /root/dai-trader/deploy
chmod +x setup_domain.sh
sudo bash setup_domain.sh

# Follow prompts:
# - Enter domain name (e.g., daitrader.com)
# - Enter email for SSL certificate
# - Wait for DNS confirmation
# - Script will:
#   * Install Nginx
#   * Configure reverse proxy
#   * Obtain SSL certificate
#   * Set up auto-renewal
#   * Enable HTTPS
```

### Step 8: Test Dashboard

**Via IP Address:**
```
http://159.65.247.84:5000
```

**Via Domain (after setup):**
```
https://yourdomain.com
```

**Login credentials:**
- Password: (DASHBOARD_PASSWORD from .env, default: dai-trader-2025)

## New Dashboard Features

### Control Panel

**Safe Mode:**
- Toggle on/off automatic risk reduction
- View real-time danger score (0-100)
- See capital multiplier based on market conditions

**Bot Control:**
- Start/Stop trading bot
- Bot status indicator (Running/Stopped)

**Risk Level:**
- Conservative: 10% High, 20% Medium, 70% Low Risk
- Moderate: 20% High, 30% Medium, 50% Low Risk (default)
- Aggressive: 40% High, 35% Medium, 25% Low Risk
- Real-time visualization of allocation

**AI Learning:**
- Enable/disable reinforcement learning
- Bot continues trading without RL if disabled

**Alerts:**
- Enable/disable notifications
- Controls logging verbosity

**Emergency Stop:**
- Double confirmation required
- Immediately closes ALL positions
- Halts trading bot
- Use only in emergencies

### Responsive Design

**Mobile/Tablet:**
- Tables scroll horizontally
- Controls stack vertically
- Touch-friendly buttons
- Readable on small screens

**Desktop:**
- Full-width layouts
- Grid-based responsive cards
- Optimal spacing and sizing

## Security Checklist

✅ **HTTPS Enabled** - All traffic encrypted
✅ **Rate Limiting** - Prevents brute force attacks
✅ **Secure Headers** - HSTS, XSS protection, frame denial
✅ **Session Security** - Cryptographically secure sessions
✅ **CORS Protection** - Only allowed origins
✅ **Constant-time Auth** - No timing leaks
✅ **Firewall Rules** - UFW enabled (SSH, HTTP, HTTPS only)

## Monitoring

**Check Dashboard Logs:**
```bash
sudo journalctl -u dai-trader-web -n 100 -f
```

**Check Nginx Logs:**
```bash
sudo tail -f /var/log/nginx/daitrader_access.log
sudo tail -f /var/log/nginx/daitrader_error.log
```

**Check SSL Certificate:**
```bash
sudo certbot certificates
```

**Test SSL Grade:**
```
https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com
```

## Troubleshooting

### Dashboard Not Loading

**Check service:**
```bash
sudo systemctl status dai-trader-web
sudo systemctl restart dai-trader-web
```

**Check port:**
```bash
sudo netstat -tulpn | grep 5000
```

**Check logs:**
```bash
sudo journalctl -u dai-trader-web -n 50
```

### Nginx Issues

**Test config:**
```bash
sudo nginx -t
```

**Restart Nginx:**
```bash
sudo systemctl restart nginx
```

**Check Nginx status:**
```bash
sudo systemctl status nginx
```

### SSL Certificate Issues

**Renew manually:**
```bash
sudo certbot renew --dry-run
sudo certbot renew
```

**Check auto-renewal:**
```bash
sudo systemctl status certbot.timer
```

### Control Buttons Not Working

**Check browser console:**
- F12 → Console tab
- Look for JavaScript errors

**Clear cache:**
- Ctrl+Shift+R (hard refresh)

**Check API endpoints:**
```bash
# From server
curl http://localhost:5000/api/bot-state
```

## Configuration Files

**Bot State File:**
- Location: `/root/dai-trader/bot_state.json`
- Stores: Safe mode, risk level, bot status
- Auto-created on first use

**Nginx Config:**
- Location: `/etc/nginx/sites-available/daitrader`
- Symlink: `/etc/nginx/sites-enabled/daitrader`

**SSL Certificates:**
- Location: `/etc/letsencrypt/live/yourdomain.com/`
- Auto-renewal: `certbot.timer` (checks twice daily)

## API Endpoints

**Control Endpoints:**
- `GET /api/bot-state` - Get current configuration
- `POST /api/bot-state` - Update configuration
- `POST /api/emergency-stop` - Emergency shutdown
- `GET /api/safe-mode-status` - Safe mode status

**Existing Endpoints:**
- `GET /api/status` - Account and positions
- `GET /api/trades` - Recent trades
- `GET /api/performance` - Performance metrics
- `GET /api/ai-stats` - AI learning stats
- `GET /api/logs` - Recent log entries

## Next Steps

1. **Test Controls** - Toggle each setting and verify behavior
2. **Monitor Safe Mode** - Watch danger score during market hours
3. **Set Strong Password** - Update DASHBOARD_PASSWORD in .env
4. **Configure Domain** - Professional branded dashboard
5. **Enable Alerts** - Get notified of trades and risks
6. **Test Emergency Stop** - Verify it works (outside market hours)

## Support

**Dashboard Issues:**
- Check `/root/dai-trader/bot_state.json`
- Restart: `sudo systemctl restart dai-trader-web`

**Trading Bot Issues:**
- Check `/root/dai-trader/bot_state.json` - bot_running=true
- Restart: `sudo systemctl restart dai-trader`

**Server Issues:**
- Reboot: `sudo reboot`
- Check disk: `df -h`
- Check memory: `free -m`
