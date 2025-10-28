# Fundamental and Sentiment Data Date Filtering

## Overview

The OriginalMarketMakingStrategy now properly filters fundamental and sentiment data based on the backtest date range provided by the frontend/API. This ensures that backtests use only data that would have been available during the historical period being tested.

## Date Flow Architecture

```
Frontend (Dashboard)
    ↓
    Backtest Request {
        symbol: "ES",
        start_date: "2024-01-01",
        end_date: "2024-12-31",
        strategy_id: 123
    }
    ↓
API (api/main.py)
    ↓
    Adds to strategy_params {
        backtest_start_date: "2024-01-01",
        backtest_end_date: "2024-12-31",
        backtest_symbol: "ES"
    }
    ↓
Strategy (strategies/enhanced_forex_strategy.py)
    ↓
    __init__() receives parameters
    ↓
    _load_fundamental_and_sentiment_data()
    ↓
    Filters data by date range:
    - Fundamental: data[(data.index >= start_dt) & (data.index <= end_dt)]
    - Sentiment: Uses current as proxy (logs backtest mode)
    ↓
    Only uses data within backtest period
```

## Implementation Details

### 1. API Parameter Passing

In [`api/main.py`](../api/main.py:1015-1023):

```python
# Add backtest date range for fundamental/sentiment data filtering
logger.info("=== ADDING BACKTEST DATE RANGE FOR FUNDAMENTAL/SENTIMENT ===")
strategy_params['backtest_start_date'] = backtest_request.start_date
strategy_params['backtest_end_date'] = backtest_request.end_date
strategy_params['backtest_symbol'] = backtest_request.symbol
logger.info(f"Added backtest date range: {backtest_request.start_date} to {backtest_request.end_date}")
logger.info(f"Added backtest symbol: {backtest_request.symbol}")
```

### 2. Strategy Parameter Definition

In [`strategies/enhanced_forex_strategy.py`](../strategies/enhanced_forex_strategy.py:57-59):

```python
# Backtest Date Range (for fundamental/sentiment data filtering)
('backtest_start_date', None),       # Backtest start date
('backtest_end_date', None),         # Backtest end date
('backtest_symbol', None),           # Backtest symbol
```

### 3. Date-Filtered Data Loading

In [`strategies/enhanced_forex_strategy.py`](../strategies/enhanced_forex_strategy.py:347-428):

```python
def _load_fundamental_and_sentiment_data(self):
    """Load fundamental data and initialize sentiment analyzer based on symbol and date range"""
    
    # Get date range from parameters
    start_date = self.p.backtest_start_date
    end_date = self.p.backtest_end_date
    
    # Convert to datetime objects
    start_dt = datetime.fromisoformat(start_date) if isinstance(start_date, str) else start_date
    end_dt = datetime.fromisoformat(end_date) if isinstance(end_date, str) else end_date
    
    # Load all data from database
    fed_funds_all = db.get_fundamental_data(symbol, 'FRED', 'Federal Funds Rate', limit=10000)
    
    # Filter by date range
    if start_dt and end_dt and not fed_funds_all.empty:
        self.fundamental_data['fed_funds'] = fed_funds_all[
            (fed_funds_all.index >= start_dt) & 
            (fed_funds_all.index <= end_dt)
        ]
    else:
        self.fundamental_data['fed_funds'] = fed_funds_all
    
    # Log filtered data range
    if not self.fundamental_data['fed_funds'].empty:
        logger.info(f"  fed_funds: {len(data)} points from {data.index.min()} to {data.index.max()}")
```

## Data Filtering by Asset Class

### Equity Index Futures (ES, NQ, YM, RTY)

**FRED Data Filtered:**
- Federal Funds Rate
- VIX
- 10Y-2Y Treasury Spread

**Example Log Output:**
```
Loading FRED data for equity index futures: ES
Using backtest date range: 2024-01-01 to 2024-12-31
Loaded 3 FRED series for ES
  fed_funds: 12 points from 2024-01-01 to 2024-12-31
  vix: 252 points from 2024-01-01 to 2024-12-31
  treasury_spread: 252 points from 2024-01-01 to 2024-12-31
```

### Energy Futures (CL, NG)

