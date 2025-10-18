"""
HFT Futures Trading Setup Script
One-time setup to load futures data and populate strategies
Includes FRED and EIA fundamental data integration
"""

import sys
import os
import logging
from datetime import datetime
import yaml

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_api_keys():
    """Load API keys from existing config/config.yaml (DO NOT MODIFY CONFIG)"""
    fred_key = None
    eia_key = None
    usda_key = None
    
    try:
        config_path = 'config/config.yaml'
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Try to get FRED API key from config
            fred_key = config.get('data', {}).get('fred', {}).get('api_key')
            if fred_key:
                logger.info("✓ FRED API key loaded from config/config.yaml")
            else:
                logger.warning("⚠ FRED API key not found in config/config.yaml")
            
            # Try to get EIA API key from config
            eia_key = config.get('data', {}).get('eia', {}).get('api_key')
            if eia_key:
                logger.info("✓ EIA API key loaded from config/config.yaml")
            else:
                logger.warning("⚠ EIA API key not found in config/config.yaml")
            
            # Try to get USDA API key from config
            usda_key = config.get('data', {}).get('usda', {}).get('api_key')
            if usda_key:
                logger.info("✓ USDA API key loaded from config/config.yaml")
            else:
                logger.warning("⚠ USDA API key not found in config/config.yaml")
    
    except Exception as e:
        logger.warning(f"Could not load API keys from config: {e}")
    
    return fred_key, eia_key, usda_key


