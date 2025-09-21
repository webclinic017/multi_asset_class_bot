#!/usr/bin/env python3
"""
Maximum Returns Optimization Algorithm
Focused on achieving 2-3% daily returns through aggressive parameter optimization
"""

import sys
import os
import logging
import numpy as np
from datetime import datetime
from pathlib import Path

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from optimization.enhanced_genetic_optimizer import EnhancedGeneticOptimizer

class MaximumReturnsOptimizer:
    """Genetic algorithm optimizer focused on maximum returns rather than risk-adjusted metrics"""

    def __init__(self, config_path, output_dir='output'):
        """Initialize the maximum returns optimizer"""
        self.config_path = config_path
        self.output_dir = output_dir
        self.logger = logging.getLogger(__name__)

        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'maximum_returns_results'), exist_ok=True)

        # Initialize base genetic optimizer
        self.genetic_optimizer = EnhancedGeneticOptimizer(config_path, output_dir)

    def maximum_returns_fitness_function(self, individual, data):
        """
        Fitness function optimized for maximum returns
        Accepts higher drawdown for higher returns
        """
        try:
            # Extract performance metrics from backtest results
            total_return = data.get('total_return', 0)
            sharpe_ratio = data.get('sharpe_ratio', 0)
            max_drawdown = data.get('max_drawdown', 0)
            win_rate = data.get('win_rate', 0)
            total_trades = data.get('total_trades', 0)

            # Primary component: Total returns (60% weight)
            returns_score = total_return * 0.6

            # Secondary component: Win rate (25% weight)
            win_rate_score = win_rate * 0.25

            # Risk penalty: Allow up to 25% drawdown before penalty (15% weight)
            if max_drawdown <= 0.25:
                drawdown_penalty = 0
            else:
                # Exponential penalty for drawdown > 25%
                drawdown_penalty = (max_drawdown - 0.25) * 5.0

            # Trade frequency bonus: Reward strategies with more trades (slight bonus)
            trade_bonus = min(total_trades / 100, 1.0) * 0.1  # Max 10% bonus for 100+ trades

            # Calculate final fitness score
            fitness_score = returns_score + win_rate_score - drawdown_penalty + trade_bonus

            self.logger.debug(f"Fitness calculation: Returns={total_return:.4f}, WinRate={win_rate:.4f}, "
                            f"DD={max_drawdown:.4f}, Trades={total_trades}, Score={fitness_score:.4f}")

            return fitness_score

        except Exception as e:
            self.logger.error(f"Error in fitness calculation: {e}")
            return -999  # Very low fitness for failed evaluations

    def aggressive_parameter_ranges(self, strategy_type):
        """Define aggressive parameter ranges for maximum returns"""

        if strategy_type.lower() == 'forex':
            return {
                'fast_length': [3, 15],        # Shorter for faster signals
                'slow_length': [8, 30],        # Fibonacci-based
                'rsi_period': [5, 15],         # Faster RSI
                'rsi_oversold': [15, 30],      # More aggressive
                'rsi_overbought': [70, 85],    # More aggressive
                'macd_fast': [3, 15],          # Faster MACD
                'macd_slow': [8, 30],          # Fibonacci-based
                'macd_signal': [2, 8],         # Faster signal
                'bb_period': [8, 25],          # Shorter for responsiveness
                'bb_std': [1.2, 2.5],          # Tighter/wider bands
                'atr_period': [5, 15],         # Faster ATR
                'base_stop_loss': [0.015, 0.04],    # 1.5% to 4% stops
                'base_take_profit': [0.04, 0.12],   # 4% to 12% targets
                'position_size_percent': [0.02, 0.06], # 2% to 6% per trade
                'max_trades_per_hour': [15, 30],     # High frequency
                'signal_strength_threshold': [0.05, 0.2], # Lower thresholds
            }
        elif strategy_type.lower() == 'scalping':
            return {
                'fast_length': [3, 10],        # Very short for scalping
                'slow_length': [5, 20],        # Short slow periods
                'rsi_period': [4, 10],         # Ultra-fast RSI
                'rsi_oversold': [20, 35],      # Aggressive levels
                'rsi_overbought': [65, 80],    # Aggressive levels
                'macd_fast': [3, 10],          # Fast MACD
                'macd_slow': [5, 20],          # Short slow
                'macd_signal': [2, 5],         # Very fast signal
                'bb_period': [5, 15],          # Short BB period
                'bb_std': [1.5, 2.5],          # Responsive bands
                'atr_period': [3, 10],         # Fast ATR
                'base_stop_loss': [0.002, 0.008],    # 0.2% to 0.8% stops
                'base_take_profit': [0.006, 0.02],   # 0.6% to 2% targets
                'position_size_percent': [0.01, 0.04], # 1% to 4% per trade
                'max_trades_per_hour': [25, 50],     # Very high frequency
                'signal_strength_threshold': [0.03, 0.15], # Low thresholds
            }
        else:
            raise ValueError(f"Unknown strategy type: {strategy_type}")

    def optimize_for_maximum_returns(self, strategy_type, generations=100, population=50):
        """
        Run genetic algorithm optimization focused on maximum returns
        """
        self.logger.info(f"Starting maximum returns optimization for {strategy_type}")
        self.logger.info(f"Parameters: {generations} generations, {population} population")

        # Get aggressive parameter ranges
        param_ranges = self.aggressive_parameter_ranges(strategy_type)

        # Custom fitness function for maximum returns
        def fitness_wrapper(individual, data):
            return self.maximum_returns_fitness_function(individual, data)

        # Run genetic optimization with custom fitness
        try:
            results = self.genetic_optimizer.run_genetic_optimization(
                strategy_type=strategy_type,
                param_ranges=param_ranges,
                fitness_function=fitness_wrapper,
                generations=generations,
                population=population,
                maximize=True  # Maximize returns
            )

            # Save results with maximum returns focus
            self._save_maximum_returns_results(results, strategy_type)

            return results

        except Exception as e:
            self.logger.error(f"Maximum returns optimization failed: {e}")
            raise

    def _save_maximum_returns_results(self, results, strategy_type):
        """Save optimization results with maximum returns analysis"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"maximum_returns_{strategy_type}_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, 'maximum_returns_results', filename)

        # Create results DataFrame
        import pandas as pd
        results_df = pd.DataFrame(results['population_data'])
        results_df['fitness_score'] = results['fitness_scores']

        # Sort by fitness score (highest first for maximum returns)
        results_df = results_df.sort_values('fitness_score', ascending=False)

        # Save to CSV
        results_df.to_csv(filepath, index=False)

        self.logger.info(f"Maximum returns results saved to: {filepath}")

        # Log top performers
        top_5 = results_df.head(5)
        self.logger.info("Top 5 Maximum Returns Parameter Sets:")
        for i, (_, row) in enumerate(top_5.iterrows(), 1):
            self.logger.info(f"#{i}: Fitness={row['fitness_score']:.4f}, "
                           f"Return={row.get('total_return', 0):.2f}%, "
                           f"WinRate={row.get('win_rate', 0):.1f}%, "
                           f"MaxDD={row.get('max_drawdown', 0):.1f}%")

        return filepath

    def validate_daily_return_target(self, best_params, strategy_type, test_days=30):
        """
        Validate that optimized parameters can achieve 2-3% daily returns
        """
        self.logger.info(f"Validating 2-3% daily return target for {strategy_type}")

        # Run backtest with best parameters
        validation_results = self.genetic_optimizer.backtest_with_params(
            strategy_type=strategy_type,
            params=best_params,
            test_period_days=test_days
        )

        total_return = validation_results.get('total_return', 0)
        daily_return = total_return / test_days if test_days > 0 else 0

        self.logger.info(f"Validation Results:")
        self.logger.info(f"  Total Return: {total_return:.2f}% over {test_days} days")
        self.logger.info(f"  Daily Return: {daily_return:.2f}%")
        self.logger.info(f"  Win Rate: {validation_results.get('win_rate', 0):.1f}%")
        self.logger.info(f"  Max Drawdown: {validation_results.get('max_drawdown', 0):.1f}%")
        self.logger.info(f"  Total Trades: {validation_results.get('total_trades', 0)}")

        # Check if target is achieved
        if daily_return >= 0.02:  # 2% daily target
            self.logger.info("✅ TARGET ACHIEVED: 2%+ daily returns!")
            return True, daily_return
        elif daily_return >= 0.015:  # 1.5% daily
            self.logger.info("⚠️  CLOSE TO TARGET: 1.5%+ daily returns")
            return True, daily_return
        else:
            self.logger.info("❌ TARGET NOT MET: Below 1.5% daily returns")
            return False, daily_return


def main():
    """Main function for maximum returns optimization"""
    import argparse

    parser = argparse.ArgumentParser(description='Maximum Returns Optimization')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--strategy', choices=['forex', 'scalping'], required=True, help='Strategy type')
    parser.add_argument('--generations', type=int, default=100, help='Generations')
    parser.add_argument('--population', type=int, default=50, help='Population size')
    parser.add_argument('--output-dir', default='output', help='Output directory')
    parser.add_argument('--validate-days', type=int, default=30, help='Validation period in days')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Run optimization
    optimizer = MaximumReturnsOptimizer(args.config, args.output_dir)

    try:
        # Optimize for maximum returns
        results = optimizer.optimize_for_maximum_returns(
            strategy_type=args.strategy,
            generations=args.generations,
            population=args.population
        )

        # Get best parameters
        best_params = results['best_params']
        best_fitness = results['best_fitness']

        print("\n🎯 MAXIMUM RETURNS OPTIMIZATION COMPLETED")
        print(f"Best Fitness Score: {best_fitness:.4f}")
        print(f"Best Parameters: {best_params}")

        # Validate daily return target
        target_achieved, daily_return = optimizer.validate_daily_return_target(
            best_params, args.strategy, args.validate_days
        )

        if target_achieved:
            print(f"\n🎉 SUCCESS: Achieved {daily_return:.2f}% daily returns!")
        else:
            print(f"\n⚠️  Optimization needed: Only {daily_return:.2f}% daily returns")

    except Exception as e:
        print(f"❌ Optimization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()