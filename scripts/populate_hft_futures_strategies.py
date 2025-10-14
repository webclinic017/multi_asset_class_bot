"""
Populate Database with HFT Futures Strategies
Creates strategy entries in the database for all HFT futures strategies
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database_manager import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def populate_hft_strategies():
    """Populate database with HFT futures strategies"""
    db = DatabaseManager()
    
    strategies = [
        {
            'name': 'Production HFT Futures - Multi-Strategy',
            'description': 'Production-ready HFT strategy combining market making, statistical arbitrage, momentum, and order flow strategies',
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
            'description': 'Market making strategy for E-mini S&P 500 futures',
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
            'description': 'Statistical arbitrage strategy for Crude Oil futures',
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
            'description': 'Momentum ignition strategy for Gold futures',
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
            'description': 'Order flow imbalance strategy for Natural Gas futures',
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
        },
        {
            'name': 'Market Making HFT - CL',
            'description': 'Market making strategy for Crude Oil futures',
            'strategy_type': 'hft',
            'asset_class': 'futures',
            'timeframe': '1h',
            'parameters': {
                'spread_width': 0.0003,
                'max_inventory': 8,
                'quote_refresh_time': 5,
                'inventory_skew_factor': 0.5,
                'max_position_size': 8,
                'max_daily_trades': 400,
                'circuit_breaker': 0.05,
                'target_sharpe': 2.0,
                'printlog': False
            }
        },
        {
            'name': 'Momentum Ignition HFT - ES',
            'description': 'Momentum ignition strategy for E-mini S&P 500 futures',
            'strategy_type': 'hft',
            'asset_class': 'futures',
            'timeframe': '1h',
            'parameters': {
                'momentum_threshold': 0.0008,
                'momentum_window': 10,
                'volume_threshold': 1.5,
                'profit_target': 0.0025,
                'stop_loss': 0.0008,
                'max_position_size': 10,
                'max_daily_trades': 600,
                'circuit_breaker': 0.10,
                'target_sharpe': 2.5,
                'printlog': False
            }
        }
    ]
    
    logger.info("Populating HFT futures strategies...")
    
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
            logger.info(f"✓ Created strategy: {strategy['name']} (ID: {strategy_id})")
        except Exception as e:
            logger.error(f"✗ Failed to create strategy {strategy['name']}: {e}")
    
    logger.info("\nStrategy population complete!")
    
    # Verify
    all_strategies = db.get_strategies()
    hft_strategies = [s for s in all_strategies if s['strategy_type'] == 'hft']
    logger.info(f"\nTotal HFT strategies in database: {len(hft_strategies)}")
    
    for strategy in hft_strategies:
        logger.info(f"  - {strategy['name']} ({strategy['asset_class']}, {strategy['timeframe']})")


if __name__ == "__main__":
    populate_hft_strategies()