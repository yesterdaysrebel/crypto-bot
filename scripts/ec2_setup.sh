#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/crypto-bot}"
BOT_USER="${BOT_USER:-ubuntu}"
PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"

if [[ ! -d "$APP_DIR" ]]; then
  echo "APP_DIR not found: $APP_DIR"
  exit 1
fi

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python not found at $PYTHON_BIN"
  exit 1
fi

if [[ ! -d "$APP_DIR/.venv" ]]; then
  "$PYTHON_BIN" -m venv "$APP_DIR/.venv"
fi

"$APP_DIR/.venv/bin/pip" install --upgrade pip
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"

sudo install -m 0644 "$APP_DIR/scripts/crypto-bot.service" /etc/systemd/system/crypto-bot.service
sudo sed -i.bak "s|User=ubuntu|User=$BOT_USER|g" /etc/systemd/system/crypto-bot.service
sudo sed -i.bak "s|/opt/crypto-bot|$APP_DIR|g" /etc/systemd/system/crypto-bot.service

sudo systemctl daemon-reload
sudo systemctl enable crypto-bot
sudo systemctl restart crypto-bot
