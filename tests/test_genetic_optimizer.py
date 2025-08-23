#!/usr/bin/env python3
"""
Test script to debug genetic optimizer parameter issues
"""

import yaml
import sys
import os

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from optimization.genetic_optimizer import GeneticOptimizer

def main():
    """Test the genetic optimizer parameter handling"""
    
    # Load the config
    config_path = 'config/config.yaml'
    
    print("=== DEBUGGING GENETIC OPTIMIZER ===")
    
    # Initialize genetic optimizer
    optimizer = GeneticOptimizer(config_path)
    
    print(f"Parameter names: {optimizer.param_names}")
    print(f"Parameter bounds: {optimizer.param_bounds}")
    
    # Test parameter decoding
    test_solution = [10, 30, 5, 50, 2.0, 0.01, 0.02]  # Example solution
    decoded_params = optimizer.decode_solution(test_solution)
    print(f"Decoded params: {decoded_params}")
    
    # Test config creation
    test_config = optimizer.create_config_with_params(decoded_params)
    print(f"Base config strategy params: {optimizer.base_config['strategy']['params']}")
    print(f"Generated config strategy params: {test_config['strategy']['params']}")
    
    # Check for extra parameters
    base_params = set(optimizer.base_config['strategy']['params'].keys())
    generated_params = set(test_config['strategy']['params'].keys())
    extra_params = generated_params - base_params
    missing_params = base_params - generated_params
    
    print(f"Extra parameters in generated config: {extra_params}")
    print(f"Missing parameters from base config: {missing_params}")

if __name__ == "__main__":
    main()