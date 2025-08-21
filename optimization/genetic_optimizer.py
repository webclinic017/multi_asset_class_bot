"""
Genetic Algorithm Optimization for Trading Strategy Parameters
Uses PyGAD to optimize strategy parameters for better win rate and Sharpe ratio
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

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.backtest_engine import BacktestEngine
from data.data_feed import OANDADataFeed
from data.preprocessing import DataPreprocessor
from risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class GeneticOptimizer:
    """
    Genetic Algorithm optimizer for trading strategy parameters
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the genetic optimizer
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.load_base_config()
        self.setup_parameter_space()
        self.best_fitness = -np.inf
        self.best_params = None
        self.optimization_results = []  # Store all optimization results
        
    def load_base_config(self):
        """Load the base configuration"""
        with open(self.config_path, 'r') as file:
            self.base_config = yaml.safe_load(file)
            
    def setup_parameter_space(self):
        """
        Define the parameter space for optimization
        Each parameter has [min_value, max_value] bounds
        """
        self.param_bounds = {
            # Moving Average parameters
            'fast_length': [5, 20],      # Fast MA period
            'slow_length': [20, 50],     # Slow MA period
            
            # RSI parameters
            'rsi_period': [10, 21],           # RSI period
            'rsi_oversold': [20, 35],         # RSI oversold level
            'rsi_overbought': [65, 80],       # RSI overbought level
            
            # MACD parameters
            'macd_fast': [8, 16],             # MACD fast EMA
            'macd_slow': [20, 30],            # MACD slow EMA
            'macd_signal': [7, 12],           # MACD signal line
            
            # Supply/Demand parameters
            'pivot_period': [3, 10],          # Pivot detection period
            'zone_lookback': [20, 100],       # Zone lookback period
            'min_zone_strength': [1.0, 5.0], # Minimum zone strength
            
            # Risk Management parameters
            'stop_loss_percent': [0.005, 0.03],     # Stop loss percentage (0.5% to 3%)
            'take_profit_percent': [0.01, 0.05],    # Take profit percentage (1% to 5%)
        }
        
        # Create parameter names list and bounds arrays for PyGAD
        self.param_names = list(self.param_bounds.keys())
        self.gene_space = [self.param_bounds[param] for param in self.param_names]
        
    def decode_solution(self, solution: np.ndarray) -> Dict[str, Any]:
        """
        Decode genetic algorithm solution to parameter dictionary
        
        Args:
            solution: Array of parameter values from GA
            
        Returns:
            Dictionary of parameter names and values
        """
        params = {}
        for i, param_name in enumerate(self.param_names):
            if param_name in ['fast_length', 'slow_length', 'pivot_period', 'zone_lookback',
                             'rsi_period', 'rsi_oversold', 'rsi_overbought',
                             'macd_fast', 'macd_slow', 'macd_signal']:
                # Integer parameters
                params[param_name] = int(solution[i])
            else:
                # Float parameters
                params[param_name] = float(solution[i])
                
        return params
        
    def create_config_with_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a configuration dictionary with optimized parameters
        
        Args:
            params: Dictionary of optimized parameters
            
        Returns:
            Complete configuration dictionary
        """
        import copy
        config = copy.deepcopy(self.base_config)
        
        # Only update parameters that exist in our parameter space
        # This ensures we don't add unexpected parameters
        for param_name, param_value in params.items():
            if param_name in self.param_names:
                config['strategy']['params'][param_name] = param_value
        
        return config
        
    def fitness_function(self, ga_instance, solution, solution_idx):
        """
        Fitness function for genetic algorithm
        Evaluates strategy performance with given parameters
        
        Args:
            ga_instance: PyGAD instance
            solution: Parameter values array
            solution_idx: Solution index
            
        Returns:
            Fitness score (higher is better)
        """
        try:
            # Decode parameters
            params = self.decode_solution(solution)
            
            # Ensure fast_length < slow_length
            if params['fast_length'] >= params['slow_length']:
                return -1000  # Penalty for invalid parameter combination
                
            # Create configuration with optimized parameters
            config = self.create_config_with_params(params)
            
            # Run backtest with these parameters
            fitness_score = self.evaluate_strategy(config)
            
            # Track best parameters
            if fitness_score > self.best_fitness:
                self.best_fitness = fitness_score
                self.best_params = params.copy()
                logger.info(f"New best fitness: {fitness_score:.4f}")
                logger.info(f"Best params: {self.best_params}")
            
            # Store results for DataFrame export
            result_record = params.copy()
            result_record['fitness_score'] = fitness_score
            result_record['generation'] = getattr(ga_instance, 'generations_completed', 0) if ga_instance else 0
            result_record['solution_idx'] = solution_idx
            
            # Add results from backtest if available
            if hasattr(self, '_last_backtest_results') and self._last_backtest_results:
                result_record.update(self._last_backtest_results)
            
            self.optimization_results.append(result_record)
                
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error in fitness function: {e}")
            return -1000  # Penalty for errors
            
    def evaluate_strategy(self, config: Dict[str, Any]) -> float:
        """
        Evaluate strategy performance with given configuration
        
        Args:
            config: Strategy configuration
            
        Returns:
            Fitness score combining multiple metrics
        """
        try:
            # Initialize components - pass the full config as OANDADataFeed expects it
            data_feed = OANDADataFeed(config)
            preprocessor = DataPreprocessor()  # DataPreprocessor doesn't take config in __init__
            risk_manager = RiskManager(config['risk'])
            
            # Initialize backtest engine
            backtest_engine = BacktestEngine(
                data_feed=data_feed,
                preprocessor=preprocessor,
                risk_manager=risk_manager,
                config=config
            )
            
            # Load and preprocess data
            symbol = config['data']['symbols'][0]
            data = backtest_engine.load_data(
                symbol=symbol['name'],
                asset_type=symbol['type'],
                timeframe=symbol['timeframe']
            )
            
            if data is None or len(data) < 100:
                return -1000
                
            # Add strategy and run backtest
            strategy_params = config['strategy']['params'].copy()
            strategy_params['printlog'] = False  # Disable logging for optimization
            
            backtest_engine.add_strategy(
                config['strategy']['name'],
                **strategy_params
            )
            
            # Run backtest
            results = backtest_engine.run()
            
            if results is None:
                return -1000
                
            # Store results for later use in fitness function
            self._last_backtest_results = results.copy() if results else {}
            
            # Calculate fitness score
            fitness_score = self.calculate_fitness_score(results)
            
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error evaluating strategy: {e}")
            return -1000
            
    def calculate_fitness_score(self, results: Dict[str, Any]) -> float:
        """
        Calculate fitness score from backtest results
        Focus on maximizing Sharpe ratio and profit
        
        Args:
            results: Backtest results dictionary
            
        Returns:
            Composite fitness score
        """
        try:
            # Extract key metrics with safe defaults and None handling
            total_return = results.get('total_return')
            sharpe_ratio = results.get('sharpe_ratio')
            max_drawdown = results.get('max_drawdown')
            win_rate = results.get('win_rate')
            total_trades = results.get('total_trades')
            final_value = results.get('final_value')
            
            # Convert None values to safe defaults
            total_return = float(total_return) if total_return is not None else 0.0
            sharpe_ratio = float(sharpe_ratio) if sharpe_ratio is not None else 0.0
            max_drawdown = float(max_drawdown) if max_drawdown is not None else 100.0
            win_rate = float(win_rate) if win_rate is not None else 0.0
            total_trades = int(total_trades) if total_trades is not None else 0
            final_value = float(final_value) if final_value is not None else 10000.0
            
            # Ensure minimum number of trades
            if total_trades < 5:
                return -1000
                
            # Calculate actual profit/loss
            initial_capital = 10000  # From config
            actual_profit = (final_value or 10000) - initial_capital
            profit_percentage = (actual_profit / initial_capital) * 100
            
            # Normalize metrics for scoring
            # Sharpe ratio component (0-1, higher weight)
            sharpe_score = 0
            if sharpe_ratio > 0:
                sharpe_score = min(sharpe_ratio / 3.0, 1.0)  # Cap at 3.0 Sharpe
            elif sharpe_ratio < 0:
                sharpe_score = max(sharpe_ratio / 3.0, -1.0)  # Penalty for negative Sharpe
            
            # Profit component (0-1, focus on actual profit)
            profit_score = 0
            if profit_percentage > 0:
                profit_score = min(profit_percentage / 20.0, 1.0)  # Cap at 20% return
            elif profit_percentage < 0:
                profit_score = max(profit_percentage / 20.0, -1.0)  # Penalty for losses
            
            # Win rate component (0-1)
            win_rate_score = win_rate / 100.0
            
            # Drawdown component (0-1, lower drawdown is better)
            drawdown_score = max(0, (5 - abs(max_drawdown)) / 5)
            
            # Enhanced composite fitness score
            # Weights: Sharpe ratio (40%), Profit (35%), Win rate (15%), Drawdown (10%)
            fitness_score = (
                0.40 * sharpe_score +      # Sharpe ratio (most important)
                0.35 * profit_score +      # Actual profit (second most important)
                0.15 * win_rate_score +    # Win rate
                0.10 * drawdown_score      # Risk control
            )
            
            # Bonus for exceptional performance
            if sharpe_ratio > 1.5 and profit_percentage > 5:
                fitness_score += 0.2  # Significant bonus for great performance
            elif sharpe_ratio > 1.0 and profit_percentage > 2:
                fitness_score += 0.1  # Moderate bonus for good performance
            
            # Penalty for poor performance
            if sharpe_ratio < 0 or profit_percentage < -5:
                fitness_score -= 0.5  # Heavy penalty for losses
            
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error calculating fitness score: {e}")
            logger.error(f"Results: {results}")
            return -1000
            
    def optimize(self, 
                 num_generations: int = 50,
                 num_parents_mating: int = 10,
                 sol_per_pop: int = 20,
                 mutation_probability: float = 0.1) -> Dict[str, Any]:
        """
        Run genetic algorithm optimization
        
        Args:
            num_generations: Number of generations to evolve
            num_parents_mating: Number of parents for mating
            sol_per_pop: Solutions per population
            mutation_probability: Probability of mutation
            
        Returns:
            Dictionary with optimization results
        """
        logger.info("Starting genetic algorithm optimization...")
        logger.info(f"Parameter space: {self.param_names}")
        logger.info(f"Generations: {num_generations}, Population: {sol_per_pop}")
        
        # Initialize genetic algorithm
        ga_instance = pygad.GA(
            num_generations=num_generations,
            num_parents_mating=num_parents_mating,
            fitness_func=self.fitness_function,
            sol_per_pop=sol_per_pop,
            num_genes=len(self.param_names),
            gene_space=self.gene_space,
            parent_selection_type="sss",  # Steady-state selection
            keep_parents=2,
            crossover_type="single_point",
            mutation_type="random",
            mutation_probability=mutation_probability,
            random_seed=42,
            suppress_warnings=True
        )
        
        # Run optimization
        ga_instance.run()
        
        # Get best solution
        solution, solution_fitness, solution_idx = ga_instance.best_solution()
        best_optimized_params = self.decode_solution(solution)
        
        # Get complete strategy parameters
        best_complete_params = self.get_complete_strategy_params(best_optimized_params)
        
        logger.info("Optimization completed!")
        logger.info(f"Best fitness score: {solution_fitness:.4f}")
        logger.info(f"Best optimized parameters: {best_optimized_params}")
        
        return {
            'best_params': best_complete_params,  # Return complete parameters
            'best_optimized_params': best_optimized_params,  # Also return just optimized ones
            'best_fitness': solution_fitness,
            'ga_instance': ga_instance,
            'optimization_history': ga_instance.best_solutions_fitness,
            'all_results': self.optimization_results  # Include all results
        }
        
    def get_complete_strategy_params(self, optimized_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get complete strategy parameters by merging optimized params with base config
        
        Args:
            optimized_params: Optimized parameters from genetic algorithm
            
        Returns:
            Complete parameter dictionary for strategy
        """
        # Start with base strategy parameters
        complete_params = self.base_config['strategy']['params'].copy()
        
        # Update with optimized parameters
        for param_name, param_value in optimized_params.items():
            if param_name in self.param_names:
                complete_params[param_name] = param_value
        
        return complete_params
    
    def save_optimized_config(self, best_params: Dict[str, Any], output_path: str):
        """
        Save optimized configuration to file
        
        Args:
            best_params: Best parameters from optimization
            output_path: Path to save optimized configuration
        """
        optimized_config = self.create_config_with_params(best_params)
        
        with open(output_path, 'w') as file:
            yaml.dump(optimized_config, file, default_flow_style=False, indent=2)
            
        logger.info(f"Optimized configuration saved to: {output_path}")
    
    def export_results_to_csv(self, output_dir: str = "output") -> str:
        """
        Export optimization results to CSV file with timestamp
        
        Args:
            output_dir: Directory to save the CSV file
            
        Returns:
            Path to the saved CSV file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"optimization_results_{timestamp}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        if not self.optimization_results:
            logger.warning("No optimization results to export")
            return csv_path
        
        # Create DataFrame from results
        df = pd.DataFrame(self.optimization_results)
        
        # Reorder columns for better readability
        priority_columns = [
            'generation', 'solution_idx', 'fitness_score',
            'fast_length', 'slow_length', 'rsi_period', 'rsi_oversold', 'rsi_overbought',
            'macd_fast', 'macd_slow', 'macd_signal', 'pivot_period', 'zone_lookback',
            'min_zone_strength', 'stop_loss_percent', 'take_profit_percent',
            'final_value', 'total_return', 'sharpe_ratio', 'max_drawdown',
            'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
            'avg_win', 'avg_loss', 'profit_factor'
        ]
        
        # Reorder columns, keeping any additional columns at the end
        available_columns = [col for col in priority_columns if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in priority_columns]
        ordered_columns = available_columns + remaining_columns
        
        df = df[ordered_columns]
        
        # Sort by fitness score (best first)
        df = df.sort_values('fitness_score', ascending=False)
        
        # Round numeric columns for better readability
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].round(6)
        
        # Export to CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Optimization results exported to: {csv_path}")
        logger.info(f"Total results exported: {len(df)} parameter combinations")
        
        # Log summary statistics
        if len(df) > 0:
            logger.info(f"Best fitness score: {df['fitness_score'].max():.6f}")
            logger.info(f"Average fitness score: {df['fitness_score'].mean():.6f}")
            if 'win_rate' in df.columns:
                logger.info(f"Best win rate: {df['win_rate'].max():.2f}%")
                logger.info(f"Average win rate: {df['win_rate'].mean():.2f}%")
        
        return csv_path

def main():
    """Main function for running optimization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Optimize trading strategy parameters using genetic algorithm')
    parser.add_argument('--config', required=True, help='Path to base configuration file')
    parser.add_argument('--output', required=True, help='Path to save optimized configuration')
    parser.add_argument('--generations', type=int, default=30, help='Number of generations')
    parser.add_argument('--population', type=int, default=20, help='Population size')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run optimization
    optimizer = GeneticOptimizer(args.config)
    results = optimizer.optimize(
        num_generations=args.generations,
        sol_per_pop=args.population
    )
    
    # Save optimized configuration
    optimizer.save_optimized_config(results['best_params'], args.output)
    
    print(f"\nOptimization Results:")
    print(f"Best Fitness Score: {results['best_fitness']:.4f}")
    print(f"Best Parameters: {results['best_params']}")

if __name__ == "__main__":
    main()