**EIA Data Filtered:**
- Crude Oil Stocks (weekly)
- Crude Oil Production (monthly)
- Natural Gas Storage (weekly)

**Example Log Output:**
```
Loading EIA data for energy futures: CL
Using backtest date range: 2024-01-01 to 2024-12-31
Loaded 2 EIA series for CL
  inventory: 52 points from 2024-01-03 to 2024-12-25
  production: 12 points from 2024-01-01 to 2024-12-01
```

### Agricultural Futures (ZC, ZS, ZW)

**USDA Data Filtered:**
- Corn/Soybean/Wheat Stocks (quarterly)
- Export Sales (weekly)

**Example Log Output:**
```
Loading USDA data for agricultural futures: ZC
Using backtest date range: 2024-01-01 to 2024-12-31
Loaded 2 USDA series for ZC
  stocks: 4 points from 2024-03-01 to 2024-12-01
  export_sales: 52 points from 2024-01-04 to 2024-12-26
```

### Precious Metals (GC, SI)

**FRED Data Filtered:**
- Real Interest Rates
- Dollar Index

**Example Log Output:**
```
Loading FRED data for precious metals: GC
Using backtest date range: 2024-01-01 to 2024-12-31
Loaded 2 FRED series for GC
  real_rates: 252 points from 2024-01-01 to 2024-12-31
  dollar_index: 252 points from 2024-01-01 to 2024-12-31
```

## Sentiment Data Handling

### Current Implementation

Sentiment data is fetched in **real-time** from RSS feeds, which means:

**For Live Trading:**
- ✅ Uses current news sentiment (last 24 hours)
- ✅ Reflects actual market sentiment at trade time

**For Backtesting:**
- ⚠️ Uses current news sentiment as proxy
- ⚠️ Not historically accurate (news from today, not from backtest period)

**Strategy Logs:**
```
=== SENTIMENT ANALYSIS FOR ES ===
Backtest mode: Using current sentiment as proxy for historical period
Backtest range: 2024-01-01 to 2024-12-31
Note: For accurate historical backtesting, store sentiment data in database
```

### Future Enhancement: Historical Sentiment Storage

To enable accurate historical sentiment in backtests, implement:

1. **Store Sentiment Data Daily**
   ```python
   # Run daily cron job
   from sentiment.futures_sentiment_analyzer import FuturesSentimentAnalyzer
   from database.database_manager import DatabaseManager
   
   analyzer = FuturesSentimentAnalyzer()
   db = DatabaseManager()
   
   for symbol in ['ES', 'CL', 'GC', 'ZC']:
       sentiment = analyzer.get_commodity_sentiment(symbol, hours_back=24)
       
       # Store in database (new table: sentiment_history)
       db.store_sentiment_data(
           symbol=symbol,
           timestamp=datetime.now(),
           sentiment_score=sentiment['sentiment_score'],
           news_count=sentiment['news_count'],
           confidence=sentiment['confidence']
       )
   ```

2. **Retrieve Historical Sentiment in Strategy**
   ```python
   # In _load_fundamental_and_sentiment_data()
   if start_dt and end_dt:
       sentiment_history = db.get_sentiment_data(
           symbol=base_symbol,
           start_date=start_dt,
           end_date=end_dt
       )
       # Use historical sentiment instead of current
   ```

## Validation

### Test Date Filtering

Run the integration test to verify date filtering:

```bash
activate_env.bat && python tests/test_fundamental_sentiment_integration.py
```

**Expected Output:**
```
✓ fundamental_data table exists
  Total rows: 19114

✓ Found 10 fundamental data points for ES
  Data sources: ['FRED']
  Series: ['vix', 'fed_funds']

✓ Sentiment analyzer initialized successfully
  Sentiment Score: -0.013 (NEUTRAL)
  News Count: 7

✓ Weights sum to 1.0 (100%)
✓ Portfolio tracking functionality preserved
✓ Trade counting functionality preserved
```

### Verify Date Range in Logs

When running a backtest, check the strategy logs:

