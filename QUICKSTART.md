# Quick Start Guide

## Setting Up API Credentials

To use the data collection and ML training script, you need to set your Delta Exchange API credentials.

### Option 1: Environment Variables (Recommended)

```bash
export DELTA_API_KEY=your_api_key_here
export DELTA_API_SECRET=your_api_secret_here
```

### Option 2: Create a .env File

Create a `.env` file in the project root:

```bash
cp env.example .env
```

Then edit `.env` and add your credentials:

```
DELTA_API_KEY=your_api_key_here
DELTA_API_SECRET=your_api_secret_here
```

**Note:** If you use a `.env` file, you'll need to load it manually or use a package like `python-dotenv`.

### Option 3: Load .env with python-dotenv

If you want to use a `.env` file, install `python-dotenv`:

```bash
pip install python-dotenv
```

Then add this to the top of your script (before importing Config):

```python
from dotenv import load_dotenv
load_dotenv()
```

## Running Data Collection and ML Training

Once credentials are set:

```bash
# Collect data and train models for SOLUSD
python collect_and_train.py --symbols SOLUSD

# Collect 7 days of data
python collect_and_train.py --symbols SOLUSD --hours 168

# Collect 30 days of data (default)
python collect_and_train.py --symbols SOLUSD

# Train with Gradient Boosting
python collect_and_train.py --symbols SOLUSD --model-type gradient_boosting
```

## Verify Credentials Are Set

Check if your credentials are loaded:

```bash
echo $DELTA_API_KEY
echo $DELTA_API_SECRET
```

If these are empty, the credentials aren't set.
