# Crypto Trading Bot for Delta Exchange

An AI/ML-powered trading bot for Delta Exchange India that runs multiple trading strategies concurrently on a single EC2 instance with automated AWS deployment and cost optimization.

## Features

- 🤖 **AI/ML Trading**: Uses machine learning models (Random Forest, Gradient Boosting) for price prediction
- 📊 **Data Collection**: Collects OHLC, orderbook, and trade data from Delta Exchange
- 🔄 **Multiple Strategies**: Run multiple trading strategies simultaneously on the same instance
- ☁️ **AWS Deployment**: Automated deployment to AWS EC2 with minimal running costs (~$3-6/month)
- 🔒 **Risk Management**: Built-in position sizing, stop-loss, and take-profit mechanisms
- 📈 **Technical Indicators**: RSI, MACD, Bollinger Bands, ATR, and more

## Architecture

```
┌─────────────────────────────────────────────────┐
│              Trading Bot (EC2)                  │
├─────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐           │
│  │ ML Strategy  │  │ ML Strategy  │  ...      │
│  │  (BTCUSD)    │  │  (ETHUSD)    │           │
│  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                     │
│  ┌──────▼─────────────────▼───────┐           │
│  │      Main Orchestrator         │           │
│  └──────┬─────────────────┬───────┘           │
│         │                 │                     │
│  ┌──────▼──────┐  ┌───────▼──────┐            │
│  │   Data      │  │  Execution   │            │
│  │  Collector  │  │   Engine     │            │
│  └──────┬──────┘  └───────┬──────┘            │
│         │                 │                     │
│  ┌──────▼─────────────────▼───────┐           │
│  │    Delta Exchange API Client    │           │
│  └─────────────────────────────────┘           │
└─────────────────────────────────────────────────┘
```

## Project Structure

```
crypto-bot/
├── collectors/          # Data collection from Delta Exchange
│   ├── delta_client.py  # API client
│   └── data_collector.py # Market data collector
├── strategies/          # Trading strategies
│   ├── base_strategy.py # Base strategy class
│   └── ml_strategy.py   # ML-based strategy
├── execution/           # Order execution
│   ├── order_manager.py # Order management
│   └── position_manager.py # Position tracking
├── features/            # ML/AI components
│   ├── feature_engineering.py # Feature engineering
│   └── ml_models.py     # ML models
├── config/              # Configuration management
│   └── config.py        # Config loader
├── infra/               # AWS infrastructure
│   └── terraform/       # Terraform configs
├── main.py              # Main orchestrator
└── requirements.txt     # Python dependencies
```

## Quick Start

### 1. Prerequisites

- Python 3.9+
- AWS Account (for deployment)
- Delta Exchange API key and secret

### 2. Local Setup

```bash
# Clone repository
git clone <your-repo-url>
cd crypto-bot

# Create virtual environment
python3.9 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env with your API credentials
```

### 3. Configure Environment Variables

Edit `.env` file with your Delta Exchange credentials:

```bash
DELTA_API_KEY=your_api_key_here
DELTA_API_SECRET=your_api_secret_here
TRADING_PRODUCTS=BTCUSD,ETHUSD
MAX_POSITION_SIZE=1000.0
```

### 4. Run Locally

```bash
# Run the trading bot
python main.py
```

The bot will:
1. Initialize and connect to Delta Exchange
2. Collect market data
3. Train ML models on historical data
4. Start running trading strategies
5. Execute trades based on ML predictions

## AWS Deployment

### Quick Start

```bash
cd infra
chmod +x deploy.sh
./deploy.sh
```

### Detailed Guide

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete step-by-step deployment instructions.

### Cost Optimization

The deployment is optimized for minimal costs:
- **Spot Instances**: Up to 90% cheaper than on-demand
- **t3.micro**: Free tier eligible, lowest cost option
- **Minimal Logging**: 7-day CloudWatch log retention
- **Single Instance**: All strategies run on one EC2

**Estimated Monthly Cost**: ~$3-6/month

### Prerequisites

- AWS CLI configured
- Terraform installed (>= 1.0)
- SSH key pair in AWS

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

## Trading Strategies

