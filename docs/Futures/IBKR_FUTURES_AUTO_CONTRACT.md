# IBKR Futures Auto-Contract Resolution

## Overview

This document explains the automatic futures contract resolution feature that was implemented to fix the ES futures backtesting issue.

## Problem

When trying to backtest futures symbols like "ES" (E-mini S&P 500), the system would fail because:
1. No data existed in the SQLite database for "ES"
2. IBKR requires specific contract symbols like "ESZ4" (December 2024), not just "ES"
3. The system couldn't automatically determine which contract to fetch

## Solution

Implemented automatic contract determination in two places:

### 1. API Main (`api/main.py` lines 642-707)

When futures data is missing from the database, the system now:
- Detects if the symbol is a root symbol (2-3 characters like ES, CL, NG)
- Automatically determines the next quarterly contract based on current date
- Constructs the proper contract symbol (e.g., ES → ESZ4)
- Fetches data from IBKR using the specific contract
- Saves data to database using the root symbol for future backtests

**Contract Month Codes:**
- H = March
- M = June  
- U = September
- Z = December

**Example:**
- Input: "ES"
- Current date: October 2024
- Next contract: December 2024
- Generated symbol: "ESZ4"

### 2. IBKR Data Feed (`data/data_feed.py` lines 423-498)

Enhanced the `IBKRDataFeed.get_futures_data()` method to:
- Parse contract symbols properly (ESZ4 → root: ES, month: Z, year: 4)
- Map futures symbols to correct exchanges:
  - ES, NQ, RTY → CME
  - CL, NG → NYMEX
  - GC, SI, HG → COMEX
  - ZB, ZN, ZF, ZC, ZS, ZW → CBOT
- Convert month codes to IBKR format (YYYYMM)

## Supported Futures Symbols

| Symbol | Name | Exchange |
|--------|------|----------|
| ES | E-mini S&P 500 | CME |
| NQ | E-mini NASDAQ | CME |
| YM | E-mini Dow | CBOT |
| RTY | E-mini Russell 2000 | CME |
| CL | Crude Oil | NYMEX |
| NG | Natural Gas | NYMEX |
| GC | Gold | COMEX |
| SI | Silver | COMEX |
| HG | Copper | COMEX |
| ZB | 30-Year T-Bond | CBOT |
| ZN | 10-Year T-Note | CBOT |
| ZF | 5-Year T-Note | CBOT |
| ZC | Corn | CBOT |
| ZS | Soybeans | CBOT |
| ZW | Wheat | CBOT |

## Usage

### Backtesting ES Futures

1. **Ensure IBKR TWS is running:**
   - Open IBKR Trader Workstation (TWS) or IB Gateway
   - Enable API connections in settings
   - Use port 7497 for paper trading or 7496 for live

2. **Start backtest from dashboard:**
   - Select a futures strategy
   - Enter symbol: "ES" (just the root symbol)
   - Choose date range
   - Click "Run Backtest"

3. **What happens:**
   - System checks SQLite database for ES data
   - If not found, automatically determines contract (e.g., ESZ4)
   - Connects to IBKR TWS on port 7497
   - Fetches historical data for ESZ4
   - Saves to database as "ES" for future use
   - Runs backtest with the fetched data

### Manual Contract Specification

You can also specify exact contracts:
- "ESZ4" - E-mini S&P December 2024
- "ESH5" - E-mini S&P March 2025
- "NGZ4" - Natural Gas December 2024

## Configuration

IBKR settings in `config/config.yaml`:

```yaml
ibkr:
  host: 127.0.0.1
  port: 7497        # 7497 = Paper Trading, 7496 = Live Trading
  client_id: 1
```

## Troubleshooting

### "Failed to fetch futures data from IBKR"

**Possible causes:**
1. IBKR TWS/Gateway not running
2. API not enabled in TWS settings
3. Wrong port number
4. Contract doesn't exist (expired or invalid)

**Solutions:**
1. Start IBKR TWS or IB Gateway
2. Go to TWS → File → Global Configuration → API → Settings
   - Enable "Enable ActiveX and Socket Clients"
   - Check port number matches config (7497 for paper)
3. Verify contract exists on IBKR
4. Check logs in `logs/trading_bot.log`

### "Invalid futures symbol format"

The symbol must be either:
- Root symbol: 2-3 characters (ES, CL, NG)
- Full contract: Root + Month Code + Year (ESZ4, CLZ4)

### Data Not Saving to Database

Check database permissions and disk space. The system will log warnings but continue with the backtest.

## Technical Details

### Contract Month Determination Logic

```python
# Get current date
now = datetime.now()
current_month = now.month

# Quarterly contracts: March, June, September, December
month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}

# Find next quarterly month
for month in [3, 6, 9, 12]:
    if month >= current_month:
        next_contract_month = month
        break

# If past December, use next year's March
if next_contract_month is None:
    next_contract_month = 3
    year += 1
```

### IBKR Contract Format

```python
contract = Contract()
contract.symbol = "ES"              # Root symbol
contract.secType = "FUT"            # Futures
contract.exchange = "CME"           # Exchange
contract.currency = "USD"           # Currency
contract.lastTradeDateOrContractMonth = "202412"  # YYYYMM format
```

## Benefits

1. **Automatic**: No need to manually determine contract months
2. **Persistent**: Data saved to database for future backtests
3. **Flexible**: Works with both root symbols and specific contracts
4. **Robust**: Proper exchange mapping for different futures
5. **Transparent**: Detailed logging of contract determination

## Future Enhancements

Potential improvements:
- Support for non-quarterly contracts (monthly contracts)
- Automatic rollover to next contract when current expires
- Multiple contract fetching for longer date ranges
- Contract chain analysis
- Volume-based contract selection (most liquid)

## Related Files

- `api/main.py` - Main API with auto-contract logic
- `data/data_feed.py` - IBKR data feed implementation
- `config/config.yaml` - IBKR configuration
- `database/database_manager.py` - Data persistence

## See Also

- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- [Futures Contract Specifications](https://www.cmegroup.com/trading/equity-index/us-index/e-mini-sandp500_contract_specifications.html)
- [INTERACTIVE_BROKERS_INTEGRATION_ANALYSIS.md](INTERACTIVE_BROKERS_INTEGRATION_ANALYSIS.md)