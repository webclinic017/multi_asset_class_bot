# Multi-Asset Trading System Documentation

## Overview
The Multi-Asset Trading System enables simultaneous analysis and trading of both forex (EUR/USD) and cryptocurrency (SOL/USD) assets. The system intelligently compares performance between asset classes and automatically focuses trading efforts on the most profitable opportunities.

## Key Features

### 🔄 **Multi-Asset Support**
- **Forex Trading**: EUR/USD via OANDA API with advanced technical analysis
- **Crypto Trading**: SOL/USD via Kraken API with crypto-specific indicators
- **Intelligent Asset Selection**: Automatically chooses the most profitable asset class
- **Dynamic Allocation**: Adjusts capital allocation based on performance analysis

### 📊 **Performance Analysis**
- **Real-time Comparison**: Continuously compares forex vs crypto performance
- **Profitability Scoring**: Advanced scoring system based on multiple metrics
- **Risk-Adjusted Returns**: Considers volatility and drawdown in decision making
- **Confidence Intervals**: Provides confidence levels for recommendations

### 🎯 **Automated Decision Making**
- **Asset Switching**: Automatically switches between forex and crypto based on performance
- **Allocation Optimization**: Dynamically adjusts portfolio allocation (10-90% per asset)
- **Risk Management**: Asset-specific risk parameters and position sizing
- **Market Condition Adaptation**: Responds to changing market conditions

## System Architecture

### Core Components

#### 1. **Data Feeds**
- **OANDA Data Feed** (`data/data_feed.py`): Forex market data
- **Kraken Data Feed** (`data/kraken_feed.py`): Cryptocurrency market data
- **Unified Interface**: Consistent data format across all asset types

#### 2. **Trading Strategies**
- **Forex Strategy** (`strategies/forex_strategy.py`): EUR/USD optimized strategy
- **Crypto Strategy** (`strategies/crypto_strategy.py`): SOL/USD optimized strategy
- **SOL Strategy** (`strategies/crypto_strategy.py`): Specialized SOL trading logic

#### 3. **Multi-Asset Analyzer** (`utils/multi_asset_analyzer.py`)
- Performance comparison engine
- Asset allocation optimizer
- Trading recommendation generator
- Comprehensive reporting system

#### 4. **Enhanced Backtesting** (`backtesting/backtest_engine.py`)
- Multi-asset backtesting support
- Parallel strategy execution
- Comparative performance analysis
- Automated report generation

## Configuration

### Multi-Asset Settings (`config/config.yaml`)

```yaml
# Multi-asset trading configuration
multi_asset:
  enabled: true                    # Enable multi-asset mode
  analysis_enabled: true           # Enable performance analysis
  auto_asset_selection: true       # Automatic asset selection
  rebalance_frequency: "daily"     # Rebalancing frequency
  min_performance_difference: 10   # Min score difference to switch
  allocation_limits:
    forex_min: 10                  # Minimum forex allocation (%)
    forex_max: 90                  # Maximum forex allocation (%)
    crypto_min: 10                 # Minimum crypto allocation (%)
    crypto_max: 90                 # Maximum crypto allocation (%)

# Asset configuration
data:
  symbols:
    - name: EUR_USD
      type: forex
      timeframe: H1
      priority: 1
    - name: SOL/USD
      type: crypto
      timeframe: 1h
      priority: 2

# Strategy configurations
strategies:
  forex:
    name: ForexStrategy
    params:
      # Forex-specific parameters
      fast_length: 15
      slow_length: 35
      rsi_period: 21
      # ... other forex parameters
  
  crypto:
    name: SOLStrategy
    params:
      # Crypto-specific parameters
      fast_length: 10
      slow_length: 21
      rsi_period: 14
      volatility_threshold: 0.06
      # ... other crypto parameters
```

## Usage

### 1. **Backtesting Mode**
```bash
cd multi_asset_bot
python main.py --mode backtest
```

**Multi-Asset Backtesting Features:**
- Runs backtests for all configured assets simultaneously
- Compares performance across asset classes
- Generates allocation recommendations
- Exports comprehensive analysis reports

**Sample Output:**
```
=== MULTI-ASSET BACKTEST COMPLETE ===

--- EUR_USD (FOREX) ---
Final Value: $10,250.00
Total Return: 2.50%
Sharpe Ratio: 1.15
Win Rate: 58.33%
Total Trades: 24

--- SOL/USD (CRYPTO) ---
Final Value: $11,800.00
Total Return: 18.00%
Sharpe Ratio: 0.95
Win Rate: 52.17%
Total Trades: 23

=== MULTI-ASSET ANALYSIS ===
Forex Average Score: 65.2
Crypto Average Score: 78.9
Recommendation: Focus on CRYPTO
Confidence: 85.3%
Optimal Allocation: 25.0% Forex, 75.0% Crypto
Next Trade Asset: CRYPTO
Reasoning: Crypto outperforming with 85.3% confidence
```

### 2. **Live Trading Mode**
```bash
cd multi_asset_bot
python main.py --mode live
```

**Multi-Asset Live Trading Features:**
- Initial performance analysis to determine starting asset
- Real-time market condition monitoring
- Automatic asset switching based on performance
- Dynamic risk management per asset type

**Live Trading Flow:**
1. **Initial Analysis**: Runs quick backtests to determine optimal starting asset
2. **Asset Selection**: Begins trading with the highest-performing asset
3. **Continuous Monitoring**: Tracks performance and market conditions
4. **Dynamic Switching**: Switches assets when performance analysis indicates better opportunities
5. **Risk Management**: Applies asset-specific risk parameters

### 3. **Optimization Mode**
```bash
cd multi_asset_bot
python main.py --mode optimize
```

