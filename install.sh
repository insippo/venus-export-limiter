#!/bin/bash

set -e

REPO_URL="https://github.com/insippo/venus-export-limiter.git"
INSTALL_DIR="/data/dbus-limit"
SERVICE_NAME="venus-export-limiter.service"
# Expected commit hash for security verification (should be updated for each release)
EXPECTED_COMMIT_HASH="REPLACE_WITH_ACTUAL_COMMIT_HASH"

echo "📦 Kloonime reposid ja paigaldame..."

# Check if running as root (required for system installation)
if [ "$EUID" -ne 0 ]; then
    echo "❌ Palun käivita administraatori õigustes (sudo)"
    exit 1
fi

# Loo sihtkaust kui ei eksisteeri
mkdir -p /data

# Klooni või uuenda repo
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "📁 Repo juba olemas, tõmbame uuendused..."
    cd "$INSTALL_DIR"
    
    # Verify current state before updating
    current_commit=$(git rev-parse HEAD)
    echo "🔍 Praegune commit: $current_commit"
    
    git fetch origin
    latest_commit=$(git rev-parse origin/master)
    echo "🔍 Uusim commit: $latest_commit"
    
    # Only update if we can verify the commit (in production, check against known good hash)
    if [ "$EXPECTED_COMMIT_HASH" != "REPLACE_WITH_ACTUAL_COMMIT_HASH" ]; then
        if [ "$latest_commit" != "$EXPECTED_COMMIT_HASH" ]; then
            echo "⚠️  HOIATUS: Commit hash ei vasta oodatule!"
            echo "Oodatud: $EXPECTED_COMMIT_HASH"
            echo "Saadud: $latest_commit"
            read -p "Kas jätkata? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        fi
    fi
    
    git pull
else
    echo "📥 Kloonime uue repo..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    
    # Verify the cloned commit if hash is provided
    if [ "$EXPECTED_COMMIT_HASH" != "REPLACE_WITH_ACTUAL_COMMIT_HASH" ]; then
        current_commit=$(git rev-parse HEAD)
        if [ "$current_commit" != "$EXPECTED_COMMIT_HASH" ]; then
            echo "❌ Commit hash ei vasta oodatule! Katkestan turvalisuse huvides."
            echo "Oodatud: $EXPECTED_COMMIT_HASH"
            echo "Saadud: $current_commit"
            rm -rf "$INSTALL_DIR"
            exit 1
        fi
        echo "✅ Commit hash kinnitatud"
    else
        echo "⚠️  HOIATUS: Commit hash kontroll puudub - kasuta omal vastutusel"
    fi
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
