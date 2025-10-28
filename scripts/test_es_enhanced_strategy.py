"""
Test script for ES-enhanced market making strategy vs original
Compares performance and validates improvements for high-priced ES futures
"""
import sys
import os
import logging
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager
from backtesting.realtime_backtest_engine import create_realtime_backtest_engine

def test_es_enhanced_vs_original():
    """Test ES-enhanced strategy vs original for ES futures"""
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # Test configurations
    test_configs = [
        {
            'name': 'Original Market Making (ES)',
            'strategy_class': 'MarketMakingHFTStrategy',
            'params': {
                'spread_width': 0.25,
                'max_inventory': 10,
                'inventory_rebalance_threshold': 0.8,
                'quote_refresh_time': 5,
                'min_spread': 0.25,
                'max_spread': 2.0,
                'volatility_lookback': 20,
                'risk_limit': 0.02,
                'max_orders_per_side': 3,
                'order_size': 1,
                'adaptive_spread': True,
                'printlog': True
            }
        },
        {
            'name': 'ES-Enhanced Market Making',
            'strategy_class': 'ESEnhancedMarketMakingHFTStrategy',
            'params': {
                'spread_width': 0.0001,
                'max_inventory': 2,
                'inventory_rebalance_threshold': 1,
                'quote_refresh_time': 3,
                'min_spread': 0.00005,
                'max_spread': 0.0005,
                'volatility_lookback': 10,
                'risk_limit': 0.005,
                'max_orders_per_side': 1,
                'order_size': 0.1,
                'adaptive_spread': True,
                'max_notional_exposure': 50000,
                'price_adjusted_sizing': True,
                'max_contracts': 10,
                'notional_per_trade': 5000,
                'use_regime_filter': True,
                'trend_strength_threshold': 0.2,
                'volatility_regime_threshold': 0.015,
                'min_profit_threshold': 0.0002,
                'max_holding_time': 180,
                'rebalance_frequency': 5,
                'commission_adjustment': True,
                'slippage_buffer': 0.00005,
                'printlog': True
            }
        }
    ]
    
    results = []
    
    for config in test_configs:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing: {config['name']}")
        logger.info(f"{'='*60}")
        
        # Create strategy
        strategy_id = db_manager.create_strategy(
            name=config['name'],
            description=f"Test {config['name']} strategy",
            strategy_type="hft",
            asset_class="futures",
            timeframe="1h",
            parameters=config['params']
        )
        
        # Create session
        session_id = db_manager.create_trading_session(
            session_type="backtest",
            strategy_id=strategy_id,
            symbol="ES",  # E-mini S&P 500
            initial_capital=100000.0
        )
        
        # Configuration for backtest engine
        backtest_config = {
            'backtesting': {
                'initial_capital': 100000.0,
                'commission': 0.001,
                'slippage': 0.0005,
                'start_date': '2024-01-01',
                'end_date': '2024-03-01',
                'asset_class': 'futures'
            },
            'oanda': {
                'account_id': 'test',
                'access_token': 'test',
                'practice': True
            },
            'ibkr': {
                'host': '127.0.0.1',
                'port': 7497,
                'client_id': 1
            }
        }
        
        # Create backtest engine
        backtest_engine = create_realtime_backtest_engine(
            config=backtest_config,
            session_id=session_id
        )
        
        # Load data
        logger.info(f"Loading data for ES (futures, 1h)...")
        loaded_data = backtest_engine.load_data('ES', 'futures', '1h')
        
        if loaded_data is None or loaded_data.empty:
            logger.error(f"Failed to load ES data")
            results.append({
                'name': config['name'],
                'error': 'Failed to load data',
                'final_value': 100000.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'win_rate': 0.0
            })
            continue
        
        logger.info(f"Successfully loaded {len(loaded_data)} ES data points")
        logger.info(f"ES price range: ${loaded_data['close'].min():.2f} to ${loaded_data['close'].max():.2f}")
        
        # Add strategy to engine
        backtest_engine.add_strategy(config['strategy_class'], **config['params'])
        
        # Run backtest
        logger.info("Starting ES backtest...")
        result = backtest_engine.run_with_realtime_updates()
        
        if result and isinstance(result, dict):
            logger.info(f"ES backtest completed for {config['name']}")
            
            # Extract key metrics
            final_value = result.get('final_value', 100000.0)
            total_return = result.get('total_return', 0.0)
            max_drawdown = result.get('max_drawdown', 0.0)
            total_trades = result.get('total_trades', 0)
            win_rate = result.get('win_rate', 0.0)
            
            results.append({
                'name': config['name'],
                'final_value': final_value,
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'total_trades': total_trades,
                'win_rate': win_rate,
                'sharpe_ratio': result.get('sharpe_ratio', 0.0),
                'avg_win': result.get('avg_win', 0.0),
                'avg_loss': result.get('avg_loss', 0.0),
                'profit_factor': result.get('profit_factor', 0.0)
            })
            
            logger.info(f"Results for {config['name']}:")
            logger.info(f"  Final Value: ${final_value:.2f}")
            logger.info(f"  Total Return: {total_return:.2f}%")
            logger.info(f"  Max Drawdown: {max_drawdown:.2f}%")
            logger.info(f"  Total Trades: {total_trades}")
            logger.info(f"  Win Rate: {win_rate:.1f}%")
            
            # Check for catastrophic loss
            if total_return < -50:
                logger.error(f"🚨 CATASTROPHIC LOSS DETECTED: {total_return:.2f}% 🚨")
            elif max_drawdown > 100:
                logger.error(f"🚨 EXCESSIVE DRAWDOWN DETECTED: {max_drawdown:.2f}% 🚨")
                
        else:
            logger.error(f"ES backtest failed for {config['name']}")
            results.append({
                'name': config['name'],
                'error': 'Backtest failed',
                'final_value': 100000.0,
                'total_return': 0.0,
                'max_drawdown': 0.0,
                'total_trades': 0,
                'win_rate': 0.0
            })
    
    # Compare results
    logger.info(f"\n{'='*60}")
    logger.info("ES PERFORMANCE COMPARISON")
    logger.info(f"{'='*60}")
    
    if len(results) == 2:
        original = results[0]
        enhanced = results[1]
        
        logger.info(f"Original Strategy (ES):")
        logger.info(f"  Final Value: ${original['final_value']:.2f}")
        logger.info(f"  Total Return: {original['total_return']:.2f}%")
        logger.info(f"  Max Drawdown: {original['max_drawdown']:.2f}%")
        logger.info(f"  Total Trades: {original['total_trades']}")
        logger.info(f"  Win Rate: {original['win_rate']:.1f}%")
        
        logger.info(f"\nES-Enhanced Strategy:")
        logger.info(f"  Final Value: ${enhanced['final_value']:.2f}")
        logger.info(f"  Total Return: {enhanced['total_return']:.2f}%")
        logger.info(f"  Max Drawdown: {enhanced['max_drawdown']:.2f}%")
        logger.info(f"  Total Trades: {enhanced['total_trades']}")
        logger.info(f"  Win Rate: {enhanced['win_rate']:.1f}%")
        
        # Calculate improvements
        return_improvement = enhanced['total_return'] - original['total_return']
        drawdown_improvement = original['max_drawdown'] - enhanced['max_drawdown']
        value_improvement = enhanced['final_value'] - original['final_value']
        
        logger.info(f"\nES Improvements:")
        logger.info(f"  Return Improvement: {return_improvement:+.2f}%")
        logger.info(f"  Drawdown Reduction: {drawdown_improvement:+.2f}%")
        logger.info(f"  Value Improvement: ${value_improvement:+.2f}")
        
        # Determine winner
        if enhanced['total_return'] > original['total_return'] and enhanced['max_drawdown'] <= original['max_drawdown']:
            logger.info(f"\n🏆 ES-ENHANCED STRATEGY WINS! 🏆")
            logger.info("Better returns with equal or lower risk")
        elif enhanced['total_return'] > original['total_return']:
            logger.info(f"\n📈 ES-ENHANCED has better returns")
        elif enhanced['max_drawdown'] < original['max_drawdown']:
            logger.info(f"\n🛡️ ES-ENHANCED has lower risk")
        else:
            logger.info(f"\n⚖️ Strategies have trade-offs")
    
    return results

if __name__ == "__main__":
    print("Testing ES-enhanced vs original market making strategy...")
    results = test_es_enhanced_vs_original()
    
    if results:
        print(f"\nFinal result comparison:")
        for result in results:
            print(f"- {result['name']}: {result.get('total_return', 0):.2f}% return, "
                  f"{result.get('max_drawdown', 0):.2f}% max drawdown")
    else:
        print("Test failed")