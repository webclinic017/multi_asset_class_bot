"""
Test HFT Futures Integration
Comprehensive test of futures data, strategies, and backtesting
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from datetime import datetime
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_futures_data():
    """Test futures data availability"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Futures Data Availability")
    logger.info("="*80)
    
    from database.database_manager import DatabaseManager
    
    db = DatabaseManager()
    
    # Test symbols
    test_symbols = [
        ('ES', '1h', 'E-mini S&P 500'),
        ('CL', '1h', 'Crude Oil'),
        ('GC', '1d', 'Gold'),
        ('NG', '1h', 'Natural Gas')
    ]
    
    results = []
    for symbol, timeframe, name in test_symbols:
        df = db.get_market_data(symbol, timeframe, limit=1000)
        
        if df.empty:
            logger.warning(f"✗ {symbol} {timeframe} ({name}): NO DATA")
            results.append(False)
        else:
            logger.info(f"✓ {symbol} {timeframe} ({name}): {len(df)} records")
            logger.info(f"  Date range: {df.index.min()} to {df.index.max()}")
            results.append(True)
    
    success = all(results)
    logger.info(f"\nData Test: {'PASSED' if success else 'FAILED'}")
    return success


def test_strategy_loading():
    """Test HFT strategy loading"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: HFT Strategy Loading")
    logger.info("="*80)
    
    from database.database_manager import DatabaseManager
    
    db = DatabaseManager()
    
    # Get all HFT strategies
    all_strategies = db.get_strategies()
    hft_strategies = [s for s in all_strategies if s['strategy_type'] == 'hft']
    
    if not hft_strategies:
        logger.warning("✗ No HFT strategies found in database")
        return False
    
    logger.info(f"✓ Found {len(hft_strategies)} HFT strategies:")
    for strategy in hft_strategies:
        logger.info(f"  - {strategy['name']} ({strategy['asset_class']}, {strategy['timeframe']})")
        logger.info(f"    Parameters: {len(strategy['parameters'])} configured")
    
    logger.info(f"\nStrategy Loading Test: PASSED")
    return True


def test_backtest_integration():
    """Test backtesting integration"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Backtesting Integration")
    logger.info("="*80)
    
    try:
        from backtesting.backtest_engine import BacktestEngine
        from database.database_manager import DatabaseManager
        from data.data_feed import OANDADataFeed
        
        # Load config
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Get an HFT strategy
        db = DatabaseManager()
        all_strategies = db.get_strategies()
        hft_strategies = [s for s in all_strategies if s['strategy_type'] == 'hft']
        
        if not hft_strategies:
            logger.warning("✗ No HFT strategies available for testing")
            return False
        
        test_strategy = hft_strategies[0]
        logger.info(f"Testing with strategy: {test_strategy['name']}")
        
        # Initialize backtest engine
        data_feed = OANDADataFeed(config)
        engine = BacktestEngine(
            data_feed=data_feed,
            config=config
        )
        
        # Load futures data
        logger.info("Loading ES futures data...")
        data = engine.load_data('ES', 'futures', '1h')
        
        if data is None or data.empty:
            logger.warning("✗ Failed to load futures data for backtesting")
            return False
        
        logger.info(f"✓ Loaded {len(data)} data points for backtesting")
        
        # Add strategy
        strategy_name = 'NewMarketMakingHFTStrategy'
        strategy_params = test_strategy['parameters'].copy()
        strategy_params['printlog'] = False
        
        logger.info(f"Adding strategy: {strategy_name}")
        engine.add_strategy(strategy_name, **strategy_params)
        
        logger.info("✓ Strategy added successfully")
        logger.info("\nBacktest Integration Test: PASSED")
        return True
        
    except Exception as e:
        logger.error(f"✗ Backtest integration error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def test_sentiment_integration():
    """Test sentiment analysis integration"""
    logger.info("\n" + "="*80)
    logger.info("TEST 4: Sentiment Analysis Integration")
    logger.info("="*80)
    
    try:
        from sentiment.futures_sentiment_analyzer import (
            FuturesSentimentAnalyzer,
            CommodityNewsEventMonitor
        )
        
        # Test sentiment analyzer
        analyzer = FuturesSentimentAnalyzer()
        logger.info("✓ Sentiment analyzer initialized")
        
        # Test sentiment for a commodity
        logger.info("\nTesting sentiment analysis for CL (Crude Oil)...")
        sentiment = analyzer.get_commodity_sentiment('CL', hours_back=24)
        
        logger.info(f"  Sentiment Score: {sentiment['sentiment_score']:.2f}")
        logger.info(f"  Signal: {sentiment['signal']}")
        logger.info(f"  News Count: {sentiment['news_count']}")
        logger.info(f"  Confidence: {sentiment['confidence']:.2f}")
        logger.info(f"  Category: {sentiment['category']}")
        
        # Test news event monitor
        monitor = CommodityNewsEventMonitor()
        logger.info("\n✓ News event monitor initialized")
        
        # Check upcoming events
        upcoming = monitor.check_upcoming_events('CL', minutes_ahead=60)
        logger.info(f"  Upcoming events for CL: {len(upcoming)}")
        
        logger.info("\nSentiment Integration Test: PASSED")
        return True
        
    except Exception as e:
        logger.error(f"✗ Sentiment integration error: {e}")
        logger.warning("Note: Sentiment analysis requires feedparser and textblob")
        logger.warning("Install with: pip install feedparser textblob")
        return False


def run_all_tests():
    """Run all integration tests"""
    logger.info("\n" + "="*80)
    logger.info("HFT FUTURES INTEGRATION TEST SUITE")
    logger.info("="*80)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Futures Data", test_futures_data),
        ("Strategy Loading", test_strategy_loading),
        ("Backtest Integration", test_backtest_integration),
        ("Sentiment Integration", test_sentiment_integration)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            logger.error(f"\n✗ {test_name} test crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{status}: {test_name}")
    
    total_passed = sum(results.values())
    total_tests = len(results)
    
    logger.info(f"\nOverall: {total_passed}/{total_tests} tests passed")
    
    if total_passed == total_tests:
        logger.info("\n🎉 ALL TESTS PASSED! HFT Futures integration is ready.")
    else:
        logger.warning(f"\n⚠️  {total_tests - total_passed} test(s) failed. Please review errors above.")
    
    logger.info("="*80)
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)