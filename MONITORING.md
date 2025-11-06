# Monitoring Your Trading Bot on EC2

## Should You Keep the Bot Running?

**Yes, but with caution:**
- ✅ Keep it running if you want to test the trading strategy
- ⚠️ Start with small position sizes and monitor closely
- ⚠️ The bot will place REAL trades with REAL money
- ⚠️ Monitor it regularly, especially in the first few days

**Recommendations:**
1. **Start with paper trading** (if possible) or very small amounts
2. **Monitor daily** for the first week
3. **Set up alerts** for errors or unexpected behavior
4. **Review trades regularly** to ensure the strategy is working as expected

## How to Check Bot Status

### 1. Check if Bot is Running

```bash
# SSH into your EC2 instance
ssh -i ~/.ssh/your-key.pem ec2-user@<INSTANCE_IP>

# Check service status
sudo systemctl status trading-bot

# Check if service is active
sudo systemctl is-active trading-bot
```

### 2. View Live Logs

```bash
# View real-time logs
sudo journalctl -u trading-bot -f

# Or view the log file directly
tail -f /opt/trading-bot/trading_bot.log

# View last 100 lines
tail -100 /opt/trading-bot/trading_bot.log
```

### 3. Check Recent Activity

```bash
# View recent log entries
sudo journalctl -u trading-bot -n 50 --no-pager

# Search for specific events
sudo journalctl -u trading-bot | grep "Signal generated"
sudo journalctl -u trading-bot | grep "Order placed"
sudo journalctl -u trading-bot | grep "ERROR"
```

## How to Check Trades

### 1. View Trade Logs (CSV)

```bash
# List trade log files
ls -lh /opt/trading-bot/trade_logs/

# View today's trades
cat /opt/trading-bot/trade_logs/trades_$(date +%Y%m%d).csv

# View all trades
cat /opt/trading-bot/trade_logs/trades_*.csv | column -t -s,
```

### 2. View Trade Logs (JSON)

```bash
# View today's trades in JSON format
cat /opt/trading-bot/trade_logs/trades_$(date +%Y%m%d).jsonl | jq '.'

# Count total trades
cat /opt/trading-bot/trade_logs/trades_*.jsonl | wc -l

# View last 5 trades
tail -5 /opt/trading-bot/trade_logs/trades_$(date +%Y%m%d).jsonl | jq '.'
```

### 3. Check Active Orders and Positions

```bash
# View recent activity for orders
sudo journalctl -u trading-bot | grep -i "order" | tail -20

# View recent activity for positions
sudo journalctl -u trading-bot | grep -i "position" | tail -20
```

## How to Check Trading Signals

### 1. View Signal Logs (CSV)

```bash
# View today's signals
cat /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).csv

# View all signals
cat /opt/trading-bot/trade_logs/signals_*.csv | column -t -s,

# Count signals by type
cat /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).csv | cut -d',' -f4 | sort | uniq -c
```

### 2. View Signal Logs (JSON)

```bash
# View today's signals in JSON format
cat /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).jsonl | jq '.'

# View only BUY signals
cat /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).jsonl | jq 'select(.signal_action=="buy")'

# View only SELL signals
cat /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).jsonl | jq 'select(.signal_action=="sell")'

# View signals with confidence > 0.8
cat /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).jsonl | jq 'select(.signal_confidence > 0.8)'
```

### 3. View Signals in Logs

```bash
# View all signals from logs
sudo journalctl -u trading-bot | grep "SIGNAL:" | tail -20

# View signals with details
sudo journalctl -u trading-bot | grep "Signal generated" | tail -20
```

## Quick Status Check Script

Create a script to quickly check bot status:

