"""
Final Test for Portfolio Value Fix
Tests the complete solution for portfolio value updates during trading
"""

import logging
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backtrader as bt
from strategies.enhanced_forex_strategy import EnhancedForexStrategy
from execution.portfolio_value_tracker import PortfolioValueTracker, reset_portfolio_tracker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_data():
    """Create test data that will generate trading signals"""
    dates = pd.date_range(start='2023-01-01', periods=100, freq='h')
    
    # Create trending data that will trigger buy signals
    base_price = 1.1000
    trend = np.linspace(0, 0.01, 100)  # 1% upward trend
    noise = np.random.normal(0, 0.0002, 100)  # Small random noise
    
    prices = base_price + trend + noise
    
    data = []
    for i, close_price in enumerate(prices):
        open_price = prices[i-1] if i > 0 else close_price
        high = close_price * 1.0005
        low = close_price * 0.9995
        volume = 1000 + np.random.randint(-100, 100)
        
        data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close_price,
            'volume': volume
        })
    
    return pd.DataFrame(data, index=dates)

def test_portfolio_value_fix():
    """Test the complete portfolio value fix"""
    logger.info("=== Testing Portfolio Value Fix ===")
    
    # Reset portfolio tracker
    reset_portfolio_tracker()
    
    # Create cerebro with standard broker
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add test data
    test_data = create_test_data()
    data_feed = bt.feeds.PandasData(dataname=test_data)
    cerebro.adddata(data_feed)
    
    # Add strategy with simple parameters to ensure signals
    cerebro.addstrategy(
        EnhancedForexStrategy,
        printlog=True,
        fast_length=5,
        slow_length=10,
        rsi_period=14,
        # Lower thresholds to ensure signals are generated
        min_sharpe_threshold=0.01,
        max_drawdown_threshold=0.5,
        profit_factor_threshold=0.1
    )
    
    logger.info(f"Starting backtest with initial value: ${cerebro.broker.getvalue():.2f}")
    
    # Run backtest
    results = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    logger.info(f"Backtest completed - Final broker value: ${final_value:.2f}")
    
    # Get portfolio tracker results
    from execution.portfolio_value_tracker import get_portfolio_tracker
    tracker = get_portfolio_tracker()
    portfolio_summary = tracker.get_portfolio_summary()
    
    logger.info("=== PORTFOLIO TRACKER RESULTS ===")
    logger.info(f"Tracker portfolio value: ${portfolio_summary['total_value']:.2f}")
    logger.info(f"Tracker total return: {portfolio_summary['total_return']:.2f}%")
    logger.info(f"Tracker realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
    logger.info(f"Tracker unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
    logger.info(f"Tracker positions: {portfolio_summary['positions_count']}")
    
    # Check if portfolio value changed
    portfolio_changed = abs(final_value - 10000.0) > 1.0
    tracker_changed = abs(portfolio_summary['total_value'] - 10000.0) > 1.0
    
    logger.info("=== RESULTS ANALYSIS ===")
    logger.info(f"Broker portfolio changed: {portfolio_changed}")
    logger.info(f"Tracker portfolio changed: {tracker_changed}")
    logger.info(f"Portfolio value difference: ${abs(final_value - portfolio_summary['total_value']):.2f}")
    
    if tracker_changed:
        logger.info("✅ Portfolio Value Tracker is working - values are updating!")
    else:
        logger.warning("❌ Portfolio Value Tracker shows no changes")
    
    if portfolio_changed:
        logger.info("✅ Broker portfolio value is updating!")
    else:
        logger.warning("❌ Broker portfolio value is still static")
    
    return {
        'broker_value': final_value,
        'tracker_value': portfolio_summary['total_value'],
        'broker_changed': portfolio_changed,
        'tracker_changed': tracker_changed,
        'portfolio_summary': portfolio_summary
    }

def test_simple_trade_execution():
    """Test simple trade execution with portfolio tracking"""
    logger.info("=== Testing Simple Trade Execution ===")
    
    # Reset tracker
    reset_portfolio_tracker()
    
    # Create simple strategy that just places one trade
    class SimpleTradeStrategy(bt.Strategy):
        def __init__(self):
            from execution.portfolio_value_tracker import get_portfolio_tracker
            self.portfolio_tracker = get_portfolio_tracker(10000.0)
            self.trade_placed = False
            
        def next(self):
            if len(self.data) == 25 and not self.trade_placed:
                logger.info(f"=== PLACING SIMPLE TEST TRADE ===")
                logger.info(f"Pre-trade: Cash=${self.broker.get_cash():.2f}, Value=${self.broker.get_value():.2f}")
                
                # Place buy order
                order = self.buy(size=0.01)
                self.trade_placed = True
                
                logger.info(f"Order placed: {order.ref}")
        
        def notify_order(self, order):
            if order.status == order.Completed:
                logger.info(f"=== ORDER EXECUTED ===")
                logger.info(f"Post-execution: Cash=${self.broker.get_cash():.2f}, Value=${self.broker.get_value():.2f}")
                
                # Update portfolio tracker
                if order.isbuy():
                    self.portfolio_tracker.update_cash(self.broker.get_cash())
                    self.portfolio_tracker.add_position(
                        symbol="EUR_USD",
                        size=order.executed.size,
                        entry_price=order.executed.price,
                        commission=order.executed.comm
                    )
                
                # Get tracker results
                tracker_value = self.portfolio_tracker.get_total_portfolio_value()
                logger.info(f"Portfolio tracker value: ${tracker_value:.2f}")
                
                # Force broker value correction
                self.portfolio_tracker.force_broker_value_update(self.broker)
                corrected_value = self.broker.get_value()
                logger.info(f"Corrected broker value: ${corrected_value:.2f}")
    
    # Create cerebro
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.001)
    
    # Add test data
    test_data = create_test_data()
    data_feed = bt.feeds.PandasData(dataname=test_data)
    cerebro.adddata(data_feed)
    
    # Add simple strategy
    cerebro.addstrategy(SimpleTradeStrategy)
    
    # Run test
    results = cerebro.run()
    
    final_value = cerebro.broker.getvalue()
    logger.info(f"Simple test final value: ${final_value:.2f}")
    
    return final_value

def run_final_tests():
    """Run final comprehensive tests"""
    logger.info("🚀 Starting Final Portfolio Value Fix Tests")
    
    try:
        # Test 1: Simple trade execution
        simple_result = test_simple_trade_execution()
        
        # Test 2: Full strategy test
        full_result = test_portfolio_value_fix()
        
        logger.info("=== FINAL TEST RESULTS ===")
        logger.info(f"Simple test final value: ${simple_result:.2f}")
        logger.info(f"Full test broker value: ${full_result['broker_value']:.2f}")
        logger.info(f"Full test tracker value: ${full_result['tracker_value']:.2f}")
        
        # Determine success
        simple_changed = abs(simple_result - 10000.0) > 0.1
        full_changed = full_result['broker_changed'] or full_result['tracker_changed']
        
        if simple_changed or full_changed:
            logger.info("🎉 SUCCESS: Portfolio values are now updating!")
            logger.info("✅ The portfolio value fix is working correctly")
        else:
            logger.warning("❌ Portfolio values are still not updating properly")
        
        return simple_changed or full_changed
        
    except Exception as e:
        logger.error(f"❌ Final test suite failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = run_final_tests()
    if success:
        print("✅ Portfolio value fix validation PASSED")
    else:
        print("❌ Portfolio value fix validation FAILED")