# Trading Bot Dashboard

A professional trading bot dashboard with scalping strategies, real-time visualization, and comprehensive backtesting capabilities for EUR_USD forex trading.

## Features

### 🚀 Core Features
- **Scalping Strategy**: High-frequency trading optimized for 1M/5M timeframes
- **Real-time Dashboard**: Professional trading interface with live updates
- **Backtesting Engine**: 4-year historical data analysis with detailed metrics
- **REST API**: Complete API for trading operations and data access
- **WebSocket Support**: Real-time updates and notifications
- **SQLite Database**: Persistent storage for all trading data

### 📊 Professional Visualizations
- **Candlestick Charts**: Interactive charts with technical indicators
- **Portfolio Equity Curve**: Real-time portfolio performance tracking
- **Performance Metrics**: Comprehensive trading statistics
- **Risk Analytics**: Drawdown analysis and risk metrics
- **Trade History**: Detailed trade logs with P&L tracking

### 🎯 Trading Capabilities
- **Live Trading**: Connect to OANDA for live forex trading
- **Paper Trading**: Risk-free strategy testing
- **Multiple Strategies**: Support for various trading algorithms
- **Risk Management**: Advanced position sizing and stop-loss management
- **Signal Generation**: AI-powered trading signals with confidence scores

## Architecture

```
trading_bot/
├── api/                    # FastAPI REST API backend
│   └── main.py            # API server with WebSocket support
├── database/              # Database layer
│   ├── schema.sql         # SQLite database schema
│   └── database_manager.py # Database operations
├── strategies/            # Trading strategies
│   ├── scalping_forex_strategy.py # Main scalping strategy
│   └── enhanced_forex_strategy.py # Original strategy
├── frontend/              # React/Redux dashboard
│   ├── src/
│   │   ├── components/    # Reusable UI components
│   │   ├── pages/         # Dashboard pages
│   │   └── store/         # Redux state management
│   └── package.json       # Frontend dependencies
├── data/                  # Data feeds and processing
├── utils/                 # Utility functions
├── config/                # Configuration files
├── web_server.py          # Web server integration
└── main.py               # Original CLI interface
```

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+
- OANDA API account (for live trading)

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Initialize database
python -c "from database.database_manager import DatabaseManager; DatabaseManager()"
```

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Build the frontend
npm run build
```

### 3. Configuration

Edit `config/config.yaml`:

```yaml
data:
  symbols:
    - name: EUR_USD
      type: forex
      timeframe: 1m
  oanda:
    account_id: "your-account-id"
    access_token: "your-access-token"
    practice: true

strategies:
  forex:
    name: ScalpingForexStrategy
    params:
      fast_ema: 5
      slow_ema: 13
      stop_loss_pips: 3
      take_profit_pips: 6
```

### 4. Run the Dashboard

#### Live Trading Mode
```bash
python web_server.py --mode live
```

#### Backtesting Mode
```bash
python web_server.py --mode backtest
```

#### Server Only (for development)
```bash
python web_server.py --mode server-only
```

### 5. Access the Dashboard

Open your browser and navigate to:
- **Dashboard**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Usage Guide

### Dashboard Overview

The main dashboard provides:

1. **Real-time Status**: Connection status and system health
2. **Quick Stats**: Active sessions, open trades, P&L, win rate
3. **Trading Chart**: Interactive EUR_USD chart with indicators
4. **Portfolio Summary**: Current portfolio value and performance
5. **Performance Metrics**: Detailed trading statistics
6. **Market Overview**: Market conditions and analysis
7. **Recent Trades**: Latest trading activity

### Live Trading

1. **Start Live Session**:
   ```bash
   python web_server.py --mode live
   ```

2. **Monitor Dashboard**: View real-time updates at http://localhost:8000

3. **Trading Controls**: Use the web interface to:
   - Start/stop trading sessions
   - Adjust strategy parameters
   - Monitor open positions
   - View performance metrics

### Backtesting

1. **Start Backtest Interface**:
   ```bash
   python web_server.py --mode backtest
   ```

2. **Configure Backtest**:
   - Select strategy
   - Set date range (up to 4 years)
   - Choose initial capital
   - Set timeframe (1m or 5m)

3. **Run Backtest**: Click "Start Backtest" and monitor progress

4. **Analyze Results**:
   - View equity curve
   - Analyze trade statistics
   - Export detailed reports

### API Usage

The REST API provides endpoints for:

#### Strategies
- `GET /api/strategies` - List all strategies
- `POST /api/strategies` - Create new strategy
- `GET /api/strategies/{id}` - Get strategy details

