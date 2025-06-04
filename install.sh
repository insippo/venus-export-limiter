#!/bin/bash

set -e

REPO_URL="https://github.com/insippo/venus-export-limiter.git"
INSTALL_DIR="/data/dbus-limit"
SERVICE_NAME="venus-export-limiter.service"

echo "📦 Kloonime reposid ja paigaldame..."

# Loo sihtkaust kui ei eksisteeri
mkdir -p /data

# Klooni või uuenda repo
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "📁 Repo juba olemas, tõmbame uuendused..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "📥 Kloonime uue repo..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Sea õigused
chmod +x limit-control.py
touch limit.log
chown root:root limit.log

# Kopeeri systemd teenuse fail
cp systemd/$SERVICE_NAME /etc/systemd/system/

# Lae systemd uuesti ja käivita teenus
systemctl daemon-reexec
systemctl enable --now $SERVICE_NAME

echo "✅ Paigaldus lõpetatud. Teenus töötab."
