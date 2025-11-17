#!/bin/bash
# Quick deployment script for dashboard updates
# Run on server: bash deploy_dashboard.sh

set -e

echo "============================================"
echo "Dai Trader Dashboard - Deployment"
echo "============================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd /root/dai-trader

# Pull latest changes
echo -e "${GREEN}[1/5] Pulling latest code...${NC}"
git pull

# Activate virtual environment
echo -e "${GREEN}[2/5] Activating virtual environment...${NC}"
source venv/bin/activate

# Install new dependencies
echo -e "${GREEN}[3/5] Installing dependencies...${NC}"
pip install -q flask-limiter

# Restart dashboard service
echo -e "${GREEN}[4/5] Restarting dashboard service...${NC}"
sudo systemctl restart dai-trader-web

# Show status
echo -e "${GREEN}[5/5] Checking service status...${NC}"
sleep 2
sudo systemctl status dai-trader-web --no-pager -l

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "Dashboard: ${YELLOW}http://$(curl -s ifconfig.me):5000${NC}"
echo -e "Password: ${YELLOW}Check DASHBOARD_PASSWORD in .env${NC}"
echo ""
echo -e "${YELLOW}To view logs:${NC}"
echo "  sudo journalctl -u dai-trader-web -f"
echo ""
echo -e "${YELLOW}To setup domain with SSL:${NC}"
echo "  cd /root/dai-trader/deploy"
echo "  sudo bash setup_domain.sh"
echo ""
