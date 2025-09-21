"""
Web Server Integration for Trading Bot Dashboard
Integrates with main.py to provide web interface for live trading and backtesting
"""

import asyncio
import threading
import logging
import argparse
import sys
import os
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import API server
from api.main import app
import uvicorn

# Import trading bot components
from database.database_manager import DatabaseManager
from strategies.scalping_forex_strategy import ScalpingForexStrategy
from data.data_feed import OANDADataFeed
from utils.logger import setup_logging

logger = logging.getLogger(__name__)

class TradingBotWebServer:
    """
    Web server that integrates with the trading bot
    Provides dashboard interface for live trading and backtesting
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = config_path
        self.db_manager = DatabaseManager()
        self.server_thread: Optional[threading.Thread] = None
        self.server_process = None
        self.is_running = False
        
        # Setup logging with default config
        self._setup_logging()
        
    def _setup_logging(self):
        """Setup logging with config file or defaults"""
        try:
            import yaml
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
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
            logger.warning(f"Could not setup advanced logging: {e}. Using basic logging.")
        
    def start_server(self, host: str = "0.0.0.0", port: int = 8000):
        """Start the web server"""
        try:
            logger.info(f"Starting Trading Bot Web Server on {host}:{port}")
            
            # Initialize database
            self._initialize_database()
            
            # Start server in a separate thread
            self.server_thread = threading.Thread(
                target=self._run_server,
                args=(host, port),
                daemon=True
            )
            self.server_thread.start()
            self.is_running = True
            
            logger.info("Web server started successfully")
            logger.info(f"Dashboard available at: http://{host}:{port}")
            logger.info(f"API documentation at: http://{host}:{port}/docs")
            
        except Exception as e:
            logger.error(f"Failed to start web server: {e}")
            raise
    
    def _run_server(self, host: str, port: int):
        """Run the uvicorn server"""
        try:
            uvicorn.run(
                app,
                host=host,
                port=port,
                log_level="info",
                access_log=True
            )
        except Exception as e:
            logger.error(f"Server error: {e}")
            self.is_running = False
    
    def _initialize_database(self):
        """Initialize database with default data"""
        try:
            # Create default strategies if they don't exist
            strategies = self.db_manager.get_strategies()
            
            if not strategies:
                logger.info("Creating default strategies...")
                
                # Scalping EUR_USD 1M
                self.db_manager.create_strategy(
                    name="Scalping EUR_USD 1M",
                    description="High-frequency scalping strategy for EUR_USD on 1-minute timeframe",
                    strategy_type="scalping",
                    asset_class="forex",
                    timeframe="1m",
                    parameters={
                        "fast_ema": 5,
                        "slow_ema": 13,
                        "rsi_period": 7,
                        "stop_loss_pips": 3,
                        "take_profit_pips": 6,
                        "max_risk_per_trade": 0.01,
                        "position_size_percent": 0.02
                    }
                )
                
                # Scalping EUR_USD 5M
                self.db_manager.create_strategy(
                    name="Scalping EUR_USD 5M",
                    description="High-frequency scalping strategy for EUR_USD on 5-minute timeframe",
                    strategy_type="scalping",
                    asset_class="forex",
                    timeframe="5m",
                    parameters={
                        "fast_ema": 5,
                        "slow_ema": 13,
                        "rsi_period": 7,
                        "stop_loss_pips": 5,
                        "take_profit_pips": 10,
                        "max_risk_per_trade": 0.015,
                        "position_size_percent": 0.025
                    }
                )
                
                logger.info("Default strategies created successfully")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def stop_server(self):
        """Stop the web server"""
        try:
            logger.info("Stopping web server...")
            self.is_running = False
            
            if self.server_thread and self.server_thread.is_alive():
                # Note: uvicorn doesn't have a clean shutdown method when run in thread
                # In production, you'd want to use a proper process manager
                logger.info("Server thread will terminate when main process exits")
            
            logger.info("Web server stopped")
            
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")
    
    def is_server_running(self) -> bool:
        """Check if server is running"""
        return self.is_running and (self.server_thread and self.server_thread.is_alive())

def run_with_web_interface(mode: str, config_path: str = "config/config.yaml"):
    """
    Run trading bot with web interface
    
    Args:
        mode: 'live' or 'backtest'
        config_path: Path to configuration file
    """
    
    # Start web server
    web_server = TradingBotWebServer(config_path)
    web_server.start_server()
    
    try:
        if mode == "live":
            logger.info("Starting live trading with web dashboard...")
            run_live_trading_with_dashboard(config_path, web_server)
        elif mode == "backtest":
            logger.info("Starting backtesting with web dashboard...")
            run_backtesting_with_dashboard(config_path, web_server)
        else:
            logger.error(f"Invalid mode: {mode}")
            return
            
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Error in trading bot: {e}")
    finally:
        web_server.stop_server()

def run_live_trading_with_dashboard(config_path: str, web_server: TradingBotWebServer):
    """Run live trading with web dashboard"""
    import yaml
    import time
    from datetime import datetime, timedelta
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Initialize components
    db_manager = web_server.db_manager
    data_feed = OANDADataFeed(config)
    
    # Get or create a live trading session
    strategies = db_manager.get_strategies()
    if not strategies:
        logger.error("No strategies found. Please create a strategy first.")
        return
    
    # Use the first scalping strategy
    scalping_strategy = next((s for s in strategies if s['strategy_type'] == 'scalping'), strategies[0])
    
    # Create live trading session
    session_id = db_manager.create_trading_session(
        session_type="live",
        strategy_id=scalping_strategy['id'],
        symbol="EUR_USD",
        initial_capital=100000.0
    )
    
    logger.info(f"Created live trading session {session_id}")
    logger.info("Web dashboard is running. Press Ctrl+C to stop.")
    
    # Simulate live trading (in a real implementation, this would connect to broker)
    try:
        iteration = 0
        while web_server.is_server_running():
            iteration += 1
            current_time = datetime.utcnow()
            
            # Store portfolio snapshot every minute
            if iteration % 12 == 0:  # Every 60 seconds (5 second intervals)
                portfolio_value = 100000 + (iteration * 0.5)  # Simulate growth
                
                db_manager.store_portfolio_snapshot(
                    session_id=session_id,
                    timestamp=current_time,
                    total_value=portfolio_value,
                    cash_balance=portfolio_value * 0.8,
                    unrealized_pnl=iteration * 0.1,
                    realized_pnl=iteration * 0.4,
                    open_positions=2,
                    daily_pnl=iteration * 0.05
                )
            
            # Simulate occasional trades
            if iteration % 50 == 0:  # Every ~4 minutes
                trade_id = db_manager.create_trade(
                    session_id=session_id,
                    symbol="EUR_USD",
                    side="BUY" if iteration % 100 < 50 else "SELL",
                    entry_time=current_time,
                    entry_price=1.1000 + (iteration % 100) * 0.0001,
                    quantity=10000,
                    signal_strength=0.75,
                    confidence=0.85
                )
                
                logger.info(f"Simulated trade created: {trade_id}")
            
            time.sleep(5)  # Update every 5 seconds
            
    except KeyboardInterrupt:
        logger.info("Live trading stopped by user")
    
    # Update session status
    db_manager.update_trading_session(
        session_id,
        end_time=datetime.utcnow(),
        status="stopped"
    )

def run_backtesting_with_dashboard(config_path: str, web_server: TradingBotWebServer):
    """Run backtesting with web dashboard"""
    import yaml
    import time
    from datetime import datetime, timedelta
    
    # Load configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    db_manager = web_server.db_manager
    
    logger.info("Backtesting mode with web dashboard")
    logger.info("Use the web interface to start backtests")
    logger.info("Web dashboard is running. Press Ctrl+C to stop.")
    
    try:
        # Keep server running for backtesting interface
        while web_server.is_server_running():
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Backtesting interface stopped by user")

def main():
    """Main entry point for web server"""
    parser = argparse.ArgumentParser(description="Trading Bot Web Dashboard")
    parser.add_argument('--mode', type=str, required=True,
                        choices=['live', 'backtest', 'server-only'],
                        help='Operation mode: live, backtest, or server-only')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='Path to configuration file')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Server host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000,
                        help='Server port (default: 8000)')
    
    args = parser.parse_args()
    
    if args.mode == 'server-only':
            # Run only the web server
            import time
            web_server = TradingBotWebServer(args.config)
            web_server.start_server(args.host, args.port)
            
            try:
                logger.info("Web server running. Press Ctrl+C to stop.")
                while web_server.is_server_running():
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Server stopped by user")
            finally:
                web_server.stop_server()
    else:
        # Run with trading bot integration
        run_with_web_interface(args.mode, args.config)

if __name__ == "__main__":
    main()