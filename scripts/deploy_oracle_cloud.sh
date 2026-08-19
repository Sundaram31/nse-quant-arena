#!/bin/bash
# ==============================================================================
# NSE Quant Strategy Arena - Oracle Cloud (OCI Always Free) 1-Click Deployment
# ==============================================================================

set -e

echo "🚀 [1/5] Updating system packages on Oracle VM..."
if [ -f /etc/debian_version ]; then
    sudo apt update && sudo apt install -y python3 python3-pip python3-venv git htop iptables-persistent
elif [ -f /etc/oracle-release ] || [ -f /etc/redhat-release ]; then
    sudo dnf install -y python3 python3-pip git htop
fi

echo "📦 [2/5] Creating Python Virtual Environment & Installing Dependencies..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install streamlit pandas numpy altair requests yfinance scipy

echo "🔓 [3/5] Opening Port 8501 in Linux Firewall..."
if command -v iptables &> /dev/null; then
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 8501 -j ACCEPT || true
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT || true
    sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT || true
    sudo netfilter-persistent save || true
fi

echo "⚙️ [4/5] Creating 24/7 Systemd Service (nse-quant.service)..."
APP_DIR=/Users/sundaram/Documents/antigravity
SERVICE_FILE="[Unit]
Description=NSE Quantitative Strategy Arena Dashboard
After=network.target

[Service]
User=sundaram
WorkingDirectory=
ExecStart=/venv/bin/streamlit run /nse_system/dashboard/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target"

echo "" | sudo tee /etc/systemd/system/nse-quant.service > /dev/null
sudo systemctl daemon-reload
sudo systemctl enable nse-quant.service
sudo systemctl restart nse-quant.service

echo "⏰ [5/5] Configuring Automated Daily EOD Sync (Mon-Fri 16:00 IST)..."
(crontab -l 2>/dev/null | grep -v 'cron_sync.py' ; echo "30 10 * * 1-5 cd  && /venv/bin/python3 scripts/cron_sync.py >> /tmp/nse_cron.log 2>&1") | crontab -

echo ""
echo "=============================================================================="
echo "✅ NSE Quant Arena is now running 24/7 on Oracle Cloud!"
echo "📱 Access on Mobile/Desktop at: http://:8501"
echo "=============================================================================="