```bash
# Create monitoring script
cat > /opt/trading-bot/check_status.sh << 'EOF'
#!/bin/bash
echo "=== Trading Bot Status ==="
echo ""
echo "Service Status:"
sudo systemctl is-active trading-bot
echo ""
echo "Recent Activity (last 10 lines):"
sudo journalctl -u trading-bot -n 10 --no-pager
echo ""
echo "Today's Signals:"
if [ -f "/opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).csv" ]; then
    echo "Total signals: $(tail -n +2 /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).csv | wc -l)"
    echo "Buy signals: $(grep -c ",buy," /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).csv || echo 0)"
    echo "Sell signals: $(grep -c ",sell," /opt/trading-bot/trade_logs/signals_$(date +%Y%m%d).csv || echo 0)"
else
    echo "No signals file found for today"
fi
echo ""
echo "Today's Trades:"
if [ -f "/opt/trading-bot/trade_logs/trades_$(date +%Y%m%d).csv" ]; then
    echo "Total trades: $(tail -n +2 /opt/trading-bot/trade_logs/trades_$(date +%Y%m%d).csv | wc -l)"
else
    echo "No trades file found for today"
fi
EOF

chmod +x /opt/trading-bot/check_status.sh
```

Then run:
```bash
/opt/trading-bot/check_status.sh
```

## View from AWS CloudWatch

### 1. CloudWatch Logs

```bash
# View logs from CloudWatch (if configured)
aws logs tail /aws/ec2/trading-bot --follow --region ap-south-1

# View last 100 log entries
aws logs tail /aws/ec2/trading-bot --since 1h --region ap-south-1
```

### 2. AWS Console

1. Go to AWS Console → CloudWatch → Logs
2. Find log group: `/aws/ec2/trading-bot`
3. View log streams to see real-time activity

## Check Bot Performance

### 1. View P&L Summary

```bash
# View P&L from logs
sudo journalctl -u trading-bot | grep "Total P&L" | tail -20

# View cycle summaries
sudo journalctl -u trading-bot | grep "Cycle completed" | tail -20
```

### 2. Check Model Training

```bash
# View model training logs
sudo journalctl -u trading-bot | grep -i "train" | tail -20

# Check if models exist
ls -lh /opt/trading-bot/models/
```

## Common Monitoring Commands

### Quick Health Check

```bash
# Check if bot is running
sudo systemctl is-active trading-bot && echo "✅ Bot is running" || echo "❌ Bot is not running"

# Check for errors in last hour
sudo journalctl -u trading-bot --since "1 hour ago" | grep -i error | wc -l

# Check last successful cycle
sudo journalctl -u trading-bot | grep "Cycle completed" | tail -1
```

### View Specific Information

```bash
# View all orders placed today
sudo journalctl -u trading-bot --since today | grep "Order placed"

# View all signals generated today
sudo journalctl -u trading-bot --since today | grep "Signal generated"

# View errors
sudo journalctl -u trading-bot --since today | grep -i error

# View warnings
sudo journalctl -u trading-bot --since today | grep -i warning
```

## Restart/Stop the Bot

```bash
# Restart the bot
sudo systemctl restart trading-bot

# Stop the bot
sudo systemctl stop trading-bot

# Start the bot
sudo systemctl start trading-bot

# View restart history
sudo journalctl -u trading-bot | grep "Started\|Stopped"
```

## Troubleshooting

### Bot Not Running?

```bash
# Check service status
sudo systemctl status trading-bot

# Check for errors
sudo journalctl -u trading-bot -n 50 --no-pager

# Check if .env file exists and has correct values
cat /opt/trading-bot/.env | grep -v "SECRET\|KEY"
```

### No Trades Being Made?

1. Check if signals are being generated:
   ```bash
   sudo journalctl -u trading-bot | grep "Signal generated" | tail -10
   ```

2. Check if signals are HOLD:
   ```bash
   sudo journalctl -u trading-bot | grep "HOLD" | tail -10
   ```

3. Check API connectivity:
   ```bash
   sudo journalctl -u trading-bot | grep -i "api\|error" | tail -20
   ```

4. Check if model is trained:
   ```bash
   ls -lh /opt/trading-bot/models/
   ```

## Recommended Monitoring Schedule

- **First Week**: Check daily
- **After First Week**: Check every 2-3 days
- **Set up alerts**: For errors, unexpected behavior, or large P&L changes

## Next Steps

1. **Set up CloudWatch alarms** for errors
2. **Create a dashboard** to monitor key metrics
3. **Set up email/SNS notifications** for important events
4. **Regularly review trade logs** to understand bot behavior

