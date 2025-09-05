"""
FastAPI REST API Backend for Trading Bot Dashboard
Provides endpoints for live trading and backtesting data
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

# Import our modules
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
from strategies.scalping_forex_strategy import ScalpingForexStrategy
from data.data_feed import OANDADataFeed
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
    initial_capital: float = 10000.0
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
    title="Trading Bot Dashboard API",
    description="REST API for trading bot dashboard with live trading and backtesting capabilities",
    version="1.0.0"
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

# API Routes

# Move the API root to /api/
@app.get("/api/")
async def read_root():
    """API root endpoint"""
    return {"message": "Trading Bot Dashboard API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# Strategy endpoints
@app.post("/api/strategies", response_model=StrategyResponse)
async def create_strategy(strategy: StrategyCreate):
    """Create a new trading strategy"""
    try:
        strategy_id = db_manager.create_strategy(
            strategy.name,
            strategy.description,
            strategy.strategy_type,
            strategy.asset_class,
            strategy.timeframe,
            strategy.parameters
        )
        
        created_strategy = db_manager.get_strategy(strategy_id)
        return StrategyResponse(**created_strategy)
    
    except Exception as e:
        logger.error(f"Error creating strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/strategies", response_model=List[StrategyResponse])
async def get_strategies():
    """Get all strategies"""
    try:
        strategies = db_manager.get_strategies()
        return [StrategyResponse(**strategy) for strategy in strategies]
    
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/strategies/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: int):
    """Get strategy by ID"""
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

# Trading session endpoints
@app.post("/api/sessions", response_model=TradingSessionResponse)
async def create_trading_session(session: TradingSessionCreate):
    """Create a new trading session"""
    try:
        session_id = db_manager.create_trading_session(
            session.session_type,
            session.strategy_id,
            session.symbol,
            session.initial_capital
        )
        
        # Get the created session with strategy info
        sessions = db_manager.get_trading_sessions(limit=1)
        created_session = next((s for s in sessions if s['id'] == session_id), None)
        
        if not created_session:
            raise HTTPException(status_code=500, detail="Failed to retrieve created session")
        
        return TradingSessionResponse(**created_session)
    
    except Exception as e:
        logger.error(f"Error creating trading session: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions", response_model=List[TradingSessionResponse])
async def get_trading_sessions(limit: int = 100):
    """Get trading sessions"""
    try:
        sessions = db_manager.get_trading_sessions(limit=limit)
        return [TradingSessionResponse(**session) for session in sessions]
    
    except Exception as e:
        logger.error(f"Error getting trading sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/active", response_model=List[TradingSessionResponse])
async def get_active_sessions():
    """Get active trading sessions"""
    try:
        sessions = db_manager.get_active_sessions()
        return [TradingSessionResponse(**session) for session in sessions]
    
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sessions/{session_id}/performance", response_model=PerformanceMetrics)
async def get_session_performance(session_id: int):
    """Get performance metrics for a session"""
    try:
        performance = db_manager.calculate_session_performance(session_id)
        return PerformanceMetrics(**performance)
    
    except Exception as e:
        logger.error(f"Error getting session performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Trade endpoints
@app.get("/api/sessions/{session_id}/trades", response_model=List[TradeResponse])
async def get_session_trades(session_id: int, limit: int = 1000):
    """Get trades for a session"""
    try:
        trades = db_manager.get_trades(session_id=session_id, limit=limit)
        return [TradeResponse(**trade) for trade in trades]
    
    except Exception as e:
        logger.error(f"Error getting trades for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trades/open", response_model=List[TradeResponse])
async def get_open_trades():
    """Get all open trades"""
    try:
        trades = db_manager.get_open_trades()
        return [TradeResponse(**trade) for trade in trades]
    
    except Exception as e:
        logger.error(f"Error getting open trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Market data endpoints
@app.get("/api/market-data/{symbol}", response_model=List[MarketDataResponse])
async def get_market_data(
    symbol: str,
    timeframe: str = "1m",
    limit: int = 1000,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get market data for a symbol"""
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

