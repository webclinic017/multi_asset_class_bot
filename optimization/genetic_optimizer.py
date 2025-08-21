"""
Genetic Algorithm Optimization for Trading Strategy Parameters
Uses PyGAD to optimize strategy parameters for better win rate and Sharpe ratio
"""

import pygad
import numpy as np
import yaml
import logging
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
            # Moving Average parameters (match ForexStrategy parameter names)
            'fast_length': [5, 20],      # Fast MA period
            'slow_length': [20, 50],     # Slow MA period
            
            # Supply/Demand parameters
            'pivot_period': [3, 10],          # Pivot detection period
            'zone_lookback': [20, 100],       # Zone lookback period
            'min_zone_strength': [1.0, 5.0], # Minimum zone strength
            
            # Risk Management parameters (match ForexStrategy parameter names)
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
            if param_name in ['fast_length', 'slow_length', 'pivot_period', 'zone_lookback']:
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
                
            # Calculate fitness score
            fitness_score = self.calculate_fitness_score(results)
            
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error evaluating strategy: {e}")
            return -1000
            
    def calculate_fitness_score(self, results: Dict[str, Any]) -> float:
        """
        Calculate fitness score from backtest results
        
        Args:
            results: Backtest results dictionary
            
        Returns:
            Composite fitness score
        """
        try:
            # Extract key metrics with safe defaults
            total_return = results.get('total_return', 0) or 0
            sharpe_ratio = results.get('sharpe_ratio', 0) or 0
            max_drawdown = results.get('max_drawdown', 100) or 100
            win_rate = results.get('win_rate', 0) or 0
            total_trades = results.get('total_trades', 0) or 0
            
            # Convert None values to safe defaults
            if total_return is None:
                total_return = 0
            if sharpe_ratio is None:
                sharpe_ratio = 0
            if max_drawdown is None:
                max_drawdown = 100
            if win_rate is None:
                win_rate = 0
            if total_trades is None:
                total_trades = 0
            
            # Ensure minimum number of trades
            if total_trades < 10:
                return -1000
                
            # Normalize max drawdown (lower is better)
            drawdown_score = max(0, (10 - abs(max_drawdown)) / 10)
            
            # Composite fitness score
            # Weights: win_rate (40%), sharpe_ratio (30%), total_return (20%), drawdown (10%)
            fitness_score = (
                0.4 * (abs(win_rate) / 100) +           # Win rate component (0-1)
                0.3 * max(0, min(abs(sharpe_ratio), 3) / 3) +  # Sharpe ratio component (0-1, capped at 3)
                0.2 * max(0, min(abs(total_return), 50) / 50) + # Return component (0-1, capped at 50%)
                0.1 * drawdown_score                # Drawdown component (0-1)
            )
            
            # Bonus for high win rate
            if win_rate and win_rate > 50:
                fitness_score += 0.1 * ((win_rate - 50) / 50)
                
            # Bonus for positive Sharpe ratio
            if sharpe_ratio and sharpe_ratio > 1:
                fitness_score += 0.05 * min((sharpe_ratio - 1), 2)
                
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
            'optimization_history': ga_instance.best_solutions_fitness
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