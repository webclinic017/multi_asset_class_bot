"""
FastAPI REST API Backend for Trading Bot Dashboard
Serves ONLY real backtesting data from SQLite database - no simulations or synthetic data
"""

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
import pandas as pd
import numpy as np
import yaml

# Import our modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from utils.logger import setup_logging

# Pydantic models for API requests/responses
class StrategyCreate(BaseModel):
    name: str
    description: str
    strategy_type: str
    asset_class: str
    timeframe: str
    parameters: Dict[str, Any]

class StrategyResponse(BaseModel):
    id: int
    name: str
    description: str
    strategy_type: str
    asset_class: str
    timeframe: str
    parameters: Dict[str, Any]
    created_at: str
    is_active: bool

class TradingSessionCreate(BaseModel):
    strategy_id: int
    symbol: str
    initial_capital: float
    session_type: str = "live"

class TradingSessionResponse(BaseModel):
    id: int
    session_type: str
    strategy_id: int
    strategy_name: str
    symbol: str
    start_time: str
    end_time: Optional[str]
    initial_capital: float
    final_capital: Optional[float]
    total_return: Optional[float]
    max_drawdown: Optional[float]
    sharpe_ratio: Optional[float]
    win_rate: Optional[float]
    total_trades: int
    winning_trades: Optional[int]
    losing_trades: Optional[int]
    status: str

class TradeResponse(BaseModel):
    id: int
    session_id: int
    symbol: str
    side: str
    entry_time: str
    exit_time: Optional[str]
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: Optional[float]
    pnl_pips: Optional[float]
    status: str
    exit_reason: Optional[str]

class BacktestRequest(BaseModel):
    strategy_id: int
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000.0
    timeframe: str = "1m"

