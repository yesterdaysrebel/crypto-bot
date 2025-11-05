# Data Collection and ML Training Guide

This guide explains how to run data collection and ML model training locally **without placing any orders**.

## Overview

The `collect_and_train.py` script allows you to:
- Collect historical market data from Delta Exchange
- Train ML models on the collected data
- Save data and models for later use
- **NO orders are placed** - this is a read-only operation

## Prerequisites

1. **API Credentials**: Set up your Delta Exchange API credentials in environment variables:
   ```bash
   export DELTA_API_KEY=your_api_key_here
   export DELTA_API_SECRET=your_api_secret_here
   ```

   Or create a `.env` file (see `env.example` for format).

2. **Dependencies**: Ensure you have the required packages:
   ```bash
   pip install pandas numpy scikit-learn
   ```

## Usage

### Basic Usage

Collect data and train ML models for all symbols in your config:

```bash
python collect_and_train.py
```

### Collect Data for Specific Symbols

```bash
python collect_and_train.py --symbols BTCUSD ETHUSD SOLUSD
```

### Collect More Historical Data

By default, the script collects 720 hours (30 days) of data. You can specify more:

```bash
# Collect 60 days of data (1440 hours)
python collect_and_train.py --hours 1440

# Collect 90 days of data (2160 hours)
python collect_and_train.py --hours 2160
```

### Choose ML Model Type

Train with different model types:

```bash
# Use Random Forest (default)
python collect_and_train.py --model-type random_forest

# Use Gradient Boosting
python collect_and_train.py --model-type gradient_boosting
```

### Data Collection Only (Skip Training)

```bash
python collect_and_train.py --skip-training
```

### Training Only (Skip Collection, Use Existing Data)

```bash
python collect_and_train.py --skip-collection
```

### Complete Example

```bash
# Collect 60 days of data for BTCUSD and ETHUSD, train Gradient Boosting models
python collect_and_train.py \
    --symbols BTCUSD ETHUSD \
    --hours 1440 \
    --model-type gradient_boosting
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--symbols` | List of symbols to collect (space-separated) | From config |
| `--hours` | Number of hours of historical data | 720 (30 days) |
| `--model-type` | ML model type: `random_forest` or `gradient_boosting` | `random_forest` |
| `--skip-training` | Skip ML training, only collect data | False |
| `--skip-collection` | Skip data collection, train on existing data | False |

## Output

### Data Files

Collected data is saved to the `data/` directory:
```
data/
├── BTCUSD_1h_ohlc.csv
├── ETHUSD_1h_ohlc.csv
└── ...
```

### Model Files

Trained models are saved to the `models/` directory:
```
models/
├── BTCUSD/
│   ├── model.pkl
│   └── model_scaler.pkl
├── ETHUSD/
│   ├── model.pkl
│   └── model_scaler.pkl
└── ...
```

### Logs

Logs are written to:
- Console (stdout)
- `data_collection.log` file

## What the Script Does

1. **Initialization**: Loads configuration from environment variables
2. **Data Collection**:
   - Checks for existing data files
   - Updates existing data with latest from API, or collects fresh data
   - Saves data to CSV files
3. **Feature Engineering**:
   - Calculates technical indicators (RSI, MACD, Bollinger Bands, etc.)
   - Creates features for ML training
4. **ML Training**:
   - Trains the selected model type on collected data
   - Evaluates model performance
   - Saves trained models to disk

## Important Notes

- **No Orders**: This script only reads data from the API. No orders are placed.
- **API Rate Limits**: The script respects API rate limits and may take time to collect large amounts of data.
- **Data Updates**: Existing data files are updated incrementally, so you don't need to re-download everything each time.
- **Model Training**: Requires at least 50 data points per symbol to train effectively.

## Troubleshooting

### "Insufficient data" Error

If you see this error, try:
- Collecting more hours of data: `--hours 1440`
- Collecting data for more symbols
- Checking that your API credentials are correct

### API Connection Errors

- Verify your API credentials are set correctly
- Check your internet connection
- Ensure the Delta Exchange API is accessible

### Model Training Fails

- Ensure you have `scikit-learn` installed: `pip install scikit-learn`
- Check that you have enough data (at least 50 data points)
- Try collecting more historical data

## Example Workflow

1. **First Run**: Collect data and train models
   ```bash
   python collect_and_train.py --hours 720
   ```

2. **Daily Updates**: Update data and retrain models
   ```bash
   python collect_and_train.py
   ```

3. **Test Different Models**: Train with different model types
   ```bash
   python collect_and_train.py --model-type gradient_boosting
   ```

4. **Collect More Data**: Expand your dataset
   ```bash
   python collect_and_train.py --hours 2160 --skip-training
   python collect_and_train.py --skip-collection
   ```

## Integration with Main Bot

Once you've collected data and trained models, the main trading bot (`main.py`) will:
- Load the trained models automatically
- Use the collected data for strategy decisions
- Continue updating data during normal operation

The main bot will still place orders (if you enable it), but the data collection and training can be done separately using this script.

