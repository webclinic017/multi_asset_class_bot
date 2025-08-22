"""
Enhanced Genetic Algorithm Optimizer for Maximum Returns
Advanced optimization with expanded parameter spaces and multi-objective optimization
"""

import pygad
import numpy as np
import yaml
import logging
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import sys
import os
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
import pickle
import hashlib
from functools import lru_cache
import time
from scipy import stats
from sklearn.preprocessing import StandardScaler

# Add the parent directory to the path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtesting.backtest_engine import BacktestEngine
from data.data_feed import OANDADataFeed
from data.preprocessing import DataPreprocessor
from risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class EnhancedGeneticOptimizer:
    """
    Enhanced genetic algorithm optimizer focused on maximum returns
    with advanced parameter spaces and multi-objective optimization
    """
    
    def __init__(self, config_path: str, strategy_type: str = 'forex'):
        """
        Initialize the enhanced genetic optimizer
        
        Args:
            config_path: Path to the configuration file
            strategy_type: 'forex' or 'crypto'
        """
        self.config_path = config_path
        self.strategy_type = strategy_type
        self.load_base_config()
        self.setup_enhanced_parameter_space()
        self.best_fitness = -np.inf
        self.best_params = None
        self.optimization_results = []
        
        # Performance tracking
        self.fitness_history = []
        self.parameter_history = []
        self.convergence_threshold = 0.001
        self.stagnation_counter = 0
        self.max_stagnation = 10
        
        # Multi-objective weights
        self.objective_weights = {
            'total_return': 0.35,
            'sharpe_ratio': 0.25,
            'profit_factor': 0.20,
            'max_drawdown': 0.10,  # Negative weight (minimize)
            'win_rate': 0.10
        }
        
        # Cache for performance
        self.backtest_cache = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
        logger.info(f"Enhanced Genetic Optimizer initialized for {strategy_type} strategy")
        
    def load_base_config(self):
        """Load the base configuration"""
        with open(self.config_path, 'r') as file:
            self.base_config = yaml.safe_load(file)
            
    def setup_enhanced_parameter_space(self):
        """
        Define enhanced parameter space optimized for maximum returns
        """
        if self.strategy_type == 'forex':
            self.param_bounds = {
                # Core Moving Average Parameters (Expanded Range)
                'fast_length': [5, 25],
                'slow_length': [20, 60],
                'signal_length': [3, 15],
                
                # Advanced RSI Parameters
                'rsi_period': [8, 25],
                'rsi_oversold': [15, 35],
                'rsi_overbought': [65, 85],
                
                # MACD Parameters (Fine-tuned)
                'macd_fast': [8, 18],
                'macd_slow': [20, 35],
                'macd_signal': [5, 15],
                
                # Bollinger Bands
                'bb_period': [15, 30],
                'bb_std': [1.5, 3.0],
                
                # Volatility Parameters
                'atr_period': [10, 25],
                'volatility_threshold': [0.01, 0.05],
                
                # Enhanced Risk Management
                'base_stop_loss': [0.005, 0.025],
                'base_take_profit': [0.015, 0.06],
                'max_risk_per_trade': [0.01, 0.05],
                
                # Supply/Demand Parameters
                'pivot_period': [3, 15],
                'zone_lookback': [30, 120],
                'min_zone_strength': [1.0, 8.0],
                
                # Advanced Filters
                'trend_threshold': [0.4, 0.8],
                'momentum_threshold': [0.01, 0.04],
                'regime_lookback': [50, 150],
                
                # Performance Optimization
                'min_sharpe_threshold': [0.3, 1.2],
                'profit_factor_threshold': [1.0, 2.0],
            }
        else:  # crypto
            self.param_bounds = {
                # Core Parameters (Crypto-optimized)
                'fast_length': [5, 20],
                'slow_length': [15, 40],
                'signal_length': [3, 12],
                
                # RSI Parameters (Crypto volatility adjusted)
                'rsi_period': [10, 21],
                'rsi_oversold': [15, 30],
                'rsi_overbought': [70, 85],
                
                # MACD Parameters
                'macd_fast': [8, 16],
                'macd_slow': [20, 30],
                'macd_signal': [5, 12],
                
                # Bollinger Bands
                'bb_period': [15, 25],
                'bb_std': [1.8, 2.5],
                
                # Volatility (Higher for crypto)
                'atr_period': [10, 20],
                'vol_regime_threshold': [0.03, 0.08],
                
                # Risk Management (Crypto-specific)
                'base_stop_loss': [0.02, 0.06],
                'base_take_profit': [0.04, 0.12],
                'max_risk_per_trade': [0.02, 0.08],
                'max_position_size': [0.10, 0.30],
                
                # Volume Analysis
                'volume_period': [15, 30],
                'volume_spike_threshold': [1.5, 3.0],
                'vwap_period': [15, 25],
                
                # Momentum
                'momentum_threshold': [0.015, 0.035],
                'trend_strength_min': [0.4, 0.8],
                
                # Performance Targets
                'sharpe_target': [1.0, 2.5],
                'profit_factor_min': [1.2, 2.0],
                'win_rate_target': [0.45, 0.65],
            }
        
        # Create parameter names list and bounds arrays for PyGAD
        self.param_names = list(self.param_bounds.keys())
        self.gene_space = [self.param_bounds[param] for param in self.param_names]
        
        logger.info(f"Parameter space setup complete: {len(self.param_names)} parameters")
        
    def decode_solution(self, solution: np.ndarray) -> Dict[str, Any]:
        """
        Decode genetic algorithm solution to parameter dictionary
        """
        params = {}
        for i, param_name in enumerate(self.param_names):
            # Integer parameters
            if param_name in ['fast_length', 'slow_length', 'signal_length', 'rsi_period', 
                             'rsi_oversold', 'rsi_overbought', 'macd_fast', 'macd_slow', 
                             'macd_signal', 'bb_period', 'atr_period', 'pivot_period', 
                             'zone_lookback', 'regime_lookback', 'volume_period', 'vwap_period']:
                params[param_name] = int(solution[i])
            else:
                # Float parameters
                params[param_name] = float(solution[i])
                
        return params
        
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        Validate parameter combinations for logical consistency
        """
        try:
            # Moving average validation
            if 'fast_length' in params and 'slow_length' in params:
                if params['fast_length'] >= params['slow_length']:
                    return False
                    
            # RSI validation
            if 'rsi_oversold' in params and 'rsi_overbought' in params:
                if params['rsi_oversold'] >= params['rsi_overbought']:
                    return False
                    
            # MACD validation
            if 'macd_fast' in params and 'macd_slow' in params:
                if params['macd_fast'] >= params['macd_slow']:
                    return False
                    
            # Risk management validation
            if 'base_stop_loss' in params and 'base_take_profit' in params:
                if params['base_stop_loss'] >= params['base_take_profit']:
                    return False
                    
            # Bollinger Bands validation
            if 'bb_std' in params:
                if params['bb_std'] < 1.0 or params['bb_std'] > 4.0:
                    return False
                    
            return True
            
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            return False
            
    def calculate_multi_objective_fitness(self, results: Dict[str, Any]) -> float:
        """
        Calculate multi-objective fitness score optimized for maximum returns
        """
        try:
            # Extract metrics with safe defaults
            total_return = float(results.get('total_return', 0.0))
            sharpe_ratio = float(results.get('sharpe_ratio', 0.0))
            max_drawdown = float(results.get('max_drawdown', 100.0))
            win_rate = float(results.get('win_rate', 0.0))
            total_trades = int(results.get('total_trades', 0))
            profit_factor = float(results.get('profit_factor', 0.0))
            final_value = float(results.get('final_value', 10000.0))
            
            # Minimum trades requirement
            if total_trades < 10:
                return -1000
                
            # Calculate individual objective scores
            
            # 1. Total Return Score (Primary objective)
            return_score = 0.0
            if total_return > 0:
                # Exponential reward for higher returns
                return_score = min(np.log(1 + total_return / 10) * 2, 3.0)
            else:
                # Heavy penalty for losses
                return_score = max(total_return / 10, -2.0)
                
            # 2. Sharpe Ratio Score
            sharpe_score = 0.0
            if sharpe_ratio > 0:
                sharpe_score = min(sharpe_ratio / 2.0, 2.0)
            else:
                sharpe_score = max(sharpe_ratio / 2.0, -1.0)
                
            # 3. Profit Factor Score
            pf_score = 0.0
            if profit_factor > 1.0:
                pf_score = min(np.log(profit_factor) * 2, 2.0)
            else:
                pf_score = -1.0
                
            # 4. Drawdown Score (minimize drawdown)
            dd_score = 0.0
            if max_drawdown < 5:
                dd_score = 1.0
            elif max_drawdown < 10:
                dd_score = 0.5
            elif max_drawdown < 20:
                dd_score = 0.0
            else:
                dd_score = -1.0 * (max_drawdown / 20)
                
            # 5. Win Rate Score
            wr_score = (win_rate / 100.0) * 2 - 1  # Scale to -1 to 1
            
            # Calculate weighted composite score
            composite_score = (
                self.objective_weights['total_return'] * return_score +
                self.objective_weights['sharpe_ratio'] * sharpe_score +
                self.objective_weights['profit_factor'] * pf_score +
                self.objective_weights['max_drawdown'] * dd_score +
                self.objective_weights['win_rate'] * wr_score
            )
            
            # Bonus for exceptional performance
            if total_return > 20 and sharpe_ratio > 1.5 and max_drawdown < 10:
                composite_score += 1.0  # Exceptional performance bonus
            elif total_return > 10 and sharpe_ratio > 1.0 and max_drawdown < 15:
                composite_score += 0.5  # Good performance bonus
                
            # Penalty for poor risk-adjusted returns
            if sharpe_ratio < 0.5 and total_return < 5:
                composite_score -= 0.5
                
            # Strategy-specific adjustments
            if self.strategy_type == 'crypto':
                # Crypto markets are more volatile, adjust expectations
                if total_return > 30:
                    composite_score += 0.3
                if max_drawdown > 25:
                    composite_score -= 0.3
            else:  # forex
                # Forex markets are more stable, higher standards
                if total_return > 15 and max_drawdown < 8:
                    composite_score += 0.3
                    
            return composite_score
            
        except Exception as e:
            logger.error(f"Error calculating fitness: {e}")
            return -1000
            
    def get_param_hash(self, params: Dict[str, Any]) -> str:
        """Generate hash for parameter combination for caching"""
        param_str = str(sorted(params.items()))
        return hashlib.md5(param_str.encode()).hexdigest()
        
    def evaluate_strategy_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate strategy performance with given parameters
        """
        # Check cache first
        param_hash = self.get_param_hash(params)
        if param_hash in self.backtest_cache:
            self.cache_hits += 1
            return self.backtest_cache[param_hash]
            
        self.cache_misses += 1
        
        try:
            # Create configuration with optimized parameters
            config = self.create_config_with_params(params)
            
            # Initialize components
            data_feed = OANDADataFeed(config)
            preprocessor = DataPreprocessor()
            risk_manager = RiskManager(config.get('risk', {}))
            
            # Initialize backtest engine
            backtest_engine = BacktestEngine(
                data_feed=data_feed,
                preprocessor=preprocessor,
                risk_manager=risk_manager,
                config=config
            )
            
            # Load data
            symbol = config['data']['symbols'][0]
            data = backtest_engine.load_data(
                symbol=symbol['name'],
                asset_type=symbol['type'],
                timeframe=symbol['timeframe']
            )
            
            if data is None or len(data) < 100:
                return self.get_default_results()
                
            # Determine strategy class based on type
            if self.strategy_type == 'forex':
                strategy_name = 'EnhancedForexStrategy'
            else:
                strategy_name = 'EnhancedCryptoStrategy'
                
            # Add strategy and run backtest
            strategy_params = params.copy()
            strategy_params['printlog'] = False
            
            backtest_engine.add_strategy(strategy_name, **strategy_params)
            results = backtest_engine.run()
            
            if results is None:
                results = self.get_default_results()
                
            # Cache results
            self.backtest_cache[param_hash] = results
            
            return results
            
        except Exception as e:
            logger.error(f"Error evaluating strategy: {e}")
            return self.get_default_results()
            
    def get_default_results(self) -> Dict[str, Any]:
        """Return default results for failed backtests"""
        return {
            'final_value': 10000.0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 100.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0
        }
        
    def create_config_with_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create configuration dictionary with optimized parameters
        """
        import copy
        config = copy.deepcopy(self.base_config)
        
        # Update strategy parameters
        if 'strategy' not in config:
            config['strategy'] = {}
        if 'params' not in config['strategy']:
            config['strategy']['params'] = {}
            
        # Update with optimized parameters
        for param_name, param_value in params.items():
            config['strategy']['params'][param_name] = param_value
            
        return config
        
    def fitness_function(self, ga_instance, solution, solution_idx):
        """
        Enhanced fitness function with multi-objective optimization
        """
        try:
            # Decode parameters
            params = self.decode_solution(solution)
            
            # Validate parameter combinations
            if not self.validate_parameters(params):
                return -1000
                
            # Evaluate strategy performance
            results = self.evaluate_strategy_performance(params)
            
            # Calculate multi-objective fitness
            fitness_score = self.calculate_multi_objective_fitness(results)
            
            # Track best parameters
            if fitness_score > self.best_fitness:
                improvement = fitness_score - self.best_fitness
                self.best_fitness = fitness_score
                self.best_params = params.copy()
                self.stagnation_counter = 0
                
                logger.info(f"New best fitness: {fitness_score:.4f} (improvement: +{improvement:.4f})")
                logger.info(f"Return: {results.get('total_return', 0):.2f}%, "
                           f"Sharpe: {results.get('sharpe_ratio', 0):.2f}, "
                           f"DD: {results.get('max_drawdown', 0):.1f}%")
            else:
                self.stagnation_counter += 1
                
            # Store results for analysis
            result_record = params.copy()
            result_record['fitness_score'] = fitness_score
            result_record['generation'] = getattr(ga_instance, 'generations_completed', 0) if ga_instance else 0
            result_record['solution_idx'] = solution_idx
            result_record.update(results)
            
            self.optimization_results.append(result_record)
            self.fitness_history.append(fitness_score)
            self.parameter_history.append(params.copy())
            
            return fitness_score
            
        except Exception as e:
            logger.error(f"Error in fitness function: {e}")
            return -1000
            
    def check_convergence(self) -> bool:
        """
        Check if optimization has converged
        """
        if len(self.fitness_history) < 20:
            return False
            
        # Check for stagnation
        if self.stagnation_counter >= self.max_stagnation:
            logger.info(f"Optimization converged due to stagnation ({self.max_stagnation} generations)")
            return True
            
        # Check fitness improvement rate
        recent_fitness = self.fitness_history[-10:]
        if len(recent_fitness) >= 10:
            improvement_rate = (max(recent_fitness) - min(recent_fitness)) / max(abs(max(recent_fitness)), 0.001)
            if improvement_rate < self.convergence_threshold:
                logger.info(f"Optimization converged due to low improvement rate ({improvement_rate:.6f})")
                return True
                
        return False
        
    def optimize(self,
                 num_generations: int = 50,
                 num_parents_mating: int = 12,
                 sol_per_pop: int = 24,
                 mutation_probability: float = 0.15,
                 early_stopping: bool = True) -> Dict[str, Any]:
        """
        Run enhanced genetic algorithm optimization
        """
        start_time = time.time()
        
        # Validate parameters
        if num_parents_mating >= sol_per_pop:
            num_parents_mating = max(4, sol_per_pop // 2)
            
        keep_parents = min(4, num_parents_mating // 2)
        
        logger.info("Starting enhanced genetic algorithm optimization...")
        logger.info(f"Strategy Type: {self.strategy_type}")
        logger.info(f"Parameters to optimize: {len(self.param_names)}")
        logger.info(f"Generations: {num_generations}, Population: {sol_per_pop}")
        logger.info(f"Objective weights: {self.objective_weights}")
        
        # Initialize genetic algorithm
        ga_instance = pygad.GA(
            num_generations=num_generations,
            num_parents_mating=num_parents_mating,
            fitness_func=self.fitness_function,
            sol_per_pop=sol_per_pop,
            num_genes=len(self.param_names),
            gene_space=self.gene_space,
            parent_selection_type="sss",  # Steady-state selection
            keep_parents=keep_parents,
            crossover_type="single_point",
            mutation_type="random",
            mutation_probability=mutation_probability,
            random_seed=None,  # Allow randomness for better exploration
            suppress_warnings=True,
            on_generation=self._on_generation_callback if early_stopping else None
        )
        
        # Run optimization
        ga_instance.run()
        
        end_time = time.time()
        optimization_time = end_time - start_time
        
        # Get best solution
        solution, solution_fitness, solution_idx = ga_instance.best_solution()
        best_optimized_params = self.decode_solution(solution)
        
        # Calculate performance metrics
        cache_efficiency = self.cache_hits / max(self.cache_hits + self.cache_misses, 1) * 100
        
        logger.info("Enhanced optimization completed!")
        logger.info(f"Optimization time: {optimization_time:.2f} seconds")
        logger.info(f"Cache efficiency: {cache_efficiency:.1f}%")
        logger.info(f"Best fitness score: {solution_fitness:.4f}")
        logger.info(f"Convergence: {'Yes' if self.stagnation_counter >= self.max_stagnation else 'No'}")
        
        return {
            'best_params': best_optimized_params,
            'best_fitness': solution_fitness,
            'optimization_time': optimization_time,
            'cache_efficiency': cache_efficiency,
            'convergence_achieved': self.stagnation_counter >= self.max_stagnation,
            'total_evaluations': len(self.optimization_results),
            'ga_instance': ga_instance,
            'optimization_history': ga_instance.best_solutions_fitness,
            'all_results': self.optimization_results,
            'fitness_history': self.fitness_history
        }
        
    def _on_generation_callback(self, ga_instance):
        """Callback function for early stopping"""
        if self.check_convergence():
            logger.info("Early stopping triggered due to convergence")
            ga_instance.generations_completed = ga_instance.num_generations
            
    def export_results_to_csv(self, output_dir: str = "output") -> str:
        """Export optimization results to CSV with enhanced metrics"""
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"enhanced_{self.strategy_type}_optimization_{timestamp}.csv"
        csv_path = os.path.join(output_dir, csv_filename)
        
        if not self.optimization_results:
            logger.warning("No optimization results to export")
            return csv_path
            
        df = pd.DataFrame(self.optimization_results)
        
        # Sort by fitness score
        df = df.sort_values('fitness_score', ascending=False)
        
        # Round numeric columns
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        df[numeric_columns] = df[numeric_columns].round(6)
        
        # Export to CSV
        df.to_csv(csv_path, index=False)
        
        logger.info(f"Enhanced optimization results exported to: {csv_path}")
        logger.info(f"Total parameter combinations tested: {len(df)}")
        
        if len(df) > 0:
            best_result = df.iloc[0]
            logger.info(f"Best result - Fitness: {best_result['fitness_score']:.4f}, "
                       f"Return: {best_result.get('total_return', 0):.2f}%, "
                       f"Sharpe: {best_result.get('sharpe_ratio', 0):.2f}")
        
        return csv_path

def main():
    """Main function for running enhanced optimization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced genetic algorithm optimization for maximum returns')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--strategy', choices=['forex', 'crypto'], default='forex', help='Strategy type')
    parser.add_argument('--generations', type=int, default=50, help='Number of generations')
    parser.add_argument('--population', type=int, default=24, help='Population size')
    parser.add_argument('--output', default='output', help='Output directory')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run enhanced optimization
    optimizer = EnhancedGeneticOptimizer(args.config, args.strategy)
    results = optimizer.optimize(
        num_generations=args.generations,
        sol_per_pop=args.population
    )
    
    # Export results
    csv_path = optimizer.export_results_to_csv(args.output)
    
    print(f"\n🚀 Enhanced {args.strategy.upper()} Optimization Results:")
    print(f"⏱️  Time: {results['optimization_time']:.2f} seconds")
    print(f"🎯 Best Fitness: {results['best_fitness']:.4f}")
    print(f"📊 Cache Efficiency: {results['cache_efficiency']:.1f}%")
    print(f"🔄 Convergence: {'✅' if results['convergence_achieved'] else '❌'}")
    print(f"📈 Total Evaluations: {results['total_evaluations']}")
    print(f"💾 Results: {csv_path}")
    print(f"\n🏆 Best Parameters:")
    for param, value in results['best_params'].items():
        if isinstance(value, float):
            print(f"  {param}: {value:.4f}")
        else:
            print(f"  {param}: {value}")

if __name__ == "__main__":
    main()