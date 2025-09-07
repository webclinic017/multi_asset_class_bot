"""
Real-time Portfolio Manager for Live Trading
Tracks portfolio value, P&L, margin usage, and position values in real-time
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import json

@dataclass
class Position:
    """Represents an open trading position"""
    symbol: str
    side: str  # 'buy' or 'sell'
    size: float
    entry_price: float
    current_price: float
    entry_time: datetime
    unrealized_pnl: float = 0.0
    margin_used: float = 0.0
    swap: float = 0.0
    commission: float = 0.0
    
    def update_current_price(self, new_price: float):
        """Update current price and recalculate unrealized P&L"""
        self.current_price = new_price
        if self.side == 'buy':
            self.unrealized_pnl = (new_price - self.entry_price) * self.size
        else:  # sell
            self.unrealized_pnl = (self.entry_price - new_price) * self.size
    
    def get_market_value(self) -> float:
        """Get current market value of the position"""
        return self.current_price * abs(self.size)

@dataclass
class PortfolioSnapshot:
    """Snapshot of portfolio state at a specific time"""
    timestamp: datetime
    total_value: float
    cash_balance: float
    margin_used: float
    margin_available: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    positions_count: int
    positions_value: float
    equity: float
    margin_level: float  # Percentage
    
class RealTimePortfolioManager:
    """
    Real-time portfolio manager that tracks all portfolio metrics
    Integrates with OANDA broker API to maintain accurate portfolio state
    """
    
    def __init__(self, broker_connector, initial_capital: float = 10000.0, config: dict = None):
        """
        Initialize portfolio manager
        
        Args:
            broker_connector: OANDA broker connector instance
            initial_capital: Starting capital amount
            config: Configuration dictionary
        """
        self.broker_connector = broker_connector
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Portfolio state
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.realized_pnl = 0.0
        self.daily_pnl = 0.0
        self.total_commission = 0.0
        self.total_swap = 0.0
        
        # Positions tracking
        self.positions: Dict[str, Position] = {}  # trade_id -> Position
        self.position_lock = threading.Lock()
        
        # Portfolio history
        self.portfolio_history: List[PortfolioSnapshot] = []
        self.history_lock = threading.Lock()
        
        # Real-time tracking
        self.last_update = datetime.utcnow()
        self.update_interval = 5  # seconds
        self.is_tracking = False
        self.tracking_thread = None
        
        # Performance metrics
        self.peak_value = initial_capital
        self.max_drawdown = 0.0
        self.daily_start_value = initial_capital
        
        self.logger.info(f"Portfolio Manager initialized with ${initial_capital:,.2f}")
    
    def start_real_time_tracking(self):
        """Start real-time portfolio tracking"""
        if self.is_tracking:
            self.logger.warning("Portfolio tracking already running")
            return
        
        self.is_tracking = True
        self.tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self.tracking_thread.start()
        self.logger.info("Real-time portfolio tracking started")
    
    def stop_real_time_tracking(self):
        """Stop real-time portfolio tracking"""
        self.is_tracking = False
        if self.tracking_thread and self.tracking_thread.is_alive():
            self.tracking_thread.join(timeout=10)
        self.logger.info("Real-time portfolio tracking stopped")
    
    def _tracking_loop(self):
        """Main tracking loop that runs in background thread"""
        while self.is_tracking:
            try:
                self._update_portfolio_state()
                time.sleep(self.update_interval)
            except Exception as e:
                self.logger.error(f"Error in portfolio tracking loop: {e}")
                time.sleep(self.update_interval)
    
    def _update_portfolio_state(self):
        """Update portfolio state from broker API"""
        try:
            # Get current account balance from broker
            balance_info = self.broker_connector.get_balance()
            if balance_info:
                # Update cash balance from broker
                broker_balance = balance_info.get('total', self.cash_balance)
                
                # Get current positions from broker
                self._sync_positions_with_broker()
                
                # Update portfolio metrics
                self._calculate_portfolio_metrics()
                
                # Store snapshot
                self._store_portfolio_snapshot()
                
                self.last_update = datetime.utcnow()
                
        except Exception as e:
            self.logger.error(f"Error updating portfolio state: {e}")
    
    def _sync_positions_with_broker(self):
        """Synchronize positions with broker's current positions"""
        try:
            # This would need to be implemented based on OANDA's position API
            # For now, we'll update existing positions with current prices
            with self.position_lock:
                for trade_id, position in self.positions.items():
                    current_price = self.broker_connector.get_current_price(position.symbol)
                    if current_price:
                        position.update_current_price(current_price)
                        
        except Exception as e:
            self.logger.error(f"Error syncing positions with broker: {e}")
    
    def add_position(self, trade_id: str, symbol: str, side: str, size: float, 
                    entry_price: float, commission: float = 0.0):
        """
        Add a new position to portfolio tracking
        
        Args:
            trade_id: Unique trade identifier
            symbol: Trading symbol (e.g., 'EUR_USD')
            side: 'buy' or 'sell'
            size: Position size
            entry_price: Entry price
            commission: Commission paid
        """
        with self.position_lock:
            # Get current price for the symbol
            current_price = self.broker_connector.get_current_price(symbol)
            if not current_price:
                current_price = entry_price
            
            # Calculate margin used (simplified - would need proper margin calculation)
            margin_used = abs(size * entry_price) * 0.01  # 1% margin requirement
            
            position = Position(
                symbol=symbol,
                side=side,
                size=size,
                entry_price=entry_price,
                current_price=current_price,
                entry_time=datetime.utcnow(),
                margin_used=margin_used,
                commission=commission
            )
            
            position.update_current_price(current_price)
            self.positions[trade_id] = position
            
            # Update cash balance for margin and commission
            self.cash_balance -= (margin_used + commission)
            self.total_commission += commission
            
            self.logger.info(f"Position added: {trade_id} - {side.upper()} {size} {symbol} @ {entry_price}")
            self.logger.info(f"Margin used: ${margin_used:.2f}, Commission: ${commission:.2f}")
    
    def close_position(self, trade_id: str, exit_price: float, commission: float = 0.0):
        """
        Close a position and update portfolio
        
        Args:
            trade_id: Trade identifier to close
            exit_price: Exit price
            commission: Commission paid on exit
        """
        with self.position_lock:
            if trade_id not in self.positions:
                self.logger.error(f"Position {trade_id} not found")
                return
            
            position = self.positions[trade_id]
            
            # Calculate realized P&L
            if position.side == 'buy':
                pnl = (exit_price - position.entry_price) * position.size
            else:  # sell
                pnl = (position.entry_price - exit_price) * position.size
            
            # Subtract exit commission
            pnl -= commission
            
            # Update portfolio
            self.realized_pnl += pnl
            self.daily_pnl += pnl
            self.cash_balance += (position.margin_used + pnl)  # Return margin + P&L
            self.total_commission += commission
            
            # Remove position
            del self.positions[trade_id]
            
            self.logger.info(f"Position closed: {trade_id} - P&L: ${pnl:.2f}")
            self.logger.info(f"Total realized P&L: ${self.realized_pnl:.2f}")
    
    def _calculate_portfolio_metrics(self):
        """Calculate current portfolio metrics"""
        with self.position_lock:
            # Calculate total unrealized P&L
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
            
            # Calculate total margin used
            total_margin_used = sum(pos.margin_used for pos in self.positions.values())
            
            # Calculate total positions value
            total_positions_value = sum(pos.get_market_value() for pos in self.positions.values())
            
            # Calculate equity (cash + unrealized P&L)
            equity = self.cash_balance + total_unrealized_pnl
            
            # Calculate total portfolio value
            total_value = equity
            
            # Update peak value and drawdown
            if total_value > self.peak_value:
                self.peak_value = total_value
            
            current_drawdown = (self.peak_value - total_value) / self.peak_value * 100
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
            
            # Store calculated values for snapshot
            self._current_metrics = {
                'total_value': total_value,
                'cash_balance': self.cash_balance,
                'margin_used': total_margin_used,
                'margin_available': self.cash_balance - total_margin_used,
                'unrealized_pnl': total_unrealized_pnl,
                'realized_pnl': self.realized_pnl,
                'daily_pnl': self.daily_pnl,
                'positions_count': len(self.positions),
                'positions_value': total_positions_value,
                'equity': equity,
                'margin_level': (equity / max(total_margin_used, 1)) * 100
            }
    
    def _store_portfolio_snapshot(self):
        """Store current portfolio snapshot"""
        if not hasattr(self, '_current_metrics'):
            return
        
        snapshot = PortfolioSnapshot(
            timestamp=datetime.utcnow(),
            **self._current_metrics
        )
        
        with self.history_lock:
            self.portfolio_history.append(snapshot)
            
            # Keep only last 1000 snapshots to prevent memory issues
            if len(self.portfolio_history) > 1000:
                self.portfolio_history = self.portfolio_history[-1000:]
    
    def get_current_portfolio_value(self) -> float:
        """Get current total portfolio value"""
        self._calculate_portfolio_metrics()
        return self._current_metrics.get('total_value', self.initial_capital)
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        self._calculate_portfolio_metrics()
        
        summary = {
            'timestamp': datetime.utcnow().isoformat(),
            'initial_capital': self.initial_capital,
            'current_value': self._current_metrics.get('total_value', self.initial_capital),
            'total_return': ((self._current_metrics.get('total_value', self.initial_capital) - self.initial_capital) / self.initial_capital) * 100,
            'cash_balance': self._current_metrics.get('cash_balance', self.cash_balance),
            'margin_used': self._current_metrics.get('margin_used', 0),
            'margin_available': self._current_metrics.get('margin_available', self.cash_balance),
            'unrealized_pnl': self._current_metrics.get('unrealized_pnl', 0),
            'realized_pnl': self.realized_pnl,
            'daily_pnl': self.daily_pnl,
            'total_commission': self.total_commission,
            'positions_count': len(self.positions),
            'positions_value': self._current_metrics.get('positions_value', 0),
            'equity': self._current_metrics.get('equity', self.cash_balance),
            'margin_level': self._current_metrics.get('margin_level', 100),
            'peak_value': self.peak_value,
            'max_drawdown': self.max_drawdown,
            'snapshots_count': len(self.portfolio_history),
            'last_update': self.last_update.isoformat()
        }
        
        return summary
    
    def get_positions_summary(self) -> List[Dict]:
        """Get summary of all open positions"""
        with self.position_lock:
            positions_summary = []
            for trade_id, position in self.positions.items():
                positions_summary.append({
                    'trade_id': trade_id,
                    'symbol': position.symbol,
                    'side': position.side,
                    'size': position.size,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'unrealized_pnl': position.unrealized_pnl,
                    'margin_used': position.margin_used,
                    'market_value': position.get_market_value(),
                    'entry_time': position.entry_time.isoformat(),
                    'commission': position.commission
                })
            
            return positions_summary
    
    def reset_daily_pnl(self):
        """Reset daily P&L (call at start of each trading day)"""
        self.daily_pnl = 0.0
        self.daily_start_value = self.get_current_portfolio_value()
        self.logger.info("Daily P&L reset")
    
    def export_portfolio_history(self, filename: str = None) -> str:
        """Export portfolio history to JSON file"""
        if not filename:
            filename = f"portfolio_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with self.history_lock:
            history_data = []
            for snapshot in self.portfolio_history:
                history_data.append({
                    'timestamp': snapshot.timestamp.isoformat(),
                    'total_value': snapshot.total_value,
                    'cash_balance': snapshot.cash_balance,
                    'margin_used': snapshot.margin_used,
                    'unrealized_pnl': snapshot.unrealized_pnl,
                    'realized_pnl': snapshot.realized_pnl,
                    'daily_pnl': snapshot.daily_pnl,
                    'positions_count': snapshot.positions_count,
                    'equity': snapshot.equity,
                    'margin_level': snapshot.margin_level
                })
        
        with open(filename, 'w') as f:
            json.dump(history_data, f, indent=2)
        
        self.logger.info(f"Portfolio history exported to {filename}")
        return filename

if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Mock broker connector for testing
    class MockBrokerConnector:
        def get_balance(self):
            return {'total': 10000.0}
        
        def get_current_price(self, symbol):
            return 1.1000  # Mock EUR_USD price
    
    # Test portfolio manager
    mock_broker = MockBrokerConnector()
    portfolio_manager = RealTimePortfolioManager(mock_broker, 10000.0)
    
    # Add a test position
    portfolio_manager.add_position(
        trade_id="test_001",
        symbol="EUR_USD",
        side="buy",
        size=10000,
        entry_price=1.0950,
        commission=2.50
    )
    
    # Get portfolio summary
    summary = portfolio_manager.get_portfolio_summary()
    print("Portfolio Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
    
    # Close position with profit
    portfolio_manager.close_position("test_001", 1.1050, 2.50)
    
    # Get updated summary
    summary = portfolio_manager.get_portfolio_summary()
    print("\nUpdated Portfolio Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")