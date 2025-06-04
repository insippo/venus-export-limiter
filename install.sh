#!/bin/bash

set -e

echo "📦 Paigaldan Venus Export Limiter'i..."

INSTALL_DIR="/data/dbus-limit"
SERVICE_NAME="venus-export-limiter.service"

# Loo sihtkaust
mkdir -p $INSTALL_DIR

# Kopeeri failid
cp config.py limit-control.py $INSTALL_DIR/
cp systemd/$SERVICE_NAME /etc/systemd/system/

# Sea õigused
chmod +x $INSTALL_DIR/limit-control.py

# Loo logifail kui vaja
touch $INSTALL_DIR/limit.log
chown root:root $INSTALL_DIR/limit.log

# Luba ja käivita teenus
systemctl daemon-reexec
systemctl enable --now $SERVICE_NAME

echo "✅ Paigaldus valmis. Teenus käivitati."
