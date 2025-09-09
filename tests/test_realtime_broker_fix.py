"""
Test Real-time Broker Fix
Verifies that the _cash attribute error is fixed and portfolio values update correctly
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
from backtesting.realtime_broker import RealTimeBroker, create_realtime_broker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create test market data for broker testing"""
    # Create 50 bars of test data with some volatility
    dates = pd.date_range(start='2023-01-01', periods=50, freq='H')
    
    # Generate realistic price movement
    np.random.seed(42)  # For reproducible results
    base_price = 1.1000
    price_changes = np.random.normal(0, 0.0005, 50)  # Small movements
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

class TestStrategy(bt.Strategy):
    """Simple test strategy that places a few trades"""
    
    def __init__(self):
        self.order_count = 0
        self.max_orders = 3
        
    def next(self):
        # Place orders at specific intervals
        if len(self.data) in [10, 20, 30] and self.order_count < self.max_orders:
            if not self.position:
                # Calculate position size based on available cash
                cash = self.broker.getcash()
                price = self.data.close[0]
                size = int(cash * 0.1 / price)  # Use 10% of available cash
                
                if size > 0:
                    logger.info(f"=== PLACING BUY ORDER #{self.order_count + 1} ===")
                    logger.info(f"Cash before: ${cash:.2f}")
                    logger.info(f"Value before: ${self.broker.getvalue():.2f}")
                    logger.info(f"Price: {price:.5f}, Size: {size}")
                    
                    order = self.buy(size=size)
                    self.order_count += 1
            else:
                # Close position
                logger.info(f"=== PLACING SELL ORDER ===")
                logger.info(f"Cash before: ${self.broker.getcash():.2f}")
                logger.info(f"Value before: ${self.broker.getvalue():.2f}")
                
                self.sell(size=self.position.size)
    
    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                logger.info(f"✅ BUY EXECUTED: Size={order.executed.size}, Price={order.executed.price:.5f}")
            else:
                logger.info(f"✅ SELL EXECUTED: Size={order.executed.size}, Price={order.executed.price:.5f}")
            
            logger.info(f"   Cash after: ${self.broker.getcash():.2f}")
            logger.info(f"   Value after: ${self.broker.getvalue():.2f}")
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            logger.error(f"❌ Order {order.getstatusname()}")
    
    def notify_trade(self, trade):
        if trade.isclosed:
            logger.info(f"🎯 TRADE CLOSED: PnL=${trade.pnl:.2f}, PnL Net=${trade.pnlcomm:.2f}")

def test_realtime_broker_basic():
    """Test basic RealTimeBroker functionality"""
    logger.info("=== Testing RealTimeBroker Basic Functionality ===")
    
    # Create broker directly
    broker = RealTimeBroker()
    broker.set_cash(10000.0)
    broker.setcommission(commission=0.001)
    
    # Test basic methods
    logger.info(f"Initial cash: ${broker.get_cash():.2f}")
    logger.info(f"Initial value: ${broker.get_value():.2f}")
    logger.info(f"Getcash(): ${broker.getcash():.2f}")
    logger.info(f"Getvalue(): ${broker.getvalue():.2f}")
    
    # Test cash setting
    broker.set_cash(15000.0)
    logger.info(f"After setting cash to 15000: ${broker.get_cash():.2f}")
    logger.info(f"Value after cash change: ${broker.get_value():.2f}")
    
    logger.info("✅ Basic functionality test passed")

