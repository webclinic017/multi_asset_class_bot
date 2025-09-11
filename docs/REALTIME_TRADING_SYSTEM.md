# Real-time Trading System with Comprehensive Logging

## Overview

This document describes the comprehensive real-time trading system with buy/sell signal logs and broker activity tracking for 1m and 5m scalping strategies, similar to the enhanced forex strategy functionality.

## 🚀 Key Features

### ✅ Enhanced Real-time Broker
- **Comprehensive Logging**: Every order creation, submission, acceptance, and execution is logged
- **Signal Integration**: Direct integration with trading signals for complete traceability
- **WebSocket Broadcasting**: Real-time updates sent to connected clients
- **Database Persistence**: All activities stored in database for analysis
- **Portfolio Tracking**: Real-time portfolio value updates

### ✅ Real-time Signal Logging System
- **Multi-priority Signals**: LOW, MEDIUM, HIGH, CRITICAL priority levels
- **Comprehensive Metadata**: Indicators, market conditions, risk metrics, execution context
- **Real-time Processing**: Asynchronous signal processing with queue management
- **WebSocket Broadcasting**: Live signal updates to frontend
- **Database Storage**: Persistent signal history with analytics

### ✅ Enhanced Scalping Strategies
- **1M Strategy**: `EnhancedRealtimeScalping1MStrategy` - High-frequency 1-minute scalping
- **5M Strategy**: `EnhancedRealtimeScalping5MStrategy` - Medium-frequency 5-minute scalping
- **Multi-asset Support**: EUR_USD, GBP_USD, USD_JPY, AUD_USD, BTC_USD, ETH_USD
- **Advanced Indicators**: EMA, RSI, MACD, Bollinger Bands, Stochastic, Williams %R
- **Dynamic Position Sizing**: Kelly Criterion-based position sizing
- **Regime Detection**: Market regime analysis for signal filtering

### ✅ Real-time API Endpoints
- **Signal Data**: `/api/realtime/signals/{session_id}`
- **Order Activities**: `/api/realtime/activities/{session_id}`
- **Broker Statistics**: `/api/realtime/broker-stats/{session_id}`
- **Analytics**: `/api/realtime/analytics/signals/{session_id}`
- **Dashboard Data**: `/api/realtime/dashboard/{session_id}`
- **Live Trading**: `/api/live-trading/start`, `/api/live-trading/stop/{session_id}`

### ✅ WebSocket Support
- **Real-time Updates**: Live signal and activity broadcasting
- **Session-specific**: `/ws/realtime/{session_id}` for targeted updates
- **Multiple Clients**: Support for multiple connected clients
- **Auto-reconnection**: Frontend handles connection drops gracefully

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   API Server     │    │   Database      │
│   (React)       │◄──►│   (FastAPI)      │◄──►│   (SQLite)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         ▲                        ▲                       ▲
         │                        │                       │
         ▼                        ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   WebSocket     │    │ Signal Logger    │    │ Enhanced Broker │
│   Manager       │◄──►│ (Real-time)      │◄──►│ (Backtrader)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                ▲                       ▲
                                │                       │
                                ▼                       ▼
                    ┌──────────────────┐    ┌─────────────────┐
                    │ Trading Engine   │◄──►│ Scalping        │
                    │ (Real-time)      │    │ Strategies      │
                    └──────────────────┘    └─────────────────┘