**Multi-Asset Optimization Features:**
- Optimizes parameters for both forex and crypto strategies
- Compares optimized performance across assets
- Generates recommendations for parameter updates
- Exports optimization results for both asset classes

## Performance Metrics

### Scoring System
The multi-asset analyzer uses a weighted scoring system:

- **Total Return** (30%): Raw performance
- **Sharpe Ratio** (25%): Risk-adjusted returns
- **Win Rate** (20%): Consistency of profits
- **Profit Factor** (15%): Ratio of wins to losses
- **Max Drawdown** (10%): Risk control (inverted)

### Asset Allocation Logic
```python
# Allocation based on performance difference
if forex_score > crypto_score + min_difference:
    allocation = "Favor Forex"
    forex_allocation = 50 + (confidence * 0.4)  # Up to 90%
elif crypto_score > forex_score + min_difference:
    allocation = "Favor Crypto" 
    crypto_allocation = 50 + (confidence * 0.4)  # Up to 90%
else:
    allocation = "Balanced"
    forex_allocation = crypto_allocation = 50%
```

## API Integration

### Kraken API Setup
1. **Create Kraken Account**: Sign up at kraken.com
2. **Generate API Keys**: Create API key with trading permissions
3. **Configure Credentials**:
```yaml
kraken:
  api_key: "your_kraken_api_key"
  api_secret: "your_kraken_api_secret"
```

### OANDA API (Existing)
```yaml
oanda:
  account_id: "your_oanda_account_id"
  access_token: "your_oanda_access_token"
  practice: true
```

## Risk Management

### Asset-Specific Risk Parameters

#### Forex (EUR/USD)
- **Stop Loss**: 1.5% (lower volatility)
- **Take Profit**: 4.5% (3:1 risk/reward)
- **Position Size**: 10% of capital
- **Volatility Threshold**: 3%

#### Crypto (SOL/USD)
- **Stop Loss**: 4% (higher volatility)
- **Take Profit**: 8% (2:1 risk/reward)
- **Position Size**: 15% of capital
- **Volatility Threshold**: 6%

### Dynamic Risk Adjustment
- **Market Volatility**: Adjusts position sizes based on current volatility
- **Performance Tracking**: Reduces exposure after losses
- **Correlation Analysis**: Monitors asset correlation for diversification

## Monitoring and Alerts

### Performance Tracking
- **Real-time P&L**: Track profits/losses per asset
- **Performance Attribution**: Understand which asset is driving returns
- **Risk Metrics**: Monitor drawdown, volatility, and exposure

### Automated Reporting
- **Daily Reports**: Performance summary and allocation updates
- **Weekly Analysis**: Comprehensive multi-asset performance review
- **Monthly Optimization**: Parameter optimization recommendations

## Advanced Features

### 1. **Market Regime Detection**
- **Trend Markets**: Favor momentum strategies
- **Range Markets**: Favor mean reversion strategies
- **High Volatility**: Reduce position sizes
- **Low Volatility**: Increase position sizes

### 2. **Correlation Analysis**
- **Asset Correlation**: Monitor EUR/USD vs SOL/USD correlation
- **Diversification Benefits**: Optimize allocation for maximum diversification
- **Risk Reduction**: Avoid over-concentration in correlated assets

### 3. **Machine Learning Integration**
- **Performance Prediction**: Predict which asset will outperform
- **Market Condition Classification**: Classify market regimes
- **Adaptive Parameters**: Automatically adjust strategy parameters

## Troubleshooting

### Common Issues

1. **"No crypto data available"**
   - Check Kraken API credentials
   - Verify internet connection
   - Ensure SOL/USD is available on Kraken

2. **"Multi-asset analysis failed"**
   - Check that both data feeds are working
   - Verify configuration file syntax
   - Ensure sufficient historical data

3. **"Asset switching too frequent"**
   - Increase `min_performance_difference` in config
   - Adjust `rebalance_frequency` to less frequent
   - Review performance thresholds

### Performance Optimization

1. **Data Caching**: Enable data caching for faster analysis
2. **Parallel Processing**: Use multiple cores for backtesting
3. **Memory Management**: Optimize for large datasets
4. **API Rate Limits**: Respect exchange rate limits

## Future Enhancements

### Planned Features
- **Additional Assets**: BTC/USD, ETH/USD, GBP/USD
- **Options Trading**: Multi-asset options strategies
- **Futures Integration**: Commodity and index futures
- **Social Trading**: Copy successful multi-asset traders

### Research Areas
- **Deep Learning**: Neural networks for asset selection
- **Alternative Data**: News sentiment, social media analysis
- **High-Frequency Trading**: Millisecond-level asset switching
- **Quantum Computing**: Portfolio optimization algorithms

## Support and Resources

### Documentation
- **API Documentation**: Detailed API reference
- **Strategy Guides**: Step-by-step strategy development
- **Configuration Reference**: Complete configuration options
- **Troubleshooting Guide**: Common issues and solutions

### Community
- **GitHub Repository**: Source code and issues
- **Discord Server**: Real-time support and discussion
- **Trading Forums**: Strategy sharing and analysis
- **Educational Content**: Webinars and tutorials

---

**Note**: This multi-asset trading system is designed for educational and research purposes. Always test thoroughly with paper trading before using real capital. Past performance does not guarantee future results.

## Quick Start Checklist

- [ ] Configure Kraken API credentials
- [ ] Enable multi-asset mode in config
- [ ] Run initial backtest: `python main.py --mode backtest`
- [ ] Review performance analysis reports
- [ ] Start paper trading: `python main.py --mode live`
- [ ] Monitor performance and adjust parameters
- [ ] Scale to live trading with real capital

**Ready to maximize returns across multiple asset classes!** 🚀📈