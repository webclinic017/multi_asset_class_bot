"""
Real-time Broker for Immediate Order Execution
Forces immediate execution of market orders to ensure portfolio values update in real-time
"""

import backtrader as bt
import logging
from datetime import datetime

class RealTimeBroker(bt.brokers.BackBroker):
    """
    Enhanced broker that forces immediate execution of market orders
    and provides real-time portfolio value updates
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.logger.info("RealTimeBroker initialized for immediate order execution")
        
        # Initialize cash and value properly - use the parent class method
        self.cash = 100000.0  # Set initial cash
        self.value = 100000.0  # Set initial portfolio value
        
        # Track execution for debugging
        self.execution_count = 0
        self.pending_orders = []
        
    def submit(self, order, check=True):
        """Override submit to force immediate execution of market orders"""
        self.logger.info(f"=== BROKER SUBMIT CALLED ===")
        self.logger.info(f"Order ref: {order.ref}")
        self.logger.info(f"Order type: {order.ordtype}")
        self.logger.info(f"Order size: {order.size}")
        self.logger.info(f"Order price: {order.price}")
        self.logger.info(f"Is market order: {order.ordtype == bt.Order.Market}")
        
        # Call parent submit first
        result = super().submit(order)
        
        # Force immediate execution for market orders
        if order.ordtype == bt.Order.Market and order.alive():
            self.logger.info(f"*** FORCING IMMEDIATE MARKET ORDER EXECUTION ***")
            self.logger.info(f"  Order status before: {order.getstatusname()}")
            self.logger.info(f"  Broker cash before: {self.get_cash():.2f}")
            self.logger.info(f"  Broker value before: {self.get_value():.2f}")
            
            try:
                # Force execution by calling the broker's internal execution method
                self._execute_market_order_immediately(order)
                
                self.logger.info(f"  Order status after: {order.getstatusname()}")
                self.logger.info(f"  Broker cash after: {self.get_cash():.2f}")
                self.logger.info(f"  Broker value after: {self.get_value():.2f}")
                
            except Exception as e:
                self.logger.error(f"Failed to force immediate execution: {e}")
        
        return result
    
    def _execute_market_order_immediately(self, order):
        """Force immediate execution of a market order"""
        try:
            # Get current price from the data feed
            data = order.data
            if not data:
                self.logger.error("No data available for order execution")
                return
            
            # Get current price
            current_price = data.close[0]
            if current_price <= 0:
                self.logger.error(f"Invalid current price: {current_price}")
                return
            
            self.logger.info(f"Executing market order at price: {current_price:.5f}")
            
            # Calculate execution details
            size = order.size
            value = size * current_price
            
            # Check if we have enough cash for buy orders
            if order.isbuy() and value > self.get_cash():
                self.logger.error(f"Insufficient cash for buy order: {value:.2f} > {self.get_cash():.2f}")
                order.reject()
                return
            
            # Set execution details
            order.executed.price = current_price
            order.executed.size = size
            order.executed.value = value
            order.executed.comm = self.getcommissioninfo(data).getcommission(size, current_price)
            order.executed.dt = data.datetime.datetime(0)
            
            # Update order status to completed
            order.completed()
            
            # Update broker state using proper cash management
            if order.isbuy():
                # Buy order: reduce cash, increase position
                if self.cash >= (value + order.executed.comm):
                    self.cash -= (value + order.executed.comm)
                    self.logger.info(f"Buy execution: Cash reduced by {value + order.executed.comm:.2f}")
                else:
                    order.reject()
                    self.logger.error(f"Insufficient cash for buy order: {value + order.executed.comm:.2f} > {self.cash:.2f}")
                    return
            else:
                # Sell order: increase cash, reduce position (value is negative for sell orders)
                cash_change = abs(value) - order.executed.comm
                self.cash += cash_change
                self.logger.info(f"Sell execution: Cash increased by {cash_change:.2f}")
            
            # Update portfolio value
            self._update_value()
            
            self.execution_count += 1
            self.logger.info(f"*** IMMEDIATE EXECUTION #{self.execution_count} COMPLETED ***")
            self.logger.info(f"  Final cash: {self.get_cash():.2f}")
            self.logger.info(f"  Final value: {self.get_value():.2f}")
            
        except Exception as e:
            self.logger.error(f"Error in immediate execution: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def next(self):
        """Override next to ensure all pending orders are processed"""
        # Call parent next first
        result = super().next()
        
        # Force processing of any stuck orders
        if hasattr(self, '_orders'):
            stuck_orders = [o for o in self._orders if o.alive() and o.status == bt.Order.Submitted]
            if stuck_orders:
                self.logger.warning(f"Found {len(stuck_orders)} stuck orders - forcing execution")
                for order in stuck_orders:
                    if order.ordtype == bt.Order.Market:
                        self._execute_market_order_immediately(order)
        
        return result
    
    
    def _update_value(self):
        """Update the total portfolio value"""
        try:
            # Calculate total value = cash + positions value
            positions_value = 0
            if hasattr(self, 'cerebro') and self.cerebro:
                for data in self.cerebro.datas:
                    position = self.getposition(data)
                    if position.size != 0:
                        current_price = data.close[0]
                        positions_value += position.size * current_price
            
            self.value = self.cash + positions_value
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio value: {e}")

    def get_cash(self):
        """Return current cash"""
        return self.cash
    
    def get_value(self, datas=None, mkt=False, lever=False):
        """Return current portfolio value"""
        try:
            # Update value first
            self._update_value()
            return self.value
        except Exception as e:
            self.logger.error(f"Error getting portfolio value: {e}")
            return self.value
        
    def getcash(self):
        """Backtrader compatibility method"""
        return self.get_cash()
        
    def getvalue(self):
        """Backtrader compatibility method"""
        return self.get_value()
    
    def set_cash(self, cash):
        """Set cash amount"""
        self.cash = float(cash)
        self.value = self.cash  # Reset value when cash is set
        self.logger.info(f"Cash set to: ${self.cash:.2f}")

def create_realtime_broker(initial_cash=100000.0, commission=0.001):
    """
    Factory function to create a real-time broker with immediate execution
    
    Args:
        initial_cash: Initial cash amount
        commission: Commission rate
        
    Returns:
        RealTimeBroker: Configured broker instance
    """
    broker = RealTimeBroker()
    broker.set_cash(initial_cash)
    broker.setcommission(commission=commission)
    
    logger = logging.getLogger(__name__)
    logger.info(f"RealTimeBroker created with ${initial_cash:,.2f} initial cash")
    
    return broker

if __name__ == "__main__":
    # Test the real-time broker
    logging.basicConfig(level=logging.INFO)
    
    broker = create_realtime_broker(100000.0, 0.001)
    print(f"Broker created with cash: ${broker.get_cash():.2f}")
    print(f"Broker value: ${broker.get_value():.2f}")