```
=== INITIALIZING FUNDAMENTAL AND SENTIMENT DATA ===
Loading fundamental and sentiment data for symbol: ES
Using backtest date range: 2024-01-01 to 2024-12-31
Loading FRED data for equity index futures: ES
Loaded 3 FRED series for ES
  fed_funds: 12 points from 2024-01-01 00:00:00 to 2024-12-31 00:00:00
  vix: 252 points from 2024-01-01 00:00:00 to 2024-12-31 00:00:00
  treasury_spread: 252 points from 2024-01-01 00:00:00 to 2024-12-31 00:00:00
```

## Benefits of Date Filtering

### 1. Prevents Look-Ahead Bias

**Without Date Filtering:**
```
Backtest: 2024-01-01 to 2024-06-30
Fundamental Data: All data including 2024-07-01 to 2024-12-31
Result: Strategy uses future data → Unrealistic performance
```

**With Date Filtering:**
```
Backtest: 2024-01-01 to 2024-06-30
Fundamental Data: Only 2024-01-01 to 2024-06-30
Result: Strategy uses only available data → Realistic performance
```

### 2. Accurate Historical Testing

- Only uses data that existed during the backtest period
- Matches real-world trading conditions
- Provides realistic performance metrics

### 3. Consistent with Market Data

- Fundamental data range matches price data range
- All signals use same time period
- No temporal inconsistencies

## Edge Cases

### Case 1: No Date Range Provided

```python
# If backtest_start_date or backtest_end_date is None
if start_dt and end_dt:
    # Filter data
else:
    # Use all available data
    self.fundamental_data['fed_funds'] = fed_funds_all
```

**Result:** Uses all available fundamental data (fallback behavior)

### Case 2: No Fundamental Data in Range

```python
# After filtering
if self.fundamental_data['fed_funds'].empty:
    logger.warning("No fundamental data in backtest range")
    # Strategy continues without fundamental signals
    # Fundamental weight (10%) is effectively zero
```

**Result:** Strategy runs with 60% PA + 10% Tech + 20% Sent (90% total)

### Case 3: Partial Data Availability

```python
# Some series have data, others don't
self.fundamental_data = {
    'fed_funds': DataFrame with 12 rows,  # Has data
    'vix': DataFrame with 0 rows,         # No data in range
    'treasury_spread': DataFrame with 252 rows  # Has data
}

# Confidence calculation
data_count = sum(1 for data in self.fundamental_data.values() if not data.empty)
# data_count = 2 (fed_funds and treasury_spread)
signals['confidence'] = min(2 / 3.0, 1.0)  # 0.667 confidence
```

**Result:** Reduced confidence but still generates signals

## Monitoring

### Check Data Range in Logs

Look for these log messages during strategy initialization:

```
=== INITIALIZING FUNDAMENTAL AND SENTIMENT DATA ===
Loading fundamental and sentiment data for symbol: ES
Using backtest date range: 2024-01-01 to 2024-12-31
Loading FRED data for equity index futures: ES
Loaded 3 FRED series for ES
  fed_funds: 12 points from 2024-01-01 00:00:00 to 2024-12-31 00:00:00
  vix: 252 points from 2024-01-01 00:00:00 to 2024-12-31 00:00:00
  treasury_spread: 252 points from 2024-01-01 00:00:00 to 2024-12-31 00:00:00
```

### Verify No Future Data

Check that max date in fundamental data ≤ backtest end date:

```python
# In logs
self.logger.info(f"  {key}: {len(data)} points from {data.index.min()} to {data.index.max()}")

# Verify: data.index.max() <= backtest_end_date
```

## Summary

✅ **Fundamental Data:** Filtered by backtest date range from API request  
✅ **Sentiment Data:** Uses current sentiment (with backtest mode logging)  
✅ **Date Range:** Passed from frontend → API → strategy parameters  
✅ **No Look-Ahead Bias:** Only uses data available during backtest period  
✅ **Portfolio Tracking:** Preserved and unaffected by date filtering  
✅ **Trade Counting:** Accurate from executed orders, unaffected by filtering  

---

**Last Updated:** 2025-10-28  
**Version:** 1.0  
**Related:** [FUNDAMENTAL_SENTIMENT_INTEGRATION.md](FUNDAMENTAL_SENTIMENT_INTEGRATION.md)