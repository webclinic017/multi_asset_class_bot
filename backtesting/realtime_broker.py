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
            
            # Update broker state
            if order.isbuy():
                # Buy order: reduce cash, increase position
                self._cash -= (value + order.executed.comm)
                self.logger.info(f"Buy execution: Cash reduced by {value + order.executed.comm:.2f}")
            else:
                # Sell order: increase cash, reduce position
                self._cash += (value - order.executed.comm)
                self.logger.info(f"Sell execution: Cash increased by {value - order.executed.comm:.2f}")
            
            # CRITICAL FIX: Force immediate portfolio value recalculation
            self._value = None  # Clear cached value
            
            # Force update of all position values
            if hasattr(self, '_positions'):
                for data_feed, position_size in self._positions.items():
                    if position_size != 0:
                        current_price = data_feed.close[0]
                        self.logger.info(f"Position update: {position_size} units @ {current_price:.5f}")
            
            # Force complete value recalculation
            new_value = self.get_value()
            
            # Double-check the calculation manually
            total_cash = self.get_cash()
            total_position_value = 0
            
            if hasattr(self, '_positions'):
                for data_feed, position_size in self._positions.items():
                    if position_size != 0:
                        current_price = data_feed.close[0]
                        position_value = position_size * current_price
                        total_position_value += position_value
                        self.logger.info(f"Position value calculation: {position_size} * {current_price:.5f} = {position_value:.2f}")
            
            manual_total = total_cash + total_position_value
            self.logger.info(f"Manual portfolio calculation: Cash({total_cash:.2f}) + Positions({total_position_value:.2f}) = {manual_total:.2f}")
            self.logger.info(f"Broker get_value() result: {new_value:.2f}")
            
            if abs(manual_total - new_value) > 0.01:
                self.logger.error(f"*** PORTFOLIO VALUE MISMATCH ***")
                self.logger.error(f"Manual calculation: {manual_total:.2f}")
                self.logger.error(f"Broker get_value(): {new_value:.2f}")
                self.logger.error(f"Difference: {abs(manual_total - new_value):.2f}")
                
                # Force the correct value
                self._value = manual_total
                self.logger.error(f"*** FORCING CORRECT PORTFOLIO VALUE: {manual_total:.2f} ***")
            
            self.execution_count += 1
            self.logger.info(f"*** IMMEDIATE EXECUTION #{self.execution_count} COMPLETED ***")
            self.logger.info(f"  Final cash: {self.get_cash():.2f}")
            self.logger.info(f"  Final value: {new_value:.2f}")
            
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
    
    def get_value(self, datas=None, mkt=False, lever=False):
        """Override get_value to ensure accurate portfolio calculation"""
        try:
            # Force recalculation of portfolio value
            value = super().get_value(datas, mkt, lever)
            
            # Debug portfolio calculation
            if hasattr(self, '_positions') and self._positions:
                total_position_value = 0
                for data, position in self._positions.items():
                    if position:
                        current_price = data.close[0] if hasattr(data, 'close') else 0
                        position_value = position * current_price
                        total_position_value += position_value
                
                calculated_value = self.get_cash() + total_position_value
                
                if abs(calculated_value - value) > 0.01:
                    self.logger.debug(f"Portfolio calculation: Cash={self.get_cash():.2f}, "
                                    f"Positions={total_position_value:.2f}, "
                                    f"Calculated={calculated_value:.2f}, "
                                    f"Broker={value:.2f}")
            
            return value
            
        except Exception as e:
            self.logger.error(f"Error calculating portfolio value: {e}")
            return super().get_value(datas, mkt, lever)

def create_realtime_broker(initial_cash=10000.0, commission=0.001):
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
    
    broker = create_realtime_broker(10000.0, 0.001)
    print(f"Broker created with cash: ${broker.get_cash():.2f}")
    print(f"Broker value: ${broker.get_value():.2f}")