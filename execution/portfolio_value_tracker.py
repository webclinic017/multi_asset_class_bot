"""
Portfolio Value Tracker - Definitive Fix for Portfolio Value Updates
Forces real-time portfolio value calculation that reflects actual trading results
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

class PortfolioValueTracker:
    """
    Tracks and forces correct portfolio value calculation
    Bypasses backtrader's internal value calculation issues
    """
    
    def __init__(self, initial_capital: float = 100000.0):
        self.logger = logging.getLogger(__name__)
        self.initial_capital = initial_capital
        self.current_cash = initial_capital
        self.positions = {}  # symbol -> {'size': float, 'entry_price': float, 'current_price': float}
        self.realized_pnl = 0.0
        self.total_commission = 0.0
        
        self.logger.info(f"Portfolio Value Tracker initialized with ${initial_capital:,.2f}")
    
    def update_cash(self, new_cash: float):
        """Update cash balance"""
        old_cash = self.current_cash
        self.current_cash = new_cash
        self.logger.info(f"Cash updated: ${old_cash:.2f} → ${new_cash:.2f}")
    
    def add_position(self, symbol: str, size: float, entry_price: float, commission: float = 0.0):
        """Add or update a position"""
        self.positions[symbol] = {
            'size': size,
            'entry_price': entry_price,
            'current_price': entry_price,
            'commission': commission
        }
        self.total_commission += commission
        self.logger.info(f"Position added: {size} {symbol} @ {entry_price:.5f} (Commission: ${commission:.2f})")
    
    def update_position_price(self, symbol: str, current_price: float):
        """Update current price for a position"""
        if symbol in self.positions:
            old_price = self.positions[symbol]['current_price']
            self.positions[symbol]['current_price'] = current_price
            self.logger.debug(f"Position price updated: {symbol} {old_price:.5f} → {current_price:.5f}")
    
    def close_position(self, symbol: str, exit_price: float, commission: float = 0.0):
        """Close a position and calculate realized P&L"""
        if symbol not in self.positions:
            self.logger.error(f"Cannot close position {symbol} - not found")
            return 0.0
        
        position = self.positions[symbol]
        size = position['size']
        entry_price = position['entry_price']
        
        # Calculate realized P&L
        if size > 0:  # Long position
            pnl = (exit_price - entry_price) * size
        else:  # Short position
            pnl = (entry_price - exit_price) * abs(size)
        
        # Subtract commission
        pnl -= commission
        self.realized_pnl += pnl
        self.total_commission += commission
        
        # Remove position
        del self.positions[symbol]
        
        self.logger.info(f"Position closed: {size} {symbol} @ {exit_price:.5f} - P&L: ${pnl:.2f}")
        return pnl
    
    def get_unrealized_pnl(self) -> float:
        """Calculate total unrealized P&L"""
        total_unrealized = 0.0
        for symbol, position in self.positions.items():
            size = position['size']
            entry_price = position['entry_price']
            current_price = position['current_price']
            
            if size > 0:  # Long position
                unrealized = (current_price - entry_price) * size
            else:  # Short position
                unrealized = (entry_price - current_price) * abs(size)
            
            total_unrealized += unrealized
        
        return total_unrealized
    
    def get_positions_value(self) -> float:
        """Calculate total market value of all positions"""
        total_value = 0.0
        for symbol, position in self.positions.items():
            size = position['size']
            current_price = position['current_price']
            market_value = abs(size) * current_price
            total_value += market_value
        
        return total_value
    
    def get_total_portfolio_value(self) -> float:
        """Calculate total portfolio value (cash + unrealized P&L)"""
        unrealized_pnl = self.get_unrealized_pnl()
        total_value = self.current_cash + unrealized_pnl
        
        self.logger.debug(f"Portfolio calculation: Cash(${self.current_cash:.2f}) + Unrealized(${unrealized_pnl:.2f}) = ${total_value:.2f}")
        return total_value
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get comprehensive portfolio summary"""
        total_value = self.get_total_portfolio_value()
        unrealized_pnl = self.get_unrealized_pnl()
        positions_value = self.get_positions_value()
        total_return = ((total_value - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'initial_capital': self.initial_capital,
            'current_cash': self.current_cash,
            'total_value': total_value,
            'total_return': total_return,
            'unrealized_pnl': unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'positions_value': positions_value,
            'positions_count': len(self.positions),
            'total_commission': self.total_commission,
            'net_pnl': self.realized_pnl + unrealized_pnl - self.total_commission
        }
    
    def force_broker_value_update(self, broker):
        """Force broker to use correct portfolio value"""
        try:
            correct_value = self.get_total_portfolio_value()
            
            # Force update broker's internal value
            if hasattr(broker, '_value'):
                old_value = broker._value
                broker._value = correct_value
                self.logger.info(f"*** FORCED BROKER VALUE UPDATE ***")
                self.logger.info(f"  Old broker value: ${old_value:.2f}")
                self.logger.info(f"  New broker value: ${correct_value:.2f}")
                self.logger.info(f"  Value change: ${correct_value - old_value:.2f}")
                return True
            else:
                self.logger.warning("Broker does not have _value attribute")
                return False
                
        except Exception as e:
            self.logger.error(f"Error forcing broker value update: {e}")
            return False

# Global portfolio tracker instance
_global_portfolio_tracker = None

def get_portfolio_tracker(initial_capital: float = 100000.0) -> PortfolioValueTracker:
    """Get or create global portfolio tracker instance"""
    global _global_portfolio_tracker
    if _global_portfolio_tracker is None:
        _global_portfolio_tracker = PortfolioValueTracker(initial_capital)
    return _global_portfolio_tracker

def reset_portfolio_tracker():
    """Reset global portfolio tracker"""
    global _global_portfolio_tracker
    _global_portfolio_tracker = None

def force_reset_portfolio_tracker_to_100k():
    """Force reset portfolio tracker to use $100,000"""
    global _global_portfolio_tracker
    _global_portfolio_tracker = PortfolioValueTracker(100000.0)
    return _global_portfolio_tracker

if __name__ == "__main__":
    # Test portfolio value tracker
    logging.basicConfig(level=logging.INFO)
    
    tracker = PortfolioValueTracker(10000.0)
    
    print("=== Testing Portfolio Value Tracker ===")
    print(f"Initial: {tracker.get_portfolio_summary()}")
    
    # Add position
    tracker.add_position("EUR_USD", 0.01, 1.1000, 2.50)
    tracker.update_position_price("EUR_USD", 1.1050)
    
    print(f"With position: {tracker.get_portfolio_summary()}")
    
    # Close position
    pnl = tracker.close_position("EUR_USD", 1.1050, 2.50)
    print(f"After closing: {tracker.get_portfolio_summary()}")
    print(f"Trade P&L: ${pnl:.2f}")