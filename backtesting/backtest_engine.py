"""
Backtesting Engine Module for Trading Bot

This module provides a backtesting framework using backtrader to evaluate
trading strategies with historical data.
"""

import backtrader as bt
import datetime
import logging
import yaml
import os
import pandas as pd
import numpy as np

# Import components from our trading bot structure
from data.data_feed import OANDADataFeed, CCXTDataFeed # Assuming these are the primary data sources for backtesting
from data.kraken_feed import KrakenDataFeed
from data.preprocessing import DataPreprocessor
from strategies.forex_strategy import ForexStrategy
from strategies.improved_forex_strategy import ImprovedForexStrategy
from strategies.profitable_forex_strategy import ProfitableForexStrategy
from strategies.crypto_strategy import CryptoStrategy, SOLStrategy
from strategies.futures_strategy import FuturesStrategy
from strategies.enhanced_forex_strategy import EnhancedForexStrategy
from strategies.enhanced_crypto_strategy import EnhancedCryptoStrategy
from strategies.simple_crypto_strategy import SimpleCryptoStrategy
from strategies.ultra_simple_crypto_strategy import UltraSimpleCryptoStrategy
from strategies.advanced_quant_crypto_strategy import AdvancedQuantCryptoStrategy
from strategies.production_quant_crypto_strategy import ProductionQuantCryptoStrategy
from strategies.realtime_scalping_1m_strategy import RealtimeScalping1MStrategy
from strategies.realtime_scalping_5m_strategy import RealtimeScalping5MStrategy
from strategies.market_making_hft_strategy import MarketMakingHFTStrategy
from strategies.statistical_arbitrage_hft_strategy import StatisticalArbitrageHFTStrategy
from strategies.latency_arbitrage_hft_strategy import LatencyArbitrageHFTStrategy
from strategies.momentum_ignition_hft_strategy import MomentumIgnitionHFTStrategy
from strategies.hft_market_making_strategy import MarketMakingHFTStrategy as NewMarketMakingHFTStrategy
from strategies.hft_statistical_arbitrage_strategy import StatisticalArbitrageHFTStrategy as NewStatArbHFTStrategy
from strategies.hft_momentum_ignition_strategy import MomentumIgnitionHFTStrategy as NewMomentumHFTStrategy
from strategies.hft_order_flow_strategy import OrderFlowImbalanceHFTStrategy
from strategies.production_hft_futures_strategy import ProductionHFTFuturesStrategy
from risk.risk_manager import RiskManager # For integrating risk management into backtesting
from utils.multi_asset_analyzer import MultiAssetAnalyzer

class OrderCountAnalyzer(bt.Analyzer):
    """
    Custom analyzer that counts ALL orders (not just closed trades)
    and classifies them as winning or losing based on portfolio value changes
    """
    
    def __init__(self):
        super(OrderCountAnalyzer, self).__init__()
        self.orders = []
        self.portfolio_values = []
        self.total_orders = 0
        self.winning_orders = 0
        self.losing_orders = 0
        self.last_portfolio_value = None
        
    def start(self):
        """Called when backtest starts"""
        self.last_portfolio_value = self.strategy.broker.getvalue()
        
    def notify_order(self, order):
        """Called when an order status changes"""
        if order.status in [order.Completed]:
            # Order was executed
            current_value = self.strategy.broker.getvalue()
            
            # Classify as winning or losing based on portfolio value change
            if self.last_portfolio_value is not None:
                value_change = current_value - self.last_portfolio_value
                
                self.total_orders += 1
                if value_change > 0:
                    self.winning_orders += 1
                elif value_change < 0:
                    self.losing_orders += 1
                # If value_change == 0, don't count as win or loss
                
                self.orders.append({
                    'value_before': self.last_portfolio_value,
                    'value_after': current_value,
                    'change': value_change,
                    'is_winning': value_change > 0
                })
            
            self.last_portfolio_value = current_value
    
    def get_analysis(self):
        """Return analysis results"""
        return {
            'total_orders': self.total_orders,
            'winning_orders': self.winning_orders,
            'losing_orders': self.losing_orders,
            'orders': self.orders
        }


