"""
Real-time Trading Engine with Comprehensive Logging
Integrates enhanced broker, signal logging, and strategy execution for live trading
"""

import backtrader as bt
import logging
import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Callable
import json

# Import our enhanced components
from backtesting.enhanced_realtime_broker import create_enhanced_realtime_broker
from utils.realtime_signal_logger import get_signal_logger
from database.database_manager import DatabaseManager

class RealTimeTradingEngine:
    """
    Comprehensive real-time trading engine with enhanced logging and monitoring
    """
    
    def __init__(self, config: Dict[str, Any], session_id: int, 
                 websocket_manager=None, db_manager: DatabaseManager = None):
        self.config = config
        self.session_id = session_id
        self.websocket_manager = websocket_manager
        self.db_manager = db_manager or DatabaseManager()
        
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.cerebro = None
        self.broker = None
        self.strategy = None
        self.data_feed = None
        
        # Real-time logging components
        self.signal_logger = get_signal_logger(websocket_manager, db_manager)
        
        # Engine state
        self.is_running = False
        self.is_paused = False
        self.start_time = None
        self.end_time = None
        
        # Performance tracking
        self.total_signals = 0
        self.total_trades = 0
        self.total_pnl = 0.0
        
        # Threading
        self.engine_thread = None
        self.monitoring_thread = None
        
        self.logger.info(f"RealTimeTradingEngine initialized for session {session_id}")
    
    def setup_engine(self, strategy_class_name: str, strategy_params: Dict[str, Any],
                    initial_capital: float = 100000.0, commission: float = 0.001):
        """Setup the trading engine with strategy and broker"""
        try:
            # Create Cerebro engine
            self.cerebro = bt.Cerebro()
            
            # Extract symbol from config for commission setup
            symbol = self.config.get('symbol')
            if not symbol:
                # Try to get from backtesting config
                backtest_config = self.config.get('backtesting', {})
                symbol = backtest_config.get('symbol')
            
            # Create enhanced real-time broker with symbol for proper commission
            self.broker = create_enhanced_realtime_broker(initial_capital, commission, symbol=symbol)
            self.broker.set_websocket_manager(self.websocket_manager)
            self.broker.set_database_manager(self.db_manager)
            self.broker.set_session_id(self.session_id)
            
            # Set broker in cerebro
            self.cerebro.setbroker(self.broker)
            
            # Import and add strategy
            strategy_class = self._get_strategy_class(strategy_class_name)
            if strategy_class:
                # Set session_id in strategy params
                strategy_params['session_id'] = self.session_id
                self.cerebro.addstrategy(strategy_class, **strategy_params)
                self.logger.info(f"Added strategy: {strategy_class_name} with params: {strategy_params}")
            else:
                raise Exception(f"Strategy class not found: {strategy_class_name}")
            
            # Add analyzers for performance tracking
            self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            
            self.logger.info("Real-time trading engine setup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up trading engine: {e}")
            return False
    
    def _get_strategy_class(self, strategy_class_name: str):
        """Dynamically import strategy class"""
        try:
            if strategy_class_name == 'MarketMakingHFTStrategy':
                from strategies.market_making_hft_strategy import MarketMakingHFTStrategy
                return MarketMakingHFTStrategy
            elif strategy_class_name == 'StatisticalArbitrageHFTStrategy':
                from strategies.statistical_arbitrage_hft_strategy import StatisticalArbitrageHFTStrategy
                return StatisticalArbitrageHFTStrategy
            elif strategy_class_name == 'LatencyArbitrageHFTStrategy':
                from strategies.latency_arbitrage_hft_strategy import LatencyArbitrageHFTStrategy
                return LatencyArbitrageHFTStrategy
            elif strategy_class_name == 'MomentumIgnitionHFTStrategy':
                from strategies.momentum_ignition_hft_strategy import MomentumIgnitionHFTStrategy
                return MomentumIgnitionHFTStrategy
            elif strategy_class_name == 'EnhancedRealtimeScalping1MStrategy':
                from strategies.enhanced_realtime_scalping_1m_strategy import EnhancedRealtimeScalping1MStrategy
                return EnhancedRealtimeScalping1MStrategy
            elif strategy_class_name == 'EnhancedRealtimeScalping5MStrategy':
                from strategies.enhanced_realtime_scalping_5m_strategy import EnhancedRealtimeScalping5MStrategy
                return EnhancedRealtimeScalping5MStrategy
            elif strategy_class_name == 'OriginalMarketMakingStrategy':
                from strategies.enhanced_forex_strategy import OriginalMarketMakingStrategy
                return OriginalMarketMakingStrategy
            elif strategy_class_name == 'EnhancedForexStrategy':
                from strategies.enhanced_forex_strategy import EnhancedForexStrategy
                return EnhancedForexStrategy
            elif strategy_class_name == 'RealtimeScalping1MStrategy':
                from strategies.realtime_scalping_1m_strategy import RealtimeScalping1MStrategy
                return RealtimeScalping1MStrategy
            elif strategy_class_name == 'RealtimeScalping5MStrategy':
                from strategies.realtime_scalping_5m_strategy import RealtimeScalping5MStrategy
                return RealtimeScalping5MStrategy

            else:
                self.logger.error(f"Unknown strategy class: {strategy_class_name}")
                return None
        except ImportError as e:
            self.logger.error(f"Error importing strategy {strategy_class_name}: {e}")
            return None
    def add_data_feed(self, symbol: str, timeframe: str, data_source):
        """Add data feed to the engine"""
        try:
            # Convert data source to backtrader data feed
            if hasattr(data_source, 'to_backtrader_feed'):
                data_feed = data_source.to_backtrader_feed()
            else:
                # Assume it's already a backtrader data feed
                data_feed = data_source
            
            self.cerebro.adddata(data_feed, name=symbol)
            self.data_feed = data_feed
            
            self.logger.info(f"Added data feed for {symbol} {timeframe}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding data feed: {e}")
            return False
    
    def start_trading(self):
        """Start real-time trading"""
        if self.is_running:
            self.logger.warning("Trading engine is already running")
            return False
        
        try:
            self.is_running = True
            self.start_time = datetime.utcnow()
            
            # Update session status
            self.db_manager.update_trading_session(
                self.session_id,
                status="running",
                start_time=self.start_time
            )
            
            # Start engine thread
            self.engine_thread = threading.Thread(target=self._run_trading_loop, daemon=True)
            self.engine_thread.start()
            
            # Start monitoring thread
            self.monitoring_thread = threading.Thread(target=self._run_monitoring_loop, daemon=True)
            self.monitoring_thread.start()
            
            # Broadcast start event
            if self.websocket_manager:
                asyncio.create_task(self.websocket_manager.broadcast(json.dumps({
                    "type": "realtime_trading_started",
                    "session_id": self.session_id,
                    "timestamp": self.start_time.isoformat()
                })))
            
            self.logger.info(f"Real-time trading started for session {self.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting trading: {e}")
            self.is_running = False
            return False
    
    def stop_trading(self):
        """Stop real-time trading"""
        if not self.is_running:
            self.logger.warning("Trading engine is not running")
            return False
        
        try:
            self.is_running = False
            self.end_time = datetime.utcnow()
            
            # Wait for threads to finish
            if self.engine_thread and self.engine_thread.is_alive():
                self.engine_thread.join(timeout=10)
            
            if self.monitoring_thread and self.monitoring_thread.is_alive():
                self.monitoring_thread.join(timeout=5)
            
            # Update session status
            final_value = self.broker.get_value() if self.broker else 0
            initial_capital = self.config.get('initial_capital', 100000)
            total_return = (final_value - initial_capital) / initial_capital if initial_capital > 0 else 0
            
            self.db_manager.update_trading_session(
                self.session_id,
                status="stopped",
                end_time=self.end_time,
                final_capital=final_value,
                total_return=total_return
            )
            
            # Broadcast stop event
            if self.websocket_manager:
                asyncio.create_task(self.websocket_manager.broadcast(json.dumps({
                    "type": "realtime_trading_stopped",
                    "session_id": self.session_id,
                    "timestamp": self.end_time.isoformat(),
                    "final_value": final_value,
                    "total_return": total_return
                })))
            
            self.logger.info(f"Real-time trading stopped for session {self.session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping trading: {e}")
            return False
    
    def pause_trading(self):
        """Pause real-time trading"""
        self.is_paused = True
        self.logger.info("Real-time trading paused")
    
    def resume_trading(self):
        """Resume real-time trading"""
        self.is_paused = False
        self.logger.info("Real-time trading resumed")
    
    def _run_trading_loop(self):
        """Main trading loop"""
        try:
            self.logger.info("Starting trading loop")
            
            # Run the cerebro engine
            results = self.cerebro.run()
            
            if results:
                self.strategy = results[0]
                self.logger.info("Trading loop completed successfully")
            else:
                self.logger.error("Trading loop completed with no results")
                
        except Exception as e:
            self.logger.error(f"Error in trading loop: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        finally:
            self.is_running = False
    
    def _run_monitoring_loop(self):
        """Monitoring loop for real-time statistics"""
        try:
            self.logger.info("Starting monitoring loop")
            
            while self.is_running:
                if not self.is_paused and self.broker:
                    # Collect broker statistics
                    broker_stats = self.broker.get_broker_stats()
                    
                    # Store in database
                    self.db_manager.store_realtime_broker_stats(
                        session_id=self.session_id,
                        timestamp=datetime.utcnow(),
                        cash=broker_stats['cash'],
                        portfolio_value=broker_stats['value'],
                        total_signals=broker_stats['total_signals'],
                        total_orders=broker_stats['total_orders'],
                        executions=broker_stats['executions'],
                        buy_signals=broker_stats['buy_signals'],
                        sell_signals=broker_stats['sell_signals'],
                        completed_orders=broker_stats['completed_orders'],
                        rejected_orders=broker_stats['rejected_orders']
                    )
                    
                    # Broadcast statistics
                    if self.websocket_manager:
                        asyncio.create_task(self.websocket_manager.broadcast(json.dumps({
                            "type": "broker_stats_update",
                            "session_id": self.session_id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "data": broker_stats
                        })))
                
                # Sleep for monitoring interval
                time.sleep(5)  # Update every 5 seconds
                
        except Exception as e:
            self.logger.error(f"Error in monitoring loop: {e}")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        status = {
            "session_id": self.session_id,
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
        }
        
        if self.broker:
            broker_stats = self.broker.get_broker_stats()
            status.update({
                "broker_stats": broker_stats,
                "current_cash": self.broker.get_cash(),
                "current_value": self.broker.get_value()
            })
        
        return status
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        if not self.strategy:
            return {"error": "No strategy results available"}
        
        try:
            # Get analyzer results
            analyzers = {}
            if hasattr(self.strategy, 'analyzers'):
                for name, analyzer in self.strategy.analyzers.getitems():
                    analyzers[name] = analyzer.get_analysis()
            
            # Get broker statistics
            broker_stats = self.broker.get_broker_stats() if self.broker else {}
            
            # Calculate performance metrics
            initial_capital = self.config.get('initial_capital', 100000)
            current_value = self.broker.get_value() if self.broker else initial_capital
            total_return = (current_value - initial_capital) / initial_capital if initial_capital > 0 else 0
            
            return {
                "initial_capital": initial_capital,
                "current_value": current_value,
                "total_return": total_return,
                "total_return_percent": total_return * 100,
                "analyzers": analyzers,
                "broker_stats": broker_stats,
                "session_duration": (datetime.utcnow() - self.start_time).total_seconds() if self.start_time else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}

# Factory function
def create_realtime_trading_engine(config: Dict[str, Any], session_id: int,
                                  websocket_manager=None, db_manager: DatabaseManager = None):
    """Create a real-time trading engine instance"""
    return RealTimeTradingEngine(config, session_id, websocket_manager, db_manager)

if __name__ == "__main__":
    # Test the real-time trading engine
    logging.basicConfig(level=logging.INFO)
    
    config = {
        "initial_capital": 100000.0,
        "commission": 0.001,
        "strategy": "EnhancedRealtimeScalping1MStrategy",
        "symbol": "EUR_USD",
        "timeframe": "1m"
    }
    
    engine = create_realtime_trading_engine(config, session_id=1)
    
    # Setup engine
    strategy_params = {
        "fast_length": 5,
        "slow_length": 13,
        "signal_strength_threshold": 0.1,
        "printlog": True
    }
    
    if engine.setup_engine("EnhancedRealtimeScalping1MStrategy", strategy_params):
        print("Engine setup successful")
        print(f"Current status: {engine.get_current_status()}")
    else:
        print("Engine setup failed")