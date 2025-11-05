# Data Storage Strategy

## Current Implementation

The bot supports **both approaches**:

### 1. **With Data Storage (Recommended)**
- ✅ **Pros**: Faster startup, better performance, historical analysis
- ✅ **Cons**: Requires disk space (~few MB per symbol)
- ✅ **Use Case**: Production, long-running bots

### 2. **Without Data Storage (Current Default)**
- ✅ **Pros**: No disk space, always fresh data
- ❌ **Cons**: Slower startup, API rate limits, no historical analysis
- ✅ **Use Case**: Testing, quick runs

## How It Works

### Data Collection Flow

```
┌─────────────────────────────────────────┐
│  Runtime Data Collection               │
├─────────────────────────────────────────┤
│  1. Check local CSV files               │
│  2. Fetch new data from API             │
│  3. Merge and save to CSV               │
│  4. Use merged data for predictions     │
└─────────────────────────────────────────┘
```

### ML Training Flow

```
┌─────────────────────────────────────────┐
│  ML Model Training                      │
├─────────────────────────────────────────┤
│  1. Load historical data from CSV       │
│  2. If insufficient, fetch from API     │
│  3. Train model on historical data     │
│  4. Save model to disk (.pkl)           │
└─────────────────────────────────────────┘
```

## Storage Locations

### Data Files
- **Location**: `data/` directory
- **Format**: CSV files
- **Naming**: `{SYMBOL}_{TIMEFRAME}_ohlc.csv`
- **Example**: `BTCUSD_1h_ohlc.csv`

### Model Files
- **Location**: `models/` directory (configurable via `ML_MODEL_PATH`)
- **Format**: `.pkl` files (joblib)
- **Files**: `model.pkl` (model), `model_scaler.pkl` (scaler)

## Data Storage Size

### Per Symbol (1 hour timeframe)
- **7 days**: ~168 rows × ~50 bytes = ~8 KB
- **30 days**: ~720 rows × ~50 bytes = ~36 KB
- **1 year**: ~8,760 rows × ~50 bytes = ~438 KB

### Total Storage (10 symbols, 1 year)
- **Data**: ~4.4 MB
- **Models**: ~1-2 MB per model
- **Total**: ~5-10 MB (very minimal!)

## Configuration

### Enable Data Storage

Already enabled! The code automatically:
1. Loads existing data on startup
2. Updates with new data during runtime
3. Saves data to CSV files

### Disable Data Storage (Runtime Only)

To disable saving during runtime (but keep training data):

```python
# In collect_market_data(), change save=True to save=False
ohlc_df = self.data_collector.collect_ohlc(
    symbol=symbol,
    save=False  # Don't save runtime data
)
```

## Benefits of Data Storage

### 1. **Faster Startup**
- No need to fetch 7 days of data on every startup
- Model loads instantly if data exists

### 2. **Better ML Training**
- More historical data = better models
- Can train on weeks/months of data
- Incremental learning possible

### 3. **API Rate Limiting**
- Fewer API calls = less rate limit issues
- Only fetch new data, not all historical

### 4. **Historical Analysis**
- Analyze past performance
- Backtest strategies
- Debug issues with historical data

### 5. **Cost Optimization**
- Fewer API calls on AWS
- Faster training = less compute time

## Recommendations

### For Production (AWS EC2)
✅ **Enable data storage** (default)
- Small disk space (~10-50 MB)
- Better performance
- Faster startup after first run

### For Testing
✅ **Can disable runtime saving**
- But keep training data
- Faster for quick tests

### For Long-term Running
✅ **Keep historical data**
- Build up dataset over time
- Retrain models periodically
- Better predictions over time

## Data Retention

Currently, data is kept indefinitely. To add retention:

```python
# In data_collector.py, add cleanup:
def cleanup_old_data(self, days_to_keep: int = 90):
    """Remove data older than specified days."""
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    # Filter data older than cutoff_date
```

## Database Option (Future Enhancement)

For production, consider:
- **SQLite**: Simple, file-based, no setup
- **PostgreSQL**: For multiple instances
- **TimescaleDB**: Optimized for time-series data

## Summary

**Current Implementation**: ✅ **Hybrid Approach**
- Stores data to CSV files
- Stores models to disk
- Fetches new data incrementally
- Minimal storage (~10-50 MB)

**Recommendation**: ✅ **Keep data storage enabled**
- Benefits outweigh costs
- Minimal disk space required
- Better performance and reliability

