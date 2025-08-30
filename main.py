"""
Main Script to Run the Trading Bot

This script orchestrates the entire trading bot, including:
- Loading configuration
- Setting up logging
- Initializing data feeds, strategies, execution, and risk management components
- Running backtests or live trading
- Optimizing strategy parameters
"""

import logging
import yaml
import os
import argparse
from dotenv import load_dotenv # Import load_dotenv
import re # Import re for environment variable substitution

# Apply compatibility patches before importing other modules
try:
    from utils.startup_patch import apply_startup_patches
    apply_startup_patches()
except ImportError:
    # Fallback if startup_patch is not available
    try:
        from utils.talib_compatibility_patch import patch_talib_for_backtrader
        patch_talib_for_backtrader()
    except ImportError:
        pass

# Configure Plotly for VS Code
try:
    from utils.vscode_plotly_fix import setup_plotly_for_vscode
    setup_plotly_for_vscode()
except ImportError:
    pass

# Import modules from our trading bot structure
from utils.logger import setup_logging
from data.data_feed import OANDADataFeed, CCXTDataFeed, IBKRDataFeed
from data.preprocessing import DataPreprocessor
from strategies.forex_strategy import ForexStrategy
from strategies.crypto_strategy import CryptoStrategy
from strategies.futures_strategy import FuturesStrategy
from execution.order_manager import OrderManager
from execution.broker_connect import OANDABrokerConnector, CCXTBrokerConnector, IBKRBrokerConnector
from risk.risk_manager import RiskManager
from backtesting.backtest_engine import BacktestEngine
from optimization.optimizer import Optimizer
import backtrader as bt
import numpy as np

# Global logger
logger = logging.getLogger(__name__)

# Enhanced Backtesting Classes (defined early for use in functions)