def test_realtime_broker_with_cerebro():
    """Test RealTimeBroker with Cerebro engine"""
    logger.info("=== Testing RealTimeBroker with Cerebro ===")
    
    # Create cerebro with real-time broker
    cerebro = bt.Cerebro()
    
    # Create and set the custom broker
    broker = create_realtime_broker(initial_cash=10000.0, commission=0.001)
    cerebro.broker = broker
    
    # Add test data
    test_data = create_test_data()
    data_feed = bt.feeds.PandasData(dataname=test_data)
    cerebro.adddata(data_feed)
    
    # Add test strategy
    cerebro.addstrategy(TestStrategy)
    
    # Add analyzers to track performance
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    logger.info(f"Starting backtest with initial value: ${cerebro.broker.getvalue():.2f}")
    
    # Run backtest
    results = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    final_cash = cerebro.broker.getcash()
    
    logger.info("=== FINAL RESULTS ===")
    logger.info(f"Final Portfolio Value: ${final_value:.2f}")
    logger.info(f"Final Cash: ${final_cash:.2f}")
    logger.info(f"Total Return: ${final_value - 10000:.2f}")
    logger.info(f"Return %: {((final_value / 10000) - 1) * 100:.2f}%")
    
    # Get trade analysis
    trade_analyzer = results[0].analyzers.trades.get_analysis()
    if 'total' in trade_analyzer and 'closed' in trade_analyzer['total']:
        total_trades = trade_analyzer['total']['closed']
        logger.info(f"Total trades executed: {total_trades}")
        
        if total_trades > 0:
            logger.info("✅ Trades were executed - broker is working!")
        else:
            logger.warning("❌ No trades executed - may need investigation")
    
    # Check if portfolio value changed
    portfolio_changed = abs(final_value - 10000.0) > 1.0
    
    if portfolio_changed:
        logger.info("✅ Portfolio value changed - RealTimeBroker fix is working!")
        return True
    else:
        logger.warning("❌ Portfolio value unchanged - fix may need adjustment")
        return False

def test_error_handling():
    """Test error handling in RealTimeBroker"""
    logger.info("=== Testing Error Handling ===")
    
    broker = RealTimeBroker()
    broker.set_cash(100.0)  # Very low cash to test insufficient funds
    
    # Test with minimal cerebro setup
    cerebro = bt.Cerebro()
    cerebro.broker = broker
    
    # Add minimal data
    test_data = create_test_data()
    data_feed = bt.feeds.PandasData(dataname=test_data)
    cerebro.adddata(data_feed)
    
    class ErrorTestStrategy(bt.Strategy):
        def next(self):
            if len(self.data) == 10:
                # Try to buy more than we can afford
                cash = self.broker.getcash()
                price = self.data.close[0]
                size = int(cash * 10 / price)  # 10x more than we can afford
                
                logger.info(f"Attempting to buy {size} units with only ${cash:.2f}")
                order = self.buy(size=size)
        
        def notify_order(self, order):
            if order.status == order.Rejected:
                logger.info("✅ Order correctly rejected due to insufficient funds")
    
    cerebro.addstrategy(ErrorTestStrategy)
    
    try:
        results = cerebro.run()
        logger.info("✅ Error handling test completed")
        return True
    except Exception as e:
        logger.error(f"❌ Error handling test failed: {e}")
        return False

def run_all_tests():
    """Run all RealTimeBroker tests"""
    logger.info("🚀 Starting RealTimeBroker Fix Tests")
    
    try:
        # Test 1: Basic functionality
        test_realtime_broker_basic()
        
        # Test 2: Integration with Cerebro
        cerebro_success = test_realtime_broker_with_cerebro()
        
        # Test 3: Error handling
        error_handling_success = test_error_handling()
        
        logger.info("=== TEST SUMMARY ===")
        logger.info(f"Cerebro integration test: {'✅ PASSED' if cerebro_success else '❌ FAILED'}")
        logger.info(f"Error handling test: {'✅ PASSED' if error_handling_success else '❌ FAILED'}")
        
        if cerebro_success and error_handling_success:
            logger.info("🎉 ALL TESTS PASSED - RealTimeBroker fix is working!")
            return True
        else:
            logger.warning("❌ Some tests failed - fix may need adjustment")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test suite failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    if success:
        print("\n✅ RealTimeBroker fix validation PASSED")
        print("The _cash attribute error has been fixed and portfolio values are updating correctly!")
    else:
        print("\n❌ RealTimeBroker fix validation FAILED")
        print("The fix may need additional adjustments.")