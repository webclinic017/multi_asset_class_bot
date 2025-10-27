#!/usr/bin/env python3
"""
Force reset all portfolio trackers and verify $100,000 initial capital
Run this script to clear any cached instances and ensure $100,000 is used
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def force_reset_all_capital():
    """Force reset all capital references to $100,000"""
    print("=== FORCING RESET TO $100,000 INITIAL CAPITAL ===")
    
    # Reset portfolio tracker
    from execution.portfolio_value_tracker import reset_portfolio_tracker, get_portfolio_tracker
    print("1. Resetting portfolio tracker...")
    reset_portfolio_tracker()
    
    # Create new tracker with $100,000
    tracker = get_portfolio_tracker(100000.0)
    print(f"   ✓ New Portfolio Tracker Initial Capital: ${tracker.initial_capital:,}")
    
    # Test broker creation
    print("2. Testing broker creation...")
    from backtesting.enhanced_realtime_broker import create_enhanced_realtime_broker
    broker = create_enhanced_realtime_broker(100000.0, symbol='EUR_USD')
    print(f"   ✓ Enhanced Broker Cash: ${broker.get_cash():,}")
    print(f"   ✓ Enhanced Broker Value: ${broker.get_value():,}")
    
    # Test strategy loading
    print("3. Testing strategy loading...")
    from strategies.enhanced_forex_strategy import EnhancedForexStrategy
    print("   ✓ Enhanced Forex Strategy loaded")
    
    print("\n=== RESET COMPLETE ===")
    print("All components should now use $100,000 initial capital")
    print("Restart the web server to see the changes in logs")
    
    return True

if __name__ == "__main__":
    force_reset_all_capital()