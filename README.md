# Delta Exchange SOL Scalping Bot

This is a minimal, risk-managed trading bot scaffold built around Delta Exchange's
official Python REST client. It places an entry order, a stop-loss, and an optional
take-profit using a simple trend + pullback strategy.

Important: rotate any API keys you may have shared publicly. Never commit secrets
to GitHub or paste them into chat.

## References
- Delta REST client on PyPI: https://pypi.org/project/delta-rest-client/
- Delta API docs: https://docs.delta.exchange/#introduction

## Quick start (local)
1. Create a virtual environment and install deps:
   - `python3 -m venv .venv`
   - `. .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Create a `.env` file from `env.example` and fill in your values.
3. Run:
   - `python main.py`

## Environment variables
See `env.example` for all options. Required:
- `DELTA_API_KEY`
- `DELTA_API_SECRET`
- `SYMBOL` (example: `SOLUSD`)

Optional but recommended:
- `PRODUCT_ID` (numeric id from Delta products list)
- `QUOTE_ASSET_ID` (asset id for balance lookup)
- `DRY_RUN=true` to test live data without placing orders
- `JOURNAL_PATH=journals/trade_journal.csv` to log every signal/trade
- `LEVERAGE=25` and `DAILY_CAPITAL=10000` to cap max notional size

## EC2 deployment
This bot is designed to run continuously on EC2 with systemd.

1. SSH to your EC2 instance and create the app directory:
   - `sudo mkdir -p /opt/crypto-bot`
   - `sudo chown $USER:$USER /opt/crypto-bot`
2. Copy the repo to `/opt/crypto-bot` (the GitHub Action does this).
3. Create `/opt/crypto-bot/.env` with your secrets and config.
4. Run:
   - `cd /opt/crypto-bot`
   - `./scripts/ec2_setup.sh`
5. Check status:
   - `systemctl status crypto-bot`
   - `journalctl -u crypto-bot -f`

## GitHub Actions deploy
Add these secrets in your GitHub repo:
- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`

Push to `main` and the workflow will sync the repo to `/opt/crypto-bot`
and restart the service.

## Notes
- This scaffold assumes the Delta REST client methods are available in your
  installed version. If any method names differ, adjust `bot/delta_client.py`.
- Use testnet first and verify orders before trading live.