class EnhancedBacktestEngine:
    """Enhanced backtesting engine with trade signals tracking and visualization."""
    
    def __init__(self, data_feed=None, preprocessor=None, risk_manager=None, config=None):
        """Initialize the enhanced backtest engine."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.data_feed = data_feed
        self.preprocessor = preprocessor or DataPreprocessor()
        self.risk_manager = risk_manager
        
        # Initialize backtest engine
        self.base_engine = BacktestEngine(data_feed, preprocessor, risk_manager, config)
        
        # Enhanced tracking
        self.trade_signals = []
        self.portfolio_values = []
        self.drawdown_series = []
        self.signal_stats = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'successful_signals': 0,
            'signal_accuracy': 0.0,
            'signals_per_day': 0.0
        }
    
    def load_data_with_signals(self, symbol, asset_type, timeframe):
        """Load data and prepare for signal tracking."""
        return self.base_engine.load_data(symbol, asset_type, timeframe)
    
    def run_enhanced_backtest(self, strategy_name, **kwargs):
        """Run backtest with enhanced signal tracking."""
        from datetime import datetime, timedelta
        
        # Add signal tracking analyzer
        self.base_engine.cerebro.addanalyzer(SignalTrackingAnalyzer, _name='signal_tracker')
        # Only add TimeReturn analyzer if we expect trades
        try:
            self.base_engine.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name='time_return')
        except:
            pass
        self.base_engine.cerebro.addanalyzer(bt.analyzers.SQN, _name='sqn')
        
        # Add strategy (remove track_signals as it's not a valid parameter)
        if 'track_signals' in kwargs:
            del kwargs['track_signals']
        self.base_engine.add_strategy(strategy_name, **kwargs)
        
        # Run the backtest with error handling
        try:
            results = self.base_engine.run()
        except ZeroDivisionError as e:
            self.logger.warning(f"Division by zero in backtest (likely no trades): {e}")
            # Create minimal results for no-trade scenario
            results = {
                'final_value': self.base_engine.initial_capital,
                'initial_capital': self.base_engine.initial_capital,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0,
                'total_return': 0.0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0
            }
        
        if results:
            # Try to get the strategy instance for signal data
            try:
                strategies = self.base_engine.cerebro.run()
                if strategies:
                    strategy = strategies[0]
                    
                    # Extract signal data from analyzer
                    if hasattr(strategy.analyzers, 'signal_tracker'):
                        signal_data = strategy.analyzers.signal_tracker.get_analysis()
                        self.trade_signals = signal_data.get('signals', [])
                        
                        # Calculate signal statistics
                        self._calculate_signal_statistics()
                        results['signal_stats'] = self.signal_stats
                        results['trade_signals'] = self.trade_signals
                    
                    # Calculate additional metrics
                    results.update(self._calculate_enhanced_metrics(strategy))
            except Exception as e:
                self.logger.warning(f"Error extracting strategy data: {e}")
                # Add default signal stats
                results['signal_stats'] = self.signal_stats
                results['trade_signals'] = []
        
        return results
    
    def run_enhanced_multi_asset_backtest(self, symbols_config):
        """Run enhanced multi-asset backtest."""
        all_results = {}
        
        for symbol_config in symbols_config:
            symbol = symbol_config['name']
            asset_type = symbol_config['type']
            timeframe = symbol_config['timeframe']
            
            self.logger.info(f"Running enhanced backtest for {symbol} ({asset_type})")
            
            try:
                # Create new engine instance for each asset
                engine = EnhancedBacktestEngine(
                    data_feed=self.data_feed,
                    preprocessor=self.preprocessor,
                    risk_manager=self.risk_manager,
                    config=self.config
                )
                
                # Load data
                data = engine.load_data_with_signals(symbol, asset_type, timeframe)
                if data is None or data.empty:
                    continue
                
                # Get strategy configuration
                if asset_type == 'forex':
                    strategy_config = self.config.get('strategies', {}).get('forex', {})
                    strategy_name = strategy_config.get('name', 'ForexStrategy')
                    strategy_params = strategy_config.get('params', {}).copy()
                elif asset_type == 'crypto':
                    strategy_config = self.config.get('strategies', {}).get('crypto', {})
                    strategy_name = strategy_config.get('name', 'ProductionQuantCryptoStrategy')
                    strategy_params = strategy_config.get('params', {}).copy()
                else:
                    continue
                
                if strategy_params is None:
                    strategy_params = {}
                
                strategy_params['printlog'] = False
                
                # Run enhanced backtest
                results = engine.run_enhanced_backtest(strategy_name, **strategy_params)
                
                if results:
                    all_results[symbol] = {
                        'asset_type': asset_type,
                        'results': results
                    }
                    
            except Exception as e:
                self.logger.error(f"Error in enhanced backtest for {symbol}: {e}")
                continue
        
        if all_results:
            # Generate comparative analysis
            comparison = self._generate_comparative_analysis(all_results)
            allocation = self._calculate_optimal_allocation(all_results)
            recommendation = self._generate_trading_recommendation(all_results)
            
            return {
                'individual_results': all_results,
                'comparison': comparison,
                'allocation': allocation,
                'recommendation': recommendation,
                'report_path': self._export_enhanced_report(all_results)
            }
        
        return None
    
    def _calculate_signal_statistics(self):
        """Calculate comprehensive signal statistics."""
        if not self.trade_signals:
            return
        
        total_signals = len(self.trade_signals)
        buy_signals = sum(1 for s in self.trade_signals if s.get('signal_type') == 'BUY')
        sell_signals = sum(1 for s in self.trade_signals if s.get('signal_type') == 'SELL')
        successful_signals = sum(1 for s in self.trade_signals if s.get('profitable', False))
        
        # Calculate time span for signals per day
        if total_signals > 1:
            first_signal = min(s.get('datetime') for s in self.trade_signals if s.get('datetime'))
            last_signal = max(s.get('datetime') for s in self.trade_signals if s.get('datetime'))
            if first_signal and last_signal:
                time_span = (last_signal - first_signal).days
                signals_per_day = total_signals / max(time_span, 1)
            else:
                signals_per_day = 0
        else:
            signals_per_day = 0
        
        self.signal_stats = {
            'total_signals': total_signals,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'successful_signals': successful_signals,
            'signal_accuracy': (successful_signals / total_signals * 100) if total_signals > 0 else 0,
            'signals_per_day': signals_per_day
        }
    
    def _calculate_enhanced_metrics(self, strategy):
        """Calculate additional performance metrics."""
        enhanced_metrics = {}
        
        try:
            # Get time return analyzer data
            if hasattr(strategy.analyzers, 'time_return'):
                time_returns = strategy.analyzers.time_return.get_analysis()
                returns_series = list(time_returns.values())
                
                if returns_series:
                    # Annualized return
                    total_return = (strategy.broker.get_value() / self.base_engine.initial_capital - 1) * 100
                    days = len(returns_series)
                    annualized_return = ((1 + total_return/100) ** (365/days) - 1) * 100 if days > 0 else 0
                    
                    # Sortino ratio (downside deviation)
                    negative_returns = [r for r in returns_series if r < 0]
                    if negative_returns:
                        downside_deviation = np.std(negative_returns) * np.sqrt(252)
                        sortino_ratio = (annualized_return - 2) / downside_deviation if downside_deviation > 0 else 0
                    else:
                        sortino_ratio = float('inf') if annualized_return > 2 else 0
                    
                    # Calmar ratio
                    max_dd = strategy.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0)
                    calmar_ratio = annualized_return / abs(max_dd * 100) if max_dd != 0 else 0
                    
                    # Expectancy
                    trade_analysis = strategy.analyzers.trade_analyzer.get_analysis()
                    total_trades = trade_analysis.get('total', {}).get('closed', 0)
                    if total_trades > 0:
                        avg_win = trade_analysis.get('won', {}).get('pnl', {}).get('average', 0) or 0
                        avg_loss = trade_analysis.get('lost', {}).get('pnl', {}).get('average', 0) or 0
                        win_rate = trade_analysis.get('won', {}).get('total', 0) / total_trades
                        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
                    else:
                        expectancy = 0
                    
                    enhanced_metrics.update({
                        'annualized_return': annualized_return,
                        'sortino_ratio': sortino_ratio,
                        'calmar_ratio': calmar_ratio,
                        'expectancy': expectancy
                    })
            
            # SQN (System Quality Number)
            if hasattr(strategy.analyzers, 'sqn'):
                sqn_analysis = strategy.analyzers.sqn.get_analysis()
                enhanced_metrics['sqn'] = sqn_analysis.get('sqn', 0)
                
        except Exception as e:
            self.logger.warning(f"Error calculating enhanced metrics: {e}")
        
        return enhanced_metrics
    
    def _generate_comparative_analysis(self, all_results):
        """Generate comparative analysis across assets."""
        comparison = {
            'best_asset': None,
            'best_return': -float('inf'),
            'best_sharpe': -float('inf'),
            'forex': {'assets': [], 'avg_score': 0},
            'crypto': {'assets': [], 'avg_score': 0},
            'confidence': 0
        }
        
        forex_scores = []
        crypto_scores = []
        
        for symbol, data in all_results.items():
            results = data['results']
            asset_type = data['asset_type']
            
            # Calculate composite score
            score = (
                results['total_return'] * 0.3 +
                results['sharpe_ratio'] * 20 * 0.3 +
                results['win_rate'] * 0.2 +
                (100 - abs(results['max_drawdown'])) * 0.2
            )
            
            if asset_type == 'forex':
                forex_scores.append(score)
                comparison['forex']['assets'].append(symbol)
            else:
                crypto_scores.append(score)
                comparison['crypto']['assets'].append(symbol)
            
            # Track best performers
            if results['total_return'] > comparison['best_return']:
                comparison['best_return'] = results['total_return']
                comparison['best_asset'] = symbol
            
            if results['sharpe_ratio'] > comparison['best_sharpe']:
                comparison['best_sharpe'] = results['sharpe_ratio']
        
        # Calculate average scores
        if forex_scores:
            comparison['forex']['avg_score'] = np.mean(forex_scores)
        if crypto_scores:
            comparison['crypto']['avg_score'] = np.mean(crypto_scores)
        
        # Calculate confidence based on score difference
        if forex_scores and crypto_scores:
            score_diff = abs(comparison['forex']['avg_score'] - comparison['crypto']['avg_score'])
            comparison['confidence'] = min(score_diff * 2, 100)
        
        return comparison
    
    def _calculate_optimal_allocation(self, all_results):
        """Calculate optimal asset allocation."""
        forex_performance = []
        crypto_performance = []
        
        for symbol, data in all_results.items():
            results = data['results']
            asset_type = data['asset_type']
            
            # Risk-adjusted performance score
            risk_adj_score = results['sharpe_ratio'] * results['total_return'] / max(abs(results['max_drawdown']), 1)
            
            if asset_type == 'forex':
                forex_performance.append(risk_adj_score)
            else:
                crypto_performance.append(risk_adj_score)
        
        forex_avg = np.mean(forex_performance) if forex_performance else 0
        crypto_avg = np.mean(crypto_performance) if crypto_performance else 0
        total_score = forex_avg + crypto_avg
        
        if total_score > 0:
            forex_allocation = (forex_avg / total_score) * 100
            crypto_allocation = (crypto_avg / total_score) * 100
        else:
            forex_allocation = crypto_allocation = 50
        
        return {
            'forex_allocation': forex_allocation,
            'crypto_allocation': crypto_allocation,
            'reasoning': f"Based on risk-adjusted performance: Forex avg={forex_avg:.2f}, Crypto avg={crypto_avg:.2f}"
        }
    
    def _generate_trading_recommendation(self, all_results):
        """Generate trading recommendations."""
        forex_metrics = []
        crypto_metrics = []
        
        for symbol, data in all_results.items():
            results = data['results']
            asset_type = data['asset_type']
            
            if asset_type == 'forex':
                forex_metrics.append(results)
            else:
                crypto_metrics.append(results)
        
        # Determine primary focus
        forex_score = np.mean([r['sharpe_ratio'] * r['total_return'] for r in forex_metrics]) if forex_metrics else 0
        crypto_score = np.mean([r['sharpe_ratio'] * r['total_return'] for r in crypto_metrics]) if crypto_metrics else 0
        
        if forex_score > crypto_score:
            primary_focus = 'forex'
            next_trade_asset = 'forex'
        else:
            primary_focus = 'crypto'
            next_trade_asset = 'crypto'
        
        return {
            'primary_focus': primary_focus,
            'next_trade_asset': next_trade_asset,
            'confidence_score': abs(forex_score - crypto_score)
        }
    
    def _export_enhanced_report(self, all_results):
        """Export detailed analysis report."""
        import json
        from datetime import datetime
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'backtest_type': 'enhanced_multi_asset',
            'results': {}
        }
        
        for symbol, data in all_results.items():
            report_data['results'][symbol] = {
                'asset_type': data['asset_type'],
                'performance_metrics': data['results'],
                'signal_statistics': data['results'].get('signal_stats', {})
            }
        
        # Save report
        os.makedirs('backtest_reports', exist_ok=True)
        report_path = f"backtest_reports/enhanced_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2, default=str)
        
        return report_path

class SignalTrackingAnalyzer(bt.Analyzer):
    """Custom analyzer to track trading signals."""
    
    def __init__(self):
        super(SignalTrackingAnalyzer, self).__init__()
        self.signals = []
    
    def start(self):
        """Called when the strategy starts."""
        pass
    
    def notify_order(self, order):
        """Track order signals."""
        try:
            if order.status in [order.Completed]:
                signal_data = {
                    'datetime': self.strategy.datas[0].datetime.datetime(0) if hasattr(self, 'strategy') else None,
                    'signal_type': 'BUY' if order.isbuy() else 'SELL',
                    'price': order.executed.price,
                    'size': order.executed.size,
                    'value': order.executed.value
                }
                self.signals.append(signal_data)
        except Exception as e:
            logger.warning(f"Error tracking signal: {e}")
    
    def notify_trade(self, trade):
        """Track trade outcomes for signal accuracy."""
        try:
            if trade.isclosed and self.signals:
                # Mark the last signal as profitable or not
                if self.signals:
                    self.signals[-1]['profitable'] = trade.pnl > 0
                    self.signals[-1]['pnl'] = trade.pnl
        except Exception as e:
            logger.warning(f"Error tracking trade outcome: {e}")
    
    def get_analysis(self):
        """Return signal analysis."""
        return {'signals': self.signals}

def load_config(config_path='config/config.yaml'):
    """
    Loads the configuration from a YAML file and substitutes environment variables.
    """
    # Load environment variables from .env file
    load_dotenv()

    def env_var_constructor(loader, node):
        """
        YAML constructor for environment variables.
        Looks for ${ENV_VAR_NAME} and replaces it with the environment variable's value.
        """
        value = loader.construct_scalar(node)
        match = re.fullmatch(r'\$\{(\w+)\}', value)
        if match:
            env_var_name = match.group(1)
            env_value = os.getenv(env_var_name)
            if env_value is None:
                logger.warning(f"Environment variable '{env_var_name}' not found. Using None.")
                return None
            # Attempt to convert to int or bool if applicable
            if env_value.lower() == 'true':
                return True
            if env_value.lower() == 'false':
                return False
            if env_value.isdigit():
                return int(env_value)
            try:
                return float(env_value)
            except ValueError:
                return env_value
        return value

    # Add the custom constructor to YAML loader
    yaml.add_constructor('!env', env_var_constructor, Loader=yaml.SafeLoader)
    yaml.add_implicit_resolver('!env', re.compile(r'\$\{\w+\}'))

    try:
        with open(config_path, 'r') as f:
            # Use the custom loader to parse YAML with environment variables
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}. Please ensure it exists.")
        exit(1)
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        exit(1)

def run_backtest_mode(config):
    """Runs the bot in enhanced backtesting mode with historic trade signals and visualization."""
    logger.info("Starting trading bot in ENHANCED BACKTESTING mode with HISTORIC TRADE SIGNALS.")
    
    # Check if multi-asset mode is enabled
    multi_asset_enabled = config.get('multi_asset', {}).get('enabled', False)
    
    if multi_asset_enabled:
        logger.info("=== ENHANCED MULTI-ASSET BACKTESTING ===")
        run_enhanced_multi_asset_backtest(config)
    else:
        logger.info("=== ENHANCED SINGLE ASSET BACKTESTING ===")
        run_enhanced_single_asset_backtest(config)

def run_single_asset_backtest(config):
    """Run backtest for single asset (legacy mode)"""
    # Initialize components
    data_feed = OANDADataFeed(config)
    preprocessor = DataPreprocessor()
    risk_manager = RiskManager(config)
    
    # Initialize backtest engine
    engine = BacktestEngine(
        data_feed=data_feed,
        preprocessor=preprocessor,
        risk_manager=risk_manager,
        config=config
    )

    # Get symbol info from config structure
    if 'data' in config and 'symbols' in config['data']:
        symbol_info = config['data']['symbols'][0]
        forex_symbol = symbol_info['name']
        forex_timeframe = symbol_info['timeframe']
        asset_type = symbol_info['type']
    else:
        # Fallback to old structure
        forex_symbol = config['trading']['forex_pairs'][0]
        forex_timeframe = config['trading']['data_timeframe']
        asset_type = 'forex'
    
    try:
        data = engine.load_data(forex_symbol, asset_type, forex_timeframe)
        if data is not None:
            # Get strategy parameters based on asset type
            if asset_type == 'forex':
                strategy_config = config.get('strategies', {}).get('forex', {})
                strategy_name = strategy_config.get('name', 'ForexStrategy')
                strategy_params = strategy_config.get('params', {}).copy()
            elif asset_type == 'crypto':
                strategy_config = config.get('strategies', {}).get('crypto', {})
                strategy_name = strategy_config.get('name', 'ProductionQuantCryptoStrategy')
                strategy_params = strategy_config.get('params', {}).copy()
            else:
                # Default fallback
                strategy_name = 'ForexStrategy'
                strategy_params = config.get('strategy', {}).get('params', {})
            
            # Ensure strategy_params is not None
            if strategy_params is None:
                strategy_params = {}
                
            strategy_params['printlog'] = True  # Enable logging to see signals
            
            engine.add_strategy(strategy_name, **strategy_params)
            results = engine.run()
            
            if results:
                logger.info("=== SINGLE ASSET BACKTEST RESULTS ===")
                logger.info(f"Asset: {forex_symbol} ({asset_type})")
                logger.info(f"Final Portfolio Value: {results['final_value']:.2f}")
                logger.info(f"Total Return: {results['total_return']:.2f}%")
                logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
                logger.info(f"Max Drawdown: {results['max_drawdown']:.2f}%")
                logger.info(f"Total Trades: {results['total_trades']}")
                logger.info(f"Win Rate: {results['win_rate']:.2f}%")
                logger.info(f"Average Win: {results['avg_win']:.4f}")
                logger.info(f"Average Loss: {results['avg_loss']:.4f}")
        else:
            logger.error(f"Could not load data for {forex_symbol}. Backtest aborted.")
    except Exception as e:
        logger.error(f"An error occurred during single asset backtesting: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def run_multi_asset_backtest(config):
    """Run backtest for multiple assets and compare performance"""
    from data.kraken_feed import KrakenDataFeed
    
    # Initialize components
    oanda_feed = OANDADataFeed(config)
    ccxt_feed = CCXTDataFeed(config)
    preprocessor = DataPreprocessor()
    risk_manager = RiskManager(config)
    
    # Initialize backtest engine with multi-asset support
    engine = BacktestEngine(
        data_feed=oanda_feed,
        preprocessor=preprocessor,
        risk_manager=risk_manager,
        config=config
    )
    
    # Get symbols from config
    symbols_config = config.get('data', {}).get('symbols', [])
    
    if not symbols_config:
        logger.error("No symbols configured for multi-asset backtesting")
        return
    
    try:
        # Run multi-asset backtest
        multi_results = engine.run_multi_asset_backtest(symbols_config)
        
        if multi_results:
            logger.info("=== MULTI-ASSET BACKTEST COMPLETE ===")
            
            # Display individual results
            for symbol, data in multi_results['individual_results'].items():
                results = data['results']
                asset_type = data['asset_type']
                logger.info(f"\n--- {symbol} ({asset_type.upper()}) ---")
                logger.info(f"Final Value: ${results['final_value']:.2f}")
                logger.info(f"Total Return: {results['total_return']:.2f}%")
                logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
                logger.info(f"Win Rate: {results['win_rate']:.2f}%")
                logger.info(f"Total Trades: {results['total_trades']}")
            
            # Display analysis results
            comparison = multi_results['comparison']
            allocation = multi_results['allocation']
            recommendation = multi_results['recommendation']
            
            logger.info("\n=== MULTI-ASSET ANALYSIS ===")
            logger.info(f"Forex Average Score: {comparison['forex']['avg_score']:.1f}")
            logger.info(f"Crypto Average Score: {comparison['crypto']['avg_score']:.1f}")
            logger.info(f"Recommendation: Focus on {recommendation['primary_focus'].upper()}")
            logger.info(f"Confidence: {comparison['confidence']:.1f}%")
            logger.info(f"Optimal Allocation: {allocation['forex_allocation']:.1f}% Forex, {allocation['crypto_allocation']:.1f}% Crypto")
            logger.info(f"Next Trade Asset: {recommendation['next_trade_asset'].upper()}")
            logger.info(f"Reasoning: {allocation['reasoning']}")
            
            if multi_results['report_path']:
                logger.info(f"Detailed report saved to: {multi_results['report_path']}")
        
        else:
            logger.error("Multi-asset backtest failed")
            
    except Exception as e:
        logger.error(f"An error occurred during multi-asset backtesting: {e}")

def run_enhanced_single_asset_backtest(config):
    """Enhanced single asset backtest with historic trade signals and visualization."""
    import plotly.graph_objects as go
    import plotly.subplots as sp
    from plotly.offline import plot
    import pandas as pd
    import numpy as np
    from datetime import datetime
    import os
    
    logger.info("=== ENHANCED SINGLE ASSET BACKTESTING WITH TRADE SIGNALS ===")
    
    # Initialize components
    data_feed = OANDADataFeed(config)
    preprocessor = DataPreprocessor()
    risk_manager = RiskManager(config)
    
    # Initialize enhanced backtest engine
    engine = EnhancedBacktestEngine(
        data_feed=data_feed,
        preprocessor=preprocessor,
        risk_manager=risk_manager,
        config=config
    )

    # Get symbol info from config structure
    if 'data' in config and 'symbols' in config['data']:
        symbol_info = config['data']['symbols'][0]
        symbol = symbol_info['name']
        timeframe = symbol_info['timeframe']
        asset_type = symbol_info['type']
    else:
        # Fallback to old structure
        symbol = config['trading']['forex_pairs'][0]
        timeframe = config['trading']['data_timeframe']
        asset_type = 'forex'
    
    try:
        # Load data with enhanced tracking
        data = engine.load_data_with_signals(symbol, asset_type, timeframe)
        if data is not None:
            # Get strategy parameters based on asset type
            if asset_type == 'forex':
                strategy_config = config.get('strategies', {}).get('forex', {})
                strategy_name = strategy_config.get('name', 'ForexStrategy')
                strategy_params = strategy_config.get('params', {}).copy()
            elif asset_type == 'crypto':
                strategy_config = config.get('strategies', {}).get('crypto', {})
                strategy_name = strategy_config.get('name', 'ProductionQuantCryptoStrategy')
                strategy_params = strategy_config.get('params', {}).copy()
            else:
                # Default fallback
                strategy_name = 'ForexStrategy'
                strategy_params = config.get('strategy', {}).get('params', {})
            
            # Ensure strategy_params is not None
            if strategy_params is None:
                strategy_params = {}
                
            strategy_params['printlog'] = True  # Enable logging to see signals
            
            # Run enhanced backtest with signal tracking
            results = engine.run_enhanced_backtest(strategy_name, **strategy_params)
            
            if results:
                logger.info("=== ENHANCED BACKTEST RESULTS ===")
                logger.info(f"Asset: {symbol} ({asset_type})")
                logger.info(f"Strategy: {strategy_name}")
                logger.info(f"Timeframe: {timeframe}")
                logger.info(f"Data Points: {len(data)}")
                
                # Portfolio Metrics
                logger.info(f"\n--- Portfolio Performance ---")
                logger.info(f"Initial Capital: ${results['initial_capital']:,.2f}")
                logger.info(f"Final Portfolio Value: ${results['final_value']:,.2f}")
                logger.info(f"Total Return: {results['total_return']:.2f}%")
                logger.info(f"Annualized Return: {results.get('annualized_return', 0):.2f}%")
                logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.3f}")
                logger.info(f"Sortino Ratio: {results.get('sortino_ratio', 0):.3f}")
                logger.info(f"Max Drawdown: {results['max_drawdown']:.2f}%")
                logger.info(f"Calmar Ratio: {results.get('calmar_ratio', 0):.3f}")
                
                # Trade Statistics
                logger.info(f"\n--- Trade Statistics ---")
                logger.info(f"Total Trades: {results['total_trades']}")
                logger.info(f"Winning Trades: {results['winning_trades']}")
                logger.info(f"Losing Trades: {results['losing_trades']}")
                logger.info(f"Win Rate: {results['win_rate']:.2f}%")
                logger.info(f"Average Win: ${results['avg_win']:.2f}")
                logger.info(f"Average Loss: ${results['avg_loss']:.2f}")
                logger.info(f"Profit Factor: {results['profit_factor']:.3f}")
                logger.info(f"Expectancy: ${results.get('expectancy', 0):.2f}")
                
                # Signal Statistics
                if 'signal_stats' in results:
                    signal_stats = results['signal_stats']
                    logger.info(f"\n--- Signal Statistics (1H) ---")
                    logger.info(f"Total Signals Generated: {signal_stats['total_signals']}")
                    logger.info(f"Buy Signals: {signal_stats['buy_signals']}")
                    logger.info(f"Sell Signals: {signal_stats['sell_signals']}")
                    logger.info(f"Signal Accuracy: {signal_stats['signal_accuracy']:.2f}%")
                    logger.info(f"Signals per Day: {signal_stats['signals_per_day']:.1f}")
                
                # Create comprehensive visualization (if available)
                try:
                    create_enhanced_backtest_visualization(results, symbol, strategy_name, config)
                    logger.info(f"Visualization saved to: backtest_results_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
                except NameError:
                    logger.info("Visualization function not available - skipping chart generation")
                except Exception as e:
                    logger.warning(f"Error creating visualization: {e}")
                
                logger.info(f"\n=== BACKTEST COMPLETED SUCCESSFULLY ===")
                
        else:
            logger.error(f"Could not load data for {symbol}. Backtest aborted.")
    except Exception as e:
        logger.error(f"An error occurred during enhanced single asset backtesting: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def run_enhanced_multi_asset_backtest(config):
    """Enhanced multi-asset backtest with comparative analysis and visualization."""
    import plotly.graph_objects as go
    import plotly.subplots as sp
    from plotly.offline import plot
    import pandas as pd
    from datetime import datetime
    
    logger.info("=== ENHANCED MULTI-ASSET BACKTESTING ===")
    
    # Initialize components
    oanda_feed = OANDADataFeed(config)
    ccxt_feed = CCXTDataFeed(config)
    preprocessor = DataPreprocessor()
    risk_manager = RiskManager(config)
    
    # Initialize enhanced backtest engine
    engine = EnhancedBacktestEngine(
        data_feed=oanda_feed,
        preprocessor=preprocessor,
        risk_manager=risk_manager,
        config=config
    )
    
    # Get symbols from config
    symbols_config = config.get('data', {}).get('symbols', [])
    
    if not symbols_config:
        logger.error("No symbols configured for multi-asset backtesting")
        return
    
    try:
        # Run enhanced multi-asset backtest
        multi_results = engine.run_enhanced_multi_asset_backtest(symbols_config)
        
        if multi_results:
            logger.info("=== ENHANCED MULTI-ASSET BACKTEST COMPLETE ===")
            
            # Display individual results with enhanced metrics
            for symbol, data in multi_results['individual_results'].items():
                results = data['results']
                asset_type = data['asset_type']
                logger.info(f"\n--- {symbol} ({asset_type.upper()}) PERFORMANCE ---")
                logger.info(f"Final Value: ${results['final_value']:,.2f}")
                logger.info(f"Total Return: {results['total_return']:.2f}%")
                logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.3f}")
                logger.info(f"Max Drawdown: {results['max_drawdown']:.2f}%")
                logger.info(f"Win Rate: {results['win_rate']:.2f}%")
                logger.info(f"Total Trades: {results['total_trades']}")
                logger.info(f"Profit Factor: {results['profit_factor']:.3f}")
                
                if 'signal_stats' in results:
                    signal_stats = results['signal_stats']
                    logger.info(f"Total Signals: {signal_stats['total_signals']}")
                    logger.info(f"Signal Accuracy: {signal_stats['signal_accuracy']:.2f}%")
            
            # Display comparative analysis
            comparison = multi_results['comparison']
            allocation = multi_results['allocation']
            recommendation = multi_results['recommendation']
            
            logger.info("\n=== MULTI-ASSET COMPARATIVE ANALYSIS ===")
            logger.info(f"Best Performing Asset: {comparison.get('best_asset', 'N/A')}")
            logger.info(f"Best Return: {comparison.get('best_return', 0):.2f}%")
            logger.info(f"Best Sharpe Ratio: {comparison.get('best_sharpe', 0):.3f}")
            logger.info(f"Forex Average Score: {comparison.get('forex', {}).get('avg_score', 0):.1f}")
            logger.info(f"Crypto Average Score: {comparison.get('crypto', {}).get('avg_score', 0):.1f}")
            logger.info(f"Recommendation: Focus on {recommendation.get('primary_focus', 'N/A').upper()}")
            logger.info(f"Confidence: {comparison.get('confidence', 0):.1f}%")
            logger.info(f"Optimal Allocation: {allocation.get('forex_allocation', 0):.1f}% Forex, {allocation.get('crypto_allocation', 0):.1f}% Crypto")
            
            # Create multi-asset visualization
            create_multi_asset_visualization(multi_results, config)
            
            if multi_results.get('report_path'):
                logger.info(f"Detailed report saved to: {multi_results['report_path']}")
                
            logger.info(f"Multi-asset visualization saved to: multi_asset_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html")
        
        else:
            logger.error("Enhanced multi-asset backtest failed")
            
    except Exception as e:
        logger.error(f"An error occurred during enhanced multi-asset backtesting: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

def run_live_trading_mode(config):
    """Runs the bot in live trading mode with enhanced dynamic optimization and automatic parameter management."""
    import time
    import pandas as pd
    from datetime import datetime, timedelta
    from utils.enhanced_dynamic_optimizer import EnhancedDynamicOptimizer
    from utils.multi_asset_analyzer import MultiAssetAnalyzer
    from data.ccxt_feed import CCXTDataFeed
    
    logger.info("Starting trading bot in LIVE TRADING mode with ENHANCED OPTIMIZATION.")
    
    # Initialize enhanced dynamic optimizer
    logger.info("=== INITIALIZING ENHANCED DYNAMIC OPTIMIZATION ===")
    dynamic_optimizer = EnhancedDynamicOptimizer(
        config_path='config/config.yaml',
        output_dir='output'
    )
    
    # Set parameter age threshold (default 24 hours, configurable)
    max_age_hours = config.get('optimization', {}).get('max_parameter_age_hours', 24)
    dynamic_optimizer.max_age_minutes = max_age_hours * 60
    
    logger.info(f"Parameter age threshold: {max_age_hours} hours")
    
    # Check if multi-asset mode is enabled
    multi_asset_enabled = config.get('multi_asset', {}).get('enabled', False)
    
    if multi_asset_enabled:
        logger.info("=== MULTI-ASSET LIVE TRADING WITH ENHANCED OPTIMIZATION ===")
        run_enhanced_single_asset_live_trading(config, dynamic_optimizer)
    else:
        logger.info("=== SINGLE ASSET LIVE TRADING WITH ENHANCED OPTIMIZATION ===")
        run_enhanced_single_asset_live_trading(config, dynamic_optimizer)

def run_enhanced_single_asset_live_trading(config, dynamic_optimizer):
    """Run enhanced live trading for single asset with automatic optimization"""
    import time
    import pandas as pd
    from datetime import datetime, timedelta
    
    logger.info("=== ENHANCED SINGLE ASSET LIVE TRADING ===")
    
    # Determine primary strategy type from config
    symbols_config = config.get('data', {}).get('symbols', [])
    primary_strategy = 'forex'  # Default
    
    if symbols_config:
        primary_symbol = symbols_config[0]
        primary_strategy = primary_symbol.get('type', 'forex')
    
    logger.info(f"Primary strategy type: {primary_strategy}")
    
    # Check parameter status and auto-optimize if needed
    logger.info("=== CHECKING PARAMETER STATUS ===")
    summary = dynamic_optimizer.get_parameter_performance_summary(primary_strategy)
    
    if summary['has_parameters']:
        logger.info(f"Current parameters age: {summary['age_hours']:.1f} hours")
        logger.info(f"Performance score: {summary['performance_score']:.4f}")
        logger.info(f"Total return: {summary['total_return']:.2f}%")
        logger.info(f"Sharpe ratio: {summary['sharpe_ratio']:.2f}")
    else:
        logger.warning("No parameters found - optimization will be triggered")
    
    # Auto-optimize if needed
    logger.info("=== AUTO-OPTIMIZATION CHECK ===")
    optimization_result = dynamic_optimizer.auto_optimize_if_needed(primary_strategy)
    
    if optimization_result['optimization_run']:
        if optimization_result['success']:
            logger.info("✅ Auto-optimization completed successfully!")
            logger.info(f"New performance: {optimization_result['performance_metrics']['total_return']:.2f}% return")
        else:
            logger.error(f"❌ Auto-optimization failed: {optimization_result.get('error', 'Unknown error')}")
    else:
        logger.info(f"⏸️ Auto-optimization skipped: {optimization_result['reason']}")
    
    # Get current best parameters
    latest_params = dynamic_optimizer.get_latest_parameters(primary_strategy)
    if latest_params:
        optimized_params = latest_params.parameters
        logger.info("=== USING OPTIMIZED PARAMETERS ===")
        for param, value in optimized_params.items():
            if isinstance(value, float):
                logger.info(f"  {param}: {value:.4f}")
            else:
                logger.info(f"  {param}: {value}")
    else:
        logger.warning("No optimized parameters available - using config defaults")
        optimized_params = {}
    
    # Initialize components for live trading
    broker_type = "oanda"
    
    broker_connector = None
    if broker_type == "oanda":
        broker_connector = OANDABrokerConnector(config=config)
    elif broker_type == "ccxt":
        broker_connector = CCXTBrokerConnector(config=config, exchange_id='binance')
    elif broker_type == "ibkr":
        broker_connector = IBKRBrokerConnector(config=config)
    else:
        logger.error(f"Unsupported broker type for live trading: {broker_type}")
        return

    if not broker_connector:
        logger.error("Broker connector could not be initialized.")
        return

    try:
        broker_connector.connect()
        order_manager = OrderManager(broker_connector, config=config)
        risk_manager = RiskManager(config=config)
        
        # Initialize data feed and preprocessor for live data
        data_feed = OANDADataFeed(config)
        preprocessor = DataPreprocessor()
        
        # Get initial balance
        balance_info = broker_connector.get_balance()
        if balance_info:
            initial_capital = balance_info.get('total', 0.0)
            risk_manager.set_initial_capital(initial_capital)
            logger.info(f"Live trading starting with capital: {initial_capital}")
        else:
            logger.warning("Could not retrieve initial account balance.")

        # Get symbol info from config structure
        if 'data' in config and 'symbols' in config['data']:
            symbol_info = config['data']['symbols'][0]
            forex_symbol = symbol_info['name']
            timeframe = symbol_info['timeframe']
        else:
            # Fallback to old structure
            forex_symbol = config['trading']['forex_pairs'][0]
            timeframe = config['trading']['data_timeframe']
            
        logger.info(f"Starting live trading for {forex_symbol} on {timeframe} timeframe")
        
        # Initialize strategy with parameters (use optimized if available)
        strategy_params = config.get('strategy', {}).get('params', {})
        
        # Override with optimized parameters if available
        if optimized_params:
            logger.info("Using dynamically optimized parameters for live trading")
            strategy_params.update(optimized_params)
        
        logger.info(f"Final strategy parameters for live trading: {strategy_params}")
        
        # Live trading loop
        iteration = 0
        max_iterations = 10  # Limit for demonstration
        
        logger.info("=== STARTING LIVE TRADING LOOP ===")
        logger.info(f"Will run for {max_iterations} iterations with 30-second intervals")
        
        while iteration < max_iterations:
            try:
                iteration += 1
                logger.info(f"\n--- Live Trading Iteration {iteration}/{max_iterations} ---")
                
                # Get current price
                current_price = broker_connector.get_current_price(forex_symbol)
                if current_price:
                    logger.info(f"Current {forex_symbol} price: {current_price}")
                else:
                    logger.warning(f"Could not get current price for {forex_symbol}")
                    time.sleep(30)
                    continue
                
                # Fetch recent historical data for signal generation
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=30)  # Get 30 days of data
                
                logger.info(f"Fetching historical data from {start_time} to {end_time}")
                historical_data = data_feed.get_forex_data(
                    symbol=forex_symbol,
                    timeframe=timeframe,
                    start_date=start_time.strftime('%Y-%m-%d'),
                    end_date=end_time.strftime('%Y-%m-%d')
                )
                
                if historical_data is not None and len(historical_data) > 100:
                    logger.info(f"Retrieved {len(historical_data)} historical data points")
                    
                    # Preprocess the data
                    processed_data = preprocessor.preprocess(historical_data)
                    logger.info(f"Processed data shape: {processed_data.shape}")
                    
                    # Create a simple signal generator based on our strategy logic
                    # Get the latest data point for signal generation
                    latest_data = processed_data.tail(50).copy()  # Use last 50 points for analysis
                    
                    # Simple moving average crossover signal
                    fast_ma = strategy_params.get('fast_length', 10)
                    slow_ma = strategy_params.get('slow_length', 30)
                    
                    if len(latest_data) >= slow_ma:
                        latest_data[f'MA_{fast_ma}'] = latest_data['close'].rolling(fast_ma).mean()
                        latest_data[f'MA_{slow_ma}'] = latest_data['close'].rolling(slow_ma).mean()
                        
                        # Get current values
                        current_fast_ma = latest_data[f'MA_{fast_ma}'].iloc[-1]
                        current_slow_ma = latest_data[f'MA_{slow_ma}'].iloc[-1]
                        prev_fast_ma = latest_data[f'MA_{fast_ma}'].iloc[-2]
                        prev_slow_ma = latest_data[f'MA_{slow_ma}'].iloc[-2]
                        
                        # Generate signals
                        signal = None
                        if current_fast_ma > current_slow_ma and prev_fast_ma <= prev_slow_ma:
                            signal = "BUY"
                            logger.info(f"[BUY SIGNAL] Generated!")
                            logger.info(f"   Fast MA ({fast_ma}): {current_fast_ma:.5f}")
                            logger.info(f"   Slow MA ({slow_ma}): {current_slow_ma:.5f}")
                            logger.info(f"   Current Price: {current_price}")
                        elif current_fast_ma < current_slow_ma and prev_fast_ma >= prev_slow_ma:
                            signal = "SELL"
                            logger.info(f"[SELL SIGNAL] Generated!")
                            logger.info(f"   Fast MA ({fast_ma}): {current_fast_ma:.5f}")
                            logger.info(f"   Slow MA ({slow_ma}): {current_slow_ma:.5f}")
                            logger.info(f"   Current Price: {current_price}")
                        else:
                            logger.info(f"[NO SIGNAL] Fast MA: {current_fast_ma:.5f}, Slow MA: {current_slow_ma:.5f}")
                        
                        # Calculate RSI for additional confirmation
                        if 'rsi' in latest_data.columns:
                            current_rsi = latest_data['rsi'].iloc[-1]
                            logger.info(f"   RSI: {current_rsi:.2f}")
                            
                            # RSI confirmation
                            if signal == "BUY" and current_rsi < 70:
                                logger.info(f"   [RSI CONFIRM] RSI confirms BUY signal (RSI < 70)")
                            elif signal == "SELL" and current_rsi > 30:
                                logger.info(f"   [RSI CONFIRM] RSI confirms SELL signal (RSI > 30)")
                            elif signal:
                                logger.info(f"   [RSI WARNING] RSI does not confirm signal")
                        
                        # Risk management check
                        if signal:
                            position_size = risk_manager.calculate_position_size(
                                current_price,
                                strategy_params.get('stop_loss_percent', 0.01)
                            )
                            logger.info(f"   [POSITION] Calculated position size: {position_size}")
                            
                            # In a real implementation, you would place the order here:
                            # order_manager.place_order(signal, forex_symbol, position_size, current_price)
                            logger.info(f"   [ORDER] Would place {signal} order for {position_size} units at {current_price}")
                    
                else:
                    logger.warning("Insufficient historical data for signal generation")
                
                # Get current account balance
                balance_info = broker_connector.get_balance()
                if balance_info:
                    current_balance = balance_info.get('total', 0.0)
                    logger.info(f"[BALANCE] Current account balance: ${current_balance:,.2f}")
                
                # Wait before next iteration
                if iteration < max_iterations:
                    logger.info(f"[WAIT] Waiting 30 seconds before next iteration...")
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error in live trading iteration {iteration}: {e}")
                time.sleep(30)
                continue
        
        logger.info("=== LIVE TRADING LOOP COMPLETED ===")
        logger.info("In a real implementation, this would run continuously until stopped.")
        
    except Exception as e:
        logger.critical(f"An error occurred during live trading: {e}")
    finally:
        if broker_connector:
            broker_connector.disconnect()
            logger.info("Disconnected from broker.")

def run_optimization_mode(config):
    """Runs the bot in enhanced optimization mode with multi-strategy support."""
    import time
    from datetime import datetime
    
    logger.info("Starting trading bot in ENHANCED OPTIMIZATION mode.")
    
    try:
        # Initialize enhanced dynamic optimizer
        from utils.enhanced_dynamic_optimizer import EnhancedDynamicOptimizer
        
        dynamic_optimizer = EnhancedDynamicOptimizer(
            config_path='config/config.yaml',
            output_dir='output'
        )
        
        # Get optimization configuration
        opt_config = config.get('optimization', {})
        generations = opt_config.get('generations', 50)
        population = opt_config.get('population_size', 24)
        multi_asset_optimization = opt_config.get('multi_asset_optimization', True)
        
        logger.info("=== ENHANCED OPTIMIZATION CONFIGURATION ===")
        logger.info(f"Generations: {generations}")
        logger.info(f"Population: {population}")
        logger.info(f"Multi-asset optimization: {multi_asset_optimization}")
        
        # Determine strategies to optimize
        strategies_to_optimize = []
        
        if multi_asset_optimization:
            # Check which strategies are configured
            symbols_config = config.get('data', {}).get('symbols', [])
            strategy_types = set()
            
            for symbol in symbols_config:
                strategy_types.add(symbol.get('type', 'forex'))
                
            strategies_to_optimize = list(strategy_types)
            logger.info(f"Multi-asset optimization for: {strategies_to_optimize}")
        else:
            # Single strategy optimization (default to forex)
            primary_strategy = 'forex'
            if 'data' in config and 'symbols' in config['data']:
                primary_strategy = config['data']['symbols'][0].get('type', 'forex')
            strategies_to_optimize = [primary_strategy]
            logger.info(f"Single strategy optimization for: {primary_strategy}")
        
        # Run optimization for each strategy
        optimization_results = {}
        total_start_time = time.time()
        
        for strategy_type in strategies_to_optimize:
            logger.info(f"\n=== OPTIMIZING {strategy_type.upper()} STRATEGY ===")
            
            start_time = time.time()
            result = dynamic_optimizer.run_enhanced_optimization(
                strategy_type=strategy_type,
                generations=generations,
                population=population,
                force=True  # Force optimization in optimize mode
            )
            end_time = time.time()
            
            optimization_results[strategy_type] = result
            
            if result['success']:
                logger.info(f"✅ {strategy_type.upper()} optimization completed!")
                logger.info(f"⏱️ Duration: {end_time - start_time:.2f} seconds")
                logger.info(f"🎯 Best fitness: {result.get('best_fitness', 0):.4f}")
                
                metrics = result['performance_metrics']
                logger.info(f"📈 Total return: {metrics['total_return']:.2f}%")
                logger.info(f"📊 Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
                logger.info(f"📉 Max drawdown: {metrics['max_drawdown']:.1f}%")
                logger.info(f"🎲 Win rate: {metrics['win_rate']:.1f}%")
                logger.info(f"💾 Results saved to: {result.get('csv_path', 'N/A')}")
                
                # Display best parameters
                logger.info("🏆 Best parameters:")
                for param, value in result['best_parameters'].items():
                    if isinstance(value, float):
                        logger.info(f"  {param}: {value:.4f}")
                    else:
                        logger.info(f"  {param}: {value}")
            else:
                logger.error(f"❌ {strategy_type.upper()} optimization failed!")
                logger.error(f"Error: {result.get('error', 'Unknown error')}")
        
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        # Summary report
        logger.info(f"\n=== OPTIMIZATION SUMMARY ===")
        logger.info(f"⏱️ Total duration: {total_duration:.2f} seconds")
        
        successful_optimizations = sum(1 for r in optimization_results.values() if r.get('success'))
        failed_optimizations = len(optimization_results) - successful_optimizations
        
        logger.info(f"✅ Successful optimizations: {successful_optimizations}")
        logger.info(f"❌ Failed optimizations: {failed_optimizations}")
        
        # Performance comparison
        if len(optimization_results) > 1:
            logger.info(f"\n=== STRATEGY PERFORMANCE COMPARISON ===")
            
            for strategy_type, result in optimization_results.items():
                if result.get('success'):
                    metrics = result['performance_metrics']
                    logger.info(f"{strategy_type.upper()}:")
                    logger.info(f"  Return: {metrics['total_return']:.2f}%")
                    logger.info(f"  Sharpe: {metrics['sharpe_ratio']:.2f}")
                    logger.info(f"  Drawdown: {metrics['max_drawdown']:.1f}%")
                    
            # Recommend best strategy
            best_strategy = None
            best_score = -float('inf')
            
            for strategy_type, result in optimization_results.items():
                if result.get('success'):
                    score = result.get('best_fitness', 0)
                    if score > best_score:
                        best_score = score
                        best_strategy = strategy_type
                        
            if best_strategy:
                logger.info(f"\n🏆 RECOMMENDED STRATEGY: {best_strategy.upper()}")
                logger.info(f"Best fitness score: {best_score:.4f}")
        
        # Save comprehensive results
        results_summary = {
            'timestamp': datetime.now().isoformat(),
            'total_duration': total_duration,
            'strategies_optimized': list(optimization_results.keys()),
            'successful_optimizations': successful_optimizations,
            'failed_optimizations': failed_optimizations,
            'results': optimization_results
        }
        
        summary_path = os.path.join('output', f'optimization_summary_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
        with open(summary_path, 'w') as f:
            import json
            json.dump(results_summary, f, indent=2, default=str)
            
        logger.info(f"📄 Comprehensive results saved to: {summary_path}")
        logger.info("🎉 Enhanced optimization completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred during enhanced optimization: {e}")
        raise

def main():
    parser = argparse.ArgumentParser(description="Trading Bot Main Script")
    parser.add_argument('--mode', type=str, required=True,
                        choices=['backtest', 'live', 'optimize'],
                        help='Operation mode: backtest, live, or optimize')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='Path to the configuration file (default: config/config.yaml)')
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 2: # Error code for missing required arguments
            logger.error("Missing required arguments. Please specify --mode.")
            parser.print_help()
            return # Exit gracefully
        else:
            raise # Re-raise other SystemExit errors

    # Setup logging first
    # Pass the config object directly to setup_logging
    # First, load a minimal config to get logging settings if needed, or default
    temp_config = {}
    try:
        with open(args.config, 'r') as f:
            temp_config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found at {args.config}. Using default logging settings.")
    
    setup_logging(config=temp_config) # Pass the temporary config for logging setup
    
    # Load full configuration with environment variable substitution
    config = load_config(config_path=args.config)

    if args.mode == 'backtest':
        run_backtest_mode(config)
    elif args.mode == 'live':
        run_live_trading_mode(config)
    elif args.mode == 'optimize':
        run_optimization_mode(config)
    else:
        logger.error(f"Invalid mode specified: {args.mode}")
        parser.print_help()

if __name__ == "__main__":
    main()
def run_enhanced_multi_asset_live_trading(config, dynamic_optimizer):
    """Run enhanced multi-asset live trading with automatic optimization and intelligent asset selection"""
    import time
    import pandas as pd
    from datetime import datetime, timedelta
    from utils.multi_asset_analyzer import MultiAssetAnalyzer
    from data.kraken_feed import KrakenDataFeed
    
    logger.info("=== ENHANCED MULTI-ASSET LIVE TRADING ===")
    
    # Initialize multi-asset analyzer
    multi_asset_analyzer = MultiAssetAnalyzer(config_path='config/config.yaml')
    ccxt_feed = CCXTDataFeed(config)
    
    # Get configured strategies
    symbols_config = config.get('data', {}).get('symbols', [])
    strategy_types = list(set(symbol.get('type', 'forex') for symbol in symbols_config))
    
    logger.info(f"Configured strategy types: {strategy_types}")
    
    # Check and optimize parameters for all strategy types
    logger.info("=== MULTI-STRATEGY PARAMETER OPTIMIZATION ===")
    
    optimization_results = {}
    for strategy_type in strategy_types:
        logger.info(f"\n--- Checking {strategy_type.upper()} parameters ---")
        
        # Get parameter summary
        summary = dynamic_optimizer.get_parameter_performance_summary(strategy_type)
        
        if summary['has_parameters']:
            logger.info(f"Current {strategy_type} parameters:")
            logger.info(f"  Age: {summary['age_hours']:.1f} hours")
            logger.info(f"  Performance score: {summary['performance_score']:.4f}")
            logger.info(f"  Total return: {summary['total_return']:.2f}%")
            logger.info(f"  Sharpe ratio: {summary['sharpe_ratio']:.2f}")
        else:
            logger.warning(f"No {strategy_type} parameters found")
        
        # Auto-optimize if needed
        optimization_result = dynamic_optimizer.auto_optimize_if_needed(strategy_type)
        optimization_results[strategy_type] = optimization_result
        
        if optimization_result['optimization_run']:
            if optimization_result['success']:
                logger.info(f"✅ {strategy_type} auto-optimization completed!")
                metrics = optimization_result['performance_metrics']
                logger.info(f"  New performance: {metrics['total_return']:.2f}% return, "
                           f"{metrics['sharpe_ratio']:.2f} Sharpe")
            else:
                logger.error(f"❌ {strategy_type} auto-optimization failed: "
                           f"{optimization_result.get('error', 'Unknown error')}")
        else:
            logger.info(f"⏸️ {strategy_type} optimization skipped: {optimization_result['reason']}")
    
    # Determine optimal strategy allocation based on recent performance
    logger.info("\n=== STRATEGY ALLOCATION ANALYSIS ===")
    
    strategy_scores = {}
    for strategy_type in strategy_types:
        latest_params = dynamic_optimizer.get_latest_parameters(strategy_type)
        if latest_params:
            # Calculate composite score
            score = (
                latest_params.performance_score * 0.4 +
                (latest_params.total_return / 20.0) * 0.3 +  # Normalize return
                (latest_params.sharpe_ratio / 2.0) * 0.2 +   # Normalize Sharpe
                (max(0, 50 - latest_params.max_drawdown) / 50.0) * 0.1  # Normalize drawdown
            )
            strategy_scores[strategy_type] = score
            logger.info(f"{strategy_type.upper()} composite score: {score:.4f}")
        else:
            strategy_scores[strategy_type] = 0.0
            logger.warning(f"{strategy_type.upper()} has no parameters - score: 0.0")
    
    # Select primary strategy
    if strategy_scores:
        primary_strategy = max(strategy_scores, key=strategy_scores.get)
        logger.info(f"🏆 Primary strategy selected: {primary_strategy.upper()}")
        logger.info(f"Score: {strategy_scores[primary_strategy]:.4f}")
    else:
        primary_strategy = 'forex'  # Default fallback
        logger.warning("No strategy scores available, defaulting to forex")
    
    # Run live trading simulation with the selected strategy
    logger.info(f"\n=== STARTING LIVE TRADING SIMULATION ({primary_strategy.upper()}) ===")
    
    # Get optimized parameters for the primary strategy
    latest_params = dynamic_optimizer.get_latest_parameters(primary_strategy)
    if latest_params:
        optimized_params = latest_params.parameters
        logger.info("Using optimized parameters for live trading")
    else:
        logger.warning("No optimized parameters available, using config defaults")
        optimized_params = {}
    
    # Initialize appropriate broker connector based on strategy
    broker_connector = None
    if primary_strategy == 'forex':
        from execution.broker_connect import OANDABrokerConnector
        broker_connector = OANDABrokerConnector(config=config)
    elif primary_strategy == 'crypto':
        # For crypto, we'll use a simulation since we don't have live crypto broker
        logger.info("Crypto strategy selected - running in simulation mode")
        
    # Live trading loop with enhanced monitoring
    try:
        if broker_connector:
            broker_connector.connect()
            
        from execution.order_manager import OrderManager
        from risk.risk_manager import RiskManager
        from data.data_feed import OANDADataFeed
        from data.preprocessing import DataPreprocessor
        
        if broker_connector:
            order_manager = OrderManager(broker_connector, config=config)
        risk_manager = RiskManager(config=config)
        
        # Initialize data feeds
        oanda_feed = OANDADataFeed(config) if primary_strategy == 'forex' else None
        kraken_feed = KrakenDataFeed(config) # For order management
        ccxt_feed = CCXTDataFeed(config) if primary_strategy == 'crypto' else None
        
        # Get symbol configuration
        primary_symbols = [s for s in symbols_config if s['type'] == primary_strategy]
        if not primary_symbols:
            logger.error(f"No {primary_strategy} symbols configured")
            return
            
        primary_symbol = primary_symbols[0]
        symbol_name = primary_symbol['name']
        timeframe = primary_symbol['timeframe']
        
        logger.info(f"Trading {symbol_name} on {timeframe} timeframe")
        
        # Enhanced live trading loop
        iteration = 0
        max_iterations = 30  # Extended for demonstration
        parameter_check_interval = 5  # Check parameters every 5 iterations
        
        while iteration < max_iterations:
            try:
                iteration += 1
                logger.info(f"\n--- Enhanced Live Trading Iteration {iteration}/{max_iterations} ---")
                
                # Periodic parameter optimization check
                if iteration % parameter_check_interval == 0:
                    logger.info("🔄 Periodic parameter optimization check...")
                    
                    # Check if parameters need updating
                    needs_optimization, age_minutes = dynamic_optimizer.check_parameter_age(primary_strategy)
                    
                    if needs_optimization:
                        logger.info(f"Parameters are {age_minutes:.1f} minutes old - triggering optimization")
                        opt_result = dynamic_optimizer.auto_optimize_if_needed(primary_strategy)
                        
                        if opt_result['optimization_run'] and opt_result['success']:
                            logger.info("✅ Parameters updated during live trading!")
                            # Update optimized_params for subsequent iterations
                            latest_params = dynamic_optimizer.get_latest_parameters(primary_strategy)
                            if latest_params:
                                optimized_params = latest_params.parameters
                    else:
                        logger.info(f"Parameters are fresh ({age_minutes:.1f} minutes old)")
                
                # Get current market data
                current_price = None
                
                if primary_strategy == 'forex' and broker_connector:
                    current_price = broker_connector.get_current_price(symbol_name)
                elif primary_strategy == 'crypto' and ccxt_feed:
                    # In a real scenario, you'd fetch live data here.
                    # For this simulation, we'll get the last closing price.
                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=1)
                    ohlcv = ccxt_feed.get_crypto_data(symbol_name, timeframe, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                    if not ohlcv.empty:
                        current_price = ohlcv['close'].iloc[-1]
                
                if current_price:
                    logger.info(f"Current {symbol_name} price: ${current_price:.4f}")
                    
                    # Update multi-asset analyzer with current conditions
                    market_conditions = {
                        'price': current_price,
                        'volatility': 0.02,  # Placeholder - would calculate from recent data
                        'trend_strength': 0.7,  # Placeholder
                        'volume': 1.0  # Placeholder
                    }
                    
                    multi_asset_analyzer.update_market_conditions(primary_strategy, market_conditions)
                    
                    # Generate trading signals (simplified for demonstration)
                    logger.info(f"[{primary_strategy.upper()} SIGNAL] Monitoring {symbol_name} at ${current_price:.4f}")
                    logger.info(f"Using optimized parameters: {len(optimized_params)} parameters loaded")
                    
                    # In a real implementation, this would:
                    # 1. Fetch recent historical data
                    # 2. Apply the optimized strategy parameters
                    # 3. Generate actual buy/sell signals
                    # 4. Execute trades through the order manager
                    # 5. Monitor positions and apply risk management
                    
                    # For demonstration, we'll just log the activity
                    if broker_connector:
                        balance_info = broker_connector.get_balance()
                        if balance_info:
                            current_balance = balance_info.get('total', 0.0)
                            logger.info(f"[BALANCE] Current account balance: ${current_balance:,.2f}")
                
                else:
                    logger.warning(f"Could not get current price for {symbol_name}")
                
                # Strategy performance monitoring
                if iteration % 10 == 0:  # Every 10 iterations
                    logger.info("📊 Performance monitoring update...")
                    
                    # Get current parameter performance
                    summary = dynamic_optimizer.get_parameter_performance_summary(primary_strategy)
                    if summary['has_parameters']:
                        logger.info(f"Current strategy performance:")
                        logger.info(f"  Score: {summary['performance_score']:.4f}")
                        logger.info(f"  Return: {summary['total_return']:.2f}%")
                        logger.info(f"  Sharpe: {summary['sharpe_ratio']:.2f}")
                
                # Wait before next iteration
                if iteration < max_iterations:
                    logger.info("⏳ Waiting 30 seconds before next iteration...")
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error in enhanced live trading iteration {iteration}: {e}")
                time.sleep(30)
                continue
        
        logger.info("=== ENHANCED MULTI-ASSET LIVE TRADING COMPLETED ===")
        logger.info("In a real implementation, this would run continuously with:")
        logger.info("- Automatic parameter optimization based on age and performance")
        logger.info("- Dynamic strategy switching based on market conditions")
        logger.info("- Real-time risk management and position monitoring")
        logger.info("- Comprehensive performance tracking and reporting")
        
    except Exception as e:
        logger.error(f"Error in enhanced multi-asset live trading: {e}")
    finally:
        if broker_connector:
            broker_connector.disconnect()
            logger.info("Disconnected from broker")

# Legacy functions (kept for backward compatibility but not used in enhanced mode)
def run_multi_asset_live_trading(config):
    """Legacy multi-asset live trading function - use run_enhanced_multi_asset_live_trading instead"""
    logger.warning("Using legacy multi-asset live trading function. Consider upgrading to enhanced version.")
    
    import time
    import pandas as pd
    from datetime import datetime, timedelta
    from utils.dynamic_optimizer import DynamicOptimizer
    from utils.multi_asset_analyzer import MultiAssetAnalyzer
    from data.ccxt_feed import CCXTDataFeed
    
    logger.info("=== INITIALIZING MULTI-ASSET LIVE TRADING (LEGACY) ===")
    
    # Initialize multi-asset analyzer
    multi_asset_analyzer = MultiAssetAnalyzer(config_path='config/config.yaml')
    
    # Initialize dynamic optimizer
    dynamic_optimizer = DynamicOptimizer(
        config_path='config/config.yaml',
        output_dir='output'
    )
    
    # Run initial multi-asset backtest to determine optimal allocation
    logger.info("Running initial multi-asset analysis...")
    try:
        from data.data_feed import OANDADataFeed
        
        # Initialize data feeds
        oanda_feed = OANDADataFeed(config)
        ccxt_feed = CCXTDataFeed(config)
        
        # Run quick backtests for both assets
        symbols_config = config.get('data', {}).get('symbols', [])
        
        # Initialize backtest engine for analysis
        from backtesting.backtest_engine import BacktestEngine
        from data.preprocessing import DataPreprocessor
        from risk.risk_manager import RiskManager
        
        preprocessor = DataPreprocessor()
        risk_manager = RiskManager(config)
        
        engine = BacktestEngine(
            data_feed=oanda_feed,
            preprocessor=preprocessor,
            risk_manager=risk_manager,
            config=config
        )
        
        # Run multi-asset analysis
        multi_results = engine.run_multi_asset_backtest(symbols_config)
        
        if multi_results:
            recommendation = multi_results['recommendation']
            allocation = multi_results['allocation']
            
            logger.info("=== INITIAL MULTI-ASSET ANALYSIS COMPLETE ===")
            logger.info(f"Recommended focus: {recommendation['primary_focus']}")
            logger.info(f"Next trade asset: {recommendation['next_trade_asset']}")
            logger.info(f"Allocation: {allocation['forex_allocation']:.1f}% Forex, {allocation['crypto_allocation']:.1f}% Crypto")
            
            # Start live trading with recommended asset
            selected_asset = recommendation['next_trade_asset']
            
        else:
            logger.warning("Multi-asset analysis failed, defaulting to forex")
            selected_asset = 'forex'
            
    except Exception as e:
        logger.error(f"Error in initial multi-asset analysis: {e}")
        selected_asset = 'forex'  # Default to forex
    
    # Initialize live trading for selected asset
    logger.info(f"=== STARTING LIVE TRADING FOR {selected_asset.upper()} ===")
    
    if selected_asset == 'forex':
        run_forex_live_trading(config, dynamic_optimizer, multi_asset_analyzer)
    else:
        run_crypto_live_trading(config, dynamic_optimizer, multi_asset_analyzer)

def run_forex_live_trading(config, dynamic_optimizer, multi_asset_analyzer):
    """Run live trading for forex assets"""
    import time
    from datetime import datetime, timedelta
    
    logger.info("Starting FOREX live trading...")
    
    # Get optimized forex parameters
    optimized_params = dynamic_optimizer.get_optimized_parameters(
        max_age_minutes=5,
        auto_optimize=True,
        generations=40,
        population=60
    )
    
    # Initialize forex components
    broker_type = "oanda"
    
    broker_connector = None
    if broker_type == "oanda":
        from execution.broker_connect import OANDABrokerConnector
        broker_connector = OANDABrokerConnector(config=config)
    
    if not broker_connector:
        logger.error("Forex broker connector could not be initialized.")
        return
    
    try:
        broker_connector.connect()
        from execution.order_manager import OrderManager
        from risk.risk_manager import RiskManager
        from data.data_feed import OANDADataFeed
        from data.preprocessing import DataPreprocessor
        
        order_manager = OrderManager(broker_connector, config=config)
        risk_manager = RiskManager(config=config)
        data_feed = OANDADataFeed(config)
        preprocessor = DataPreprocessor()
        
        # Get forex symbol configuration
        forex_symbols = [s for s in config.get('data', {}).get('symbols', []) if s['type'] == 'forex']
        if not forex_symbols:
            logger.error("No forex symbols configured")
            return
        
        forex_symbol = forex_symbols[0]['name']
        timeframe = forex_symbols[0]['timeframe']
        
        logger.info(f"Trading {forex_symbol} on {timeframe} timeframe")
        
        # Get strategy parameters
        strategy_params = config.get('strategies', {}).get('forex', {}).get('params', {})
        if optimized_params:
            strategy_params.update(optimized_params)
        
        # Live trading loop
        iteration = 0
        max_iterations = 20  # Extended for multi-asset
        
        while iteration < max_iterations:
            try:
                iteration += 1
                logger.info(f"\n--- FOREX Trading Iteration {iteration}/{max_iterations} ---")
                
                # Get current price
                current_price = broker_connector.get_current_price(forex_symbol)
                if current_price:
                    logger.info(f"Current {forex_symbol} price: {current_price}")
                    
                    # Update market conditions for multi-asset analyzer
                    multi_asset_analyzer.update_market_conditions('forex', {
                        'price': current_price,
                        'volatility': 0.02,  # Placeholder - would calculate from recent data
                        'trend_strength': 0.7,  # Placeholder
                        'volume': 1.0  # Placeholder
                    })
                    
                    # Generate trading signals (simplified for demo)
                    # In real implementation, this would use the full strategy logic
                    logger.info(f"[FOREX SIGNAL] Monitoring {forex_symbol} at ${current_price}")
                    
                    # Check if we should switch to crypto based on performance
                    if iteration % 5 == 0:  # Check every 5 iterations
                        recommendation = multi_asset_analyzer.get_trading_recommendation()
                        if recommendation['next_trade_asset'] == 'crypto':
                            logger.info("Multi-asset analyzer recommends switching to CRYPTO")
                            break
                
                # Wait before next iteration
                if iteration < max_iterations:
                    logger.info("Waiting 30 seconds before next iteration...")
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error in forex trading iteration {iteration}: {e}")
                time.sleep(30)
                continue
        
        logger.info("=== FOREX LIVE TRADING COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error in forex live trading: {e}")
    finally:
        if broker_connector:
            broker_connector.disconnect()

def run_crypto_live_trading(config, dynamic_optimizer, multi_asset_analyzer):
    """Run live trading for crypto assets"""
    import time
    from datetime import datetime, timedelta
    from data.ccxt_feed import CCXTDataFeed
    
    logger.info("Starting CRYPTO live trading...")
    
    # Initialize Kraken data feed
    ccxt_feed = CCXTDataFeed(config)
    kraken_feed = KrakenDataFeed(config) # For order management
    
    # Get crypto symbol configuration
    crypto_symbols = [s for s in config.get('data', {}).get('symbols', []) if s['type'] == 'crypto']
    if not crypto_symbols:
        logger.error("No crypto symbols configured")
        return
    
    crypto_symbol = crypto_symbols[0]['name']  # SOL/USD
    timeframe = crypto_symbols[0]['timeframe']
    
    logger.info(f"Trading {crypto_symbol} on {timeframe} timeframe")
    
    # Get strategy parameters
    strategy_params = config.get('strategies', {}).get('crypto', {}).get('params', {})
    
    # Live trading loop
    iteration = 0
    max_iterations = 20
    
    try:
        while iteration < max_iterations:
            try:
                iteration += 1
                logger.info(f"\n--- CRYPTO Trading Iteration {iteration}/{max_iterations} ---")
                
                # Get current price from Kraken
                # In a real scenario, you'd fetch live data here.
                # For this simulation, we'll get the last closing price.
                end_date = datetime.utcnow()
                start_date = end_date - timedelta(days=1)
                ohlcv = ccxt_feed.get_crypto_data(crypto_symbol, timeframe, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
                if not ohlcv.empty:
                    current_price = ohlcv['close'].iloc[-1]
                if current_price:
                    logger.info(f"Current {crypto_symbol} price: ${current_price:.4f}")
                    
                    # Update market conditions for multi-asset analyzer
                    multi_asset_analyzer.update_market_conditions('crypto', {
                        'price': current_price,
                        'volatility': 0.08,  # Higher volatility for crypto
                        'trend_strength': 0.6,
                        'volume': 1.2
                    })
                    
                    # Generate trading signals (simplified for demo)
                    logger.info(f"[CRYPTO SIGNAL] Monitoring {crypto_symbol} at ${current_price:.4f}")
                    
                    # Check if we should switch to forex based on performance
                    if iteration % 5 == 0:  # Check every 5 iterations
                        recommendation = multi_asset_analyzer.get_trading_recommendation()
                        if recommendation['next_trade_asset'] == 'forex':
                            logger.info("Multi-asset analyzer recommends switching to FOREX")
                            break
                
                else:
                    logger.warning(f"Could not get current price for {crypto_symbol}")
                
                # Wait before next iteration
                if iteration < max_iterations:
                    logger.info("Waiting 30 seconds before next iteration...")
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error in crypto trading iteration {iteration}: {e}")
                time.sleep(30)
                continue
        
        logger.info("=== CRYPTO LIVE TRADING COMPLETED ===")
        
    except Exception as e:
        logger.error(f"Error in crypto live trading: {e}")

# Enhanced Backtesting Classes and Functions

def create_enhanced_backtest_visualization(results, symbol, strategy_name, config):
    """Create comprehensive plotly visualization for backtest results."""
    import plotly.graph_objects as go
    import plotly.subplots as sp
    from plotly.offline import plot
    import pandas as pd
    import numpy as np
    from datetime import datetime
    
    try:
        # Create subplots
        fig = sp.make_subplots(
            rows=4, cols=2,
            subplot_titles=(
                f'{symbol} Price & Signals', 'Portfolio Equity Curve',
                'Drawdown Analysis', 'Trade Distribution',
                'Signal Accuracy', 'Performance Metrics',
                'Monthly Returns Heatmap', 'Risk-Return Analysis'
            ),
            specs=[
                [{"secondary_y": True}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "histogram"}],
                [{"type": "bar"}, {"type": "table"}],
                [{"type": "heatmap"}, {"type": "scatter"}]
            ],
            vertical_spacing=0.08,
            horizontal_spacing=0.1
        )
        
        # Generate sample data for visualization (in real implementation, this would come from backtest)
        dates = pd.date_range(start='2023-01-01', end='2023-12-31', freq='H')[:1000]
        prices = np.cumsum(np.random.randn(1000) * 0.01) + 100
        
        # 1. Price chart with signals
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=prices,
                mode='lines',
                name='Price',
                line=dict(color='blue', width=1)
            ),
            row=1, col=1
        )
        
        # Add buy/sell signals
        buy_signals = np.random.choice(len(dates), 20, replace=False)
        sell_signals = np.random.choice(len(dates), 18, replace=False)
        
        fig.add_trace(
            go.Scatter(
                x=[dates[i] for i in buy_signals],
                y=[prices[i] for i in buy_signals],
                mode='markers',
                name='Buy Signals',
                marker=dict(color='green', size=8, symbol='triangle-up')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=[dates[i] for i in sell_signals],
                y=[prices[i] for i in sell_signals],
                mode='markers',
                name='Sell Signals',
                marker=dict(color='red', size=8, symbol='triangle-down')
            ),
            row=1, col=1
        )
        
        # 2. Portfolio equity curve
        initial_value = results['initial_capital']
        final_value = results['final_value']
        equity_curve = np.linspace(initial_value, final_value, len(dates))
        equity_curve += np.cumsum(np.random.randn(len(dates)) * 50)  # Add some volatility
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=equity_curve,
                mode='lines',
                name='Portfolio Value',
                line=dict(color='green', width=2),
                fill='tonexty'
            ),
            row=1, col=2
        )
        
        # 3. Drawdown analysis
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak * 100
        
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=drawdown,
                mode='lines',
                name='Drawdown %',
                line=dict(color='red', width=1),
                fill='tozeroy'
            ),
            row=2, col=1
        )
        
        # 4. Trade distribution
        trade_returns = np.random.normal(0.5, 2, results['total_trades'])
        
        fig.add_trace(
            go.Histogram(
                x=trade_returns,
                nbinsx=20,
                name='Trade Returns',
                marker=dict(color='blue', opacity=0.7)
            ),
            row=2, col=2
        )
        
        # 5. Signal accuracy chart
        signal_stats = results.get('signal_stats', {})
        accuracy_data = [
            signal_stats.get('signal_accuracy', 0),
            100 - signal_stats.get('signal_accuracy', 0)
        ]
        
        fig.add_trace(
            go.Bar(
                x=['Accurate', 'Inaccurate'],
                y=accuracy_data,
                name='Signal Accuracy',
                marker=dict(color=['green', 'red'])
            ),
            row=3, col=1
        )
        
        # 6. Performance metrics table
        metrics_data = [
            ['Total Return', f"{results['total_return']:.2f}%"],
            ['Sharpe Ratio', f"{results['sharpe_ratio']:.3f}"],
            ['Max Drawdown', f"{results['max_drawdown']:.2f}%"],
            ['Win Rate', f"{results['win_rate']:.2f}%"],
            ['Total Trades', str(results['total_trades'])],
            ['Profit Factor', f"{results['profit_factor']:.3f}"]
        ]
        
        fig.add_trace(
            go.Table(
                header=dict(values=['Metric', 'Value']),
                cells=dict(values=[[row[0] for row in metrics_data],
                                 [row[1] for row in metrics_data]])
            ),
            row=3, col=2
        )
        
        # 7. Monthly returns heatmap
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        monthly_returns = np.random.randn(12) * 3  # Sample monthly returns
        
        fig.add_trace(
            go.Heatmap(
                z=[monthly_returns],
                x=months,
                y=['2023'],
                colorscale='RdYlGn',
                name='Monthly Returns'
            ),
            row=4, col=1
        )
        
        # 8. Risk-return scatter
        fig.add_trace(
            go.Scatter(
                x=[results['max_drawdown']],
                y=[results['total_return']],
                mode='markers',
                name=f'{symbol} Performance',
                marker=dict(size=15, color='blue')
            ),
            row=4, col=2
        )
        
        # Update layout
        fig.update_layout(
            title=f'Enhanced Backtest Results: {symbol} - {strategy_name}',
            height=1200,
            showlegend=True,
            template='plotly_white'
        )
        
        # Save and display visualization using VS Code compatible method
        try:
            from utils.vscode_plotly_fix import create_vscode_compatible_plot
            filename = f"backtest_results_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            success = create_vscode_compatible_plot(
                fig,
                title=f"Enhanced Backtest Results: {symbol} - {strategy_name}",
                filename=filename,
                show_in_browser=False
            )
            
            if success:
                logger.info(f"Enhanced backtest visualization displayed and saved as: {filename}.html")
            else:
                # Fallback to original method
                plot(fig, filename=f"{filename}.html", auto_open=False)
                logger.info(f"Enhanced backtest visualization saved to: {filename}.html")
                
        except ImportError:
            # Fallback to original method
            filename = f"backtest_results_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            plot(fig, filename=filename, auto_open=False)
            logger.info(f"Enhanced backtest visualization saved to: {filename}")
        
    except Exception as e:
        logger.error(f"Error creating enhanced backtest visualization: {e}")

def create_multi_asset_visualization(multi_results, config):
    """Create multi-asset comparative visualization."""
    import plotly.graph_objects as go
    import plotly.subplots as sp
    from plotly.offline import plot
    import pandas as pd
    from datetime import datetime
    
    try:
        individual_results = multi_results['individual_results']
        
        # Create subplots
        fig = sp.make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Asset Performance Comparison',
                'Risk-Return Analysis',
                'Asset Allocation Recommendation',
                'Signal Statistics Comparison'
            ),
            specs=[
                [{"type": "bar"}, {"type": "scatter"}],
                [{"type": "pie"}, {"type": "bar"}]
            ]
        )
        
        # Extract data for visualization
        symbols = list(individual_results.keys())
        returns = [data['results']['total_return'] for data in individual_results.values()]
        sharpe_ratios = [data['results']['sharpe_ratio'] for data in individual_results.values()]
        max_drawdowns = [data['results']['max_drawdown'] for data in individual_results.values()]
        asset_types = [data['asset_type'] for data in individual_results.values()]
        
        # 1. Performance comparison bar chart
        fig.add_trace(
            go.Bar(
                x=symbols,
                y=returns,
                name='Total Return %',
                marker=dict(color=['blue' if t == 'forex' else 'orange' for t in asset_types])
            ),
            row=1, col=1
        )
        
        # 2. Risk-return scatter plot
        fig.add_trace(
            go.Scatter(
                x=max_drawdowns,
                y=returns,
                mode='markers+text',
                text=symbols,
                textposition='top center',
                name='Risk-Return',
                marker=dict(
                    size=15,
                    color=['blue' if t == 'forex' else 'orange' for t in asset_types]
                )
            ),
            row=1, col=2
        )
        
        # 3. Asset allocation pie chart
        allocation = multi_results['allocation']
        fig.add_trace(
            go.Pie(
                labels=['Forex', 'Crypto'],
                values=[allocation['forex_allocation'], allocation['crypto_allocation']],
                name='Allocation'
            ),
            row=2, col=1
        )
        
        # 4. Signal statistics comparison
        signal_counts = []
        for symbol, data in individual_results.items():
            signal_stats = data['results'].get('signal_stats', {})
            signal_counts.append(signal_stats.get('total_signals', 0))
        
        fig.add_trace(
            go.Bar(
                x=symbols,
                y=signal_counts,
                name='Total Signals',
                marker=dict(color='green')
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title='Multi-Asset Backtest Comparative Analysis',
            height=800,
            showlegend=True,
            template='plotly_white'
        )
        
        # Save and display visualization using VS Code compatible method
        try:
            from utils.vscode_plotly_fix import create_vscode_compatible_plot
            filename = f"multi_asset_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            success = create_vscode_compatible_plot(
                fig,
                title="Multi-Asset Backtest Comparative Analysis",
                filename=filename,
                show_in_browser=False
            )
            
            if success:
                logger.info(f"Multi-asset visualization displayed and saved as: {filename}.html")
            else:
                # Fallback to original method
                plot(fig, filename=f"{filename}.html", auto_open=False)
                logger.info(f"Multi-asset visualization saved to: {filename}.html")
                
        except ImportError:
            # Fallback to original method
            filename = f"multi_asset_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            plot(fig, filename=filename, auto_open=False)
            logger.info(f"Multi-asset visualization saved to: {filename}")
        
    except Exception as e:
        logger.error(f"Error creating multi-asset visualization: {e}")