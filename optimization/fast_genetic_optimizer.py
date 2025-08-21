"""
High-Performance Genetic Algorithm Optimization with GPU Acceleration
Optimized version with caching, parallel processing, and GPU support
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
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import pickle
import hashlib
from functools import lru_cache
import time

# GPU acceleration imports (optional)
try:
    import cupy as cp
    GPU_AVAILABLE = True
    print("GPU acceleration available with CuPy")
except ImportError:
    GPU_AVAILABLE = False
    print("GPU acceleration not available - using CPU")

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.backtest_engine import BacktestEngine
from data.data_feed import OANDADataFeed
from data.preprocessing import DataPreprocessor
from risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class FastGeneticOptimizer:
    """
    High-performance genetic algorithm optimizer with GPU acceleration and caching
    """
    
    def __init__(self, config_path: str):
        """
        Initialize the fast genetic optimizer
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.load_base_config()
        self.setup_parameter_space()
        self.best_fitness = -np.inf
        self.best_params = None
        self.optimization_results = []
        
        # Performance optimizations
        self.data_cache = {}
        self.backtest_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Pre-load and cache data once
        self.cached_data = None
        self.preload_data()
        
        logger.info("FastGeneticOptimizer initialized with performance optimizations")
        
    def load_base_config(self):
        """Load the base configuration"""
        with open(self.config_path, 'r') as file:
            self.base_config = yaml.safe_load(file)
            
    def setup_parameter_space(self):
        """
        Define the parameter space for optimization
        """
        self.param_bounds = {
            # Moving Average parameters
            'fast_length': [5, 20],
            'slow_length': [20, 50],
            
            # RSI parameters
            'rsi_period': [10, 21],
            'rsi_oversold': [20, 35],
            'rsi_overbought': [65, 80],
            
            # MACD parameters
            'macd_fast': [8, 16],
            'macd_slow': [20, 30],
            'macd_signal': [7, 12],
            
            # Supply/Demand parameters
            'pivot_period': [3, 10],
            'zone_lookback': [20, 100],
            'min_zone_strength': [1.0, 5.0],
            
            # Risk Management parameters
            'stop_loss_percent': [0.005, 0.03],
            'take_profit_percent': [0.01, 0.05],
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
            
    def get_param_hash(self, params: Dict[str, Any]) -> str:
        """Generate hash for parameter combination for caching"""
        param_str = str(sorted(params.items()))
        return hashlib.md5(param_str.encode()).hexdigest()
        
    def decode_solution(self, solution: np.ndarray) -> Dict[str, Any]:
        """Decode genetic algorithm solution to parameter dictionary"""
        params = {}
        for i, param_name in enumerate(self.param_names):
            if param_name in ['fast_length', 'slow_length', 'pivot_period', 'zone_lookback',
                             'rsi_period', 'rsi_oversold', 'rsi_overbought',
                             'macd_fast', 'macd_slow', 'macd_signal']:
                params[param_name] = int(solution[i])
            else:
                params[param_name] = float(solution[i])
        return params
        
    def fast_backtest_evaluation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fast backtest evaluation using cached data and optimized calculations
        """
        # Check cache first
        param_hash = self.get_param_hash(params)
        if param_hash in self.backtest_cache:
            self.cache_hits += 1
            return self.backtest_cache[param_hash]
            
        self.cache_misses += 1
        
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
            
            # Add required parameters that might be missing
            strategy_params.update({
                'use_supply_demand': True,
                'use_rsi_filter': True,
                'use_macd_filter': True,
                'use_volume_filter': True,
                'max_zones': 10,
                'min_risk_reward': 2.0,
                'zone_buffer': 0.0005,
                'volume_levels': 20,
                'volume_period': 50
            })
            
            backtest_engine.add_strategy(
                self.base_config['strategy']['name'],
                **strategy_params
            )
            
            # Run fast backtest
            results = backtest_engine.run()
            
            if results and isinstance(results, dict):
                # Ensure all required fields are present with safe defaults
                safe_results = self.get_default_results()
                safe_results.update(results)
                
                # Additional safety checks for None values
                for key, value in safe_results.items():
                    if value is None:
                        if key in ['final_value']:
                            safe_results[key] = 10000.0
                        elif key in ['total_return', 'sharpe_ratio', 'win_rate', 'avg_win', 'avg_loss', 'profit_factor']:
                            safe_results[key] = 0.0
                        elif key in ['max_drawdown']:
                            safe_results[key] = 100.0
                        elif key in ['total_trades', 'winning_trades', 'losing_trades']:
                            safe_results[key] = 0
                
                # Cache results
                self.backtest_cache[param_hash] = safe_results
                return safe_results
            else:
                return self.get_default_results()
                
        except Exception as e:
            logger.error(f"Error in fast backtest: {e}")
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
        
    def calculate_fitness_score_gpu(self, results_batch: List[Dict[str, Any]]) -> np.ndarray:
        """
        GPU-accelerated fitness calculation for batch of results
        """
        if not GPU_AVAILABLE or len(results_batch) < 10:
            # Fall back to CPU for small batches
            return np.array([self.calculate_fitness_score_cpu(r) for r in results_batch])
            
        try:
            # Convert to GPU arrays with safe None handling
            def safe_extract(results_list, key, default):
                return [default if r.get(key) is None else r.get(key, default) for r in results_list]
            
            batch_size = len(results_batch)
            
            # Extract metrics with None safety
            total_returns = cp.array(safe_extract(results_batch, 'total_return', 0.0))
            sharpe_ratios = cp.array(safe_extract(results_batch, 'sharpe_ratio', 0.0))
            max_drawdowns = cp.array(safe_extract(results_batch, 'max_drawdown', 100.0))
            win_rates = cp.array(safe_extract(results_batch, 'win_rate', 0.0))
            total_trades = cp.array(safe_extract(results_batch, 'total_trades', 0))
            final_values = cp.array(safe_extract(results_batch, 'final_value', 10000.0))
            
            # Vectorized fitness calculation on GPU
            initial_capital = 10000.0
            actual_profits = final_values - initial_capital
            profit_percentages = (actual_profits / initial_capital) * 100
            
            # Sharpe score component
            sharpe_scores = cp.where(sharpe_ratios > 0, 
                                   cp.minimum(sharpe_ratios / 3.0, 1.0),
                                   cp.maximum(sharpe_ratios / 3.0, -1.0))
            
            # Profit score component
            profit_scores = cp.where(profit_percentages > 0,
                                   cp.minimum(profit_percentages / 20.0, 1.0),
                                   cp.maximum(profit_percentages / 20.0, -1.0))
            
            # Win rate and drawdown components
            win_rate_scores = win_rates / 100.0
            drawdown_scores = cp.maximum(0, (5 - cp.abs(max_drawdowns)) / 5)
            
            # Composite fitness scores
            fitness_scores = (0.40 * sharpe_scores + 
                            0.35 * profit_scores + 
                            0.15 * win_rate_scores + 
                            0.10 * drawdown_scores)
            
            # Apply penalties for insufficient trades
            fitness_scores = cp.where(total_trades < 5, -1000, fitness_scores)
            
            # Bonuses and penalties
            bonus_mask = (sharpe_ratios > 1.5) & (profit_percentages > 5)
            fitness_scores = cp.where(bonus_mask, fitness_scores + 0.2, fitness_scores)
            
            moderate_bonus_mask = (sharpe_ratios > 1.0) & (profit_percentages > 2)
            fitness_scores = cp.where(moderate_bonus_mask, fitness_scores + 0.1, fitness_scores)
            
            penalty_mask = (sharpe_ratios < 0) | (profit_percentages < -5)
            fitness_scores = cp.where(penalty_mask, fitness_scores - 0.5, fitness_scores)
            
            # Convert back to CPU
            return cp.asnumpy(fitness_scores)
            
        except Exception as e:
            logger.error(f"GPU fitness calculation failed: {e}, falling back to CPU")
            return np.array([self.calculate_fitness_score_cpu(r) for r in results_batch])
            
    def calculate_fitness_score_cpu(self, results: Dict[str, Any]) -> float:
        """CPU-based fitness calculation for single result"""
        try:
            # Extract metrics with safe defaults and None handling
            def safe_float(value, default=0.0):
                if value is None:
                    return default
                try:
                    return float(value)
                except (ValueError, TypeError):
                    return default
                    
            def safe_int(value, default=0):
                if value is None:
                    return default
                try:
                    return int(value)
                except (ValueError, TypeError):
                    return default
            
            total_return = safe_float(results.get('total_return'), 0.0)
            sharpe_ratio = safe_float(results.get('sharpe_ratio'), 0.0)
            max_drawdown = safe_float(results.get('max_drawdown'), 100.0)
            win_rate = safe_float(results.get('win_rate'), 0.0)
            total_trades = safe_int(results.get('total_trades'), 0)
            final_value = safe_float(results.get('final_value'), 10000.0)
            
            # Minimum trades requirement
            if total_trades < 5:
                return -1000
                
            # Calculate profit
            initial_capital = 10000.0
            actual_profit = final_value - initial_capital
            profit_percentage = (actual_profit / initial_capital) * 100
            
            # Component scores
            sharpe_score = min(sharpe_ratio / 3.0, 1.0) if sharpe_ratio > 0 else max(sharpe_ratio / 3.0, -1.0)
            profit_score = min(profit_percentage / 20.0, 1.0) if profit_percentage > 0 else max(profit_percentage / 20.0, -1.0)
            win_rate_score = win_rate / 100.0
            drawdown_score = max(0, (5 - abs(max_drawdown)) / 5)
            
            # Composite fitness
            fitness_score = (0.40 * sharpe_score + 0.35 * profit_score + 
                           0.15 * win_rate_score + 0.10 * drawdown_score)
            
            # Bonuses and penalties
            if sharpe_ratio > 1.5 and profit_percentage > 5:
                fitness_score += 0.2
            elif sharpe_ratio > 1.0 and profit_percentage > 2:
                fitness_score += 0.1
                
            if sharpe_ratio < 0 or profit_percentage < -5:
                fitness_score -= 0.5
                
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error calculating fitness: {e}")
            return -1000
            
    def fitness_function(self, ga_instance, solution, solution_idx):
        """Optimized fitness function with caching"""
        try:
            params = self.decode_solution(solution)
            
            # Parameter validation
            if params['fast_length'] >= params['slow_length']:
                return -1000
                
            # Fast backtest evaluation
            results = self.fast_backtest_evaluation(params)
            fitness_score = self.calculate_fitness_score_cpu(results)
            
            # Track best parameters
            if fitness_score > self.best_fitness:
                self.best_fitness = fitness_score
                self.best_params = params.copy()
                logger.info(f"New best fitness: {fitness_score:.4f}")
                logger.info(f"Cache hits: {self.cache_hits}, misses: {self.cache_misses}")
                
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
            return -1000
            
    def optimize(self,
                 num_generations: int = 20,  # Reduced for faster testing
                 num_parents_mating: int = 8,
                 sol_per_pop: int = 16,  # Reduced population size
                 mutation_probability: float = 0.15) -> Dict[str, Any]:
        """
        Run optimized genetic algorithm
        """
        start_time = time.time()
        
        # Validate and adjust parameters
        if num_parents_mating >= sol_per_pop:
            num_parents_mating = max(2, sol_per_pop // 2)
            logger.warning(f"Adjusted num_parents_mating to {num_parents_mating} (must be < sol_per_pop)")
            
        keep_parents = min(2, num_parents_mating // 2)
        
        logger.info("Starting fast genetic algorithm optimization...")
        logger.info(f"GPU acceleration: {'Enabled' if GPU_AVAILABLE else 'Disabled'}")
        logger.info(f"Generations: {num_generations}, Population: {sol_per_pop}")
        logger.info(f"Parents for mating: {num_parents_mating}, Keep parents: {keep_parents}")
        logger.info(f"Cached data shape: {self.cached_data.shape if self.cached_data is not None else 'None'}")
        
        # Initialize genetic algorithm with optimized settings
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
            suppress_warnings=True,
            parallel_processing=['thread', min(4, sol_per_pop)]  # Enable parallel processing
        )
        
        # Run optimization
        ga_instance.run()
        
        end_time = time.time()
        optimization_time = end_time - start_time
        
        # Get best solution
        solution, solution_fitness, solution_idx = ga_instance.best_solution()
        best_optimized_params = self.decode_solution(solution)
        
        logger.info("Fast optimization completed!")
        logger.info(f"Optimization time: {optimization_time:.2f} seconds")
        logger.info(f"Cache efficiency: {self.cache_hits}/{self.cache_hits + self.cache_misses} hits")
        logger.info(f"Best fitness score: {solution_fitness:.4f}")
        logger.info(f"Best parameters: {best_optimized_params}")
        
        return {
            'best_params': best_optimized_params,
            'best_fitness': solution_fitness,
            'optimization_time': optimization_time,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'ga_instance': ga_instance,
            'optimization_history': ga_instance.best_solutions_fitness,
            'all_results': self.optimization_results
        }
        
    def export_results_to_csv(self, output_dir: str = "output") -> str:
        """Export optimization results to CSV with performance metrics"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"fast_optimization_results_{timestamp}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        if not self.optimization_results:
            logger.warning("No optimization results to export")
            return csv_path
            
        df = pd.DataFrame(self.optimization_results)
        
        # Reorder columns
        priority_columns = [
            'generation', 'solution_idx', 'fitness_score',
            'fast_length', 'slow_length', 'rsi_period', 'rsi_oversold', 'rsi_overbought',
            'macd_fast', 'macd_slow', 'macd_signal', 'pivot_period', 'zone_lookback',
            'min_zone_strength', 'stop_loss_percent', 'take_profit_percent',
            'final_value', 'total_return', 'sharpe_ratio', 'max_drawdown',
            'total_trades', 'winning_trades', 'losing_trades', 'win_rate',
            'avg_win', 'avg_loss', 'profit_factor'
        ]
        
        available_columns = [col for col in priority_columns if col in df.columns]
        remaining_columns = [col for col in df.columns if col not in priority_columns]
        ordered_columns = available_columns + remaining_columns
        
        df = df[ordered_columns]
        df = df.sort_values('fitness_score', ascending=False)
        
        # Round numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].round(6)
        
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Fast optimization results exported to: {csv_path}")
        logger.info(f"Total results: {len(df)} parameter combinations")
        
        if len(df) > 0:
            logger.info(f"Best fitness: {df['fitness_score'].max():.6f}")
            logger.info(f"Average fitness: {df['fitness_score'].mean():.6f}")
            
        return csv_path

def main():
    """Main function for running fast optimization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fast genetic algorithm optimization')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--generations', type=int, default=20, help='Number of generations')
    parser.add_argument('--population', type=int, default=16, help='Population size')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run fast optimization
    optimizer = FastGeneticOptimizer(args.config)
    results = optimizer.optimize(
        num_generations=args.generations,
        sol_per_pop=args.population
    )
    
    # Export results
    csv_path = optimizer.export_results_to_csv()
    
    print(f"\n🚀 Fast Optimization Results:")
    print(f"⏱️  Optimization Time: {results['optimization_time']:.2f} seconds")
    print(f"🎯 Best Fitness Score: {results['best_fitness']:.4f}")
    print(f"📊 Cache Efficiency: {results['cache_hits']}/{results['cache_hits'] + results['cache_misses']} hits")
    print(f"💾 Results exported to: {csv_path}")
    print(f"🏆 Best Parameters: {results['best_params']}")

if __name__ == "__main__":
    main()