def main():
    """Main setup function"""
    logger.info("="*80)
    logger.info("HFT FUTURES TRADING SETUP")
    logger.info("="*80)
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Load API keys from existing config (DO NOT MODIFY CONFIG)
    fred_key, eia_key, usda_key = load_api_keys()
    
    logger.info("\nAPI Keys Status:")
    logger.info(f"  FRED: {'✓ Configured' if fred_key else '✗ Not configured (optional)'}")
    logger.info(f"  EIA:  {'✓ Configured' if eia_key else '✗ Not configured (optional)'}")
    logger.info(f"  USDA: {'✓ Configured' if usda_key else '✗ Not configured (optional)'}")
    
    if not (fred_key or eia_key or usda_key):
        logger.warning("\n⚠ No fundamental data API keys found")
        logger.warning("  System will work with price data only (Yahoo Finance)")
        logger.warning("  For enhanced fundamental data, add keys to config/config.yaml:")
        logger.warning("    data.fred.api_key: YOUR_FRED_KEY")
        logger.warning("    data.eia.api_key: YOUR_EIA_KEY")
        logger.warning("    data.usda.api_key: YOUR_USDA_KEY")
    
    logger.info("")
    
    # Step 1: Load futures market data
    logger.info("STEP 1: Loading Futures Market Data (with Fundamentals)")
    logger.info("-"*80)
    
    try:
        from data.futures_data_loader import FuturesDataLoader
        
        loader = FuturesDataLoader(
            fred_api_key=fred_key,
            eia_api_key=eia_key,
            usda_api_key=usda_key
        )
        
        # Load Tier 1 futures (high liquidity - best for HFT)
        logger.info("\n### Loading Tier 1 Futures (High Liquidity) ###")
        logger.info("Includes: Price data + FRED fundamentals + EIA data")
        results_tier1 = loader.load_all_futures_data(
            start_date='2024-01-01',
            end_date=datetime.now().strftime('%Y-%m-%d'),
            intervals=['1h', '1d'],
            tier_filter=1,
            include_fundamentals=True
        )
        
        # Load Tier 2 futures (medium liquidity)
        logger.info("\n### Loading Tier 2 Futures (Medium Liquidity) ###")
        logger.info("Includes: Price data + FRED fundamentals + EIA data")
        results_tier2 = loader.load_all_futures_data(
            start_date='2024-01-01',
            end_date=datetime.now().strftime('%Y-%m-%d'),
            intervals=['1h', '1d'],
            tier_filter=2,
            include_fundamentals=True
        )
        
        # Load Tier 3 futures (specialized)
        logger.info("\n### Loading Tier 3 Futures (Specialized) ###")
        logger.info("Includes: Price data only (daily)")
        results_tier3 = loader.load_all_futures_data(
            start_date='2024-01-01',
            end_date=datetime.now().strftime('%Y-%m-%d'),
            intervals=['1d'],  # Only daily for tier 3
            tier_filter=3,
            include_fundamentals=False
        )
        
        # Combine results
        all_results = {**results_tier1, **results_tier2, **results_tier3}
        
        # Generate report
        report = loader.generate_report(all_results)
        logger.info(report)
        
        logger.info("\n✓ Futures data loading completed successfully!")
        
    except Exception as e:
        logger.error(f"\n✗ Error loading futures data: {e}")
        logger.error("Please ensure yfinance is installed: pip install yfinance")
        return False
    
    # Step 2: Populate HFT strategies
    logger.info("\n" + "="*80)
    logger.info("STEP 2: Populating HFT Futures Strategies")
    logger.info("-"*80)
    
    try:
        from database.database_manager import DatabaseManager
        
        db = DatabaseManager()
        
        strategies = [
            {
                'name': 'Production HFT Futures - Multi-Strategy',
                'description': 'Production-ready HFT strategy combining market making, statistical arbitrage, momentum, and order flow strategies with sentiment analysis',
                'strategy_type': 'hft',
                'asset_class': 'futures',
                'timeframe': '1h',
                'parameters': {
                    'market_making_weight': 0.4,
                    'stat_arb_weight': 0.3,
                    'momentum_weight': 0.2,
                    'order_flow_weight': 0.1,
                    'max_position_size': 10,
                    'target_sharpe': 2.0,
                    'target_daily_return': 0.01,
                    'max_daily_loss': -0.02,
                    'max_daily_trades': 500,
                    'circuit_breaker': 0.10,
                    'use_sentiment': True,
                    'sentiment_weight': 0.3,
                    'use_news_events': True,
                    'printlog': False
                }
            },
            {
                'name': 'Market Making HFT - ES',
                'description': 'Market making strategy for E-mini S&P 500 futures - captures bid-ask spread',
                'strategy_type': 'hft',
                'asset_class': 'futures',
                'timeframe': '1h',
                'parameters': {
                    'spread_width': 0.0002,
                    'max_inventory': 10,
                    'quote_refresh_time': 5,
                    'inventory_skew_factor': 0.5,
                    'max_position_size': 10,
                    'max_daily_trades': 500,
                    'circuit_breaker': 0.05,
                    'target_sharpe': 2.0,
                    'printlog': False
                }
            },
            {
                'name': 'Statistical Arbitrage HFT - CL',
                'description': 'Statistical arbitrage strategy for Crude Oil futures - trades mean reversion',
                'strategy_type': 'hft',
                'asset_class': 'futures',
                'timeframe': '1h',
                'parameters': {
                    'lookback_period': 100,
                    'entry_threshold': 2.0,
                    'exit_threshold': 0.5,
                    'correlation_threshold': 0.7,
                    'max_position_size': 10,
                    'max_daily_trades': 500,
                    'circuit_breaker': 0.08,
                    'target_sharpe': 2.5,
                    'printlog': False
                }
            },
            {
                'name': 'Momentum Ignition HFT - GC',
                'description': 'Momentum ignition strategy for Gold futures - capitalizes on price momentum',
                'strategy_type': 'hft',
                'asset_class': 'futures',
                'timeframe': '1h',
                'parameters': {
                    'momentum_threshold': 0.001,
                    'momentum_window': 10,
                    'volume_threshold': 1.5,
                    'profit_target': 0.003,
                    'stop_loss': 0.001,
                    'max_position_size': 10,
                    'max_daily_trades': 500,
                    'circuit_breaker': 0.10,
                    'target_sharpe': 2.3,
                    'printlog': False
                }
            },
            {
                'name': 'Order Flow HFT - NG',
                'description': 'Order flow imbalance strategy for Natural Gas futures - trades order book dynamics',
                'strategy_type': 'hft',
                'asset_class': 'futures',
                'timeframe': '1h',
                'parameters': {
                    'imbalance_threshold': 0.3,
                    'depth_levels': 5,
                    'min_liquidity': 100,
                    'hold_time': 30,
                    'max_position_size': 10,
                    'max_daily_trades': 500,
                    'circuit_breaker': 0.06,
                    'target_sharpe': 1.8,
                    'printlog': False
                }
            }
        ]
        
        logger.info("Creating HFT futures strategies in database...")
        
        for strategy in strategies:
            try:
                strategy_id = db.create_strategy(
                    name=strategy['name'],
                    description=strategy['description'],
                    strategy_type=strategy['strategy_type'],
                    asset_class=strategy['asset_class'],
                    timeframe=strategy['timeframe'],
                    parameters=strategy['parameters']
                )
                logger.info(f"✓ Created: {strategy['name']} (ID: {strategy_id})")
            except Exception as e:
                logger.error(f"✗ Failed to create {strategy['name']}: {e}")
        
        # Verify
        all_strategies = db.get_strategies()
        hft_strategies = [s for s in all_strategies if s['strategy_type'] == 'hft']
        
        logger.info(f"\n✓ Strategy population completed!")
        logger.info(f"Total HFT strategies in database: {len(hft_strategies)}")
        
    except Exception as e:
        logger.error(f"\n✗ Error populating strategies: {e}")
        return False
    
    # Step 3: Verify setup
    logger.info("\n" + "="*80)
    logger.info("STEP 3: Verification")
    logger.info("-"*80)
    
    try:
        # Verify data for key symbols
        logger.info("\nVerifying futures data:")
        samples = [('ES', '1h'), ('CL', '1h'), ('GC', '1d'), ('NG', '1h')]
        
        for symbol, timeframe in samples:
            verification = loader.verify_data(symbol, timeframe)
            status_icon = "✓" if verification['status'] == 'OK' else "✗"
            logger.info(f"{status_icon} {symbol} {timeframe}: {verification.get('records', 0)} records")
        
        # Verify strategies
        logger.info("\nVerifying HFT strategies:")
        for strategy in hft_strategies[:5]:  # Show first 5
            logger.info(f"✓ {strategy['name']}")
        
        logger.info("\n" + "="*80)
        logger.info("SETUP COMPLETE!")
        logger.info("="*80)
        logger.info("\nNext steps:")
        logger.info("1. Start the backend API: python api/main.py")
        logger.info("2. Start the frontend: cd frontend && npm start")
        logger.info("3. Navigate to Backtesting page")
        logger.info("4. Select an HFT futures strategy and run a backtest")
        logger.info("\nRecommended first backtest:")
        logger.info("  - Strategy: Production HFT Futures - Multi-Strategy")
        logger.info("  - Symbol: ES (E-mini S&P 500)")
        logger.info("  - Date Range: 2024-01-01 to 2024-12-31")
        logger.info("  - Timeframe: 1h")
        logger.info("="*80)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Verification error: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)