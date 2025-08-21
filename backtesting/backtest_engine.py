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

# Import components from our trading bot structure
from data.data_feed import OANDADataFeed, CCXTDataFeed # Assuming these are the primary data sources for backtesting
from data.preprocessing import DataPreprocessor
from strategies.forex_strategy import ForexStrategy
from strategies.profitable_forex_strategy import ProfitableForexStrategy
from strategies.crypto_strategy import CryptoStrategy
from strategies.futures_strategy import FuturesStrategy
from risk.risk_manager import RiskManager # For integrating risk management into backtesting

class BacktestEngine:
    """
    A backtesting engine that uses backtrader to run and evaluate trading strategies.
    """

    def __init__(self, data_feed=None, preprocessor=None, risk_manager=None, config=None):
        """
        Initialize the BacktestEngine.
 
        Args:
            data_feed: Data feed instance
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

        # Get backtesting config with defaults
        backtest_config = self.config.get('backtesting', {})
        self.initial_capital = backtest_config.get('initial_capital', 10000)
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
            # Get data from data feed
            if asset_type == 'forex':
                raw_data_df = self.data_feed.get_forex_data(
                    symbol,
                    timeframe,
                    self.start_date.strftime('%Y-%m-%d'),
                    self.end_date.strftime('%Y-%m-%d')
                )
            else:
                self.logger.error(f"Unsupported asset type: {asset_type}")
                return None

            if raw_data_df is None or raw_data_df.empty:
                self.logger.error(f"No data retrieved for {symbol}.")
                return None

            # Preprocess the data
            processed_data_df = self.data_preprocessor.preprocess(raw_data_df.copy())
            
            # Ensure the DataFrame has the columns expected by backtrader
            if processed_data_df.index.name != 'datetime':
                processed_data_df.index.name = 'datetime'
            
            # Add data to cerebro
            data = bt.feeds.PandasData(
                dataname=processed_data_df,
                fromdate=self.start_date,
                todate=self.end_date
            )
            self.cerebro.adddata(data)
            
            self.logger.info(f"Data for {symbol} loaded and preprocessed. Shape: {processed_data_df.shape}")
            return processed_data_df
            
        except Exception as e:
            self.logger.error(f"Error loading data for {symbol}: {e}")
            return None

    def add_strategy(self, strategy_name: str, **kwargs):
        """
        Adds a trading strategy to the backtesting engine.

        Args:
            strategy_name (str): Name of the strategy ('ForexStrategy', etc.)
            **kwargs: Parameters to pass to the strategy.
        """
        # Import strategy class based on name
        if strategy_name == 'ForexStrategy':
            strategy_class = ForexStrategy
        elif strategy_name == 'ProfitableForexStrategy':
            strategy_class = ProfitableForexStrategy
        elif strategy_name == 'CryptoStrategy':
            strategy_class = CryptoStrategy
        elif strategy_name == 'FuturesStrategy':
            strategy_class = FuturesStrategy
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
        
        # Add analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade_analyzer')

        # Run the backtest
        strategies = self.cerebro.run()
        
        if not strategies:
            self.logger.error("No strategies executed")
            return None
            
        strategy = strategies[0]  # Get the first strategy instance

        self.logger.info("Backtest finished.")
        
        # Get results
        final_value = self.cerebro.broker.getvalue()
        self.logger.info(f'Final Portfolio Value: {final_value:.2f}')
        
        # Analyze results
        sharpe_analysis = strategy.analyzers.sharpe.get_analysis()
        drawdown_analysis = strategy.analyzers.drawdown.get_analysis()
        returns_analysis = strategy.analyzers.returns.get_analysis()
        trade_analysis = strategy.analyzers.trade_analyzer.get_analysis()
        
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
        
        # Trade statistics with None handling
        total_trades = trade_analysis.get('total', {}).get('closed', 0) or 0
        winning_trades = trade_analysis.get('won', {}).get('total', 0) or 0
        losing_trades = trade_analysis.get('lost', {}).get('total', 0) or 0
        
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
        
        # Return comprehensive results
        return {
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
            'profit_factor': abs(avg_win * winning_trades / (avg_loss * losing_trades)) if (avg_loss != 0 and losing_trades > 0 and avg_win != 0 and winning_trades > 0) else 0.0
        }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {
        'backtesting': {
            'initial_capital': 10000,
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