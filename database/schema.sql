-- SQLite Database Schema for Trading Bot Dashboard
-- Supports both live trading and backtesting data storage

-- Trading strategies table
CREATE TABLE IF NOT EXISTS strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50) NOT NULL, -- 'scalping', 'swing', 'trend'
    asset_class VARCHAR(50) NOT NULL,   -- 'forex', 'crypto', 'futures'
    timeframe VARCHAR(10) NOT NULL,     -- '1m', '5m', '1h', etc.
    parameters TEXT,                    -- JSON string of strategy parameters
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1
);

-- Trading sessions table
CREATE TABLE IF NOT EXISTS trading_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_type VARCHAR(20) NOT NULL, -- 'live', 'backtest'
    strategy_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    initial_capital DECIMAL(15,2) NOT NULL,
    final_capital DECIMAL(15,2),
    total_return DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- 'active', 'completed', 'stopped'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
);

-- Individual trades table
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    trade_id VARCHAR(50), -- External trade ID from broker
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL, -- 'BUY', 'SELL'
    entry_time TIMESTAMP NOT NULL,
    exit_time TIMESTAMP,
    entry_price DECIMAL(12,6) NOT NULL,
    exit_price DECIMAL(12,6),
    quantity DECIMAL(15,6) NOT NULL,
    stop_loss DECIMAL(12,6),
    take_profit DECIMAL(12,6),
    pnl DECIMAL(15,2),
    pnl_pips DECIMAL(8,2),
    commission DECIMAL(10,4),
    swap DECIMAL(10,4),
    duration_seconds INTEGER,
    exit_reason VARCHAR(50), -- 'take_profit', 'stop_loss', 'trailing_stop', 'manual'
    signal_strength DECIMAL(4,3),
    confidence DECIMAL(4,3),
    status VARCHAR(20) DEFAULT 'open', -- 'open', 'closed', 'cancelled'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id)
);

-- Market data table (OHLCV)
CREATE TABLE IF NOT EXISTS market_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open_price DECIMAL(12,6) NOT NULL,
    high_price DECIMAL(12,6) NOT NULL,
    low_price DECIMAL(12,6) NOT NULL,
    close_price DECIMAL(12,6) NOT NULL,
    volume DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, timestamp)
);

-- Technical indicators table
CREATE TABLE IF NOT EXISTS technical_indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    indicator_name VARCHAR(50) NOT NULL,
    indicator_value DECIMAL(12,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, timeframe, timestamp, indicator_name)
);

-- Trading signals table
CREATE TABLE IF NOT EXISTS trading_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    signal_type VARCHAR(10) NOT NULL, -- 'BUY', 'SELL', 'HOLD'
    signal_strength DECIMAL(4,3) NOT NULL,
    confidence DECIMAL(4,3) NOT NULL,
    price DECIMAL(12,6) NOT NULL,
    indicators TEXT, -- JSON string of indicator values
    executed BOOLEAN DEFAULT 0,
    trade_id INTEGER, -- Reference to executed trade
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

-- Portfolio snapshots table (for equity curve)
CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    total_value DECIMAL(15,2) NOT NULL,
    cash_balance DECIMAL(15,2) NOT NULL,
    unrealized_pnl DECIMAL(15,2) DEFAULT 0,
    realized_pnl DECIMAL(15,2) DEFAULT 0,
    open_positions INTEGER DEFAULT 0,
    daily_pnl DECIMAL(15,2) DEFAULT 0,
    drawdown DECIMAL(8,4) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id)
);

-- Risk metrics table
CREATE TABLE IF NOT EXISTS risk_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    var_1d DECIMAL(10,4), -- 1-day Value at Risk
    var_5d DECIMAL(10,4), -- 5-day Value at Risk
    max_drawdown DECIMAL(8,4),
    current_drawdown DECIMAL(8,4),
    volatility DECIMAL(8,4),
    beta DECIMAL(6,4),
    sharpe_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    calmar_ratio DECIMAL(8,4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id)
);