### ML Strategy

The ML strategy uses machine learning to predict price direction:
- **Features**: Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- **Model**: Random Forest or Gradient Boosting
- **Signal**: Buy/Sell/Hold based on prediction confidence
- **Risk Management**: Stop-loss and take-profit levels

### Adding Custom Strategies

Create a new strategy by extending `BaseStrategy`:

```python
from strategies.base_strategy import BaseStrategy, Signal

class MyStrategy(BaseStrategy):
    def generate_signal(self, data: Dict) -> Signal:
        # Your strategy logic
        return Signal(
            symbol="BTCUSD",
            action="buy",
            size=0.1,
            price=50000.0,
            confidence=0.8,
            reason="Your reason"
        )
    
    def should_close_position(self, position: Dict, data: Dict) -> bool:
        # Position closing logic
        return False
```

## Configuration

### Trading Configuration

```python
TRADING_PRODUCTS=BTCUSD,ETHUSD      # Products to trade
MAX_POSITION_SIZE=1000.0            # Maximum position size (USD)
MAX_LEVERAGE=10                     # Maximum leverage
RISK_PER_TRADE=0.02                 # Risk per trade (2% of capital)
DEFAULT_TIMEFRAME=1h                # Default timeframe
```

### ML Configuration

```python
ML_MODEL_PATH=models                # Path to save models
ML_RETRAIN_INTERVAL_HOURS=24        # Retrain frequency
ML_FEATURE_WINDOW=100               # Feature window size
ML_PREDICTION_THRESHOLD=0.6         # Minimum confidence threshold
```

## Data Collection

The bot collects:
- **OHLC Data**: Historical candlestick data
- **Orderbook**: L2 orderbook data
- **Trades**: Recent trade data
- **Tickers**: Current market prices

Data is stored in the `data/` directory and used for:
- Feature engineering
- ML model training
- Strategy decision making

## Monitoring

### Local Logs

```bash
tail -f trading_bot.log
```

### AWS CloudWatch

```bash
aws logs tail /aws/ec2/trading-bot --follow
```

### Service Status (on EC2)

```bash
sudo systemctl status trading-bot
sudo journalctl -u trading-bot -f
```

## API Reference

### Delta Exchange API

The bot uses the Delta Exchange REST API:
- [API Documentation](https://docs.delta.exchange/#introduction)

Key endpoints used:
- `/v2/products` - Get products
- `/v2/tickers/{symbol}` - Get ticker
- `/v2/history/candles` - Get OHLC data
- `/v2/orders` - Place/cancel orders
- `/v2/positions` - Get positions

## Risk Disclaimer

⚠️ **Trading cryptocurrencies involves substantial risk of loss. This bot is for educational purposes only. Use at your own risk.**

- Always test with small amounts first
- Use testnet environment for initial testing
- Monitor the bot regularly
- Set appropriate risk limits
- Never invest more than you can afford to lose

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
flake8 .
```

### Adding New Features

1. Create feature branch
2. Implement feature
3. Add tests
4. Submit pull request

## Troubleshooting

### API Errors

- Check API key and secret are correct
- Verify API permissions
- Check rate limits

### ML Model Issues

- Ensure sufficient historical data
- Check feature engineering pipeline
- Verify model training completed

### Deployment Issues

- Check AWS credentials
- Verify Terraform configuration
- Review CloudWatch logs

## License

See [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation
- Review Delta Exchange API docs

## Backtesting

Test your strategies on historical data before risking real money:

```bash
# Backtest ML strategy
python backtest.py --symbol BTCUSD --strategy ml

# Backtest with date range
python backtest.py --symbol BTCUSD --strategy ml --start-date 2024-01-01 --end-date 2024-06-01

# Compare strategies
python backtest.py --symbol BTCUSD --strategy mean_reversion
```

See [docs/BACKTESTING.md](docs/BACKTESTING.md) for detailed backtesting guide.

## Roadmap

- [x] Backtesting framework
- [ ] WebSocket support for real-time data
- [ ] Additional ML models (XGBoost, LSTM)
- [ ] Portfolio optimization
- [ ] Web dashboard for monitoring
- [ ] Multi-exchange support
