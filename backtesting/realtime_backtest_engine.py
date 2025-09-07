"""
Real-time Portfolio Tracking Backtest Engine
Extends the standard backtest engine to provide real-time portfolio value updates
during backtest execution for the dashboard API
"""

import backtrader as bt
import logging
import threading
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
import pandas as pd
import numpy as np

from backtesting.backtest_engine import BacktestEngine
from execution.portfolio_manager import RealTimePortfolioManager, PortfolioSnapshot

class RealTimeBacktestEngine(BacktestEngine):
    """
    Enhanced backtest engine that provides real-time portfolio tracking
    and updates during backtest execution
    """
    
    def __init__(self, data_feed=None, preprocessor=None, risk_manager=None, config=None, 
                 update_callback=None, websocket_manager=None, session_id=None):
        """
        Initialize real-time backtest engine
        
        Args:
            data_feed: Data feed instance
            preprocessor: Data preprocessor instance  
            risk_manager: Risk manager instance
            config: Configuration dictionary
            update_callback: Callback function for portfolio updates
            websocket_manager: WebSocket manager for real-time updates
            session_id: Trading session ID for database updates
        """
        super().__init__(data_feed, preprocessor, risk_manager, config)
        
        self.update_callback = update_callback
        self.websocket_manager = websocket_manager
        self.session_id = session_id
        self.logger = logging.getLogger(__name__)
        
        # Real-time tracking
        self.portfolio_snapshots = []
        self.current_bar = 0
        self.total_bars = 0
        self.start_time = None
        self.last_update_time = None
        self.update_interval = 1.0  # Update every 1 second during backtest
        
        # Portfolio tracking
        self.portfolio_history = []
        self.trade_count = 0
        self.current_drawdown = 0.0
        self.peak_value = self.initial_capital
        
        # Real-time update thread
        self.update_thread = None
        self.is_running = False
        self.stop_event = threading.Event()
        
        self.logger.info(f"RealTimeBacktestEngine initialized for session {session_id}")
    
    def run_with_realtime_updates(self):
        """
        Run backtest with real-time portfolio value updates
        
        Returns:
            dict: Backtest results with real-time tracking data
        """
        self.logger.info("Starting real-time backtest execution...")
        
        # Start real-time update thread
        self.start_time = datetime.utcnow()
        self.is_running = True
        self.update_thread = threading.Thread(target=self._realtime_update_loop, daemon=True)
        self.update_thread.start()
        
        try:
            # Add custom analyzer for real-time tracking
            self.cerebro.addanalyzer(RealTimePortfolioAnalyzer, 
                                   _name='realtime_portfolio',
                                   engine=self)
            
            # Run the standard backtest
            results = super().run()
            
            # Stop real-time updates
            self.is_running = False
            self.stop_event.set()
            
            if self.update_thread and self.update_thread.is_alive():
                self.update_thread.join(timeout=5)
            
            # Add real-time tracking data to results
            if results:
                results['portfolio_snapshots'] = self.portfolio_snapshots
                results['realtime_updates'] = len(self.portfolio_snapshots)
                results['execution_time'] = (datetime.utcnow() - self.start_time).total_seconds()
            
            self.logger.info(f"Real-time backtest completed with {len(self.portfolio_snapshots)} portfolio updates")
            return results
            
        except Exception as e:
            self.logger.error(f"Error in real-time backtest: {e}")
            self.is_running = False
            self.stop_event.set()
            raise
    
    def _realtime_update_loop(self):
        """Background thread for real-time portfolio updates"""
        while self.is_running and not self.stop_event.is_set():
            try:
                self._update_portfolio_snapshot()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Error in real-time update loop: {e}")
                time.sleep(self.update_interval)
    
    def _update_portfolio_snapshot(self):
        """Update portfolio snapshot and broadcast to clients"""
        try:
            if not hasattr(self.cerebro, 'broker'):
                return
            
            # Get current portfolio value from backtrader broker
            current_value = self.cerebro.broker.getvalue()
            current_cash = self.cerebro.broker.getcash()
            
            # Calculate metrics
            total_return = ((current_value - self.initial_capital) / self.initial_capital) * 100
            unrealized_pnl = current_value - self.initial_capital
            
            # Update peak value and drawdown
            if current_value > self.peak_value:
                self.peak_value = current_value
            
            self.current_drawdown = ((self.peak_value - current_value) / self.peak_value) * 100
            
            # Create portfolio snapshot
            snapshot = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_value': current_value,
                'cash_balance': current_cash,
                'unrealized_pnl': unrealized_pnl,
                'total_return': total_return,
                'drawdown': self.current_drawdown,
                'trade_count': self.trade_count,
                'current_bar': self.current_bar,
                'progress': (self.current_bar / max(self.total_bars, 1)) * 100 if self.total_bars > 0 else 0
            }
            
            self.portfolio_snapshots.append(snapshot)
            
            # Store in database if session_id is available
            if self.session_id and hasattr(self, 'db_manager'):
                try:
                    self.db_manager.store_portfolio_snapshot(
                        session_id=self.session_id,
                        timestamp=datetime.utcnow(),
                        total_value=current_value,
                        cash_balance=current_cash,
                        unrealized_pnl=unrealized_pnl,
                        realized_pnl=0.0,  # Will be updated by trade analyzer
                        open_positions=0,  # Will be updated by trade analyzer
                        daily_pnl=unrealized_pnl
                    )
                except Exception as e:
                    self.logger.warning(f"Could not store portfolio snapshot: {e}")
            
            # Call update callback if provided
            if self.update_callback:
                try:
                    self.update_callback(snapshot)
                except Exception as e:
                    self.logger.warning(f"Update callback failed: {e}")
            
            # Broadcast via WebSocket if available
            if self.websocket_manager:
                try:
                    message = {
                        "type": "portfolio_update",
                        "session_id": self.session_id,
                        "data": snapshot
                    }
                    # Note: This would need to be called from an async context
                    # For now, we'll just log it
                    self.logger.debug(f"Would broadcast: {message}")
                except Exception as e:
                    self.logger.warning(f"WebSocket broadcast failed: {e}")
            
            # Keep only last 1000 snapshots to prevent memory issues
            if len(self.portfolio_snapshots) > 1000:
                self.portfolio_snapshots = self.portfolio_snapshots[-1000:]
                
        except Exception as e:
            self.logger.error(f"Error updating portfolio snapshot: {e}")
    
    def update_progress(self, current_bar: int, total_bars: int):
        """Update backtest progress"""
        self.current_bar = current_bar
        self.total_bars = total_bars
    
    def update_trade_count(self, count: int):
        """Update trade count"""
        self.trade_count = count
    
    def get_current_portfolio_value(self) -> float:
        """Get current portfolio value"""
        if hasattr(self.cerebro, 'broker'):
            return self.cerebro.broker.getvalue()
        return self.initial_capital
    
    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary"""
        current_value = self.get_current_portfolio_value()
        return {
            'current_value': current_value,
            'initial_capital': self.initial_capital,
            'total_return': ((current_value - self.initial_capital) / self.initial_capital) * 100,
            'unrealized_pnl': current_value - self.initial_capital,
            'peak_value': self.peak_value,
            'current_drawdown': self.current_drawdown,
            'trade_count': self.trade_count,
            'snapshots_count': len(self.portfolio_snapshots),
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None
        }

class RealTimePortfolioAnalyzer(bt.Analyzer):
    """
    Custom analyzer that tracks portfolio changes in real-time
    and updates the real-time backtest engine
    """
    
    def __init__(self):
        super(RealTimePortfolioAnalyzer, self).__init__()
        self.engine = self.p.engine
        self.trade_count = 0
        self.bar_count = 0
        
    def start(self):
        """Called when backtest starts"""
        self.engine.logger.info("Real-time portfolio analyzer started")
        
    def next(self):
        """Called on each bar"""
        self.bar_count += 1
        
        # Update progress every 10 bars to avoid too frequent updates
        if self.bar_count % 10 == 0:
            # Estimate total bars (this is approximate)
            total_bars = len(self.strategy.datas[0]) if hasattr(self.strategy, 'datas') and self.strategy.datas else 1000
            self.engine.update_progress(self.bar_count, total_bars)
    
    def notify_trade(self, trade):
        """Called when a trade is closed"""
        if trade.isclosed:
            self.trade_count += 1
            self.engine.update_trade_count(self.trade_count)
            
            # Log trade details
            self.engine.logger.info(f"Trade #{self.trade_count} closed: "
                                  f"P&L: {trade.pnl:.2f}, "
                                  f"Portfolio Value: {self.strategy.broker.getvalue():.2f}")
    
    def notify_order(self, order):
        """Called when an order status changes"""
        if order.status in [order.Completed]:
            # Force a portfolio update when orders are executed
            self.engine._update_portfolio_snapshot()
    
    def stop(self):
        """Called when backtest ends"""
        self.engine.logger.info(f"Real-time portfolio analyzer stopped. "
                              f"Total trades: {self.trade_count}, "
                              f"Total bars: {self.bar_count}")
    
    def get_analysis(self):
        """Return analysis results"""
        return {
            'total_trades': self.trade_count,
            'total_bars': self.bar_count,
            'portfolio_snapshots': len(self.engine.portfolio_snapshots)
        }

# Integration function for the API
def create_realtime_backtest_engine(config: dict, session_id: int, 
                                   update_callback=None, websocket_manager=None):
    """
    Factory function to create a real-time backtest engine
    
    Args:
        config: Backtest configuration
        session_id: Trading session ID
        update_callback: Optional callback for portfolio updates
        websocket_manager: Optional WebSocket manager for broadcasting
        
    Returns:
        RealTimeBacktestEngine: Configured engine instance
    """
    from data.data_feed import OANDADataFeed
    from data.preprocessing import DataPreprocessor
    from risk.risk_manager import RiskManager
    
    # Initialize components
    data_feed = OANDADataFeed(config)
    preprocessor = DataPreprocessor()
    risk_manager = RiskManager(config)
    
    # Create real-time engine
    engine = RealTimeBacktestEngine(
        data_feed=data_feed,
        preprocessor=preprocessor,
        risk_manager=risk_manager,
        config=config,
        update_callback=update_callback,
        websocket_manager=websocket_manager,
        session_id=session_id
    )
    
    return engine

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Mock configuration
    config = {
        'backtesting': {
            'initial_capital': 10000,
            'commission': 0.001,
            'slippage': 0.0005,
            'start_date': '2023-01-01',
            'end_date': '2023-01-31'
        },
        'oanda': {
            'account_id': 'test',
            'access_token': 'test',
            'practice': True
        }
    }
    
    # Create engine
    engine = create_realtime_backtest_engine(
        config=config,
        session_id=1,
        update_callback=lambda snapshot: print(f"Portfolio update: ${snapshot['total_value']:.2f}")
    )
    
    print("Real-time backtest engine created successfully")