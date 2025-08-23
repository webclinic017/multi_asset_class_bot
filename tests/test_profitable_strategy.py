#!/usr/bin/env python3
"""
Test script for the new profitable strategy and optimizer
"""

import sys
import os
import time
import argparse
import logging

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.profit_optimizer import ProfitOptimizer

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler()
        ]
    )

def main():
    """Main function for testing profitable strategy"""
    parser = argparse.ArgumentParser(description='Test Profitable Strategy Optimization')
    parser.add_argument('--config', default='config/config.yaml', help='Path to configuration file')
    parser.add_argument('--generations', type=int, default=5, help='Number of generations (default: 5)')
    parser.add_argument('--population', type=int, default=8, help='Population size (default: 8)')
    parser.add_argument('--output-dir', default='output', help='Output directory for results')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("PROFITABLE STRATEGY OPTIMIZATION TEST")
    print("=" * 60)
    print(f"Config: {args.config}")
    print(f"Generations: {args.generations}")
    print(f"Population: {args.population}")
    print(f"Output: {args.output_dir}")
    print("=" * 60)
    
    start_time = time.time()
    
    try:
        # Initialize profit optimizer
        logger.info("Initializing ProfitOptimizer...")
        optimizer = ProfitOptimizer(args.config)
        
        # Run optimization
        logger.info("Starting profit-focused optimization...")
        results = optimizer.optimize(
            num_generations=args.generations,
            sol_per_pop=args.population
        )
        
        # Export results
        logger.info("Exporting results...")
        csv_path = optimizer.export_results_to_csv(args.output_dir)
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Display results
        print("\n" + "=" * 60)
        print("PROFITABLE OPTIMIZATION COMPLETED!")
        print("=" * 60)
        print(f"Total Time: {total_time:.2f} seconds")
        print(f"Best Fitness: {results['best_fitness']:.6f}")
        print(f"Results File: {csv_path}")
        
        print("\nOPTIMAL PARAMETERS:")
        print("-" * 40)
        
        best_params = results['best_params']
        for param, value in best_params.items():
            if isinstance(value, float):
                print(f"  {param}: {value:.4f}")
            else:
                print(f"  {param}: {value}")
        
        print("\nPROFITABILITY FOCUS:")
        print("-" * 40)
        print("  Strategy: Simplified profitable forex strategy")
        print("  Fitness: 60% actual profit + 25% Sharpe + 15% other metrics")
        print("  Risk Management: Better risk/reward ratios (1:2 minimum)")
        print("  Trade Execution: Less restrictive entry conditions")
        
        # Get the best result from optimization
        if optimizer.optimization_results:
            best_result = max(optimizer.optimization_results, key=lambda x: x['fitness_score'])
            profit_pct = best_result.get('total_return', 0)
            sharpe = best_result.get('sharpe_ratio', 0)
            win_rate = best_result.get('win_rate', 0)
            total_trades = best_result.get('total_trades', 0)
            
            print(f"\nBEST RESULT METRICS:")
            print("-" * 40)
            print(f"  Total Return: {profit_pct:.3f}%")
            print(f"  Sharpe Ratio: {sharpe:.3f}")
            print(f"  Win Rate: {win_rate:.1f}%")
            print(f"  Total Trades: {total_trades}")
            
            if profit_pct > 0:
                print(f"\n✅ SUCCESS: Strategy is PROFITABLE! (+{profit_pct:.3f}%)")
            else:
                print(f"\n⚠️  WARNING: Strategy still losing money ({profit_pct:.3f}%)")
                print("   Consider:")
                print("   - Longer optimization (more generations)")
                print("   - Different time period for backtesting")
                print("   - Further strategy simplification")
        
        print("\nOptimization completed successfully!")
        
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        print(f"\nERROR: {e}")
        print("Check the logs for more details.")
        sys.exit(1)

if __name__ == "__main__":
    main()