```

## 📊 Database Schema

### Real-time Signal Logs
```sql
CREATE TABLE realtime_signal_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id VARCHAR(100) NOT NULL UNIQUE,
    session_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    signal_type VARCHAR(10) NOT NULL, -- 'BUY', 'SELL', 'HOLD'
    signal_strength DECIMAL(4,3) NOT NULL,
    confidence DECIMAL(4,3) NOT NULL,
    price DECIMAL(12,6) NOT NULL,
    source VARCHAR(20) NOT NULL, -- 'strategy', 'indicator', 'manual', 'system'
    priority INTEGER NOT NULL, -- 1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL
    strategy_name VARCHAR(100) NOT NULL,
    indicators TEXT, -- JSON string of indicator values
    market_conditions TEXT, -- JSON string of market conditions
    risk_metrics TEXT, -- JSON string of risk metrics
    execution_context TEXT, -- JSON string of execution context
    executed BOOLEAN DEFAULT 0,
    execution_time TIMESTAMP,
    execution_price DECIMAL(12,6),
    trade_id INTEGER,
    pnl DECIMAL(15,2)
);
```

### Real-time Order Activities
```sql
CREATE TABLE realtime_order_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    activity_id VARCHAR(100) NOT NULL,
    session_id INTEGER NOT NULL,
    order_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    order_type VARCHAR(20) NOT NULL, -- 'Market', 'Limit', 'Stop', etc.
    side VARCHAR(10) NOT NULL, -- 'BUY', 'SELL'
    size DECIMAL(15,6) NOT NULL,
    price DECIMAL(12,6),
    status VARCHAR(20) NOT NULL, -- 'created', 'submitted', 'accepted', 'completed', etc.
    message TEXT NOT NULL,
    execution_price DECIMAL(12,6),
    execution_size DECIMAL(15,6),
    commission DECIMAL(10,4),
    strategy_name VARCHAR(100),
    signal_id VARCHAR(100)
);
```

## 🚀 Getting Started

### 1. Database Setup
The enhanced strategies are automatically added to the database when you initialize it:

```python
from database.database_manager import DatabaseManager
db_manager = DatabaseManager()  # Automatically creates tables and strategies
```

### 2. Frontend Integration
The new strategies automatically appear in the existing backtesting dropdown:

1. Navigate to the **Backtesting** page
2. Select **Symbol** (EUR_USD, GBP_USD, etc.)
3. Choose from **Enhanced Realtime Scalping** strategies in the dropdown
4. The strategies are filtered by symbol compatibility

### 3. Running Real-time Trading

#### Option A: Via Web Interface
1. Go to `/api/live-trading/start` endpoint
2. POST with strategy configuration:
```json
{
    "strategy_id": 25,
    "symbol": "EUR_USD",
    "initial_capital": 10000.0
}
```

#### Option B: Via Python Code
```python
from backtesting.realtime_trading_engine import create_realtime_trading_engine

config = {
    "initial_capital": 10000.0,
    "commission": 0.001,
    "strategy": "EnhancedRealtimeScalping1MStrategy",
    "symbol": "EUR_USD",
    "timeframe": "1m"
}

engine = create_realtime_trading_engine(config, session_id=1)

strategy_params = {
    "fast_length": 5,
    "slow_length": 13,
    "signal_strength_threshold": 0.1,
    "high_confidence_threshold": 0.7,
    "max_trades_per_hour": 15,
    "dynamic_sizing": True
}

if engine.setup_engine("EnhancedRealtimeScalping1MStrategy", strategy_params):
    engine.start_trading()
```

### 4. Monitoring Real-time Data

#### WebSocket Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/realtime/1');

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'realtime_signal') {
        console.log('New Signal:', data.data);
    } else if (data.type === 'order_activity') {
        console.log('Order Activity:', data.data);
    } else if (data.type === 'broker_stats_update') {
        console.log('Broker Stats:', data.data);
    }
};
```

#### API Endpoints
```bash
# Get real-time signals
curl http://localhost:8000/api/realtime/signals/1

# Get order activities
curl http://localhost:8000/api/realtime/activities/1

# Get broker statistics
curl http://localhost:8000/api/realtime/broker-stats/1/latest

# Get comprehensive dashboard data
curl http://localhost:8000/api/realtime/dashboard/1
```

## 📈 Available Strategies

### Enhanced Real-time Scalping Strategies

| Strategy Name | Symbol | Timeframe | Max Trades/Hour | Features |
|---------------|--------|-----------|-----------------|----------|
| Enhanced Realtime Scalping EUR_USD 1M | EUR_USD | 1m | 15 | High-frequency, quick exits |
| Enhanced Realtime Scalping EUR_USD 5M | EUR_USD | 5m | 8 | Medium-frequency, larger targets |
| Enhanced Realtime Scalping GBP_USD 1M | GBP_USD | 1m | 12 | Volatility-adjusted |
| Enhanced Realtime Scalping GBP_USD 5M | GBP_USD | 5m | 6 | Trend-following |
| Enhanced Realtime Scalping USD_JPY 1M | USD_JPY | 1m | 18 | Asian session optimized |
| Enhanced Realtime Scalping USD_JPY 5M | USD_JPY | 5m | 10 | Carry trade aware |
| Enhanced Realtime Scalping BTC_USD 1M | BTC_USD | 1m | 20 | Crypto volatility adapted |
| Enhanced Realtime Scalping BTC_USD 5M | BTC_USD | 5m | 12 | Institutional flow aware |
| Enhanced Realtime Scalping ETH_USD 1M | ETH_USD | 1m | 18 | DeFi correlation |
| Enhanced Realtime Scalping ETH_USD 5M | ETH_USD | 5m | 10 | Gas fee consideration |

## 🔧 Configuration Parameters

