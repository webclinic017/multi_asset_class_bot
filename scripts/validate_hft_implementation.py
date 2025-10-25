"""
HFT Futures Implementation Validation Script
Comprehensive validation of all components
"""

import sys
import os
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_files():
    """Validate all required files exist"""
    logger.info("\n" + "="*80)
    logger.info("VALIDATION 1: File Structure")
    logger.info("="*80)
    
    required_files = [
        # Data loading
        ('data/futures_data_loader.py', 'Futures Data Loader'),
        
        # HFT Strategies
        ('strategies/hft_market_making_strategy.py', 'Market Making HFT'),
        ('strategies/hft_statistical_arbitrage_strategy.py', 'Statistical Arbitrage HFT'),
        ('strategies/hft_momentum_ignition_strategy.py', 'Momentum Ignition HFT'),
        ('strategies/hft_order_flow_strategy.py', 'Order Flow HFT'),
        ('strategies/production_hft_futures_strategy.py', 'Production HFT Multi-Strategy'),
        
        # Sentiment Analysis
        ('sentiment/futures_sentiment_analyzer.py', 'Futures Sentiment Analyzer'),
        
        # Setup & Testing
        ('setup_hft_futures.py', 'Setup Script'),
        ('tests/test_hft_futures_integration.py', 'Integration Tests'),
        ('RUN_HFT_FUTURES_SETUP.bat', 'Quick Start Script'),
        
        # Documentation
        ('docs/HFT_FUTURES_IMPLEMENTATION_GUIDE.md', 'Implementation Guide'),
        ('HFT_FUTURES_README.md', 'Main README'),
        
        # Existing files (should already exist)
        ('backtesting/backtest_engine.py', 'Backtest Engine'),
        ('api/main.py', 'API Backend'),
        ('frontend/src/pages/Backtesting/Backtesting.jsx', 'Frontend Backtesting Page'),
        ('database/database_manager.py', 'Database Manager'),
    ]
    
    all_exist = True
    for filepath, description in required_files:
        if os.path.exists(filepath):
            logger.info(f"✓ {description}: {filepath}")
        else:
            logger.error(f"✗ {description}: {filepath} - MISSING")
            all_exist = False
    
    return all_exist


def validate_imports():
    """Validate all imports work"""
    logger.info("\n" + "="*80)
    logger.info("VALIDATION 2: Python Imports")
    logger.info("="*80)
    
    imports = [
        ('data.futures_data_loader', 'FuturesDataLoader'),
        ('strategies.hft_market_making_strategy', 'MarketMakingHFTStrategy'),
        ('strategies.hft_statistical_arbitrage_strategy', 'StatisticalArbitrageHFTStrategy'),
        ('strategies.hft_momentum_ignition_strategy', 'MomentumIgnitionHFTStrategy'),
        ('strategies.hft_order_flow_strategy', 'OrderFlowImbalanceHFTStrategy'),
        ('strategies.production_hft_futures_strategy', 'ProductionHFTFuturesStrategy'),
        ('sentiment.futures_sentiment_analyzer', 'FuturesSentimentAnalyzer'),
        ('database.database_manager', 'DatabaseManager'),
        ('backtesting.backtest_engine', 'BacktestEngine'),
    ]
    
    all_imported = True
    for module_name, class_name in imports:
        try:
            module = __import__(module_name, fromlist=[class_name])
            cls = getattr(module, class_name)
            logger.info(f"✓ {module_name}.{class_name}")
        except Exception as e:
            logger.error(f"✗ {module_name}.{class_name} - {e}")
            all_imported = False
    
    return all_imported


def validate_dependencies():
    """Validate required Python packages"""
    logger.info("\n" + "="*80)
    logger.info("VALIDATION 3: Python Dependencies")
    logger.info("="*80)
    
    required_packages = [
        'yfinance',
        'feedparser',
        'textblob',
        'scipy',
        'numpy',
        'pandas',
        'backtrader',
        'fastapi',
        'yaml'
    ]
    
    all_installed = True
    for package in required_packages:
        try:
            __import__(package)
            logger.info(f"✓ {package}")
        except ImportError:
            logger.error(f"✗ {package} - NOT INSTALLED")
            all_installed = False
    
    if not all_installed:
        logger.warning("\nInstall missing packages with:")
        logger.warning("pip install yfinance feedparser textblob scipy")
    
    return all_installed


