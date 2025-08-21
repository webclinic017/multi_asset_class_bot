"""
Profit-Focused Genetic Algorithm Optimizer
Optimizes for actual profitability rather than complex metrics
"""

import pygad
import numpy as np
import yaml
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any
import sys
import os
import time

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.backtest_engine import BacktestEngine
from data.data_feed import OANDADataFeed
from data.preprocessing import DataPreprocessor
from risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class ProfitOptimizer:
    """
    Genetic algorithm optimizer focused on maximizing actual profits
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the profit optimizer
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.load_base_config()
        self.setup_parameter_space()
        self.best_fitness = -np.inf
        self.best_params = None
        self.optimization_results = []
        
        # Pre-load and cache data once for speed
        self.cached_data = None
        self.preload_data()
        
        logger.info("ProfitOptimizer initialized")
        
    def load_base_config(self):
        """Load the base configuration"""
        with open(self.config_path, 'r') as file:
            self.base_config = yaml.safe_load(file)
            
    def setup_parameter_space(self):
        """
        Define simplified parameter space focused on profitable parameters
        """
        self.param_bounds = {
            # Moving Average parameters (most important)
            'fast_length': [5, 20],
            'slow_length': [20, 50],
            
            # RSI parameters
            'rsi_period': [10, 21],
            'rsi_oversold': [25, 35],
            'rsi_overbought': [65, 75],
            
            # Risk Management (critical for profitability)
            'stop_loss_percent': [0.005, 0.02],    # 0.5% to 2%
            'take_profit_percent': [0.01, 0.04],   # 1% to 4%
            
            # Trade management
            'max_trades_per_day': [2, 5],
            'min_bars_between_trades': [3, 10],
        }
        
        self.param_names = list(self.param_bounds.keys())
        self.gene_space = [self.param_bounds[param] for param in self.param_names]
        
    def preload_data(self):
        """Pre-load and cache market data to avoid repeated API calls"""
        logger.info("Pre-loading market data for optimization...")
        
        try:
            # Initialize components once
            data_feed = OANDADataFeed(self.base_config)
            preprocessor = DataPreprocessor()
            
            # Load data once
            symbol = self.base_config['data']['symbols'][0]
            
            # Get raw data
            if symbol['type'] == 'forex':
                backtest_config = self.base_config.get('backtesting', {})
                start_date = backtest_config.get('start_date', '2023-01-01')
                end_date = backtest_config.get('end_date', '2023-12-31')
                
                raw_data = data_feed.get_forex_data(
                    symbol['name'],
                    symbol['timeframe'],
                    start_date,
                    end_date
                )
                
                if raw_data is not None and not raw_data.empty:
                    # Preprocess once
                    processed_data = preprocessor.preprocess(raw_data.copy())
                    self.cached_data = processed_data
                    logger.info(f"Data cached successfully. Shape: {processed_data.shape}")
                else:
                    logger.error("Failed to load data for caching")
                    
        except Exception as e:
            logger.error(f"Error pre-loading data: {e}")
            
    def decode_solution(self, solution: np.ndarray) -> Dict[str, Any]:
        """Decode genetic algorithm solution to parameter dictionary"""
        params = {}
        for i, param_name in enumerate(self.param_names):
            if param_name in ['fast_length', 'slow_length', 'rsi_period', 
                             'max_trades_per_day', 'min_bars_between_trades']:
                params[param_name] = int(solution[i])
            else:
                params[param_name] = float(solution[i])
        return params
        
    def evaluate_strategy(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate strategy with given parameters using cached data
        """
        try:
            if self.cached_data is None:
                logger.error("No cached data available")
                return self.get_default_results()
                
            # Use cached data for faster backtesting
            risk_manager = RiskManager(self.base_config.get('risk', {}))
            
            backtest_engine = BacktestEngine(
                data_feed=None,  # We'll use cached data
                preprocessor=None,
                risk_manager=risk_manager,
                config=self.base_config
            )
            
            # Add cached data directly to cerebro
            import backtrader as bt
            data_feed = bt.feeds.PandasData(
                dataname=self.cached_data,
                fromdate=backtest_engine.start_date,
                todate=backtest_engine.end_date
            )
            backtest_engine.cerebro.adddata(data_feed)
            
            # Add strategy with optimized parameters
            strategy_params = params.copy()
            strategy_params['printlog'] = False
            
            # Use the profitable strategy
            backtest_engine.add_strategy(
                'ProfitableForexStrategy',  # Use our new profitable strategy
                **strategy_params
            )
            
            # Run backtest
            results = backtest_engine.run()
            
            if results:
                return results
            else:
                return self.get_default_results()
                
        except Exception as e:
            logger.error(f"Error evaluating strategy: {e}")
            return self.get_default_results()
            
    def get_default_results(self) -> Dict[str, Any]:
        """Return default results for failed backtests"""
        return {
            'final_value': 10000.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 100.0,
            'total_return': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0
        }
        
    def calculate_profit_fitness(self, results: Dict[str, Any]) -> float:
        """
        Calculate fitness score focused on actual profitability
        """
        try:
            # Extract metrics with safe defaults and None handling
            final_value = results.get('final_value')
            if final_value is None:
                final_value = 10000.0
            else:
                final_value = float(final_value)
                
            total_return = results.get('total_return')
            if total_return is None:
                total_return = 0.0
            else:
                total_return = float(total_return)
                
            sharpe_ratio = results.get('sharpe_ratio')
            if sharpe_ratio is None or sharpe_ratio == 'None' or not isinstance(sharpe_ratio, (int, float)):
                sharpe_ratio = 0.0
            else:
                try:
                    sharpe_ratio = float(sharpe_ratio)
                except (ValueError, TypeError):
                    sharpe_ratio = 0.0
                
            max_drawdown = results.get('max_drawdown')
            if max_drawdown is None:
                max_drawdown = 100.0
            else:
                max_drawdown = float(max_drawdown)
                
            win_rate = results.get('win_rate')
            if win_rate is None:
                win_rate = 0.0
            else:
                win_rate = float(win_rate)
                
            total_trades = results.get('total_trades')
            if total_trades is None:
                total_trades = 0
            else:
                total_trades = int(total_trades)
                
            profit_factor = results.get('profit_factor')
            if profit_factor is None:
                profit_factor = 0.0
            else:
                profit_factor = float(profit_factor)
            
            # Minimum trades requirement
            if total_trades < 10:
                return -1000
                
            # Calculate actual profit
            initial_capital = 10000.0
            actual_profit = final_value - initial_capital
            profit_percentage = (actual_profit / initial_capital) * 100
            
            # PRIMARY FOCUS: Actual profit (60% weight)
            profit_score = profit_percentage * 10  # Scale up profit importance
            
            # SECONDARY: Risk-adjusted returns (25% weight)
            if sharpe_ratio > 0:
                sharpe_score = min(sharpe_ratio * 5, 25)  # Cap at 25 points
            else:
                sharpe_score = max(sharpe_ratio * 5, -25)  # Penalty for negative Sharpe
            
            # TERTIARY: Win rate and drawdown (15% weight)
            win_rate_score = (win_rate / 100) * 10  # 0-10 points
            drawdown_score = max(0, (10 - abs(max_drawdown)) / 2)  # 0-5 points
            
            # Composite fitness score
            fitness_score = (0.60 * profit_score + 
                           0.25 * sharpe_score + 
                           0.10 * win_rate_score + 
                           0.05 * drawdown_score)
            
            # BONUSES for exceptional performance
            if profit_percentage > 10:  # 10%+ returns
                fitness_score += 50
            elif profit_percentage > 5:  # 5%+ returns
                fitness_score += 25
            elif profit_percentage > 2:  # 2%+ returns
                fitness_score += 10
                
            # PENALTIES for poor performance
            if profit_percentage < -5:  # Losing more than 5%
                fitness_score -= 100
            elif profit_percentage < -2:  # Losing more than 2%
                fitness_score -= 50
                
            # Penalty for excessive drawdown
            if max_drawdown > 20:
                fitness_score -= 50
            elif max_drawdown > 10:
                fitness_score -= 25
                
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error calculating fitness: {e}")
            return -1000
            
    def fitness_function(self, ga_instance, solution, solution_idx):
        """Fitness function for genetic algorithm"""
        try:
            params = self.decode_solution(solution)
            
            # Parameter validation
            if params['fast_length'] >= params['slow_length']:
                return -1000
                
            # Ensure reasonable risk/reward ratio
            if params['take_profit_percent'] <= params['stop_loss_percent']:
                return -1000
                
            # Evaluate strategy
            results = self.evaluate_strategy(params)
            
            # Debug: Check results structure
            logger.debug(f"Results from evaluate_strategy: {results}")
            
            fitness_score = self.calculate_profit_fitness(results)
            
            # Track best parameters
            if fitness_score > self.best_fitness:
                self.best_fitness = fitness_score
                self.best_params = params.copy()
                logger.info(f"New best fitness: {fitness_score:.4f}")
                logger.info(f"Profit: {results.get('total_return', 0):.2f}%")
                
            # Store results
            result_record = params.copy()
            result_record['fitness_score'] = fitness_score
            result_record['generation'] = getattr(ga_instance, 'generations_completed', 0) if ga_instance else 0
            result_record['solution_idx'] = solution_idx
            result_record.update(results)
            
            self.optimization_results.append(result_record)
            
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error in fitness function: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return -1000
            
    def optimize(self, 
                 num_generations: int = 20,
                 num_parents_mating: int = 8,
                 sol_per_pop: int = 16,
                 mutation_probability: float = 0.2) -> Dict[str, Any]:
        """
        Run profit-focused genetic algorithm optimization
        """
        start_time = time.time()
        
        # Validate and adjust parameters
        if num_parents_mating >= sol_per_pop:
            num_parents_mating = max(2, sol_per_pop // 2)
            logger.warning(f"Adjusted num_parents_mating to {num_parents_mating}")
            
        keep_parents = min(2, num_parents_mating // 2)
        
        logger.info("Starting profit-focused genetic algorithm optimization...")
        logger.info(f"Generations: {num_generations}, Population: {sol_per_pop}")
        logger.info(f"Cached data shape: {self.cached_data.shape if self.cached_data is not None else 'None'}")
        
        # Initialize genetic algorithm
        ga_instance = pygad.GA(
            num_generations=num_generations,
            num_parents_mating=num_parents_mating,
            fitness_func=self.fitness_function,
            sol_per_pop=sol_per_pop,
            num_genes=len(self.param_names),
            gene_space=self.gene_space,
            parent_selection_type="sss",
            keep_parents=keep_parents,
            crossover_type="single_point",
            mutation_type="random",
            mutation_probability=mutation_probability,
            random_seed=42,
            suppress_warnings=True
        )
        
        # Run optimization
        ga_instance.run()
        
        end_time = time.time()
        optimization_time = end_time - start_time
        
        # Get best solution
        solution, solution_fitness, solution_idx = ga_instance.best_solution()
        best_optimized_params = self.decode_solution(solution)
        
        logger.info("Profit optimization completed!")
        logger.info(f"Optimization time: {optimization_time:.2f} seconds")
        logger.info(f"Best fitness score: {solution_fitness:.4f}")
        logger.info(f"Best parameters: {best_optimized_params}")
        
        return {
            'best_params': best_optimized_params,
            'best_fitness': solution_fitness,
            'optimization_time': optimization_time,
            'ga_instance': ga_instance,
            'optimization_history': ga_instance.best_solutions_fitness,
            'all_results': self.optimization_results
        }
        
    def export_results_to_csv(self, output_dir: str = "output") -> str:
        """Export optimization results to CSV"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"profit_optimization_results_{timestamp}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        if not self.optimization_results:
            logger.warning("No optimization results to export")
            return csv_path
            
        df = pd.DataFrame(self.optimization_results)
        
        # Sort by fitness score (best first)
        df = df.sort_values('fitness_score', ascending=False)
        
        # Round numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].round(6)
        
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        logger.info(f"Profit optimization results exported to: {csv_path}")
        logger.info(f"Total results: {len(df)} parameter combinations")
        
        if len(df) > 0:
            best_result = df.iloc[0]
            logger.info(f"Best fitness: {best_result['fitness_score']:.6f}")
            logger.info(f"Best profit: {best_result.get('total_return', 0):.3f}%")
            
        return csv_path

def main():
    """Main function for running profit optimization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Profit-focused genetic algorithm optimization')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--generations', type=int, default=15, help='Number of generations')
    parser.add_argument('--population', type=int, default=12, help='Population size')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run profit optimization
    optimizer = ProfitOptimizer(args.config)
    results = optimizer.optimize(
        num_generations=args.generations,
        sol_per_pop=args.population
    )
    
    # Export results
    csv_path = optimizer.export_results_to_csv()
    
    print(f"\nPROFIT OPTIMIZATION RESULTS:")
    print(f"Best Fitness Score: {results['best_fitness']:.4f}")
    print(f"Optimization Time: {results['optimization_time']:.2f} seconds")
    print(f"Results exported to: {csv_path}")
    print(f"Best Parameters: {results['best_params']}")

if __name__ == "__main__":
    main()