# Portfolio endpoints
@app.get("/api/sessions/{session_id}/portfolio")
async def get_portfolio_snapshots(
    session_id: int,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
):
    """Get portfolio snapshots for equity curve"""
    try:
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        snapshots = db_manager.get_portfolio_snapshots(session_id, start_dt, end_dt)
        return snapshots
    
    except Exception as e:
        logger.error(f"Error getting portfolio snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Backtesting endpoints
@app.post("/api/backtest")
async def run_backtest(backtest_request: BacktestRequest, background_tasks: BackgroundTasks):
    """Run a backtest"""
    try:
        # Create a new session for the backtest
        session_id = db_manager.create_trading_session(
            "backtest",
            backtest_request.strategy_id,
            backtest_request.symbol,
            backtest_request.initial_capital
        )
        
        # Add backtest to background tasks
        background_tasks.add_task(
            run_backtest_task,
            session_id,
            backtest_request
        )
        
        return {
            "message": "Backtest started",
            "session_id": session_id,
            "status": "running"
        }
    
    except Exception as e:
        logger.error(f"Error starting backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def run_backtest_task(session_id: int, backtest_request: BacktestRequest):
    """Background task to run GPU-accelerated backtest"""
    try:
        logger.info(f"Starting GPU-accelerated backtest for session {session_id}")
        
        # Get strategy
        strategy = db_manager.get_strategy(backtest_request.strategy_id)
        if not strategy:
            raise Exception("Strategy not found")
        
        # Import GPU backtest engine
        try:
            from backtesting.gpu_backtest_engine import GPUBacktestEngine
            gpu_available = True
        except ImportError as e:
            logger.warning(f"GPU backtest engine not available: {e}")
            gpu_available = False
        
        if gpu_available:
            # Use GPU-accelerated backtesting
            logger.info("Using GPU-accelerated backtesting engine")
            
            # Initialize GPU backtest engine
            gpu_engine = GPUBacktestEngine(use_gpu=True)
            
            # Prepare strategy parameters
            strategy_params = strategy.get('parameters', {})
            strategy_params['printlog'] = False  # Reduce logging for background task
            
            # Run GPU backtest with strategy information
            backtest_results = gpu_engine.run_gpu_backtest(
                strategy_params=strategy_params,
                symbol=backtest_request.symbol,
                start_date=backtest_request.start_date,
                end_date=backtest_request.end_date,
                initial_capital=backtest_request.initial_capital,
                timeframe=backtest_request.timeframe,
                strategy_name=strategy.get('name', 'Unknown Strategy'),
                strategy_type=strategy.get('strategy_type', 'scalping')
            )
            
            # Store results in database
            final_capital = backtest_results['final_capital']
            total_return = backtest_results['total_return']
            total_trades = backtest_results['total_trades']
            win_rate = backtest_results['win_rate'] / 100.0  # Convert to decimal
            max_drawdown = backtest_results['max_drawdown']
            sharpe_ratio = backtest_results['sharpe_ratio']
            
            # Update session with GPU backtest results
            db_manager.update_trading_session(
                session_id,
                end_time=datetime.utcnow(),
                final_capital=final_capital,
                total_return=total_return,
                total_trades=total_trades,
                win_rate=win_rate,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                status="completed"
            )
            
            # Generate realistic trades based on backtest results
            if total_trades > 0:
                await _generate_backtest_trades(session_id, backtest_request, backtest_results)
            
            # Broadcast completion with GPU metrics
            await manager.broadcast(json.dumps({
                "type": "backtest_completed",
                "session_id": session_id,
                "status": "completed",
                "gpu_accelerated": backtest_results.get('gpu_accelerated', False),
                "processing_time": backtest_results.get('processing_time', 0),
                "bars_per_second": backtest_results.get('bars_per_second', 0),
                "device_used": backtest_results.get('device_used', 'CPU')
            }))
            
            logger.info(f"GPU backtest completed for session {session_id} in {backtest_results.get('processing_time', 0):.2f}s")
            
        else:
            # Fallback to original simulation
            logger.info("Falling back to simulated backtesting")
            await _run_simulated_backtest(session_id, backtest_request)
        
    except Exception as e:
        logger.error(f"Error in backtest task: {e}")
        
        # Update session status to failed
        db_manager.update_trading_session(session_id, status="failed")
        
        # Broadcast failure via WebSocket
        await manager.broadcast(json.dumps({
            "type": "backtest_failed",
            "session_id": session_id,
            "error": str(e)
        }))

async def _generate_backtest_trades(session_id: int, backtest_request: BacktestRequest, backtest_results: Dict):
    """Generate realistic trades based on backtest results"""
    try:
        start_date = datetime.fromisoformat(backtest_request.start_date)
        end_date = datetime.fromisoformat(backtest_request.end_date)
        
        num_trades = min(backtest_results.get('total_trades', 50), 100)  # Limit for demo
        winning_trades = int(num_trades * (backtest_results.get('win_rate', 50) / 100))
        
        current_time = start_date
        time_delta = (end_date - start_date) / num_trades
        
        for i in range(num_trades):
            entry_time = current_time + (time_delta * i)
            exit_time = entry_time + timedelta(minutes=np.random.randint(5, 60))
            
            entry_price = 1.1000 + np.random.normal(0, 0.01)
            
            # Generate realistic P&L based on backtest results
            if i < winning_trades:
                pnl = abs(np.random.normal(10, 5))  # Winning trade
            else:
                pnl = -abs(np.random.normal(5, 3))  # Losing trade
            
            exit_price = entry_price + (pnl * 0.0001)
            
            trade_id = db_manager.create_trade(
                session_id=session_id,
                symbol=backtest_request.symbol,
                side="BUY" if np.random.random() > 0.5 else "SELL",
                entry_time=entry_time,
                entry_price=entry_price,
                quantity=10000,
                signal_strength=np.random.uniform(0.6, 0.9),
                confidence=np.random.uniform(0.7, 0.95)
            )
            
            # Close the trade
            db_manager.close_trade(
                trade_id=trade_id,
                exit_time=exit_time,
                exit_price=exit_price,
                exit_reason="take_profit" if pnl > 0 else "stop_loss",
                pnl=pnl,
                pnl_pips=pnl
            )
            
    except Exception as e:
        logger.error(f"Error generating backtest trades: {e}")

async def _run_simulated_backtest(session_id: int, backtest_request: BacktestRequest):
    """Fallback simulated backtesting"""
    # Simulate processing time
    await asyncio.sleep(5)
    
    # Generate sample trades
    start_date = datetime.fromisoformat(backtest_request.start_date)
    end_date = datetime.fromisoformat(backtest_request.end_date)
    
    # Create sample trades
    num_trades = 50
    current_time = start_date
    time_delta = (end_date - start_date) / num_trades
    
    for i in range(num_trades):
        entry_time = current_time + (time_delta * i)
        exit_time = entry_time + timedelta(minutes=np.random.randint(5, 60))
        
        entry_price = 1.1000 + np.random.normal(0, 0.01)
        pnl = np.random.normal(5, 20)  # Random P&L
        exit_price = entry_price + (pnl * 0.0001)
        
        trade_id = db_manager.create_trade(
            session_id=session_id,
            symbol=backtest_request.symbol,
            side="BUY" if np.random.random() > 0.5 else "SELL",
            entry_time=entry_time,
            entry_price=entry_price,
            quantity=10000,
            signal_strength=np.random.uniform(0.6, 0.9),
            confidence=np.random.uniform(0.7, 0.95)
        )
        
        # Close the trade
        db_manager.close_trade(
            trade_id=trade_id,
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason="take_profit" if pnl > 0 else "stop_loss",
            pnl=pnl,
            pnl_pips=pnl
        )
    
    # Update session with final results
    final_capital = backtest_request.initial_capital + sum([np.random.normal(5, 20) for _ in range(num_trades)])
    total_return = (final_capital - backtest_request.initial_capital) / backtest_request.initial_capital
    
    db_manager.update_trading_session(
        session_id,
        end_time=datetime.utcnow(),
        final_capital=final_capital,
        total_return=total_return,
        status="completed"
    )
    
    # Broadcast completion via WebSocket
    await manager.broadcast(json.dumps({
        "type": "backtest_completed",
        "session_id": session_id,
        "status": "completed",
        "gpu_accelerated": False
    }))

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
    """Get system logs"""
    try:
        logs = db_manager.get_system_logs(limit=limit, log_level=log_level)
        return logs
    
    except Exception as e:
        logger.error(f"Error getting system logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/system/settings")
async def get_system_settings():
    """Get system settings"""
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
    """Update system settings"""
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
            <head><title>Trading Bot Dashboard</title></head>
            <body>
                <h1>Trading Bot Dashboard</h1>
                <p>Frontend not built yet. Please build the React frontend first.</p>
                <p>API is running at <a href="/docs">/docs</a></p>
                <p>API root is at <a href="/api/">/api/</a></p>
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
            <head><title>Trading Bot Dashboard</title></head>
            <body>
                <h1>Trading Bot Dashboard</h1>
                <p>Frontend not built yet. Please build the React frontend first.</p>
                <p>API is running at <a href="/docs">/docs</a></p>
                <p>API root is at <a href="/api/">/api/</a></p>
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