class BacktestEngine:
    """
    A backtesting engine that uses backtrader to run and evaluate trading strategies.
    """

    def __init__(self, data_feed=None, preprocessor=None, risk_manager=None, config=None):
        """
        Initialize the BacktestEngine.
 
        Args:
            data_feed: Data feed instance (can be OANDA, Kraken, etc.)
            preprocessor: Data preprocessor instance
            risk_manager: Risk manager instance
            config (dict): Configuration dictionary.
        """
        self.config = config or {}
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("BacktestEngine initialized")
        
        self.cerebro = bt.Cerebro()
        self.data_feed = data_feed
        self.data_preprocessor = preprocessor or DataPreprocessor()
        self.risk_manager = risk_manager
        
        # Initialize multi-asset analyzer if enabled
        self.multi_asset_analyzer = None
        if self.config.get('multi_asset', {}).get('analysis_enabled', False):
            self.multi_asset_analyzer = MultiAssetAnalyzer(config_path='config/config.yaml')
            self.logger.info("Multi-asset analyzer initialized")
        
        # Initialize additional data feeds for multi-asset support
        self.kraken_feed = None
        if 'kraken' in self.config:
            self.kraken_feed = KrakenDataFeed(self.config)
            self.logger.info("Kraken data feed initialized")

        self.ccxt_feed = None
        if 'ccxt' in self.config:
            try:
                self.logger.info("Attempting to initialize CCXT data feed...")
                self.ccxt_feed = CCXTDataFeed(self.config)
                self.logger.info("CCXT data feed initialized successfully")
            except Exception as e:
                self.logger.error(f"Failed to initialize CCXT data feed: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                self.ccxt_feed = None
        else:
            self.logger.warning("No 'ccxt' section found in config")

        # Get backtesting config with defaults
        backtest_config = self.config.get('backtesting', {})
        self.initial_capital = backtest_config.get('initial_capital', 100000)
        self.commission = backtest_config.get('commission', 0.001)
        self.slippage = backtest_config.get('slippage', 0.0005)
        
        start_date_str = backtest_config.get('start_date', '2023-01-01')
        end_date_str = backtest_config.get('end_date', '2023-12-31')
        
        self.start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
        self.end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d')

        self.cerebro.broker.setcash(self.initial_capital)
        self.cerebro.broker.setcommission(commission=self.commission)
        self.cerebro.broker.set_slippage_perc(perc=self.slippage)

    def load_data(self, symbol: str, asset_type: str, timeframe: str):
        """
        Loads historical data for backtesting.

        Args:
            symbol (str): The trading pair/instrument (e.g., 'EUR_USD', 'BTC/USDT').
            asset_type (str): Type of asset ('forex', 'crypto', 'futures').
            timeframe (str): Timeframe for the data (e.g., 'H1', '1h', '1 day').

        Returns:
            pandas.DataFrame: Processed data or None if failed
        """
        self.logger.info(f"Loading data for {symbol} ({asset_type}, {timeframe})...")
        
        if not self.data_feed:
            self.logger.error("No data feed provided")
            return None
            
        try:
            # Get data from appropriate data feed
            if asset_type == 'forex':
                if not self.data_feed:
                    self.logger.error("No forex data feed available")
                    return None
                raw_data_df = self.data_feed.get_forex_data(
                    symbol,
                    timeframe,
                    self.start_date.strftime('%Y-%m-%d'),
                    self.end_date.strftime('%Y-%m-%d')
                )
            elif asset_type == 'crypto':
                if not self.ccxt_feed:
                    self.logger.error("CCXT data feed not available")
                    return None

                raw_data_df = self.ccxt_feed.get_crypto_data(
                    symbol,
                    timeframe,
                    self.start_date.strftime('%Y-%m-%d'),
                    self.end_date.strftime('%Y-%m-%d')
                )
            elif asset_type == 'futures':
                # For futures, we use the database directly since we loaded the data from yfinance
                # The data is already stored in the database, so we can retrieve it directly
                from database.database_manager import DatabaseManager
                db_manager = DatabaseManager()
                raw_data_df = db_manager.get_market_data(
                    symbol,
                    timeframe,
                    self.start_date,
                    self.end_date,
                    limit=10000
                )
                if raw_data_df is None or raw_data_df.empty:
                    self.logger.error(f"No futures data found in database for {symbol} {timeframe}")
                    return None
            else:
                self.logger.error(f"Unsupported asset type: {asset_type}")
                return None

            if raw_data_df is None or raw_data_df.empty:
                self.logger.error(f"No data retrieved for {symbol}.")
                return None

            # **Definitive Fix**: Enforce a strict minimum data length to prevent indicator errors.
            # The strategy requires a substantial lookback period for its various calculations
            # (volatility, momentum, Kelly criterion, etc.). A value of 200 is a safe minimum
            # to accommodate the largest lookback window plus a buffer.
            MIN_DATA_LENGTH = 200
            if len(raw_data_df) < MIN_DATA_LENGTH:
                self.logger.error(f"Insufficient data for {symbol}: {len(raw_data_df)} rows. Minimum required is {MIN_DATA_LENGTH}.")
                return None

            # Preprocess the data
            processed_data_df = self.data_preprocessor.preprocess(raw_data_df.copy())
            
            # Check if preprocessing left enough data (increased for backtrader indicators)
            if processed_data_df.empty or len(processed_data_df) < 60:
                self.logger.error(f"Insufficient data after preprocessing for {symbol}: {len(processed_data_df)} rows (minimum 60 required)")
                return None
            
            # Ensure the DataFrame has the required columns for backtrader
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in processed_data_df.columns]
            if missing_columns:
                self.logger.error(f"Missing required columns for {symbol}: {missing_columns}")
                return None
            
            # Ensure the DataFrame has the columns expected by backtrader
            if processed_data_df.index.name != 'datetime':
                processed_data_df.index.name = 'datetime'
            
            # Validate data integrity
            if processed_data_df[required_columns].isnull().any().any():
                self.logger.warning(f"Data contains NaN values for {symbol}, filling with forward fill")
                processed_data_df[required_columns] = processed_data_df[required_columns].fillna(method='ffill').fillna(method='bfill')
            
            # Ensure positive values for OHLCV data
            for col in ['open', 'high', 'low', 'close']:
                if (processed_data_df[col] <= 0).any():
                    self.logger.error(f"Invalid price data (non-positive values) for {symbol} in column {col}")
                    return None
            
            # Add data to cerebro with error handling and proper column mapping
            try:
                # Ensure we have enough data for backtrader's internal calculations
                if len(processed_data_df) < 60:
                    self.logger.error(f"Final data check failed for {symbol}: {len(processed_data_df)} rows (minimum 60 required for backtrader)")
                    return None
                
                # Create a clean DataFrame with only required columns in correct order
                clean_df = processed_data_df[['open', 'high', 'low', 'close', 'volume']].copy()
                
                # Ensure all data is numeric and finite
                for col in clean_df.columns:
                    clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce')
                    if clean_df[col].isnull().any():
                        self.logger.warning(f"Found NaN values in {col} for {symbol}, filling with forward fill")
                        clean_df[col] = clean_df[col].fillna(method='ffill').fillna(method='bfill')
                
                # Final validation - ensure no infinite or NaN values
                if not clean_df.replace([np.inf, -np.inf], np.nan).dropna().equals(clean_df):
                    self.logger.error(f"Data contains infinite or NaN values for {symbol}")
                    return None
                
                data = bt.feeds.PandasData(
                    dataname=clean_df,
                    fromdate=self.start_date,
                    todate=self.end_date
                )
                self.cerebro.adddata(data)
                
                self.logger.info(f"Data for {symbol} loaded and preprocessed. Final shape: {clean_df.shape}")
                return clean_df
                
            except Exception as e:
                self.logger.error(f"Error adding data to cerebro for {symbol}: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return None
            
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {e}")
            return None

    def add_strategy(self, strategy_name: str, **kwargs):
        """
        Adds a trading strategy to the backtesting engine.

        Args:
            strategy_name (str): Name of the strategy ('ForexStrategy', 'SOLStrategy', etc.)
            **kwargs: Parameters to pass to the strategy.
        """
        # Import strategy class based on name
        if strategy_name == 'ForexStrategy':
            strategy_class = ForexStrategy
        elif strategy_name == 'ImprovedForexStrategy':
            strategy_class = ImprovedForexStrategy
        elif strategy_name == 'ProfitableForexStrategy':
            strategy_class = ProfitableForexStrategy
        elif strategy_name == 'EnhancedForexStrategy':
            strategy_class = EnhancedForexStrategy
        elif strategy_name == 'RealtimeScalping1MStrategy':
            strategy_class = RealtimeScalping1MStrategy
        elif strategy_name == 'RealtimeScalping5MStrategy':
            strategy_class = RealtimeScalping5MStrategy
        elif strategy_name == 'CryptoStrategy':
            strategy_class = CryptoStrategy
        elif strategy_name == 'EnhancedCryptoStrategy':
            strategy_class = EnhancedCryptoStrategy
        elif strategy_name == 'SimpleCryptoStrategy':
            strategy_class = SimpleCryptoStrategy
        elif strategy_name == 'UltraSimpleCryptoStrategy':
            strategy_class = UltraSimpleCryptoStrategy
        elif strategy_name == 'AdvancedQuantCryptoStrategy':
            strategy_class = AdvancedQuantCryptoStrategy
        elif strategy_name == 'ProductionQuantCryptoStrategy':
            strategy_class = ProductionQuantCryptoStrategy
        elif strategy_name == 'SOLStrategy':
            strategy_class = SOLStrategy
        elif strategy_name == 'FuturesStrategy':
            strategy_class = FuturesStrategy
        elif strategy_name == 'MarketMakingHFTStrategy':
            strategy_class = MarketMakingHFTStrategy
        elif strategy_name == 'StatisticalArbitrageHFTStrategy':
            strategy_class = StatisticalArbitrageHFTStrategy
        elif strategy_name == 'LatencyArbitrageHFTStrategy':
            strategy_class = LatencyArbitrageHFTStrategy
        elif strategy_name == 'MomentumIgnitionHFTStrategy':
            strategy_class = MomentumIgnitionHFTStrategy
        # New HFT Futures Strategies
        elif strategy_name == 'NewMarketMakingHFTStrategy':
            strategy_class = NewMarketMakingHFTStrategy
        elif strategy_name == 'NewStatisticalArbitrageHFTStrategy':
            strategy_class = NewStatArbHFTStrategy
        elif strategy_name == 'NewMomentumIgnitionHFTStrategy':
            strategy_class = NewMomentumHFTStrategy
        elif strategy_name == 'OrderFlowImbalanceHFTStrategy':
            strategy_class = OrderFlowImbalanceHFTStrategy
        elif strategy_name == 'ProductionHFTFuturesStrategy':
            strategy_class = ProductionHFTFuturesStrategy
        elif strategy_name == 'EnhancedMarketMakingHFTStrategy':
            from strategies.enhanced_market_making_hft_strategy import EnhancedMarketMakingHFTStrategy
            strategy_class = EnhancedMarketMakingHFTStrategy
        else:
            raise ValueError(f"Unknown strategy: {strategy_name}")
            
        self.logger.info(f"Adding strategy: {strategy_name} with params: {kwargs}")
        self.cerebro.addstrategy(strategy_class, **kwargs)

    def run(self):
        """
        Runs the backtest and returns detailed results.
        
        Returns:
            dict: Dictionary containing backtest results and metrics
        """
        self.logger.info("Starting backtest...")
        
        # Add analyzers with error handling
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')
        # Add custom order analyzer to count ALL orders (not just closed trades)
        self.cerebro.addanalyzer(OrderCountAnalyzer, _name='order_counter')

        # Run the backtest with error handling
        try:
            strategies = self.cerebro.run()
        except ZeroDivisionError as e:
            self.logger.warning(f"Division by zero in analyzer (likely no trades made): {e}")
            # Return minimal results for no-trade scenarios
            return {
                'final_value': self.cerebro.broker.getvalue(),
                'initial_capital': self.initial_capital,
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
        
        if not strategies:
            self.logger.error("No strategies executed")
            return None
            
        strategy = strategies[0]  # Get the first strategy instance

        self.logger.info(f"EK log Strategy executed: {strategies[0]}")

        self.logger.info("Backtest finished.")
        
        # Get results
        final_value = self.cerebro.broker.getvalue()
        self.logger.info(f'Final Portfolio Value: {final_value:.2f}')
        
        # Analyze results
        sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
        drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
        returns_analysis = strategy.analyzers.returns.get_analysis()
        trade_analysis = strategy.analyzers.trade_analyzer.get_analysis()
        order_analysis = strategy.analyzers.order_counter.get_analysis()
        
        # Extract metrics with safe defaults and None handling
        sharpe_ratio = sharpe_analysis.get('sharperatio')
        if sharpe_ratio is None:
            sharpe_ratio = 0.0
        else:
            sharpe_ratio = float(sharpe_ratio)
            
        max_drawdown = drawdown_analysis.get('max', {}).get('drawdown')
        if max_drawdown is None:
            max_drawdown = 0.0
        else:
            max_drawdown = float(max_drawdown)
            
        total_return = returns_analysis.get('rtot')
        if total_return is None:
            total_return = 0.0
        else:
            total_return = float(total_return)
        
        # Convert to percentage
        max_drawdown_pct = max_drawdown * 100 if max_drawdown else 0.0
        total_return_pct = total_return * 100 if total_return else 0.0
        
        # Trade statistics - use custom order counter for accurate counts
        self.logger.info(f"=== TRADE ANALYZER RAW OUTPUT ===")
        self.logger.info(f"Full trade_analysis dict: {trade_analysis}")
        self.logger.info(f"Full order_analysis dict: {order_analysis}")
        
        # Use order counter for accurate trade counts
        total_trades = order_analysis.get('total_orders', 0)
        winning_trades = order_analysis.get('winning_orders', 0)
        losing_trades = order_analysis.get('losing_orders', 0)
        
        self.logger.info(f"Order Counter: total={total_trades}, winning={winning_trades}, losing={losing_trades}")
        self.logger.info(f"TradeAnalyzer (for comparison): total={trade_analysis.get('total', {}).get('closed', 0)}, "
                        f"won={trade_analysis.get('won', {}).get('total', 0)}, "
                        f"lost={trade_analysis.get('lost', {}).get('total', 0)}")
        
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        
        avg_win = trade_analysis.get('won', {}).get('pnl', {}).get('average')
        if avg_win is None:
            avg_win = 0.0
        else:
            avg_win = float(avg_win)
            
        avg_loss = trade_analysis.get('lost', {}).get('pnl', {}).get('average')
        if avg_loss is None:
            avg_loss = 0.0
        else:
            avg_loss = float(avg_loss)
        
        # Log results
        self.logger.info(f'Sharpe Ratio: {sharpe_ratio:.2f}')
        self.logger.info(f'Max Drawdown: {max_drawdown_pct:.2f}%')
        self.logger.info(f'Total Return: {total_return_pct:.2f}%')
        self.logger.info(f'Total Trades: {total_trades}')
        self.logger.info(f'Winning Trades: {winning_trades}')
        self.logger.info(f'Losing Trades: {losing_trades}')
        self.logger.info(f'Win Rate: {win_rate:.2f}%')
        self.logger.info(f'Avg Win: {avg_win:.2f}')
        self.logger.info(f'Avg Loss: {avg_loss:.2f}')
        
        # Prepare comprehensive results
        results = {
            'final_value': final_value,
            'initial_capital': self.initial_capital,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown_pct,
            'total_return': total_return_pct,
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': self._calculate_profit_factor(avg_win, winning_trades, avg_loss, losing_trades)
        }
        
        return results
    
    def _calculate_profit_factor(self, avg_win, winning_trades, avg_loss, losing_trades):
        """
        Calculate profit factor with safe handling of None values and division by zero
        
        Args:
            avg_win: Average winning trade amount
            winning_trades: Number of winning trades
            avg_loss: Average losing trade amount
            losing_trades: Number of losing trades
            
        Returns:
            float: Profit factor or 0.0 if calculation fails
        """
        try:
            # Ensure all values are valid numbers
            if (avg_win is None or winning_trades is None or
                avg_loss is None or losing_trades is None):
                return 0.0
            
            # Convert to float and handle None/invalid values
            avg_win = float(avg_win) if avg_win is not None else 0.0
            winning_trades = int(winning_trades) if winning_trades is not None else 0
            avg_loss = float(avg_loss) if avg_loss is not None else 0.0
            losing_trades = int(losing_trades) if losing_trades is not None else 0
            
            # Calculate total wins and losses
            total_wins = avg_win * winning_trades
            total_losses = abs(avg_loss * losing_trades)  # Ensure positive
            
            # Avoid division by zero
            if total_losses == 0 or losing_trades == 0:
                return total_wins if total_wins > 0 else 0.0
            
            # Calculate profit factor
            profit_factor = total_wins / total_losses
            
            # Return reasonable bounds (cap at 100 for extreme cases)
            return min(profit_factor, 100.0)
            
        except (TypeError, ValueError, ZeroDivisionError) as e:
            self.logger.warning(f"Error calculating profit factor: {e}")
            return 0.0
    
    def run_multi_asset_backtest(self, symbols_config: list):
        """
        Run backtests for multiple assets and compare performance
        
        Args:
            symbols_config (list): List of symbol configurations from config file
            
        Returns:
            dict: Multi-asset analysis results
        """
        self.logger.info("Starting multi-asset backtest...")
        
        if not self.multi_asset_analyzer:
            self.logger.warning("Multi-asset analyzer not initialized")
            return None
        
        all_results = {}
        
        for symbol_config in symbols_config:
            symbol = symbol_config['name']
            asset_type = symbol_config['type']
            timeframe = symbol_config['timeframe']
            
            self.logger.info(f"Running backtest for {symbol} ({asset_type})")
            
            try:
                # Create new cerebro instance for each asset
                self.cerebro = bt.Cerebro()
                self.cerebro.broker.setcash(self.initial_capital)
                self.cerebro.broker.setcommission(commission=self.commission)
                self.cerebro.broker.set_slippage_perc(perc=self.slippage)
                
                # Load data for this asset with enhanced validation
                data = self.load_data(symbol, asset_type, timeframe)
                if data is None or data.empty:
                    self.logger.error(f"Failed to load data for {symbol} - no data available for the specified date range")
                    continue
                
                # Validate data has minimum required rows
                if len(data) < 50:
                    self.logger.error(f"Insufficient data for {symbol}: {len(data)} rows (minimum 50 required)")
                    continue
                
                # Add appropriate strategy with error handling
                try:
                    if asset_type == 'forex':
                        strategy_config = self.config.get('strategies', {}).get('forex', {})
                        strategy_name = strategy_config.get('name', 'ForexStrategy')
                        strategy_params = strategy_config.get('params', {}).copy()
                    elif asset_type == 'crypto':
                        strategy_config = self.config.get('strategies', {}).get('crypto', {})
                        strategy_name = strategy_config.get('name', 'SOLStrategy')
                        strategy_params = strategy_config.get('params', {}).copy()
                    else:
                        self.logger.error(f"Unsupported asset type: {asset_type}")
                        continue
                    
                    # Ensure strategy params are not None
                    if strategy_params is None:
                        strategy_params = {}
                    
                    # Disable logging for individual backtests
                    strategy_params['printlog'] = False
                    
                    # Validate critical parameters based on strategy type
                    if strategy_name == 'UltraSimpleCryptoStrategy':
                        required_params = ['lookback_period', 'price_change_threshold']
                        for param in required_params:
                            if param not in strategy_params or strategy_params[param] is None:
                                self.logger.warning(f"Missing or None parameter {param} for {symbol}, using default")
                                if param == 'lookback_period':
                                    strategy_params[param] = 5
                                elif param == 'price_change_threshold':
                                    strategy_params[param] = 0.02
                    elif strategy_name == 'AdvancedQuantCryptoStrategy':
                        required_params = ['vol_lookback', 'momentum_short', 'bb_period', 'rsi_period']
                        for param in required_params:
                            if param not in strategy_params or strategy_params[param] is None:
                                self.logger.warning(f"Missing or None parameter {param} for {symbol}, using default")
                                if param == 'vol_lookback':
                                    strategy_params[param] = 20
                                elif param == 'momentum_short':
                                    strategy_params[param] = 5
                                elif param == 'bb_period':
                                    strategy_params[param] = 20
                                elif param == 'rsi_period':
                                    strategy_params[param] = 14
                    elif strategy_name == 'ProductionQuantCryptoStrategy':
                        required_params = ['vol_lookback', 'momentum_short', 'bb_period', 'rsi_period']
                        for param in required_params:
                            if param not in strategy_params or strategy_params[param] is None:
                                self.logger.warning(f"Missing or None parameter {param} for {symbol}, using default")
                                if param == 'vol_lookback':
                                    strategy_params[param] = 20
                                elif param == 'momentum_short':
                                    strategy_params[param] = 5
                                elif param == 'bb_period':
                                    strategy_params[param] = 20
                                elif param == 'rsi_period':
                                    strategy_params[param] = 14
                    else:
                        # For other strategies (forex, enhanced crypto, etc.)
                        required_params = ['fast_length', 'slow_length', 'rsi_period']
                        for param in required_params:
                            if param not in strategy_params or strategy_params[param] is None:
                                self.logger.warning(f"Missing or None parameter {param} for {symbol}, using default")
                                if param == 'fast_length':
                                    strategy_params[param] = 10
                                elif param == 'slow_length':
                                    strategy_params[param] = 21
                                elif param == 'rsi_period':
                                    strategy_params[param] = 14
                    
                    self.add_strategy(strategy_name, **strategy_params)
                    
                except Exception as e:
                    self.logger.error(f"Error setting up strategy for {symbol}: {e}")
                    continue
                
                # Run backtest with enhanced error handling
                try:
                    results = self.run()
                    
                    if results and isinstance(results, dict):
                        # Validate results contain required fields
                        required_fields = ['total_return', 'sharpe_ratio', 'final_value']
                        if all(field in results and results[field] is not None for field in required_fields):
                            all_results[symbol] = {
                                'asset_type': asset_type,
                                'results': results
                            }
                            
                            # Analyze with multi-asset analyzer
                            self.multi_asset_analyzer.analyze_asset_performance(
                                asset_type, symbol, results
                            )
                            
                            self.logger.info(f"Completed backtest for {symbol}: "
                                           f"Return: {results['total_return']:.2f}%, "
                                           f"Sharpe: {results['sharpe_ratio']:.2f}")
                        else:
                            self.logger.error(f"Invalid results for {symbol}: missing required fields")
                    else:
                        self.logger.error(f"No valid results returned for {symbol}")
                        
                except Exception as e:
                    self.logger.error(f"Error running backtest execution for {symbol}: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    continue
                
            except Exception as e:
                self.logger.error(f"Error running backtest for {symbol}: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        # Generate multi-asset analysis
        if all_results:
            comparison = self.multi_asset_analyzer.compare_asset_classes()
            allocation = self.multi_asset_analyzer.get_optimal_asset_allocation()
            recommendation = self.multi_asset_analyzer.get_trading_recommendation()
            
            # Export analysis report
            report_path = self.multi_asset_analyzer.export_analysis_report()
            
            multi_asset_results = {
                'individual_results': all_results,
                'comparison': comparison,
                'allocation': allocation,
                'recommendation': recommendation,
                'report_path': report_path
            }
            
            self.logger.info("=== MULTI-ASSET ANALYSIS COMPLETE ===")
            self.logger.info(f"Recommendation: Focus on {recommendation['primary_focus']}")
            self.logger.info(f"Allocation: {allocation['forex_allocation']:.1f}% Forex, "
                           f"{allocation['crypto_allocation']:.1f}% Crypto")
            self.logger.info(f"Next trade: {recommendation['next_trade_asset']}")
            
            return multi_asset_results
        
        else:
            self.logger.error("No successful backtests completed")
            return None

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {
        'backtesting': {
            'initial_capital': 100000,
            'commission': 0.001,
            'slippage': 0.0005,
            'start_date': "2023-01-01",
            'end_date': "2023-01-05" # Short period for quick test
        },
        'trading': {
            'risk_per_trade': 0.01,
            'max_drawdown_limit': 0.20,
            'max_concurrent_positions': 5,
            'position_sizing_method': "fixed_fraction",
            'fixed_fraction': 0.02
        },
        'oanda': { # Required by OANDADataFeed
            'account_id': 'dummy',
            'access_token': 'dummy',
            'practice': True
        },
        'ccxt': { # Required by CCXTDataFeed
            'api_key': 'dummy',
            'secret': 'dummy',
            'password': 'dummy'
        }
    }
    engine = BacktestEngine(config=dummy_config)

    # Create dummy data for testing purposes
    # In a real scenario, this would come from DataFeed
    dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05'])
    dummy_data = pd.DataFrame({
        'open': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'close': [100.5, 101.5, 102.5, 103.5, 104.5],
        'volume': [1000, 1100, 1200, 1300, 1400]
    }, index=dates)
    dummy_data.index.name = 'datetime' # Ensure index name is 'datetime' for backtrader

    # Preprocess dummy data
    preprocessor = DataPreprocessor()
    processed_dummy_data = preprocessor.preprocess(dummy_data.copy())

    # Add processed dummy data to cerebro
    data_feed = bt.feeds.PandasData(
        dataname=processed_dummy_data,
        fromdate=engine.start_date,
        todate=engine.end_date
    )
    engine.cerebro.adddata(data_feed)

    # Add a strategy (e.g., ForexStrategy)
    engine.add_strategy(ForexStrategy, printlog=True)

    # Run the backtest
    engine.run_backtest()

    # No need to clean up dummy config file as it's not created