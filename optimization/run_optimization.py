#!/usr/bin/env python3
"""
Optimization Runner Script
Runs genetic algorithm optimization to find optimal trading strategy parameters
"""

import sys
import os
import logging
import argparse

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from optimization.genetic_optimizer import GeneticOptimizer

def setup_logging():
    """Setup logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/optimization.log')
        ]
    )

def main():
    """Main optimization function"""
    parser = argparse.ArgumentParser(description='Optimize trading strategy parameters using genetic algorithm')
    parser.add_argument('--config', default='config/config.yaml', help='Path to base configuration file')
    parser.add_argument('--output', default='config/optimized_config.yaml', help='Path to save optimized configuration')
    parser.add_argument('--generations', type=int, default=20, help='Number of generations (default: 20)')
    parser.add_argument('--population', type=int, default=16, help='Population size (default: 16)')
    parser.add_argument('--parents', type=int, default=8, help='Number of parents for mating (default: 8)')
    parser.add_argument('--mutation', type=float, default=0.15, help='Mutation probability (default: 0.15)')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("GENETIC ALGORITHM OPTIMIZATION STARTED")
    logger.info("="*60)
    logger.info(f"Configuration file: {args.config}")
    logger.info(f"Output file: {args.output}")
    logger.info(f"Generations: {args.generations}")
    logger.info(f"Population size: {args.population}")
    logger.info(f"Parents for mating: {args.parents}")
    logger.info(f"Mutation probability: {args.mutation}")
    logger.info("="*60)
    
    try:
        # Initialize optimizer
        optimizer = GeneticOptimizer(args.config)
        
        # Run optimization
        results = optimizer.optimize(
            num_generations=args.generations,
            num_parents_mating=args.parents,
            sol_per_pop=args.population,
            mutation_probability=args.mutation
        )
        
        # Save optimized configuration
        optimizer.save_optimized_config(results['best_params'], args.output)
        
        # Print final results
        logger.info("="*60)
        logger.info("OPTIMIZATION COMPLETED SUCCESSFULLY")
        logger.info("="*60)
        logger.info(f"Best Fitness Score: {results['best_fitness']:.4f}")
        logger.info("Best Parameters:")
        for param, value in results['best_params'].items():
            logger.info(f"  {param}: {value}")
        logger.info(f"Optimized configuration saved to: {args.output}")
        logger.info("="*60)
        
        print(f"\nOptimization completed successfully!")
        print(f"Best fitness score: {results['best_fitness']:.4f}")
        print(f"Optimized config saved to: {args.output}")
        print(f"Best parameters:")
        for param, value in results['best_params'].items():
            print(f"   - {param}: {value}")
            
    except Exception as e:
        logger.error(f"Optimization failed: {e}")
        print(f"Optimization failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()