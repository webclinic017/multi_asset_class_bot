"""
Dynamic Optimization Module for Live Trading
Automatically checks for recent optimization results and runs new optimization if needed
"""

import os
import glob
import subprocess
import logging
import pandas as pd
from datetime import datetime, timedelta
import yaml
import time

logger = logging.getLogger(__name__)

class DynamicOptimizer:
    """
    Handles dynamic optimization for live trading mode.
    Checks for recent CSV results and runs optimization if needed.
    """
    
    def __init__(self, config_path='config/config.yaml', output_dir='output'):
        self.config_path = config_path
        self.output_dir = output_dir
        self.csv_pattern = os.path.join(output_dir, '*optimization_results_*.csv')
        
    def get_latest_csv_file(self):
        """
        Find the most recent optimization results CSV file.
        Returns (file_path, file_age_minutes) or (None, None) if no file found.
        """
        try:
            csv_files = glob.glob(self.csv_pattern)
            if not csv_files:
                logger.info("No optimization CSV files found")
                return None, None
            
            # Get the most recent file
            latest_file = max(csv_files, key=os.path.getctime)
            
            # Calculate file age in minutes
            file_time = os.path.getctime(latest_file)
            current_time = time.time()
            age_minutes = (current_time - file_time) / 60
            
            logger.info(f"Latest CSV file: {latest_file}")
            logger.info(f"File age: {age_minutes:.1f} minutes")
            
            return latest_file, age_minutes
            
        except Exception as e:
            logger.error(f"Error finding latest CSV file: {e}")
            return None, None
    
    def run_fast_optimization(self, generations=40, population=60):
        """
        Run fast optimization using the fast_optimize.py script.
        Returns True if successful, False otherwise.
        """
        try:
            logger.info("Starting fast optimization...")
            logger.info(f"Generations: {generations}, Population: {population}")
            
            # Construct the command
            cmd = [
                'python', 'fast_optimize.py',
                '--config', self.config_path,
                '--generations', str(generations),
                '--population', str(population)
            ]
            
            # Run the optimization
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=os.path.dirname(os.path.abspath(__file__ + '/../')),
                capture_output=True,
                text=True,
                timeout=1800  # 30 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                logger.info(f"Fast optimization completed successfully in {duration:.1f} seconds")
                logger.info("Optimization output:")
                for line in result.stdout.split('\n')[-10:]:  # Show last 10 lines
                    if line.strip():
                        logger.info(f"  {line}")
                return True
            else:
                logger.error(f"Fast optimization failed with return code {result.returncode}")
                logger.error(f"Error output: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Fast optimization timed out after 30 minutes")
            return False
        except Exception as e:
            logger.error(f"Error running fast optimization: {e}")
            return False
    
    def extract_best_parameters_from_csv(self, csv_file_path):
        """
        Extract the best parameters from the optimization CSV file.
        Returns a dictionary of optimized parameters.
        """
        try:
            logger.info(f"Extracting best parameters from: {csv_file_path}")
            
            # Read the CSV file
            df = pd.read_csv(csv_file_path)
            
            if df.empty:
                logger.error("CSV file is empty")
                return None
            
            # Find the row with the highest final_value
            best_row = df.loc[df['final_value'].idxmax()]
            
            logger.info(f"Best result found:")
            logger.info(f"  Generation: {best_row.get('generation', 'N/A')}")
            logger.info(f"  Solution: {best_row.get('solution', 'N/A')}")
            logger.info(f"  Final Value: {best_row['final_value']:.6f}")
            logger.info(f"  Fitness: {best_row.get('fitness', 'N/A')}")
            
            # Extract the optimized parameters
            optimized_params = {}
            param_columns = [
                'fast_length', 'slow_length', 'rsi_period', 'rsi_oversold', 'rsi_overbought',
                'stop_loss_percent', 'take_profit_percent'
            ]
            
            for param in param_columns:
                if param in best_row:
                    value = best_row[param]
                    optimized_params[param] = value
                    logger.info(f"  {param}: {value}")
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"Error extracting parameters from CSV: {e}")
            return None
    
    def update_strategy_parameters(self, optimized_params):
        """
        Update the strategy parameters in both the strategy file and config file.
        """
        try:
            # Update config file
            self.update_config_file(optimized_params)
            
            # Update strategy file
            self.update_strategy_file(optimized_params)
            
            logger.info("Strategy parameters updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error updating strategy parameters: {e}")
            return False
    
    def update_config_file(self, optimized_params):
        """Update the configuration file with optimized parameters."""
        try:
            # Load current config
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Update strategy parameters
            if 'strategy' not in config:
                config['strategy'] = {}
            if 'params' not in config['strategy']:
                config['strategy']['params'] = {}
            
            for param, value in optimized_params.items():
                config['strategy']['params'][param] = value
                logger.info(f"Config updated: {param} = {value}")
            
            # Save updated config
            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration file updated: {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error updating config file: {e}")
            raise
    
    def update_strategy_file(self, optimized_params):
        """Update the strategy file with optimized parameters."""
        try:
            strategy_file = 'strategies/forex_strategy.py'
            strategy_path = os.path.join(os.path.dirname(self.config_path + '/../'), strategy_file)
            
            # Read current strategy file
            with open(strategy_path, 'r') as f:
                content = f.read()
            
            # Update parameters in the strategy file
            for param, value in optimized_params.items():
                # Find and replace parameter values
                import re
                pattern = f"(self\.{param}\s*=\s*params\.get\(['\"]?{param}['\"]?,\s*)([^)]+)(\))"
                replacement = f"\\g<1>{value}\\g<3>"
                content = re.sub(pattern, replacement, content)
                logger.info(f"Strategy file updated: {param} = {value}")
            
            # Save updated strategy file
            with open(strategy_path, 'w') as f:
                f.write(content)
            
            logger.info(f"Strategy file updated: {strategy_path}")
            
        except Exception as e:
            logger.error(f"Error updating strategy file: {e}")
            raise
    
    def get_optimized_parameters(self, max_age_minutes=5, auto_optimize=True, 
                                generations=40, population=60):
        """
        Main method to get optimized parameters for live trading.
        
        Args:
            max_age_minutes: Maximum age of CSV file before running new optimization
            auto_optimize: Whether to automatically run optimization if needed
            generations: Number of generations for optimization
            population: Population size for optimization
            
        Returns:
            Dictionary of optimized parameters or None if failed
        """
        logger.info("=== DYNAMIC OPTIMIZATION CHECK ===")
        
        # Check for existing CSV file
        csv_file, age_minutes = self.get_latest_csv_file()
        
        need_optimization = False
        
        if csv_file is None:
            logger.info("No optimization results found - need to run optimization")
            need_optimization = True
        elif age_minutes > max_age_minutes:
            logger.info(f"Latest results are {age_minutes:.1f} minutes old (max: {max_age_minutes}) - need fresh optimization")
            need_optimization = True
        else:
            logger.info(f"Recent optimization results found ({age_minutes:.1f} minutes old) - using existing results")
        
        # Run optimization if needed
        if need_optimization and auto_optimize:
            logger.info("Running automatic optimization...")
            success = self.run_fast_optimization(generations, population)
            
            if success:
                # Get the new CSV file
                csv_file, age_minutes = self.get_latest_csv_file()
                if csv_file is None:
                    logger.error("Optimization completed but no CSV file found")
                    return None
            else:
                logger.error("Automatic optimization failed")
                return None
        elif need_optimization and not auto_optimize:
            logger.warning("Optimization needed but auto_optimize is disabled")
            return None
        
        # Extract parameters from CSV
        if csv_file:
            optimized_params = self.extract_best_parameters_from_csv(csv_file)
            
            if optimized_params:
                # Update strategy and config files
                if self.update_strategy_parameters(optimized_params):
                    logger.info("=== DYNAMIC OPTIMIZATION COMPLETE ===")
                    return optimized_params
                else:
                    logger.error("Failed to update strategy parameters")
                    return None
            else:
                logger.error("Failed to extract parameters from CSV")
                return None
        
        return None