def validate_database():
    """Validate database structure"""
    logger.info("\n" + "="*80)
    logger.info("VALIDATION 4: Database Structure")
    logger.info("="*80)
    
    try:
        from database.database_manager import DatabaseManager
        
        db = DatabaseManager()
        
        # Check if database file exists
        if os.path.exists(db.db_path):
            logger.info(f"✓ Database file exists: {db.db_path}")
        else:
            logger.warning(f"⚠ Database file will be created: {db.db_path}")
        
        # Check tables
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = [
                'market_data',
                'strategies',
                'trading_sessions',
                'trades',
                'portfolio_snapshots'
            ]
            
            for table in required_tables:
                if table in tables:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    logger.info(f"✓ Table '{table}': {count} records")
                else:
                    logger.error(f"✗ Table '{table}': MISSING")
                    return False
        
        return True
        
    except Exception as e:
        logger.error(f"✗ Database validation error: {e}")
        return False


def validate_integration():
    """Validate component integration"""
    logger.info("\n" + "="*80)
    logger.info("VALIDATION 5: Component Integration")
    logger.info("="*80)
    
    checks = []
    
    # Check 1: Backtest engine has HFT strategies
    try:
        from backtesting.backtest_engine import BacktestEngine
        
        # Check if imports are present
        import inspect
        source = inspect.getsource(BacktestEngine)
        
        if 'ProductionHFTFuturesStrategy' in source:
            logger.info("✓ Backtest engine includes ProductionHFTFuturesStrategy")
            checks.append(True)
        else:
            logger.error("✗ Backtest engine missing ProductionHFTFuturesStrategy")
            checks.append(False)
            
    except Exception as e:
        logger.error(f"✗ Backtest engine check failed: {e}")
        checks.append(False)
    
    # Check 2: API has HFT strategy mapping
    try:
        with open('api/main.py', 'r') as f:
            api_content = f.read()
        
        if 'ProductionHFTFuturesStrategy' in api_content:
            logger.info("✓ API includes HFT strategy mapping")
            checks.append(True)
        else:
            logger.error("✗ API missing HFT strategy mapping")
            checks.append(False)
            
    except Exception as e:
        logger.error(f"✗ API check failed: {e}")
        checks.append(False)
    
    # Check 3: Frontend has futures symbols
    try:
        with open('frontend/src/pages/Backtesting/Backtesting.jsx', 'r') as f:
            frontend_content = f.read()
        
        if 'ES' in frontend_content and 'E-mini S&P 500' in frontend_content:
            logger.info("✓ Frontend includes futures symbols")
            checks.append(True)
        else:
            logger.error("✗ Frontend missing futures symbols")
            checks.append(False)
            
    except Exception as e:
        logger.error(f"✗ Frontend check failed: {e}")
        checks.append(False)
    
    return all(checks)


def main():
    """Run all validations"""
    logger.info("\n" + "="*80)
    logger.info("HFT FUTURES IMPLEMENTATION VALIDATION")
    logger.info("="*80)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    validations = [
        ("File Structure", validate_files),
        ("Python Imports", validate_imports),
        ("Dependencies", validate_dependencies),
        ("Database Structure", validate_database),
        ("Component Integration", validate_integration)
    ]
    
    results = {}
    
    for validation_name, validation_func in validations:
        try:
            results[validation_name] = validation_func()
        except Exception as e:
            logger.error(f"\n✗ {validation_name} validation crashed: {e}")
            results[validation_name] = False
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*80)
    
    for validation_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{status}: {validation_name}")
    
    total_passed = sum(results.values())
    total_validations = len(results)
    
    logger.info(f"\nOverall: {total_passed}/{total_validations} validations passed")
    
    if total_passed == total_validations:
        logger.info("\n" + "="*80)
        logger.info("🎉 ALL VALIDATIONS PASSED!")
        logger.info("="*80)
        logger.info("\nYour HFT Futures implementation is ready!")
        logger.info("\nNext steps:")
        logger.info("1. Run setup: python setup_hft_futures.py")
        logger.info("2. Start backend: python api/main.py")
        logger.info("3. Start frontend: cd frontend && npm start")
        logger.info("4. Navigate to: http://localhost:3000/backtesting")
        logger.info("="*80)
    else:
        logger.warning("\n" + "="*80)
        logger.warning(f"⚠️  {total_validations - total_passed} validation(s) failed")
        logger.warning("="*80)
        logger.warning("\nPlease review the errors above and fix them before proceeding.")
        logger.warning("="*80)
    
    return total_passed == total_validations


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)