-- Performance analytics table
CREATE TABLE IF NOT EXISTS performance_analytics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    period_start TIMESTAMP NOT NULL,
    period_end TIMESTAMP NOT NULL,
    period_type VARCHAR(20) NOT NULL, -- 'daily', 'weekly', 'monthly'
    total_return DECIMAL(8,4),
    benchmark_return DECIMAL(8,4),
    alpha DECIMAL(8,4),
    beta DECIMAL(6,4),
    information_ratio DECIMAL(8,4),
    tracking_error DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    profit_factor DECIMAL(8,4),
    expectancy DECIMAL(10,4),
    trades_count INTEGER,
    avg_trade_duration INTEGER, -- in seconds
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id)
);

-- News and events table
CREATE TABLE IF NOT EXISTS market_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'news', 'economic_data', 'earnings'
    symbol VARCHAR(20),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    impact VARCHAR(20), -- 'high', 'medium', 'low'
    actual_value DECIMAL(15,4),
    forecast_value DECIMAL(15,4),
    previous_value DECIMAL(15,4),
    sentiment_score DECIMAL(4,3), -- -1 to 1
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System logs table
CREATE TABLE IF NOT EXISTS system_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    log_level VARCHAR(20) NOT NULL, -- 'DEBUG', 'INFO', 'WARNING', 'ERROR'
    component VARCHAR(50) NOT NULL, -- 'strategy', 'data_feed', 'broker', 'risk_manager'
    message TEXT NOT NULL,
    session_id INTEGER,
    trade_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

-- User settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key VARCHAR(100) NOT NULL UNIQUE,
    setting_value TEXT,
    setting_type VARCHAR(20) DEFAULT 'string', -- 'string', 'number', 'boolean', 'json'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Real-time signal logs table (enhanced version of trading_signals)
CREATE TABLE IF NOT EXISTS realtime_signal_logs (
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
    pnl DECIMAL(15,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id),
    FOREIGN KEY (trade_id) REFERENCES trades(id)
);

-- Real-time order activity logs table
CREATE TABLE IF NOT EXISTS realtime_order_activities (
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
    signal_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id),
    FOREIGN KEY (signal_id) REFERENCES realtime_signal_logs(signal_id)
);

-- Real-time broker statistics table
CREATE TABLE IF NOT EXISTS realtime_broker_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    cash DECIMAL(15,2) NOT NULL,
    portfolio_value DECIMAL(15,2) NOT NULL,
    total_signals INTEGER DEFAULT 0,
    total_orders INTEGER DEFAULT 0,
    executions INTEGER DEFAULT 0,
    buy_signals INTEGER DEFAULT 0,
    sell_signals INTEGER DEFAULT 0,
    completed_orders INTEGER DEFAULT 0,
    rejected_orders INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id)
);

-- Backtest results table (for historical analysis)
CREATE TABLE IF NOT EXISTS backtest_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    test_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital DECIMAL(15,2) NOT NULL,
    final_capital DECIMAL(15,2) NOT NULL,
    total_return DECIMAL(8,4) NOT NULL,
    annualized_return DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    sortino_ratio DECIMAL(8,4),
    calmar_ratio DECIMAL(8,4),
    win_rate DECIMAL(8,4),
    profit_factor DECIMAL(8,4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    avg_win DECIMAL(10,4),
    avg_loss DECIMAL(10,4),
    largest_win DECIMAL(10,4),
    largest_loss DECIMAL(10,4),
    avg_trade_duration INTEGER,
    parameters TEXT, -- JSON string of strategy parameters used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES trading_sessions(id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_trades_session_id ON trades(session_id);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time);
CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);

CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timeframe ON market_data(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_market_data_timestamp ON market_data(timestamp);

CREATE INDEX IF NOT EXISTS idx_trading_signals_session_id ON trading_signals(session_id);
CREATE INDEX IF NOT EXISTS idx_trading_signals_timestamp ON trading_signals(timestamp);

CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_session_id ON portfolio_snapshots(session_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_snapshots_timestamp ON portfolio_snapshots(timestamp);

CREATE INDEX IF NOT EXISTS idx_technical_indicators_symbol_timeframe ON technical_indicators(symbol, timeframe);
CREATE INDEX IF NOT EXISTS idx_technical_indicators_timestamp ON technical_indicators(timestamp);

CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_system_logs_session_id ON system_logs(session_id);

-- Indexes for real-time tables
CREATE INDEX IF NOT EXISTS idx_realtime_signal_logs_session_id ON realtime_signal_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_realtime_signal_logs_timestamp ON realtime_signal_logs(timestamp);
CREATE INDEX IF NOT EXISTS idx_realtime_signal_logs_signal_id ON realtime_signal_logs(signal_id);
CREATE INDEX IF NOT EXISTS idx_realtime_signal_logs_symbol ON realtime_signal_logs(symbol);
CREATE INDEX IF NOT EXISTS idx_realtime_signal_logs_signal_type ON realtime_signal_logs(signal_type);

CREATE INDEX IF NOT EXISTS idx_realtime_order_activities_session_id ON realtime_order_activities(session_id);
CREATE INDEX IF NOT EXISTS idx_realtime_order_activities_timestamp ON realtime_order_activities(timestamp);
CREATE INDEX IF NOT EXISTS idx_realtime_order_activities_order_id ON realtime_order_activities(order_id);
CREATE INDEX IF NOT EXISTS idx_realtime_order_activities_signal_id ON realtime_order_activities(signal_id);

CREATE INDEX IF NOT EXISTS idx_realtime_broker_stats_session_id ON realtime_broker_stats(session_id);
CREATE INDEX IF NOT EXISTS idx_realtime_broker_stats_timestamp ON realtime_broker_stats(timestamp);

-- Insert default strategies
-- EUR/USD Strategies
INSERT OR IGNORE INTO strategies (name, description, strategy_type, asset_class, timeframe, parameters) VALUES
('Scalping EUR_USD 1M', 'High-frequency scalping strategy for EUR_USD on 1-minute timeframe', 'scalping', 'forex', '1m', '{"fast_ema": 5, "slow_ema": 13, "rsi_period": 7, "stop_loss_pips": 3, "take_profit_pips": 6}'),
('Scalping EUR_USD 5M', 'High-frequency scalping strategy for EUR_USD on 5-minute timeframe', 'scalping', 'forex', '5m', '{"fast_ema": 5, "slow_ema": 13, "rsi_period": 7, "stop_loss_pips": 5, "take_profit_pips": 10}'),
('Enhanced EUR_USD Strategy', 'Advanced quantitative forex strategy for EUR_USD with multi-timeframe analysis', 'trend', 'forex', '1h', '{"fast_length": 8, "slow_length": 21, "rsi_period": 9, "dynamic_sizing": true}'),

-- GBP/USD Strategies
('Scalping GBP_USD 1M', 'High-frequency scalping strategy for GBP_USD on 1-minute timeframe', 'scalping', 'forex', '1m', '{"fast_ema": 6, "slow_ema": 14, "rsi_period": 8, "stop_loss_pips": 4, "take_profit_pips": 8}'),
('Scalping GBP_USD 5M', 'High-frequency scalping strategy for GBP_USD on 5-minute timeframe', 'scalping', 'forex', '5m', '{"fast_ema": 6, "slow_ema": 14, "rsi_period": 8, "stop_loss_pips": 6, "take_profit_pips": 12}'),
('Enhanced GBP_USD Strategy', 'Advanced quantitative forex strategy for GBP_USD with volatility adjustment', 'trend', 'forex', '1h', '{"fast_length": 9, "slow_length": 22, "rsi_period": 10, "dynamic_sizing": true}'),

-- USD/JPY Strategies
('Scalping USD_JPY 1M', 'High-frequency scalping strategy for USD_JPY on 1-minute timeframe', 'scalping', 'forex', '1m', '{"fast_ema": 4, "slow_ema": 12, "rsi_period": 6, "stop_loss_pips": 2, "take_profit_pips": 5}'),
('Scalping USD_JPY 5M', 'High-frequency scalping strategy for USD_JPY on 5-minute timeframe', 'scalping', 'forex', '5m', '{"fast_ema": 4, "slow_ema": 12, "rsi_period": 6, "stop_loss_pips": 4, "take_profit_pips": 8}'),
('Enhanced USD_JPY Strategy', 'Advanced quantitative forex strategy for USD_JPY with Asian session optimization', 'trend', 'forex', '1h', '{"fast_length": 7, "slow_length": 20, "rsi_period": 8, "dynamic_sizing": true}'),

-- AUD/USD Strategies
('Scalping AUD_USD 1M', 'High-frequency scalping strategy for AUD_USD on 1-minute timeframe', 'scalping', 'forex', '1m', '{"fast_ema": 5, "slow_ema": 13, "rsi_period": 7, "stop_loss_pips": 3, "take_profit_pips": 7}'),
('Scalping AUD_USD 5M', 'High-frequency scalping strategy for AUD_USD on 5-minute timeframe', 'scalping', 'forex', '5m', '{"fast_ema": 5, "slow_ema": 13, "rsi_period": 7, "stop_loss_pips": 5, "take_profit_pips": 11}'),
('Enhanced AUD_USD Strategy', 'Advanced quantitative forex strategy for AUD_USD with commodity correlation', 'trend', 'forex', '1h', '{"fast_length": 8, "slow_length": 21, "rsi_period": 9, "dynamic_sizing": true}'),

-- Crypto Strategies
('Scalping BTC_USD 1M', 'High-frequency scalping strategy for BTC_USD on 1-minute timeframe', 'scalping', 'crypto', '1m', '{"fast_ema": 3, "slow_ema": 10, "rsi_period": 5, "stop_loss_percent": 0.02, "take_profit_percent": 0.04}'),
('Scalping BTC_USD 5M', 'High-frequency scalping strategy for BTC_USD on 5-minute timeframe', 'scalping', 'crypto', '5m', '{"fast_ema": 3, "slow_ema": 10, "rsi_period": 5, "stop_loss_percent": 0.03, "take_profit_percent": 0.06}'),
('Enhanced BTC_USD Strategy', 'Advanced quantitative crypto strategy for BTC_USD with volatility clustering', 'trend', 'crypto', '1h', '{"fast_length": 6, "slow_length": 18, "rsi_period": 7, "dynamic_sizing": true}'),

('Scalping ETH_USD 1M', 'High-frequency scalping strategy for ETH_USD on 1-minute timeframe', 'scalping', 'crypto', '1m', '{"fast_ema": 4, "slow_ema": 11, "rsi_period": 6, "stop_loss_percent": 0.025, "take_profit_percent": 0.05}'),
('Scalping ETH_USD 5M', 'High-frequency scalping strategy for ETH_USD on 5-minute timeframe', 'scalping', 'crypto', '5m', '{"fast_ema": 4, "slow_ema": 11, "rsi_period": 6, "stop_loss_percent": 0.035, "take_profit_percent": 0.07}'),
('Enhanced ETH_USD Strategy', 'Advanced quantitative crypto strategy for ETH_USD with DeFi correlation', 'trend', 'crypto', '1h', '{"fast_length": 7, "slow_length": 19, "rsi_period": 8, "dynamic_sizing": true}'),

('Scalping SOL_USD 1M', 'High-frequency scalping strategy for SOL_USD on 1-minute timeframe', 'scalping', 'crypto', '1m', '{"fast_ema": 3, "slow_ema": 9, "rsi_period": 5, "stop_loss_percent": 0.03, "take_profit_percent": 0.06}'),
('Scalping SOL_USD 5M', 'High-frequency scalping strategy for SOL_USD on 5-minute timeframe', 'scalping', 'crypto', '5m', '{"fast_ema": 3, "slow_ema": 9, "rsi_period": 5, "stop_loss_percent": 0.04, "take_profit_percent": 0.08}'),
('Enhanced SOL_USD Strategy', 'Advanced quantitative crypto strategy for SOL_USD with ecosystem analysis', 'trend', 'crypto', '1h', '{"fast_length": 6, "slow_length": 17, "rsi_period": 7, "dynamic_sizing": true}'),

-- Enhanced Real-time Scalping Strategies with Comprehensive Logging
('Enhanced Realtime Scalping EUR_USD 1M', 'Enhanced real-time scalping strategy for EUR_USD on 1-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '1m', '{"fast_length": 5, "slow_length": 13, "rsi_period": 7, "signal_strength_threshold": 0.1, "high_confidence_threshold": 0.7, "max_trades_per_hour": 15, "min_time_between_trades": 30, "quick_exit_threshold": 0.002, "dynamic_sizing": true, "volatility_adjustment": true}'),
('Enhanced Realtime Scalping EUR_USD 5M', 'Enhanced real-time scalping strategy for EUR_USD on 5-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '5m', '{"fast_length": 5, "slow_length": 13, "rsi_period": 7, "signal_strength_threshold": 0.12, "high_confidence_threshold": 0.75, "max_trades_per_hour": 8, "min_time_between_trades": 120, "quick_exit_threshold": 0.003, "dynamic_sizing": true, "volatility_adjustment": true}'),

('Enhanced Realtime Scalping GBP_USD 1M', 'Enhanced real-time scalping strategy for GBP_USD on 1-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '1m', '{"fast_length": 6, "slow_length": 14, "rsi_period": 8, "signal_strength_threshold": 0.1, "high_confidence_threshold": 0.7, "max_trades_per_hour": 12, "min_time_between_trades": 35, "quick_exit_threshold": 0.0025, "dynamic_sizing": true, "volatility_adjustment": true}'),
('Enhanced Realtime Scalping GBP_USD 5M', 'Enhanced real-time scalping strategy for GBP_USD on 5-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '5m', '{"fast_length": 6, "slow_length": 14, "rsi_period": 8, "signal_strength_threshold": 0.12, "high_confidence_threshold": 0.75, "max_trades_per_hour": 6, "min_time_between_trades": 150, "quick_exit_threshold": 0.0035, "dynamic_sizing": true, "volatility_adjustment": true}'),

('Enhanced Realtime Scalping USD_JPY 1M', 'Enhanced real-time scalping strategy for USD_JPY on 1-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '1m', '{"fast_length": 4, "slow_length": 12, "rsi_period": 6, "signal_strength_threshold": 0.1, "high_confidence_threshold": 0.7, "max_trades_per_hour": 18, "min_time_between_trades": 25, "quick_exit_threshold": 0.0015, "dynamic_sizing": true, "volatility_adjustment": true}'),
('Enhanced Realtime Scalping USD_JPY 5M', 'Enhanced real-time scalping strategy for USD_JPY on 5-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '5m', '{"fast_length": 4, "slow_length": 12, "rsi_period": 6, "signal_strength_threshold": 0.12, "high_confidence_threshold": 0.75, "max_trades_per_hour": 10, "min_time_between_trades": 100, "quick_exit_threshold": 0.0025, "dynamic_sizing": true, "volatility_adjustment": true}'),

('Enhanced Realtime Scalping AUD_USD 1M', 'Enhanced real-time scalping strategy for AUD_USD on 1-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '1m', '{"fast_length": 5, "slow_length": 13, "rsi_period": 7, "signal_strength_threshold": 0.1, "high_confidence_threshold": 0.7, "max_trades_per_hour": 14, "min_time_between_trades": 30, "quick_exit_threshold": 0.002, "dynamic_sizing": true, "volatility_adjustment": true}'),
('Enhanced Realtime Scalping AUD_USD 5M', 'Enhanced real-time scalping strategy for AUD_USD on 5-minute timeframe with comprehensive signal logging', 'scalping', 'forex', '5m', '{"fast_length": 5, "slow_length": 13, "rsi_period": 7, "signal_strength_threshold": 0.12, "high_confidence_threshold": 0.75, "max_trades_per_hour": 7, "min_time_between_trades": 130, "quick_exit_threshold": 0.003, "dynamic_sizing": true, "volatility_adjustment": true}'),

-- Enhanced Real-time Crypto Scalping Strategies
('Enhanced Realtime Scalping BTC_USD 1M', 'Enhanced real-time scalping strategy for BTC_USD on 1-minute timeframe with comprehensive signal logging', 'scalping', 'crypto', '1m', '{"fast_length": 3, "slow_length": 10, "rsi_period": 5, "signal_strength_threshold": 0.15, "high_confidence_threshold": 0.8, "max_trades_per_hour": 20, "min_time_between_trades": 20, "quick_exit_threshold": 0.005, "dynamic_sizing": true, "volatility_adjustment": true}'),
('Enhanced Realtime Scalping BTC_USD 5M', 'Enhanced real-time scalping strategy for BTC_USD on 5-minute timeframe with comprehensive signal logging', 'scalping', 'crypto', '5m', '{"fast_length": 3, "slow_length": 10, "rsi_period": 5, "signal_strength_threshold": 0.18, "high_confidence_threshold": 0.8, "max_trades_per_hour": 12, "min_time_between_trades": 80, "quick_exit_threshold": 0.008, "dynamic_sizing": true, "volatility_adjustment": true}'),

('Enhanced Realtime Scalping ETH_USD 1M', 'Enhanced real-time scalping strategy for ETH_USD on 1-minute timeframe with comprehensive signal logging', 'scalping', 'crypto', '1m', '{"fast_length": 4, "slow_length": 11, "rsi_period": 6, "signal_strength_threshold": 0.15, "high_confidence_threshold": 0.8, "max_trades_per_hour": 18, "min_time_between_trades": 25, "quick_exit_threshold": 0.006, "dynamic_sizing": true, "volatility_adjustment": true}'),
('Enhanced Realtime Scalping ETH_USD 5M', 'Enhanced real-time scalping strategy for ETH_USD on 5-minute timeframe with comprehensive signal logging', 'scalping', 'crypto', '5m', '{"fast_length": 4, "slow_length": 11, "rsi_period": 6, "signal_strength_threshold": 0.18, "high_confidence_threshold": 0.8, "max_trades_per_hour": 10, "min_time_between_trades": 90, "quick_exit_threshold": 0.009, "dynamic_sizing": true, "volatility_adjustment": true}'),

-- HFT Futures Strategies
('Market Making HFT', 'High-frequency market making strategy that profits from bid-ask spreads by simultaneously placing buy and sell orders', 'hft', 'futures', '1m', '{"spread_width": 0.0002, "max_inventory": 10, "inventory_rebalance_threshold": 3, "quote_refresh_time": 5, "min_spread": 0.0001, "max_spread": 0.001, "volatility_lookback": 20, "risk_limit": 0.02, "max_orders_per_side": 3, "order_size": 1, "adaptive_spread": true, "printlog": false}'),
('Statistical Arbitrage HFT', 'High-frequency statistical arbitrage strategy that exploits mean-reverting relationships between related futures contracts', 'hft', 'futures', '1m', '{"lookback_period": 100, "entry_threshold": 2.0, "exit_threshold": 0.5, "max_holding_time": 300, "min_relationship_strength": 0.7, "max_position_size": 5, "risk_limit": 0.01, "cointegration_test_period": 50, "zscore_smoothing": 5, "adaptive_threshold": true, "pairs_update_interval": 3600, "printlog": false}'),
('Latency Arbitrage HFT', 'High-frequency latency arbitrage strategy that exploits price discrepancies for the same futures contract across different exchanges', 'hft', 'futures', '1m', '{"max_position_size": 10, "min_profit_threshold": 0.0001, "max_holding_time": 60, "latency_threshold": 0.5, "price_tolerance": 0.0002, "risk_limit": 0.005, "exchange_count": 2, "arbitrage_window": 5, "volume_threshold": 100, "spread_threshold": 0.001, "adaptive_position_sizing": true, "printlog": false}'),
('Momentum Ignition HFT', 'Controversial high-frequency momentum ignition strategy that creates artificial momentum through rapid small trades to influence market behavior', 'hft', 'futures', '1m', '{"ignition_volume": 50, "trade_interval": 0.1, "momentum_threshold": 0.001, "profit_target": 0.005, "stop_loss": 0.002, "max_ignition_trades": 10, "cooldown_period": 300, "volume_multiplier": 2.0, "adaptive_ignition": true, "risk_limit": 0.01, "min_market_volume": 1000, "printlog": false}');

-- Insert default user settings
INSERT OR IGNORE INTO user_settings (setting_key, setting_value, setting_type, description) VALUES
('dashboard_refresh_interval', '5', 'number', 'Dashboard refresh interval in seconds'),
('default_chart_timeframe', '5m', 'string', 'Default timeframe for charts'),
('risk_alert_threshold', '0.15', 'number', 'Risk alert threshold (15% drawdown)'),
('max_daily_trades', '50', 'number', 'Maximum trades per day'),
('enable_notifications', 'true', 'boolean', 'Enable push notifications'),
('theme', 'dark', 'string', 'Dashboard theme (light/dark)'),
('timezone', 'UTC', 'string', 'User timezone'),
('currency_display', 'USD', 'string', 'Display currency');