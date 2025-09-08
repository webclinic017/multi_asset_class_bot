"""
Test Real-time Broker Portfolio Value Fix
Verifies that the real-time broker properly executes orders and updates portfolio values
"""

import logging
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from backtesting.realtime_broker import create_realtime_broker
from strategies.enhanced_forex_strategy import EnhancedForexStrategy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create test market data for broker testing"""
    # Create 100 bars of test data with some volatility
    dates = pd.date_range(start='2023-01-01', periods=100, freq='H')
    
    # Generate realistic forex price movement
    np.random.seed(42)  # For reproducible results
    base_price = 1.1000
    price_changes = np.random.normal(0, 0.0005, 100)  # Small forex movements
    prices = [base_price]
    
    for change in price_changes[1:]:
        new_price = prices[-1] * (1 + change)
        prices.append(new_price)
    
    # Create OHLCV data
    data = []
    for i, price in enumerate(prices):
        high = price * (1 + abs(np.random.normal(0, 0.0002)))
        low = price * (1 - abs(np.random.normal(0, 0.0002)))
        open_price = prices[i-1] if i > 0 else price
        close_price = price
        volume = np.random.randint(1000, 5000)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_standard_broker_issue():
    """Test that shows the issue with standard backtrader broker"""
    logger.info("=== Testing Standard Broker (Shows the Problem) ===")
    
    # Create cerebro with standard broker
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add test data
    test_data = create_test_data()
    data_feed = bt.feeds.PandasData(dataname=test_data)
    cerebro.adddata(data_feed)
    
    # Add strategy with logging enabled
    cerebro.addstrategy(EnhancedForexStrategy, printlog=True, fast_length=5, slow_length=10)
    
    logger.info(f"Initial portfolio value: ${cerebro.broker.getvalue():.2f}")
    
    # Run backtest
    results = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    logger.info(f"Final portfolio value: ${final_value:.2f}")
    logger.info(f"Portfolio change: ${final_value - 10000:.2f}")
    
    return final_value

def test_realtime_broker_fix():
    """Test that shows the fix with real-time broker"""
    logger.info("=== Testing Real-time Broker (Shows the Fix) ===")
    
    # Create cerebro with real-time broker
    cerebro = bt.Cerebro()
    
    # Replace with real-time broker
    realtime_broker = create_realtime_broker(initial_cash=10000.0, commission=0.001)
    cerebro.broker = realtime_broker
    
    # Add test data
    test_data = create_test_data()
    data_feed = bt.feeds.PandasData(dataname=test_data)
    cerebro.adddata(data_feed)
    
    # Add strategy with logging enabled
    cerebro.addstrategy(EnhancedForexStrategy, printlog=True, fast_length=5, slow_length=10)
    
    logger.info(f"Initial portfolio value: ${cerebro.broker.getvalue():.2f}")
    
    # Run backtest
    results = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    logger.info(f"Final portfolio value: ${final_value:.2f}")
    logger.info(f"Portfolio change: ${final_value - 10000:.2f}")
    
    return final_value

def test_immediate_execution():
    """Test immediate order execution with real-time broker"""
    logger.info("=== Testing Immediate Order Execution ===")
    
    # Create simple test strategy that places one order
    class TestStrategy(bt.Strategy):
        def __init__(self):
            self.order_placed = False
            
        def next(self):
            if not self.order_placed and len(self.data) > 20:
                logger.info(f"Placing test order at bar {len(self.data)}")
                logger.info(f"Pre-order cash: ${self.broker.get_cash():.2f}")
                logger.info(f"Pre-order value: ${self.broker.get_value():.2f}")
                
                # Place market buy order
                order = self.buy(size=0.01, exectype=bt.Order.Market)
                self.order_placed = True
                
                logger.info(f"Order placed: {order.ref}")
                
        def notify_order(self, order):
            logger.info(f"Order notification: {order.ref} - {order.getstatusname()}")
            if order.status == order.Completed:
                logger.info(f"Order executed at: ${order.executed.price:.5f}")
                logger.info(f"Post-execution cash: ${self.broker.get_cash():.2f}")
                logger.info(f"Post-execution value: ${self.broker.get_value():.2f}")
    
    # Create cerebro with real-time broker
    cerebro = bt.Cerebro()
    realtime_broker = create_realtime_broker(initial_cash=10000.0, commission=0.001)
    cerebro.broker = realtime_broker
    
    # Add test data
    test_data = create_test_data()
    data_feed = bt.feeds.PandasData(dataname=test_data)
    cerebro.adddata(data_feed)
    
    # Add test strategy
    cerebro.addstrategy(TestStrategy)
    
    # Run test
    results = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    logger.info(f"Test completed - Final value: ${final_value:.2f}")
    
    return final_value != 10000.0  # Should be different if orders executed

def run_broker_tests():
    """Run all broker tests to verify the fix"""
    logger.info("🚀 Starting Broker Portfolio Value Fix Tests")
    
    try:
        # Test 1: Show the problem with standard broker
        standard_value = test_standard_broker_issue()
        
        # Test 2: Show the fix with real-time broker  
        realtime_value = test_realtime_broker_fix()
        
        # Test 3: Test immediate execution
        execution_test_passed = test_immediate_execution()
        
        # Compare results
        logger.info("=== TEST RESULTS COMPARISON ===")
        logger.info(f"Standard broker final value: ${standard_value:.2f}")
        logger.info(f"Real-time broker final value: ${realtime_value:.2f}")
        logger.info(f"Immediate execution test passed: {execution_test_passed}")
        
        # Determine if fix is working
        standard_changed = abs(standard_value - 10000.0) > 1.0
        realtime_changed = abs(realtime_value - 10000.0) > 1.0
        
        logger.info(f"Standard broker portfolio changed: {standard_changed}")
        logger.info(f"Real-time broker portfolio changed: {realtime_changed}")
        
        if realtime_changed:
            logger.info("✅ Real-time broker fix is working - portfolio values are updating!")
        else:
            logger.warning("❌ Real-time broker fix may need adjustment")
            
        if execution_test_passed:
            logger.info("✅ Immediate execution test passed")
        else:
            logger.warning("❌ Immediate execution test failed")
        
        logger.info("🎉 Broker tests completed!")
        
    except Exception as e:
        logger.error(f"❌ Broker test suite failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise

if __name__ == "__main__":
    run_broker_tests()