class MarketDataResponse(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float

# Initialize FastAPI app
app = FastAPI(
    title="Trading Bot Dashboard API - Real Data Only",
    description="REST API serving authentic backtesting data from SQLite database",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database manager
db_manager = DatabaseManager()

# Setup logging with default config
try:
    import yaml
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        setup_logging(config)
    else:
        # Use default logging config if config file doesn't exist
        default_config = {
            'logging': {
                'level': 'INFO',
                'file': 'logs/trading_bot.log',
                'max_file_size': '10MB',
                'backup_count': 5
            }
        }
        setup_logging(default_config)
except Exception as e:
    # Fallback to basic logging if anything fails
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    print(f"Could not setup advanced logging: {e}. Using basic logging.")

logger = logging.getLogger(__name__)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected clients
                self.active_connections.remove(connection)

manager = ConnectionManager()

# Serve static files (React build)
app.mount("/static", StaticFiles(directory="frontend/build/static"), name="static")

# API Routes - REAL DATA ONLY

@app.get("/api/")
async def read_root():
    """API root endpoint"""
    return {"message": "Trading Bot Dashboard API - Real Data Only", "version": "2.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Strategy endpoints
@app.get("/api/strategies", response_model=List[StrategyResponse])
async def get_strategies():
    """Get all strategies from database"""
    try:
        strategies = db_manager.get_strategies()
        return [StrategyResponse(**strategy) for strategy in strategies]
    
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int):
    """Get strategy by ID from database"""
    try:
        strategy = db_manager.get_strategy(strategy_id)
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        
        return StrategyResponse(**strategy)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting strategy {strategy_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Trading session endpoints - REAL DATA ONLY
@app.get("/api/sessions", response_model=List[TradingSessionResponse])
async def get_trading_sessions(limit: int = 100):
    """Get all backtest sessions from database - including running, completed, and failed"""
    try:
        sessions = db_manager.get_trading_sessions(limit=limit)
        
        # Return all backtest sessions, regardless of status
        all_sessions = []
        for session in sessions:
            session_id = session.get('id')
            
            # Skip non-backtest sessions
            if session.get('session_type') != 'backtest':
                continue
            
            # Check if session has actual trades in trades table
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM trades WHERE session_id = ?", (session_id,))
                actual_trade_count = cursor.fetchone()[0]
            
            # Update session data with actual trade counts
            session['total_trades'] = actual_trade_count
            
            # For completed sessions with trades, get detailed trade statistics
            if session.get('status') == 'completed' and actual_trade_count > 0:
                # Get actual win/loss counts from trades table
                with db_manager.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT
                            COUNT(CASE WHEN pnl > 0 THEN 1 END) as wins,
                            COUNT(CASE WHEN pnl < 0 THEN 1 END) as losses,
                            SUM(pnl) as total_pnl
                        FROM trades
                        WHERE session_id = ? AND pnl IS NOT NULL
                    """, (session_id,))
                    
                    trade_stats = cursor.fetchone()
                    if trade_stats:
                        session['winning_trades'] = trade_stats[0] or 0
                        session['losing_trades'] = trade_stats[1] or 0
                        
                        # Update final capital and total return if we have P&L data
                        if trade_stats[2] is not None:
                            initial_capital = session.get('initial_capital', 10000)
                            total_pnl = trade_stats[2]
                            
                            # Calculate correct final capital: initial + total P&L
                            correct_final_capital = initial_capital + total_pnl
                            session['final_capital'] = correct_final_capital
                            
                            # Calculate total return as percentage: P&L / initial capital
                            session['total_return'] = total_pnl / initial_capital
            else:
                # For running/failed sessions, set defaults
                session['winning_trades'] = session.get('winning_trades', 0)
                session['losing_trades'] = session.get('losing_trades', 0)
            
            all_sessions.append(TradingSessionResponse(**session))
        
        logger.info(f"Returning {len(all_sessions)} backtest sessions out of {len(sessions)} total")
        return all_sessions
    
    except Exception as e:
        logger.error(f"Error getting trading sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/active", response_model=List[TradingSessionResponse])
async def get_active_sessions():
    """Get active trading sessions from database"""
    try:
        sessions = db_manager.get_active_sessions()
        return [TradingSessionResponse(**session) for session in sessions]
    
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/performance", response_model=PerformanceMetrics)
async def get_session_performance(session_id: int):
    """Get real performance metrics for a session from database"""
    try:
        performance = db_manager.calculate_session_performance(session_id)
        return PerformanceMetrics(**performance)
    
    except Exception as e:
        logger.error(f"Error getting session performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Trade endpoints - REAL DATA ONLY
@app.get("/api/sessions/{session_id}/trades", response_model=List[TradeResponse])
async def get_session_trades(session_id: int, limit: int = 1000):
    """Get real trades for a session from database"""
    try:
        trades = db_manager.get_trades(session_id=session_id, limit=limit)
        return [TradeResponse(**trade) for trade in trades]
    
    except Exception as e:
        logger.error(f"Error getting trades for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades/open", response_model=List[TradeResponse])
async def get_open_trades():
    """Get all open trades from database"""
    try:
        trades = db_manager.get_open_trades()
        return [TradeResponse(**trade) for trade in trades]
    
    except Exception as e:
        logger.error(f"Error getting open trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Market data endpoints - REAL DATA ONLY
@app.get("/api/market-data/{symbol}", response_model=List[MarketDataResponse])
async def get_market_data(
    symbol: str,
    timeframe: str = "1m",
    limit: int = 1000,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get real market data for a symbol from database"""
    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        df = db_manager.get_market_data(symbol, timeframe, start_dt, end_dt, limit)
        
        if df.empty:
            return []
        
        # Convert DataFrame to list of MarketDataResponse
        data = []
        for timestamp, row in df.iterrows():
            data.append(MarketDataResponse(
                timestamp=timestamp.isoformat(),
                open=row['open'],
                high=row['high'],
                low=row['low'],
                close=row['close'],
                volume=row['volume']
            ))
        
        return data
    
    except Exception as e:
        logger.error(f"Error getting market data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Portfolio endpoints - REAL DATA ONLY
@app.get("/api/sessions/{session_id}/portfolio")
async def get_portfolio_snapshots(
    session_id: int,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get real portfolio snapshots for equity curve from database"""
    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        snapshots = db_manager.get_portfolio_snapshots(session_id, start_dt, end_dt)
        return snapshots
    
    except Exception as e:
        logger.error(f"Error getting portfolio snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Backtesting endpoints - REAL BACKTESTING ENGINES ONLY
@app.post("/api/backtest")
async def run_backtest(backtest_request: BacktestRequest, background_tasks: BackgroundTasks):
    """Run a real backtest using authentic backtesting engines (GPU/backtrader) - NO SIMULATION"""
    try:
        # Create a new session for the backtest with correct start time
        start_date_dt = datetime.fromisoformat(backtest_request.start_date)
        session_id = db_manager.create_trading_session(
            "backtest",
            backtest_request.strategy_id,
            backtest_request.symbol,
            backtest_request.initial_capital,
            start_time=start_date_dt
        )
        
        # Add backtest to background tasks - REAL BACKTESTING ONLY
        background_tasks.add_task(
            run_real_backtest_task,
            session_id,
            backtest_request
        )
        
        return {
            "message": "Real backtest started using authentic backtesting engines",
            "session_id": session_id,
            "status": "running",
            "note": "Using real GPU/backtrader engines - no simulation"
        }
    
    except Exception as e:
        logger.error(f"Error starting real backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def load_yaml_config(filepath):
        """Loads a YAML file and returns its content as a Python dictionary."""
        with open(filepath, 'r') as file:
            # Use yaml.safe_load() for security, especially with untrusted sources
            config_data = yaml.safe_load(file)
        return config_data

async def run_real_backtest_task(session_id: int, backtest_request: BacktestRequest):
    """Background task to run REAL backtesting with real-time portfolio value tracking"""
    try:
        logger.info(f"=== STARTING REAL-TIME BACKTEST SESSION {session_id} ===")
        logger.info(f"Backtest request details: {backtest_request.dict()}")
        
        # Get strategy with detailed logging
        logger.info(f"Fetching strategy with ID: {backtest_request.strategy_id}")
        strategy = db_manager.get_strategy(backtest_request.strategy_id)
        if not strategy:
            logger.error(f"Strategy not found for ID: {backtest_request.strategy_id}")
            raise Exception("Strategy not found")
        
        logger.info(f"Retrieved strategy: {strategy}")
        
        # Convert symbol format and check available data
        symbol_db_format = backtest_request.symbol.replace('_', '')  # EUR_USD -> EURUSD
        logger.info(f"Symbol conversion: {backtest_request.symbol} -> {symbol_db_format}")
        
        # Check what data is actually available
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT symbol, timeframe, COUNT(*) as count, MIN(timestamp), MAX(timestamp)
                FROM market_data
                WHERE symbol = ? OR symbol = ?
                GROUP BY symbol, timeframe
                ORDER BY count DESC
            """, (symbol_db_format, backtest_request.symbol))
            
            available_data = cursor.fetchall()
            logger.info(f"Available data for {backtest_request.symbol}: {available_data}")
        
        if not available_data:
            raise Exception(f"No market data found for {backtest_request.symbol} or {symbol_db_format}")
        
        # Use the best available data (highest count)
        best_data = available_data[0]
        actual_symbol = best_data[0]
        actual_timeframe = best_data[1]
        data_count = best_data[2]
        data_start = best_data[3]
        data_end = best_data[4]
        
        logger.info(f"Using real market data: {actual_symbol} {actual_timeframe} ({data_count} records from {data_start} to {data_end})")
        
        # Get actual market data from database
        df = db_manager.get_market_data(
            actual_symbol,
            actual_timeframe,
            datetime.fromisoformat(backtest_request.start_date) if backtest_request.start_date >= data_start else datetime.fromisoformat(data_start),
            datetime.fromisoformat(backtest_request.end_date) if backtest_request.end_date <= data_end else datetime.fromisoformat(data_end),
            limit=10000
        )
        
        if df.empty:
            raise Exception(f"No market data retrieved for {actual_symbol}")
        
        logger.info(f"Retrieved {len(df)} real market data records for backtesting")

        config_s=load_yaml_config('config/config.yaml')
        
        # Run real backtest using REAL-TIME backtest engine with portfolio tracking
        try:
            from backtesting.realtime_backtest_engine import create_realtime_backtest_engine
            
            logger.info("=== INITIALIZING REAL-TIME BACKTEST ENGINE ===")
            
            # Create config for real-time backtest engine
            config = {
                'backtesting': {
                    'initial_capital': backtest_request.initial_capital,
                    'commission': 0.001,
                    'slippage': 0.0005,
                    'start_date': backtest_request.start_date,
                    'end_date': backtest_request.end_date
                },
                'oanda': {
                    'account_id': config_s['data']['oanda']['account_id'],
                    'access_token': config_s['data']['oanda']['access_token'],
                    'practice': True
                }
            }
            logger.info(f"Real-time backtest engine config: {config}")
            
            # Define portfolio update callback for real-time tracking
            async def portfolio_update_callback(snapshot):
                """Callback to handle real-time portfolio updates"""
                try:
                    # Store portfolio snapshot in database
                    db_manager.store_portfolio_snapshot(
                        session_id=session_id,
                        timestamp=datetime.fromisoformat(snapshot['timestamp']),
                        total_value=snapshot['total_value'],
                        cash_balance=snapshot['cash_balance'],
                        unrealized_pnl=snapshot['unrealized_pnl'],
                        realized_pnl=0.0,  # Will be updated by trades
                        open_positions=0,  # Will be updated by trades
                        daily_pnl=snapshot['unrealized_pnl']
                    )
                    
                    # Broadcast real-time update via WebSocket
                    await manager.broadcast(json.dumps({
                        "type": "portfolio_realtime_update",
                        "session_id": session_id,
                        "timestamp": snapshot['timestamp'],
                        "portfolio_value": snapshot['total_value'],
                        "total_return": snapshot['total_return'],
                        "unrealized_pnl": snapshot['unrealized_pnl'],
                        "drawdown": snapshot['drawdown'],
                        "progress": snapshot['progress'],
                        "trade_count": snapshot['trade_count']
                    }))
                    
                    logger.debug(f"Portfolio update: ${snapshot['total_value']:.2f} "
                               f"({snapshot['total_return']:.2f}% return, "
                               f"{snapshot['progress']:.1f}% complete)")
                    
                except Exception as e:
                    logger.error(f"Error in portfolio update callback: {e}")
            
            # Initialize real-time backtest engine with portfolio tracking
            backtest_engine = create_realtime_backtest_engine(
                config=config,
                session_id=session_id,
                update_callback=portfolio_update_callback,
                websocket_manager=manager
            )
            
            # Set database manager for portfolio snapshots
            backtest_engine.db_manager = db_manager
            
            logger.info(f"Real-time backtest engine initialized: {type(backtest_engine)}")
            
            # Create a custom data feed that uses our real database data
            class DatabaseDataFeed:
                def __init__(self, df):
                    self.df = df
                
                def get_forex_data(self, symbol, timeframe, start_date, end_date):
                    return self.df
            
            # Set the data feed with real data
            backtest_engine.data_feed = DatabaseDataFeed(df)
            logger.info(f"Data feed set on backtest engine: {type(backtest_engine.data_feed)}")
            
            # Load the real data
            asset_type = strategy.get('asset_class', 'forex')
            logger.info(f"Asset type from strategy: {asset_type}")
            loaded_data = backtest_engine.load_data(actual_symbol, asset_type, actual_timeframe)
            
            if loaded_data is not None and not loaded_data.empty:
                logger.info(f"Successfully loaded {len(loaded_data)} real data points for backtesting")
                
                # === DETAILED STRATEGY PARAMETER LOGGING ===
                logger.info("=== STRATEGY PARAMETER EXTRACTION AND PROCESSING ===")
                
                # Map strategy name to class name
                strategy_name = strategy.get('name', 'ForexStrategy')
                logger.info(f"Original strategy name from DB: '{strategy_name}'")
                
                if 'Enhanced' in strategy_name:
                    strategy_class_name = 'EnhancedForexStrategy'
                elif 'Realtime Scalping 1M' in strategy_name:
                    strategy_class_name = 'RealtimeScalping1MStrategy'
                elif 'Realtime Scalping 5M' in strategy_name:
                    strategy_class_name = 'RealtimeScalping5MStrategy'
                elif 'Scalping' in strategy_name and '1M' in strategy_name:
                    strategy_class_name = 'RealtimeScalping1MStrategy'
                elif 'Scalping' in strategy_name and '5M' in strategy_name:
                    strategy_class_name = 'RealtimeScalping5MStrategy'
                elif 'Scalping' in strategy_name:
                    # Default scalping to 1M strategy
                    strategy_class_name = 'RealtimeScalping1MStrategy'
                else:
                    strategy_class_name = 'EnhancedForexStrategy'
                
                logger.info(f"Mapped strategy class name: '{strategy_class_name}'")
                
                # Extract strategy parameters with detailed logging
                logger.info("=== EXTRACTING STRATEGY PARAMETERS ===")
                raw_strategy_params = strategy.get('parameters', {})
                logger.info(f"Raw strategy parameters from DB: {raw_strategy_params}")
                logger.info(f"Raw parameters type: {type(raw_strategy_params)}")
                
                if raw_strategy_params is None:
                    logger.warning("Strategy parameters is None, using empty dict")
                    raw_strategy_params = {}
                
                # Create a copy for modification
                strategy_params = raw_strategy_params.copy() if isinstance(raw_strategy_params, dict) else {}
                logger.info(f"Strategy parameters after copy: {strategy_params}")
                
                # === PARAMETER CONVERSION FOR OLD SCALPING STRATEGIES ===
                logger.info("=== CONVERTING OLD SCALPING PARAMETERS ===")
                if 'Scalping' in strategy_name and strategy_class_name in ['RealtimeScalping1MStrategy', 'RealtimeScalping5MStrategy']:
                    # Convert old parameter names to new ones
                    param_mapping = {
                        'fast_ema': 'fast_length',
                        'slow_ema': 'slow_length',
                        'signal_ema': 'signal_length',
                        'stop_loss_pips': 'base_stop_loss',
                        'take_profit_pips': 'base_take_profit'
                    }
                    
                    converted_params = {}
                    for old_param, new_param in param_mapping.items():
                        if old_param in strategy_params:
                            old_value = strategy_params[old_param]
                            logger.info(f"Converting {old_param}={old_value} to {new_param}")
                            
                            # Convert pip values to percentage values
                            if old_param in ['stop_loss_pips', 'take_profit_pips']:
                                # Convert pips to percentage (assuming EUR_USD where 1 pip = 0.0001)
                                if old_param == 'stop_loss_pips':
                                    converted_params[new_param] = old_value * 0.0001  # 3 pips = 0.0003
                                elif old_param == 'take_profit_pips':
                                    converted_params[new_param] = old_value * 0.0001  # 6 pips = 0.0006
                            else:
                                converted_params[new_param] = old_value
                    
                    # Add the converted parameters
                    strategy_params.update(converted_params)
                    
                    # Add default parameters for real-time compatibility
                    default_realtime_params = {
                        'dynamic_sizing': True,
                        'volatility_adjustment': True,
                        'use_regime_filter': True,
                        'use_volatility_filter': True,
                        'volume_confirmation': True,
                        'momentum_acceleration': 1.6 if '1M' in strategy_name else 1.4,
                        'trend_following_boost': 1.4 if '1M' in strategy_name else 1.3,
                        'breakout_multiplier': 1.8 if '1M' in strategy_name else 1.6,
                        'mean_reversion_factor': 0.7 if '1M' in strategy_name else 0.8,
                        'max_trades_per_hour': 15 if '1M' in strategy_name else 8,
                        'min_time_between_trades': 30 if '1M' in strategy_name else 120,
                        'quick_exit_threshold': 0.002 if '1M' in strategy_name else 0.003
                    }
                    
                    # Add defaults only if not already present
                    for param, value in default_realtime_params.items():
                        if param not in strategy_params:
                            strategy_params[param] = value
                    
                    logger.info(f"Converted scalping parameters: {strategy_params}")
                
                # Add printlog parameter
                logger.info("=== MODIFYING STRATEGY PARAMETERS ===")
                logger.info(f"Setting printlog=False (was: {strategy_params.get('printlog', 'not set')})")
                strategy_params['printlog'] = False
                
                logger.info(f"Final strategy parameters dictionary: {strategy_params}")
                logger.info(f"Final parameters type: {type(strategy_params)}")
                logger.info(f"Final parameters keys: {list(strategy_params.keys())}")
                
                # Log each parameter individually
                logger.info("=== INDIVIDUAL PARAMETER VALUES ===")
                for key, value in strategy_params.items():
                    logger.info(f"  {key}: {value} (type: {type(value)})")
                
                # Validate parameters before passing to engine
                logger.info("=== PARAMETER VALIDATION ===")
                if not isinstance(strategy_params, dict):
                    logger.error(f"Strategy parameters is not a dict: {type(strategy_params)}")
                    strategy_params = {}
                
                # Log the actual method call
                logger.info("=== CALLING BACKTEST ENGINE ADD_STRATEGY ===")
                logger.info(f"Method: backtest_engine.add_strategy")
                logger.info(f"Strategy class name argument: '{strategy_class_name}'")
                logger.info(f"Keyword arguments being passed: {strategy_params}")
                
                # Add strategy with real parameters
                try:
                    backtest_engine.add_strategy(strategy_class_name, **strategy_params)
                    logger.info(f"Successfully called backtest_engine.add_strategy() with {strategy_class_name}")
                except Exception as strategy_add_error:
                    logger.error(f"Error calling add_strategy: {strategy_add_error}")
                    logger.error(f"Strategy class name: {strategy_class_name}")
                    logger.error(f"Parameters passed: {strategy_params}")
                    raise
                
                # === BACKTEST ENGINE STATE BEFORE EXECUTION ===
                logger.info("=== BACKTEST ENGINE STATE BEFORE EXECUTION ===")
                logger.info(f"Engine cerebro object: {type(backtest_engine.cerebro)}")
                logger.info(f"Engine initial capital: {backtest_engine.initial_capital}")
                logger.info(f"Engine commission: {backtest_engine.commission}")
                logger.info(f"Engine slippage: {backtest_engine.slippage}")
                logger.info(f"Engine start_date: {backtest_engine.start_date}")
                logger.info(f"Engine end_date: {backtest_engine.end_date}")
                
                # Discover all cerebro attributes first
                logger.info("=== CEREBRO ATTRIBUTE DISCOVERY ===")
                cerebro_attrs = [attr for attr in dir(backtest_engine.cerebro) if not attr.startswith('__')]
                logger.info(f"Available cerebro attributes: {cerebro_attrs}")
                
                # Check for strategy-related attributes
                strategy_attrs = [attr for attr in cerebro_attrs if 'strat' in attr.lower()]
                logger.info(f"Strategy-related attributes: {strategy_attrs}")
                
                # Check cerebro strategies using multiple possible attribute names
                strategies_found = False
                for attr_name in ['_strats', 'strats', '_strategies', 'strategies']:
                    if hasattr(backtest_engine.cerebro, attr_name):
                        strategies = getattr(backtest_engine.cerebro, attr_name)
                        logger.info(f"Found strategies in '{attr_name}': {len(strategies) if hasattr(strategies, '__len__') else 'Unknown length'}")
                        strategies_found = True
                        
                        if hasattr(strategies, '__len__') and hasattr(strategies, '__iter__'):
                            for i, strat in enumerate(strategies):
                                logger.info(f"Strategy {i} from {attr_name}: {strat}")
                                logger.info(f"Strategy {i} type: {type(strat)}")
                                
                                # Check for strategy parameters/arguments
                                strat_attrs = [attr for attr in dir(strat) if not attr.startswith('__')]
                                logger.info(f"Strategy {i} attributes: {strat_attrs}")
                                
                                # Look for parameter-related attributes
                                param_attrs = [attr for attr in strat_attrs if any(keyword in attr.lower() for keyword in ['param', 'arg', 'kwarg', 'p'])]
                                logger.info(f"Strategy {i} parameter-related attributes: {param_attrs}")
                                
                                for param_attr in param_attrs:
                                    try:
                                        param_value = getattr(strat, param_attr)
                                        logger.info(f"Strategy {i} {param_attr}: {param_value}")
                                    except Exception as e:
                                        logger.warning(f"Could not access Strategy {i} {param_attr}: {e}")
                        break
                
                if not strategies_found:
                    logger.warning("No strategy attributes found in cerebro")
                
                # Check cerebro data feeds using multiple possible attribute names
                data_attrs = [attr for attr in cerebro_attrs if 'data' in attr.lower()]
                logger.info(f"Data-related attributes: {data_attrs}")
                
                data_found = False
                for attr_name in ['datas', '_datas', 'data', '_data']:
                    if hasattr(backtest_engine.cerebro, attr_name):
                        datas = getattr(backtest_engine.cerebro, attr_name)
                        logger.info(f"Found data feeds in '{attr_name}': {len(datas) if hasattr(datas, '__len__') else 'Unknown length'}")
                        data_found = True
                        
                        if hasattr(datas, '__len__') and hasattr(datas, '__iter__'):
                            for i, data in enumerate(datas):
                                logger.info(f"Data feed {i} from {attr_name}: {type(data)} - {data}")
                                
                                # Check data feed attributes
                                data_attrs_list = [attr for attr in dir(data) if not attr.startswith('__')]
                                logger.info(f"Data feed {i} attributes: {data_attrs_list}")
                                
                                # Look for name and parameter attributes
                                for check_attr in ['_name', 'name', 'params', '_params']:
                                    if hasattr(data, check_attr):
                                        try:
                                            attr_value = getattr(data, check_attr)
                                            logger.info(f"Data feed {i} {check_attr}: {attr_value}")
                                        except Exception as e:
                                            logger.warning(f"Could not access Data feed {i} {check_attr}: {e}")
                        break
                
                if not data_found:
                    logger.warning("No data attributes found in cerebro")
                
                # === DATA FEED SHAPE LOGGING ===
                logger.info("=== DATA FEED SHAPE ANALYSIS ===")
                logger.info(f"Original DataFrame shape: {df.shape}")
                logger.info(f"Original DataFrame columns: {list(df.columns)}")
                logger.info(f"Original DataFrame index type: {type(df.index)}")
                logger.info(f"Original DataFrame date range: {df.index.min()} to {df.index.max()}")
                logger.info(f"Original DataFrame first 3 rows:\n{df.head(3)}")
                logger.info(f"Original DataFrame last 3 rows:\n{df.tail(3)}")
                logger.info(f"Original DataFrame info:")
                logger.info(f"  - Non-null counts: {df.count().to_dict()}")
                logger.info(f"  - Data types: {df.dtypes.to_dict()}")
                logger.info(f"  - Memory usage: {df.memory_usage(deep=True).sum()} bytes")
                
                # Check if loaded_data is different from df
                if loaded_data is not None and not loaded_data.empty:
                    logger.info(f"Loaded data shape: {loaded_data.shape}")
                    logger.info(f"Loaded data columns: {list(loaded_data.columns)}")
                    logger.info(f"Loaded data index type: {type(loaded_data.index)}")
                    logger.info(f"Loaded data date range: {loaded_data.index.min()} to {loaded_data.index.max()}")
                    logger.info(f"Loaded data first 3 rows:\n{loaded_data.head(3)}")
                    logger.info(f"Loaded data last 3 rows:\n{loaded_data.tail(3)}")
                    
                    # Check if data was modified during loading
                    if not df.equals(loaded_data):
                        logger.info("Data was modified during backtest_engine.load_data()")
                        logger.info(f"Original shape: {df.shape} vs Loaded shape: {loaded_data.shape}")
                    else:
                        logger.info("Data unchanged during backtest_engine.load_data()")
                
                # Check broker settings
                if hasattr(backtest_engine.cerebro, 'broker'):
                    broker = backtest_engine.cerebro.broker
                    logger.info(f"Broker type: {type(broker)}")
                    logger.info(f"Broker cash: {broker.getcash()}")
                    logger.info(f"Broker value: {broker.getvalue()}")
                    if hasattr(broker, '_commission'):
                        logger.info(f"Broker commission: {broker._commission}")
                else:
                    logger.warning("Cerebro does not have broker attribute")
                
                # Log any analyzers
                if hasattr(backtest_engine.cerebro, '_analyzers'):
                    logger.info(f"Number of analyzers: {len(backtest_engine.cerebro._analyzers)}")
                    for i, analyzer in enumerate(backtest_engine.cerebro._analyzers):
                        logger.info(f"Analyzer {i}: {analyzer}")
                
                # Run real-time backtest with portfolio tracking
                logger.info("=== EXECUTING REAL-TIME BACKTEST ===")
                results = backtest_engine.run_with_realtime_updates()

                logger.info(f"=== REAL-TIME BACKTEST EXECUTION COMPLETED ===")
                logger.info(f"Results type: {type(results)}")
                logger.info(f"Portfolio snapshots captured: {len(results.get('portfolio_snapshots', []))}")

                if results and isinstance(results, dict):
                    logger.info(f"Real-time backtest completed with results: {results}")
                    
                    # Extract real results
                    final_capital = results.get('final_value', backtest_request.initial_capital)
                    total_return = ((final_capital - backtest_request.initial_capital) / backtest_request.initial_capital)
                    total_trades = results.get('total_trades', 0)
                    winning_trades = results.get('winning_trades', 0)
                    losing_trades = results.get('losing_trades', 0)
                    win_rate = (winning_trades / total_trades) if total_trades > 0 else 0.0
                    max_drawdown = results.get('max_drawdown', 0.0) / 100.0 if results.get('max_drawdown', 0.0) > 1 else results.get('max_drawdown', 0.0)
                    sharpe_ratio = results.get('sharpe_ratio', 0.0)
                    
                    # Update session with real backtest results
                    end_date_dt = datetime.fromisoformat(backtest_request.end_date)
                    db_manager.update_trading_session(
                        session_id,
                        end_time=end_date_dt,
                        final_capital=final_capital,
                        total_return=total_return,
                        total_trades=total_trades,
                        winning_trades=winning_trades,
                        losing_trades=losing_trades,
                        win_rate=win_rate,
                        max_drawdown=max_drawdown,
                        sharpe_ratio=sharpe_ratio,
                        status="completed"
                    )
                    
                    # Broadcast completion with real-time tracking metrics
                    await manager.broadcast(json.dumps({
                        "type": "backtest_completed",
                        "session_id": session_id,
                        "status": "completed",
                        "realtime_tracking": True,
                        "portfolio_snapshots": len(results.get('portfolio_snapshots', [])),
                        "execution_time": results.get('execution_time', 0),
                        "engine": "realtime_backtrader",
                        "data_points": len(loaded_data),
                        "final_capital": final_capital,
                        "total_return": total_return,
                        "max_drawdown": max_drawdown,
                        "total_trades": total_trades
                    }))
                    
                    logger.info(f"REAL-TIME backtest completed for session {session_id}: "
                              f"Final Capital: ${final_capital:.2f}, "
                              f"Return: {total_return*100:.2f}%, "
                              f"Trades: {total_trades}, "
                              f"Portfolio Updates: {len(results.get('portfolio_snapshots', []))}")

                    # Option 1: Create DataFrame with metrics as rows (key-value pairs)
                    # This creates a two-column DataFrame: Metric | Value
                    results_df = pd.DataFrame(list(results.items()), columns=['Metric', 'Value'])
                    
                    # Option 2: Alternative - transpose single row to make columns into rows
                    # results_df = pd.DataFrame([results]).T.reset_index()
                    # results_df.columns = ['Metric', 'Value']
                    
                    # Option 3: If you want to accumulate multiple backtest runs over time
                    # Add timestamp and other metadata for historical tracking
                    # results_with_metadata = {
                    #     'timestamp': datetime.now().isoformat(),
                    #     'session_id': session_id,
                    #     'symbol': actual_symbol,
                    #     'strategy': strategy.get('name', 'Unknown'),
                    #     **results
                    # }
                    # results_df = pd.DataFrame([results_with_metadata])
                    
                    # Ensure the forex_hist_csv directory exists
                    csv_dir = 'forex_hist_csv'
                    os.makedirs(csv_dir, exist_ok=True)
                    
                    csv_filename = f"bk_results_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.csv"
                    csv_path = os.path.join(csv_dir, csv_filename)
                    
                    results_df.to_csv(csv_path, index=False)
                    logger.info(f"Backtest results saved to {csv_path} with {len(results_df)} rows")
                    
                else:
                    raise Exception("Real-time backtest engine returned no valid results")
            else:
                raise Exception(f"Failed to load market data for {actual_symbol}")
                
        except Exception as backtest_error:
            logger.error(f"Real-time backtest engine failed: {backtest_error}")
            raise Exception(f"Real-time backtesting failed: {backtest_error}")
        
    except Exception as e:
        logger.error(f"Error in REAL backtest task: {e}")
        
        # Update session status to failed
        db_manager.update_trading_session(session_id, status="failed")
        
        # Broadcast failure via WebSocket
        await manager.broadcast(json.dumps({
            "type": "backtest_failed",
            "session_id": session_id,
            "error": str(e),
            "note": "Real-time backtesting engine failed - no simulation fallback available"
        }))

# Additional backtesting endpoints for detailed data
@app.get("/api/sessions/{session_id}/details")
async def get_session_details(session_id: int):
    """Get detailed real session information from database"""
    try:
        # Get session info
        sessions = db_manager.get_trading_sessions(limit=1000)
        session = next((s for s in sessions if s['id'] == session_id), None)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Only return if it's a real completed session
        if session.get('status') != 'completed' or session.get('total_trades', 0) == 0:
            raise HTTPException(status_code=404, detail="No real backtest data available for this session")
        
        # Get trades for this session
        trades = db_manager.get_trades(session_id=session_id, limit=1000)
        
        # Get performance metrics
        try:
            performance = db_manager.calculate_session_performance(session_id)
        except:
            performance = {}
        
        # Get portfolio snapshots
        try:
            portfolio_snapshots = db_manager.get_portfolio_snapshots(session_id)
        except:
            portfolio_snapshots = []
        
        return {
            "session": session,
            "trades": trades,
            "performance": performance,
            "portfolio_snapshots": portfolio_snapshots
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/backtest/status/{session_id}")
async def get_backtest_status(session_id: int):
    """Get real status of a backtest session from database"""
    try:
        sessions = db_manager.get_trading_sessions(limit=1000)
        session = next((s for s in sessions if s['id'] == session_id), None)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": session_id,
            "status": session['status'],
            "progress": "completed" if session['status'] == 'completed' else session['status'],
            "total_trades": session.get('total_trades', 0),
            "current_capital": session.get('final_capital', session.get('initial_capital', 0))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting backtest status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            # Echo back for now (can be extended for specific commands)
            await manager.send_personal_message(f"Echo: {data}", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# System endpoints
@app.get("/api/system/logs")
async def get_system_logs(limit: int = 100, log_level: Optional[str] = None):
    """Get real system logs from database"""
    try:
        logs = db_manager.get_system_logs(limit=limit, log_level=log_level)
        return logs
    
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/settings")
async def get_system_settings():
    """Get real system settings from database"""
    try:
        # Get common settings
        settings = {
            'dashboard_refresh_interval': db_manager.get_setting('dashboard_refresh_interval'),
            'default_chart_timeframe': db_manager.get_setting('default_chart_timeframe'),
            'risk_alert_threshold': db_manager.get_setting('risk_alert_threshold'),
            'theme': db_manager.get_setting('theme'),
            'timezone': db_manager.get_setting('timezone')
        }
        return settings
    
    except Exception as e:
        logger.error(f"Error getting system settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/system/settings")
async def update_system_settings(settings: Dict[str, Any]):
    """Update system settings in database"""
    try:
        for key, value in settings.items():
            # Determine setting type
            setting_type = 'string'
            if isinstance(value, bool):
                setting_type = 'boolean'
            elif isinstance(value, (int, float)):
                setting_type = 'number'
            elif isinstance(value, (dict, list)):
                setting_type = 'json'
            
            db_manager.set_setting(key, value, setting_type)
        
        return {"message": "Settings updated successfully"}
    
    except Exception as e:
        logger.error(f"Error updating system settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Database statistics endpoint
@app.get("/api/database/stats")
async def get_database_stats():
    """Get real database statistics"""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get table counts
            stats = {}
            tables = ['trading_sessions', 'trades', 'strategies', 'market_data', 'portfolio_snapshots']
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()[0]
            
            # Get completed backtests count
            cursor.execute("SELECT COUNT(*) FROM trading_sessions WHERE status = 'completed' AND total_trades > 0")
            stats['completed_backtests'] = cursor.fetchone()[0]
            
            # Get total trades from completed sessions
            cursor.execute("SELECT SUM(total_trades) FROM trading_sessions WHERE status = 'completed'")
            result = cursor.fetchone()[0]
            stats['total_backtest_trades'] = result if result else 0
            
            return stats
    
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Serve React app at root and for all non-API routes
@app.get("/", response_class=HTMLResponse)
async def serve_react_root():
    """Serve React app at root"""
    try:
        with open("frontend/build/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Trading Bot Dashboard - Real Data Only</title></head>
            <body>
                <h1>Trading Bot Dashboard - Real Data Only</h1>
                <p>Frontend not built yet. Please build the React frontend first.</p>
                <p>API is running at <a href="/docs">/docs</a></p>
                <p>API root is at <a href="/api/">/api/</a></p>
                <p><strong>This API serves only real backtesting data from SQLite database.</strong></p>
            </body>
        </html>
        """)

@app.get("/{full_path:path}", response_class=HTMLResponse)
async def serve_react_app(full_path: str):
    """Serve React app for all other non-API routes"""
    # Don't serve React app for API routes
    if full_path.startswith("api/") or full_path.startswith("docs") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not found")
    
    try:
        with open("frontend/build/index.html", "r") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(content="""
        <html>
            <head><title>Trading Bot Dashboard - Real Data Only</title></head>
            <body>
                <h1>Trading Bot Dashboard - Real Data Only</h1>
                <p>Frontend not built yet. Please build the React frontend first.</p>
                <p>API is running at <a href="/docs">/docs</a></p>
                <p>API root is at <a href="/api/">/api/</a></p>
                <p><strong>This API serves only real backtesting data from SQLite database.</strong></p>
            </body>
        </html>
        """)

if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# Real-time Signal and Activity Endpoints

@app.get("/api/realtime/signals/{session_id}")
async def get_realtime_signals(
    session_id: int,
    limit: int = 100,
    signal_type: Optional[str] = None,
    priority: Optional[int] = None
):
    """Get real-time signals for a session"""
    try:
        signals = db_manager.get_realtime_signal_logs(
            session_id=session_id,
            limit=limit,
            signal_type=signal_type,
            priority=priority
        )
        return signals
    except Exception as e:
        logger.error(f"Error getting real-time signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/realtime/activities/{session_id}")
async def get_realtime_activities(
    session_id: int,
    limit: int = 100,
    order_id: Optional[int] = None,
    status: Optional[str] = None
):
    """Get real-time order activities for a session"""
    try:
        activities = db_manager.get_realtime_order_activities(
            session_id=session_id,
            limit=limit,
            order_id=order_id,
            status=status
        )
        return activities
    except Exception as e:
        logger.error(f"Error getting real-time activities: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/realtime/broker-stats/{session_id}")
async def get_realtime_broker_stats(session_id: int, limit: int = 100):
    """Get real-time broker statistics for a session"""
    try:
        stats = db_manager.get_realtime_broker_stats(session_id=session_id, limit=limit)
        return stats
    except Exception as e:
        logger.error(f"Error getting real-time broker stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/realtime/broker-stats/{session_id}/latest")
async def get_latest_broker_stats(session_id: int):
    """Get latest broker statistics for a session"""
    try:
        stats = db_manager.get_latest_broker_stats(session_id=session_id)
        if not stats:
            raise HTTPException(status_code=404, detail="No broker stats found for session")
        return stats
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting latest broker stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/realtime/analytics/signals/{session_id}")
async def get_realtime_signal_analytics(session_id: int):
    """Get real-time signal analytics for a session"""
    try:
        analytics = db_manager.get_realtime_signal_analytics(session_id=session_id)
        return analytics
    except Exception as e:
        logger.error(f"Error getting real-time signal analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/realtime/analytics/orders/{session_id}")
async def get_realtime_order_analytics(session_id: int):
    """Get real-time order analytics for a session"""
    try:
        analytics = db_manager.get_realtime_order_analytics(session_id=session_id)
        return analytics
    except Exception as e:
        logger.error(f"Error getting real-time order analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/realtime/dashboard/{session_id}")
async def get_realtime_dashboard_data(session_id: int):
    """Get comprehensive real-time dashboard data for a session"""
    try:
        # Get session info
        sessions = db_manager.get_trading_sessions(limit=1000)
        session = next((s for s in sessions if s['id'] == session_id), None)
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get real-time data
        signals = db_manager.get_realtime_signal_logs(session_id=session_id, limit=50)
        activities = db_manager.get_realtime_order_activities(session_id=session_id, limit=50)
        broker_stats = db_manager.get_latest_broker_stats(session_id=session_id)
        signal_analytics = db_manager.get_realtime_signal_analytics(session_id=session_id)
        order_analytics = db_manager.get_realtime_order_analytics(session_id=session_id)
        
        # Get portfolio snapshots for equity curve
        portfolio_snapshots = db_manager.get_portfolio_snapshots(session_id=session_id)
        
        return {
            "session": session,
            "signals": signals,
            "activities": activities,
            "broker_stats": broker_stats,
            "signal_analytics": signal_analytics,
            "order_analytics": order_analytics,
            "portfolio_snapshots": portfolio_snapshots,
            "timestamp": datetime.utcnow().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting real-time dashboard data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Live Trading Endpoints

@app.post("/api/live-trading/start")
async def start_live_trading(session_data: Dict[str, Any]):
    """Start a live trading session with real-time logging"""
    try:
        # Create live trading session
        session_id = db_manager.create_trading_session(
            session_type="live",
            strategy_id=session_data["strategy_id"],
            symbol=session_data["symbol"],
            initial_capital=session_data.get("initial_capital", 100000.0)
        )
        
        # Initialize real-time logging components
        # This would typically start the trading bot with enhanced logging
        
        # Broadcast session start
        await manager.broadcast(json.dumps({
            "type": "live_trading_started",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": session_data
        }))
        
        return {
            "message": "Live trading session started",
            "session_id": session_id,
            "status": "active"
        }
    except Exception as e:
        logger.error(f"Error starting live trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/live-trading/stop/{session_id}")
async def stop_live_trading(session_id: int):
    """Stop a live trading session"""
    try:
        # Update session status
        db_manager.update_trading_session(
            session_id,
            end_time=datetime.utcnow(),
            status="stopped"
        )
        
        # Broadcast session stop
        await manager.broadcast(json.dumps({
            "type": "live_trading_stopped",
            "session_id": session_id,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        return {
            "message": "Live trading session stopped",
            "session_id": session_id,
            "status": "stopped"
        }
    except Exception as e:
        logger.error(f"Error stopping live trading: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/live-trading/sessions")
async def get_live_trading_sessions():
    """Get all live trading sessions"""
    try:
        sessions = db_manager.get_trading_sessions(limit=100)
        live_sessions = [s for s in sessions if s['session_type'] == 'live']
        return live_sessions
    except Exception as e:
        logger.error(f"Error getting live trading sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Enhanced WebSocket endpoint with real-time signal broadcasting
@app.websocket("/ws/realtime/{session_id}")
async def websocket_realtime_endpoint(websocket: WebSocket, session_id: int):
    """WebSocket endpoint for real-time updates for a specific session"""
    await manager.connect(websocket)
    try:
        # Send initial data
        dashboard_data = await get_realtime_dashboard_data(session_id)
        await manager.send_personal_message(json.dumps({
            "type": "initial_data",
            "data": dashboard_data
        }), websocket)
        
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                if message.get("type") == "subscribe_signals":
                    # Client wants to subscribe to signal updates
                    await manager.send_personal_message(json.dumps({
                        "type": "subscription_confirmed",
                        "subscription": "signals",
                        "session_id": session_id
                    }), websocket)
                elif message.get("type") == "get_latest_data":
                    # Client requests latest data
                    dashboard_data = await get_realtime_dashboard_data(session_id)
                    await manager.send_personal_message(json.dumps({
                        "type": "latest_data",
                        "data": dashboard_data
                    }), websocket)
            except json.JSONDecodeError:
                await manager.send_personal_message(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }), websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)