### Strategy Parameters
```python
{
    "fast_length": 5,                    # Fast EMA period
    "slow_length": 13,                   # Slow EMA period
    "rsi_period": 7,                     # RSI calculation period
    "signal_strength_threshold": 0.1,    # Minimum signal strength
    "high_confidence_threshold": 0.7,    # High confidence threshold
    "max_trades_per_hour": 15,           # Maximum trades per hour
    "min_time_between_trades": 30,       # Minimum seconds between trades
    "quick_exit_threshold": 0.002,       # Quick profit exit threshold
    "dynamic_sizing": True,              # Enable dynamic position sizing
    "volatility_adjustment": True,       # Adjust for volatility
    "use_regime_filter": True,           # Enable regime filtering
    "momentum_acceleration": 1.6,        # Momentum boost factor
    "trend_following_boost": 1.4,        # Trend following boost
    "breakout_multiplier": 1.8           # Breakout signal multiplier
}
```

## 📊 Real-time Data Examples

### Signal Log Example
```json
{
    "signal_id": "1_EUR_USD_123_1704067200",
    "session_id": 1,
    "symbol": "EUR_USD",
    "timeframe": "1m",
    "timestamp": "2024-01-01T00:00:00",
    "signal_type": "BUY",
    "signal_strength": 0.75,
    "confidence": 0.85,
    "price": 1.1234,
    "source": "strategy",
    "priority": 3,
    "strategy_name": "EnhancedRealtimeScalping1MStrategy",
    "indicators": {
        "ema_fast": 1.1230,
        "ema_slow": 1.1220,
        "rsi": 35.5,
        "macd": 0.0012,
        "bb_position": 0.25
    },
    "market_conditions": {
        "volatility": 0.0015,
        "regime": "bullish_trend",
        "regime_confidence": 0.8,
        "trend_strength": 0.0008
    },
    "risk_metrics": {
        "position_size": 0.02,
        "atr_percent": 0.0015,
        "max_risk": 0.015,
        "trades_this_hour": 3
    },
    "executed": true,
    "execution_time": "2024-01-01T00:00:05",
    "execution_price": 1.1235,
    "trade_id": 456
}
```

### Order Activity Example
```json
{
    "activity_id": "activity_123_456",
    "session_id": 1,
    "order_id": 456,
    "symbol": "EUR_USD",
    "timestamp": "2024-01-01T00:00:05",
    "order_type": "Market",
    "side": "BUY",
    "size": 0.02,
    "price": null,
    "status": "completed",
    "message": "Order executed at 1.1235, value: 22.47, commission: 0.0225",
    "execution_price": 1.1235,
    "execution_size": 0.02,
    "commission": 0.0225,
    "strategy_name": "EnhancedRealtimeScalping1MStrategy",
    "signal_id": "1_EUR_USD_123_1704067200"
}
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
cd tests
python test_realtime_system.py
```

The test suite covers:
- ✅ Enhanced broker functionality
- ✅ Signal logger operations
- ✅ Strategy signal generation
- ✅ Database operations
- ✅ Trading engine setup
- ✅ Complete integration flow
- ✅ API endpoint logic

## 🔍 Monitoring and Analytics

### Real-time Dashboard Data
Access comprehensive real-time data via:
- **Signals**: Recent buy/sell signals with full context
- **Activities**: Order lifecycle tracking
- **Broker Stats**: Portfolio value, cash, execution counts
- **Analytics**: Signal success rates, execution times
- **Portfolio**: Real-time equity curve updates

### WebSocket Events
- `realtime_signal`: New trading signal generated
- `order_activity`: Order status change
- `broker_stats_update`: Portfolio statistics update
- `signal_executed`: Signal execution confirmation
- `realtime_trading_started`: Trading session started
- `realtime_trading_stopped`: Trading session stopped

## 🚨 Important Notes

1. **Database Compatibility**: New tables are automatically created when you run the system
2. **Frontend Integration**: Strategies appear automatically in existing dropdown - no new React components needed
3. **Real-time Performance**: System processes signals asynchronously for optimal performance
4. **Memory Management**: Old signals are automatically cleaned up to prevent memory issues
5. **Error Handling**: Comprehensive error handling and logging throughout the system

## 🎯 Next Steps

1. **Run Tests**: Execute `python tests/test_realtime_system.py` to verify everything works
2. **Start Web Server**: Run `python web_server.py --mode server-only` to start the API
3. **Access Frontend**: Navigate to `http://localhost:8000` to use the web interface
4. **Select Strategy**: Choose an "Enhanced Realtime Scalping" strategy from the dropdown
5. **Monitor Logs**: Watch real-time signals and activities in the browser console or API endpoints

The system is now ready for real-time scalping with comprehensive logging and monitoring! 🚀