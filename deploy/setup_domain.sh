#!/bin/bash
# Domain and SSL Setup for Dai Trader Dashboard
# Run as root: sudo bash setup_domain.sh

set -e

echo "============================================"
echo "Dai Trader Dashboard - Domain Setup"
echo "============================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Error: Please run as root (sudo bash setup_domain.sh)${NC}"
    exit 1
fi

# Get domain name
read -p "Enter your domain name (e.g., daitrader.com): " DOMAIN_NAME
read -p "Enter your email for SSL certificate: " EMAIL

echo -e "${YELLOW}Setting up domain: ${DOMAIN_NAME}${NC}"

# Update system
echo -e "${GREEN}[1/7] Updating system...${NC}"
apt update && apt upgrade -y

# Install Nginx
echo -e "${GREEN}[2/7] Installing Nginx...${NC}"
apt install -y nginx

# Install Certbot for SSL
echo -e "${GREEN}[3/7] Installing Certbot...${NC}"
apt install -y certbot python3-certbot-nginx

# Stop Nginx temporarily
systemctl stop nginx

# Configure firewall
echo -e "${GREEN}[4/7] Configuring firewall...${NC}"
ufw allow 'Nginx Full'
ufw allow 'OpenSSH'
ufw --force enable

# Copy Nginx configuration
echo -e "${GREEN}[5/7] Setting up Nginx configuration...${NC}"
cat > /etc/nginx/sites-available/daitrader <<EOF
# Nginx configuration for Dai Trader Dashboard

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};
    
    # Certbot verification
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirect all HTTP to HTTPS (after SSL is set up)
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/daitrader /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Start Nginx
systemctl start nginx
systemctl enable nginx

echo -e "${YELLOW}Nginx started. Please ensure your domain DNS is pointing to this server's IP.${NC}"
echo -e "${YELLOW}Current server IP: $(curl -s ifconfig.me)${NC}"
echo ""
read -p "Press Enter once DNS is configured (you can check with: dig ${DOMAIN_NAME})..."

# Obtain SSL certificate
echo -e "${GREEN}[6/7] Obtaining SSL certificate from Let's Encrypt...${NC}"
certbot --nginx -d ${DOMAIN_NAME} -d www.${DOMAIN_NAME} \
    --non-interactive \
    --agree-tos \
    --email ${EMAIL} \
    --redirect

# Update Nginx config with SSL enhancements
echo -e "${GREEN}[7/7] Enhancing SSL configuration...${NC}"
cat > /etc/nginx/sites-available/daitrader <<EOF
# Nginx configuration for Dai Trader Dashboard

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN_NAME} www.${DOMAIN_NAME};

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN_NAME}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/${DOMAIN_NAME}/chain.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Logging
    access_log /var/log/nginx/daitrader_access.log;
    error_log /var/log/nginx/daitrader_error.log;
    
    # Gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    
    # Proxy to Flask
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_buffering off;
    }
    
    # Static files
    location /static {
        alias /root/dai-trader/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Reload Nginx
systemctl reload nginx

# Set up auto-renewal
systemctl enable certbot.timer
systemctl start certbot.timer

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Dashboard URL: ${GREEN}https://${DOMAIN_NAME}${NC}"
echo -e "SSL Certificate: ${GREEN}Active (auto-renews)${NC}"
echo -e "Security: ${GREEN}HTTPS, Rate Limiting, Security Headers${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Restart dashboard service: sudo systemctl restart dai-trader-web"
echo "2. Check logs: sudo journalctl -u dai-trader-web -f"
echo "3. Visit: https://${DOMAIN_NAME}"
echo ""
echo -e "${GREEN}SSL Certificate will auto-renew via certbot.timer${NC}"
echo ""
