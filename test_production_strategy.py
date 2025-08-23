#!/usr/bin/env python3
"""
Test script for ProductionQuantCryptoStrategy
Tests the production-optimized strategy to ensure it works without backtrader array index errors
"""

import sys
import os
import logging
import yaml
from datetime import datetime, timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backtesting.backtest_engine import BacktestEngine
from data.kraken_feed import KrakenDataFeed

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/test_production_strategy.log')
        ]
    )

def load_config():
    """Load configuration from config.yaml"""
    try:
        with open('config/config.yaml', 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        return None

def test_production_strategy():
    """Test the ProductionQuantCryptoStrategy with 5 years of data"""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=== TESTING PRODUCTION QUANT CRYPTO STRATEGY ===")
    
    # Load configuration
    config = load_config()
    if not config:
        logger.error("Failed to load configuration")
        return False
    
    # Override backtest dates to use 5 years of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)  # 5 years
    
    config['backtesting'] = {
        'initial_capital': 10000,
        'commission': 0.001,
        'slippage': 0.0005,
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d')
    }
    
    logger.info(f"Testing with date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    try:
        # Initialize Kraken data feed
        kraken_feed = KrakenDataFeed(config)
        
        # Initialize backtest engine
        engine = BacktestEngine(data_feed=kraken_feed, config=config)
        
        # Test symbols
        test_symbols = [
            {'name': 'SOL/USD', 'type': 'crypto', 'timeframe': '1h'},
            {'name': 'BTC/USD', 'type': 'crypto', 'timeframe': '1h'},
            {'name': 'ETH/USD', 'type': 'crypto', 'timeframe': '1h'}
        ]
        
        success_count = 0
        total_tests = len(test_symbols)
        
        for symbol_config in test_symbols:
            symbol = symbol_config['name']
            asset_type = symbol_config['type']
            timeframe = symbol_config['timeframe']
            
            logger.info(f"\n--- Testing {symbol} ---")
            
            try:
                # Create fresh cerebro instance
                import backtrader as bt
                engine.cerebro = bt.Cerebro()
                engine.cerebro.broker.setcash(engine.initial_capital)
                engine.cerebro.broker.setcommission(commission=engine.commission)
                engine.cerebro.broker.set_slippage_perc(perc=engine.slippage)
                
                # Load data
                data = engine.load_data(symbol, asset_type, timeframe)
                if data is None or data.empty:
                    logger.error(f"Failed to load data for {symbol}")
                    continue
                
                logger.info(f"Loaded {len(data)} data points for {symbol}")
                
                # Get strategy configuration
                strategy_config = config.get('strategies', {}).get('crypto', {})
                strategy_name = strategy_config.get('name', 'ProductionQuantCryptoStrategy')
                strategy_params = strategy_config.get('params', {}).copy()
                
                # Ensure we're using the production strategy
                if strategy_name != 'ProductionQuantCryptoStrategy':
                    logger.warning(f"Config uses {strategy_name}, forcing ProductionQuantCryptoStrategy")
                    strategy_name = 'ProductionQuantCryptoStrategy'
                
                # Disable logging for cleaner output
                strategy_params['printlog'] = False
                
                logger.info(f"Adding strategy: {strategy_name}")
                logger.info(f"Strategy parameters: {len(strategy_params)} params configured")
                
                # Add strategy
                engine.add_strategy(strategy_name, **strategy_params)
                
                # Run backtest
                logger.info(f"Running backtest for {symbol}...")
                results = engine.run()
                
                if results and isinstance(results, dict):
                    logger.info(f"✅ SUCCESS: {symbol} backtest completed")
                    logger.info(f"   Final Value: ${results['final_value']:.2f}")
                    logger.info(f"   Total Return: {results['total_return']:.2f}%")
                    logger.info(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
                    logger.info(f"   Max Drawdown: {results['max_drawdown']:.2f}%")
                    logger.info(f"   Total Trades: {results['total_trades']}")
                    success_count += 1
                else:
                    logger.error(f"❌ FAILED: {symbol} - No valid results returned")
                
            except Exception as e:
                logger.error(f"❌ FAILED: {symbol} - Error: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Summary
        logger.info(f"\n=== TEST SUMMARY ===")
        logger.info(f"Successful tests: {success_count}/{total_tests}")
        logger.info(f"Success rate: {(success_count/total_tests)*100:.1f}%")
        
        if success_count == total_tests:
            logger.info("🎉 ALL TESTS PASSED - ProductionQuantCryptoStrategy is working correctly!")
            return True
        elif success_count > 0:
            logger.warning(f"⚠️  PARTIAL SUCCESS - {success_count} out of {total_tests} tests passed")
            return True
        else:
            logger.error("❌ ALL TESTS FAILED - Strategy needs further debugging")
            return False
            
    except Exception as e:
        logger.error(f"Critical error in test setup: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_production_strategy()
    sys.exit(0 if success else 1)