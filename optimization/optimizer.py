"""
Optimization Module for Trading Bot

This module provides tools for optimizing strategy parameters using
methods like grid search or genetic algorithms.
"""

import backtrader as bt
import logging
import yaml
import os
import pandas as pd
import numpy as np
from itertools import product

# Import components from our trading bot structure
from backtesting.backtest_engine import BacktestEngine
from strategies.forex_strategy import ForexStrategy
from strategies.crypto_strategy import CryptoStrategy
from strategies.futures_strategy import FuturesStrategy

class Optimizer:
    """
    Optimizes trading strategy parameters using various methods.
    """

    def __init__(self, config: dict):
        """
        Initialize the Optimizer.
 
        Args:
            config (dict): Configuration dictionary.
        """
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Optimizer initialized")
        
        self.optimization_method = self.config['optimization']['method']
        self.grid_search_params = self.config['optimization'].get('grid_search_params', {})
        self.population_size = self.config['optimization'].get('population_size', 50)
        self.generations = self.config['optimization'].get('generations', 20)

    def _run_single_backtest(self, strategy_class, data_feed, params: dict):
        """
        Helper to run a single backtest with given parameters.
        """
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(self.config['backtesting']['initial_capital'])
        cerebro.broker.setcommission(commission=self.config['backtesting']['commission'])
        cerebro.broker.set_slippage_perc(perc=self.config['backtesting']['slippage'])
        
        cerebro.adddata(data_feed)
        cerebro.addstrategy(strategy_class, **params)
        
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')

        try:
            strategies = cerebro.run()
            strategy = strategies[0]
            
            sharpe_ratio = strategy.analyzers.sharpe.get_analysis().get('sharperatio', 0.0)
            total_return = strategy.analyzers.returns.get_analysis().get('rtot', 0.0)
            max_drawdown = strategy.analyzers.drawdown.get_analysis().get('max', {}).get('drawdown', 0.0)

            return {
                'params': params,
                'sharpe_ratio': sharpe_ratio,
                'total_return': total_return,
                'max_drawdown': max_drawdown
            }
        except Exception as e:
            self.logger.error(f"Error during single backtest with params {params}: {str(e)}")
            return {
                'params': params,
                'sharpe_ratio': -np.inf, # Penalize errors
                'total_return': 0.0,
                'max_drawdown': 1.0 # Max drawdown for errors
            }

    def grid_search(self, strategy_class, data_feed, param_grid: dict):
        """
        Performs a grid search optimization for strategy parameters.

        Args:
            strategy_class: The strategy class to optimize.
            data_feed: A backtrader data feed object.
            param_grid (dict): A dictionary where keys are parameter names
                               and values are lists of possible values.

        Returns:
            pd.DataFrame: A DataFrame containing results for each parameter combination.
        """
        self.logger.info(f"Starting Grid Search for {strategy_class.__name__}...")
        
        keys = param_grid.keys()
        values = param_grid.values()
        
        results = []
        
        # Generate all combinations of parameters
        for p_values in product(*values):
            params = dict(zip(keys, p_values))
            self.logger.debug(f"Testing params: {params}")
            
            result = self._run_single_backtest(strategy_class, data_feed, params)
            results.append(result)
            
        results_df = pd.DataFrame(results)
        self.logger.info("Grid Search complete.")
        return results_df.sort_values(by='sharpe_ratio', ascending=False) # Sort by Sharpe Ratio

    def genetic_algorithm(self, strategy_class, data_feed, param_ranges: dict):
        """
        Performs genetic algorithm optimization (placeholder/simplified).

        Args:
            strategy_class: The strategy class to optimize.
            data_feed: A backtrader data feed object.
            param_ranges (dict): A dictionary where keys are parameter names
                                 and values are tuples (min_val, max_val, step).

        Returns:
            dict: Best parameters found.
        """
        self.logger.warning("Genetic Algorithm optimization is a simplified placeholder. "
                            "A full implementation would involve more complex GA logic.")
        self.logger.info(f"Starting Genetic Algorithm for {strategy_class.__name__}...")

        best_params = None
        best_sharpe = -np.inf

        # Simplified GA: Randomly sample parameters for a few generations
        for generation in range(self.generations):
            self.logger.info(f"Generation {generation + 1}/{self.generations}")
            for _ in range(self.population_size):
                current_params = {}
                for param, (min_val, max_val, step) in param_ranges.items():
                    # Simple random sampling within range, respecting step
                    num_steps = int((max_val - min_val) / step) + 1
                    possible_values = [min_val + i * step for i in range(num_steps)]
                    current_params[param] = np.random.choice(possible_values)
                
                result = self._run_single_backtest(strategy_class, data_feed, current_params)
                if result['sharpe_ratio'] > best_sharpe:
                    best_sharpe = result['sharpe_ratio']
                    best_params = result['params']
                    self.logger.info(f"New best params found (Sharpe: {best_sharpe:.2f}): {best_params}")
        
        self.logger.info("Genetic Algorithm complete.")
        return best_params

    def optimize(self, strategy_class, data_feed):
        """
        Runs the chosen optimization method.

        Args:
            strategy_class: The strategy class to optimize.
            data_feed: A backtrader data feed object.

        Returns:
            Any: Results of the optimization (DataFrame for grid search, dict for GA).
        """
        if self.optimization_method == "grid_search":
            if not self.grid_search_params:
                raise ValueError("grid_search_params must be defined in config for grid_search method.")
            return self.grid_search(strategy_class, data_feed, self.grid_search_params)
        elif self.optimization_method == "genetic_algorithm":
            # For GA, param_ranges should be defined in config, e.g.,
            # optimization:
            #   method: "genetic_algorithm"
            #   param_ranges:
            #     fast_length: [5, 20, 1]
            #     slow_length: [20, 100, 5]
            if 'param_ranges' not in self.config['optimization']:
                raise ValueError("param_ranges must be defined in config for genetic_algorithm method.")
            return self.genetic_algorithm(strategy_class, data_feed, self.config['optimization']['param_ranges'])
        else:
            raise ValueError(f"Unsupported optimization method: {self.optimization_method}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {
        'backtesting': {
            'initial_capital': 10000,
            'commission': 0.001,
            'slippage': 0.0005,
            'start_date': "2023-01-01",
            'end_date': "2023-01-05"
        },
        'optimization': {
            'method': "grid_search",
            'grid_search_params': {
                'fast_length': [5, 10],
                'slow_length': [20, 30]
            },
            'population_size': 10,
            'generations': 5,
            'param_ranges': { # For genetic algorithm example
                'fast_length': [5, 15, 1],
                'slow_length': [20, 50, 5]
            }
        }
    }
    optimizer = Optimizer(config=dummy_config)
    
    # Create dummy data for testing purposes
    dates = pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05',
                            '2023-01-06', '2023-01-07', '2023-01-08', '2023-01-09', '2023-01-10',
                            '2023-01-11', '2023-01-12', '2023-01-13', '2023-01-14', '2023-01-15',
                            '2023-01-16', '2023-01-17', '2023-01-18', '2023-01-19', '2023-01-20',
                            '2023-01-21', '2023-01-22', '2023-01-23', '2023-01-24', '2023-01-25'])
    dummy_data = pd.DataFrame({
        'open': np.random.rand(25) * 100 + 100,
        'high': np.random.rand(25) * 100 + 105,
        'low': np.random.rand(25) * 100 + 95,
        'close': np.random.rand(25) * 100 + 100,
        'volume': np.random.randint(1000, 5000, 25)
    }, index=dates)
    dummy_data.index.name = 'datetime'

    # Preprocess dummy data (using DataPreprocessor from data.preprocessing)
    from data.preprocessing import DataPreprocessor
    preprocessor = DataPreprocessor()
    processed_dummy_data = preprocessor.preprocess(dummy_data.copy())

    # Create a backtrader data feed from processed data
    data_feed = bt.feeds.PandasData(
        dataname=processed_dummy_data,
        fromdate=optimizer.config['backtesting']['start_date'],
        todate=optimizer.config['backtesting']['end_date']
    )

    print("\n--- Testing Grid Search Optimization (ForexStrategy) ---")
    # Ensure ForexStrategy is imported and available
    from strategies.forex_strategy import ForexStrategy
    grid_results = optimizer.optimize(ForexStrategy, data_feed)
    print("Grid Search Results:")
    print(grid_results)

    # Change method to genetic_algorithm for testing
    optimizer.config['optimization']['method'] = "genetic_algorithm"
    print("\n--- Testing Genetic Algorithm Optimization (ForexStrategy) ---")
    ga_best_params = optimizer.optimize(ForexStrategy, data_feed)
    print("Genetic Algorithm Best Parameters:")
    print(ga_best_params)

    # No need to clean up dummy config file as it's not created