#### Trading Sessions
- `GET /api/sessions` - List trading sessions
- `POST /api/sessions` - Create new session
- `GET /api/sessions/active` - Get active sessions

#### Trades
- `GET /api/sessions/{id}/trades` - Get session trades
- `GET /api/trades/open` - Get open trades

#### Market Data
- `GET /api/market-data/{symbol}` - Get OHLCV data

#### Backtesting
- `POST /api/backtest` - Start backtest

### WebSocket Real-time Updates

Connect to `ws://localhost:8000/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
};
```

## Strategy Configuration

### Scalping Strategy Parameters

```yaml
strategies:
  forex:
    name: ScalpingForexStrategy
    params:
      # Core Parameters
      fast_ema: 5              # Fast EMA period
      slow_ema: 13             # Slow EMA period
      rsi_period: 7            # RSI period
      
      # Risk Management
      stop_loss_pips: 3        # Stop loss in pips
      take_profit_pips: 6      # Take profit in pips
      max_risk_per_trade: 0.01 # 1% risk per trade
      position_size_percent: 0.02 # 2% position size
      
      # Trading Hours
      trade_start_hour: 7      # Start trading (UTC)
      trade_end_hour: 17       # Stop trading (UTC)
      
      # Filters
      min_spread: 0.00008      # Minimum spread (0.8 pips)
      max_spread: 0.00025      # Maximum spread (2.5 pips)
      volume_threshold: 1.2    # Volume confirmation
```

## Performance Metrics

The dashboard tracks comprehensive performance metrics:

### Portfolio Metrics
- **Total Return**: Overall portfolio performance
- **Sharpe Ratio**: Risk-adjusted returns
- **Maximum Drawdown**: Largest peak-to-trough decline
- **Calmar Ratio**: Return vs. maximum drawdown
- **Sortino Ratio**: Downside risk-adjusted returns

### Trading Metrics
- **Total Trades**: Number of completed trades
- **Win Rate**: Percentage of profitable trades
- **Profit Factor**: Gross profit / gross loss
- **Average Win/Loss**: Average profit and loss per trade
- **Expectancy**: Expected value per trade

### Risk Metrics
- **Value at Risk (VaR)**: Potential loss at confidence level
- **Current Drawdown**: Current decline from peak
- **Volatility**: Portfolio volatility
- **Beta**: Correlation with market benchmark

## Database Schema

The SQLite database stores:

- **Strategies**: Trading strategy configurations
- **Trading Sessions**: Live and backtest sessions
- **Trades**: Individual trade records
- **Market Data**: OHLCV price data
- **Portfolio Snapshots**: Equity curve data
- **Performance Analytics**: Calculated metrics
- **System Logs**: Application logs

## Development

### Adding New Strategies

1. Create strategy class in `strategies/`:
```python
class MyStrategy(bt.Strategy):
    params = (
        ('param1', 10),
        ('param2', 0.02),
    )
    
    def __init__(self):
        # Initialize indicators
        pass
    
    def next(self):
        # Trading logic
        pass
```

2. Register in database:
```python
db_manager.create_strategy(
    name="My Strategy",
    description="Custom trading strategy",
    strategy_type="custom",
    asset_class="forex",
    timeframe="5m",
    parameters={"param1": 10, "param2": 0.02}
)
```

### Adding New Indicators

1. Create indicator in `indicators/custom_indicators.py`
2. Import in strategy
3. Add to chart visualization

### Extending the API

Add new endpoints in `api/main.py`:

```python
@app.get("/api/my-endpoint")
async def my_endpoint():
    return {"message": "Hello World"}
```

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   ```bash
   # Reinitialize database
   python -c "from database.database_manager import DatabaseManager; DatabaseManager()"
   ```

2. **OANDA API Error**:
   - Check API credentials in config
   - Verify account status
   - Check network connectivity

3. **Frontend Build Error**:
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

4. **Port Already in Use**:
   ```bash
   python web_server.py --mode live --port 8001
   ```

### Logging

Logs are stored in `logs/trading_bot.log`. Adjust log level in config:

```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: logs/trading_bot.log
```

## Security Considerations

- **API Keys**: Store in environment variables
- **Database**: Use proper file permissions
- **Network**: Use HTTPS in production
- **Authentication**: Implement user authentication for production

## Performance Optimization

- **Database**: Regular cleanup of old data
- **Memory**: Monitor memory usage during backtests
- **Network**: Use connection pooling for API calls
- **Caching**: Implement Redis for high-frequency data

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Create an issue on GitHub
- Check the API documentation at `/docs`
- Review the logs for error details

---

**Disclaimer**: This software is for educational purposes. Trading involves risk and you should never trade with money you cannot afford to lose.