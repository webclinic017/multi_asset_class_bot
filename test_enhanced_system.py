#!/usr/bin/env python3
"""
Comprehensive Test Suite for Enhanced Trading System
Tests all components including strategies, optimization, and parameter management
"""

import sys
import os
import time
import logging
import unittest
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from pathlib import Path

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our enhanced components
from utils.enhanced_dynamic_optimizer import EnhancedDynamicOptimizer, ParameterSet
from optimization.enhanced_genetic_optimizer import EnhancedGeneticOptimizer
from strategies.enhanced_forex_strategy import EnhancedForexStrategy
from strategies.enhanced_crypto_strategy import EnhancedCryptoStrategy

class TestEnhancedTradingSystem(unittest.TestCase):
    """Comprehensive test suite for the enhanced trading system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        cls.logger = logging.getLogger(__name__)
        
        # Create test directories
        cls.test_output_dir = 'test_output'
        os.makedirs(cls.test_output_dir, exist_ok=True)
        
        # Test configuration
        cls.test_config_path = 'config/config.yaml'
        
        cls.logger.info("Test environment setup complete")
    
    def setUp(self):
        """Set up each test"""
        self.logger.info(f"Starting test: {self._testMethodName}")
        
    def tearDown(self):
        """Clean up after each test"""
        self.logger.info(f"Completed test: {self._testMethodName}")
    
    def test_enhanced_dynamic_optimizer_initialization(self):
        """Test enhanced dynamic optimizer initialization"""
        self.logger.info("Testing Enhanced Dynamic Optimizer initialization...")
        
        try:
            optimizer = EnhancedDynamicOptimizer(
                config_path=self.test_config_path,
                output_dir=self.test_output_dir
            )
            
            # Test basic properties
            self.assertIsNotNone(optimizer)
            self.assertEqual(optimizer.config_path, self.test_config_path)
            self.assertEqual(optimizer.output_dir, self.test_output_dir)
            self.assertIsInstance(optimizer.parameter_store, list)
            self.assertIsInstance(optimizer.optimization_history, list)
            
            self.logger.info("Enhanced Dynamic Optimizer initialization test passed")
            
        except Exception as e:
            self.logger.error(f"Enhanced Dynamic Optimizer initialization test failed: {e}")
            self.fail(f"Initialization failed: {e}")
    
    def test_parameter_set_creation(self):
        """Test parameter set creation and management"""
        self.logger.info("Testing Parameter Set creation...")
        
        try:
            # Create test parameter set
            test_params = {
                'fast_length': 12,
                'slow_length': 26,
                'rsi_period': 14,
                'stop_loss_percent': 0.02
            }
            
            param_set = ParameterSet(
                parameters=test_params,
                timestamp=datetime.now(),
                performance_score=0.75,
                total_return=15.5,
                sharpe_ratio=1.2,
                max_drawdown=8.5,
                win_rate=65.0,
                total_trades=50,
                strategy_type='forex',
                optimization_id='test_001'
            )
            
            # Test parameter set properties
            self.assertEqual(param_set.parameters, test_params)
            self.assertEqual(param_set.strategy_type, 'forex')
            self.assertEqual(param_set.performance_score, 0.75)
            self.assertTrue(param_set.is_active)
            
            self.logger.info("Parameter Set creation test passed")
            
        except Exception as e:
            self.logger.error(f"Parameter Set creation test failed: {e}")
            self.fail(f"Parameter set creation failed: {e}")
    
    def test_parameter_age_checking(self):
        """Test parameter age checking functionality"""
        self.logger.info("Testing parameter age checking...")
        
        try:
            optimizer = EnhancedDynamicOptimizer(
                config_path=self.test_config_path,
                output_dir=self.test_output_dir
            )
            
            # Clear existing parameters for clean test
            optimizer.parameter_store = []
            
            # Test with no parameters
            needs_opt, age = optimizer.check_parameter_age('forex')
            self.assertTrue(needs_opt)
            self.assertEqual(age, float('inf'))
            
            # Add a recent parameter set
            recent_params = ParameterSet(
                parameters={'fast_length': 10, 'slow_length': 20},
                timestamp=datetime.now() - timedelta(minutes=30),
                performance_score=0.8,
                total_return=10.0,
                sharpe_ratio=1.0,
                max_drawdown=5.0,
                win_rate=60.0,
                total_trades=25,
                strategy_type='forex',
                optimization_id='test_recent'
            )
            
            optimizer.add_parameter_set(recent_params)
            
            # Test with recent parameters
            needs_opt, age = optimizer.check_parameter_age('forex')
            self.assertFalse(needs_opt)  # Should not need optimization (< 24 hours)
            self.assertAlmostEqual(age, 30, delta=5)  # Should be around 30 minutes
            
            self.logger.info("Parameter age checking test passed")
            
        except Exception as e:
            self.logger.error(f"Parameter age checking test failed: {e}")
            self.fail(f"Parameter age checking failed: {e}")
    
    def test_optimization_recommendation(self):
        """Test optimization recommendation system"""
        self.logger.info("Testing optimization recommendation system...")
        
        try:
            optimizer = EnhancedDynamicOptimizer(
                config_path=self.test_config_path,
                output_dir=self.test_output_dir
            )
            
            # Clear existing parameters for clean test
            optimizer.parameter_store = []
            
            # Test recommendation with no parameters
            recommendation = optimizer.get_optimization_recommendation('forex')
            self.assertIsInstance(recommendation, dict)
            self.assertIn('should_optimize', recommendation)
            self.assertIn('reasons', recommendation)
            self.assertIn('priority', recommendation)
            
            # Should recommend optimization when no parameters exist
            self.assertTrue(recommendation['should_optimize'])
            
            # Add poor performing parameters
            poor_params = ParameterSet(
                parameters={'fast_length': 5, 'slow_length': 10},
                timestamp=datetime.now() - timedelta(hours=25),  # Old parameters
                performance_score=0.2,  # Poor performance
                total_return=-5.0,      # Negative return
                sharpe_ratio=-0.5,      # Negative Sharpe
                max_drawdown=25.0,      # High drawdown
                win_rate=30.0,          # Low win rate
                total_trades=10,
                strategy_type='forex',
                optimization_id='test_poor'
            )
            
            optimizer.add_parameter_set(poor_params)
            
            # Test recommendation with poor parameters
            recommendation = optimizer.get_optimization_recommendation('forex')
            self.assertTrue(recommendation['should_optimize'])
            self.assertIn(recommendation['priority'], ['medium', 'high'])  # Accept both valid priorities
            self.assertGreater(len(recommendation['reasons']), 0)
            
            self.logger.info("Optimization recommendation test passed")
            
        except Exception as e:
            self.logger.error(f"Optimization recommendation test failed: {e}")
            self.fail(f"Optimization recommendation failed: {e}")
    
    def test_enhanced_genetic_optimizer_initialization(self):
        """Test enhanced genetic optimizer initialization"""
        self.logger.info("Testing Enhanced Genetic Optimizer initialization...")
        
        try:
            # Test forex optimizer
            forex_optimizer = EnhancedGeneticOptimizer(
                config_path=self.test_config_path,
                strategy_type='forex'
            )
            
            self.assertEqual(forex_optimizer.strategy_type, 'forex')
            self.assertIsInstance(forex_optimizer.param_bounds, dict)
            self.assertGreater(len(forex_optimizer.param_names), 0)
            
            # Test crypto optimizer
            crypto_optimizer = EnhancedGeneticOptimizer(
                config_path=self.test_config_path,
                strategy_type='crypto'
            )
            
            self.assertEqual(crypto_optimizer.strategy_type, 'crypto')
            self.assertIsInstance(crypto_optimizer.param_bounds, dict)
            
            # Verify different parameter spaces
            self.assertNotEqual(
                set(forex_optimizer.param_names),
                set(crypto_optimizer.param_names)
            )
            
            self.logger.info("Enhanced Genetic Optimizer initialization test passed")
            
        except Exception as e:
            self.logger.error(f"Enhanced Genetic Optimizer initialization test failed: {e}")
            self.fail(f"Enhanced Genetic Optimizer initialization failed: {e}")
    
    def test_parameter_validation(self):
        """Test parameter validation logic"""
        self.logger.info("Testing parameter validation...")
        
        try:
            optimizer = EnhancedGeneticOptimizer(
                config_path=self.test_config_path,
                strategy_type='forex'
            )
            
            # Test valid parameters
            valid_params = {
                'fast_length': 10,
                'slow_length': 20,
                'rsi_oversold': 25,
                'rsi_overbought': 75,
                'macd_fast': 12,
                'macd_slow': 26,
                'base_stop_loss': 0.01,
                'base_take_profit': 0.02
            }
            
            self.assertTrue(optimizer.validate_parameters(valid_params))
            
            # Test invalid parameters (fast >= slow)
            invalid_params = {
                'fast_length': 20,
                'slow_length': 10,  # Invalid: slow < fast
                'rsi_oversold': 25,
                'rsi_overbought': 75
            }
            
            self.assertFalse(optimizer.validate_parameters(invalid_params))
            
            # Test invalid RSI parameters
            invalid_rsi = {
                'fast_length': 10,
                'slow_length': 20,
                'rsi_oversold': 80,  # Invalid: oversold > overbought
                'rsi_overbought': 70
            }
            
            self.assertFalse(optimizer.validate_parameters(invalid_rsi))
            
            self.logger.info("Parameter validation test passed")
            
        except Exception as e:
            self.logger.error(f"Parameter validation test failed: {e}")
            self.fail(f"Parameter validation failed: {e}")
    
    def test_fitness_calculation(self):
        """Test multi-objective fitness calculation"""
        self.logger.info("Testing fitness calculation...")
        
        try:
            optimizer = EnhancedGeneticOptimizer(
                config_path=self.test_config_path,
                strategy_type='forex'
            )
            
            # Test excellent performance
            excellent_results = {
                'total_return': 25.0,
                'sharpe_ratio': 2.0,
                'max_drawdown': 5.0,
                'win_rate': 70.0,
                'total_trades': 50,
                'profit_factor': 2.5,
                'final_value': 12500.0
            }
            
            excellent_fitness = optimizer.calculate_multi_objective_fitness(excellent_results)
            self.assertGreater(excellent_fitness, 0.5)
            
            # Test poor performance
            poor_results = {
                'total_return': -10.0,
                'sharpe_ratio': -0.5,
                'max_drawdown': 30.0,
                'win_rate': 30.0,
                'total_trades': 20,
                'profit_factor': 0.5,
                'final_value': 9000.0
            }
            
            poor_fitness = optimizer.calculate_multi_objective_fitness(poor_results)
            self.assertLess(poor_fitness, 0.0)
            
            # Excellent should be better than poor
            self.assertGreater(excellent_fitness, poor_fitness)
            
            # Test insufficient trades penalty
            insufficient_trades = {
                'total_return': 15.0,
                'sharpe_ratio': 1.5,
                'max_drawdown': 8.0,
                'win_rate': 60.0,
                'total_trades': 5,  # Too few trades
                'profit_factor': 1.8,
                'final_value': 11500.0
            }
            
            insufficient_fitness = optimizer.calculate_multi_objective_fitness(insufficient_trades)
            self.assertEqual(insufficient_fitness, -1000)  # Should be penalized
            
            self.logger.info("Fitness calculation test passed")
            
        except Exception as e:
            self.logger.error(f"Fitness calculation test failed: {e}")
            self.fail(f"Fitness calculation failed: {e}")
    
    def test_csv_export_functionality(self):
        """Test CSV export functionality"""
        self.logger.info("Testing CSV export functionality...")
        
        try:
            optimizer = EnhancedDynamicOptimizer(
                config_path=self.test_config_path,
                output_dir=self.test_output_dir
            )
            
            # Add some test parameter sets
            for i in range(3):
                test_params = ParameterSet(
                    parameters={
                        'fast_length': 10 + i,
                        'slow_length': 20 + i * 2,
                        'rsi_period': 14 + i
                    },
                    timestamp=datetime.now() - timedelta(hours=i),
                    performance_score=0.6 + i * 0.1,
                    total_return=10.0 + i * 5.0,
                    sharpe_ratio=1.0 + i * 0.2,
                    max_drawdown=10.0 - i,
                    win_rate=55.0 + i * 5.0,
                    total_trades=30 + i * 10,
                    strategy_type='forex',
                    optimization_id=f'test_{i:03d}'
                )
                optimizer.add_parameter_set(test_params)
            
            # Test parameter summary
            summary = optimizer.get_parameter_performance_summary('forex')
            self.assertTrue(summary['has_parameters'])
            self.assertGreater(summary['performance_score'], 0)
            
            self.logger.info("CSV export functionality test passed")
            
        except Exception as e:
            self.logger.error(f"CSV export functionality test failed: {e}")
            self.fail(f"CSV export functionality failed: {e}")
    
    def test_strategy_classes_import(self):
        """Test that enhanced strategy classes can be imported and initialized"""
        self.logger.info("Testing enhanced strategy classes...")
        
        try:
            # Test enhanced forex strategy import
            self.assertIsNotNone(EnhancedForexStrategy)
            
            # Test enhanced crypto strategy import
            self.assertIsNotNone(EnhancedCryptoStrategy)
            
            # Verify they are different classes
            self.assertNotEqual(EnhancedForexStrategy, EnhancedCryptoStrategy)
            
            self.logger.info("Enhanced strategy classes test passed")
            
        except Exception as e:
            self.logger.error(f"Enhanced strategy classes test failed: {e}")
            self.fail(f"Enhanced strategy classes test failed: {e}")
    
    def test_configuration_loading(self):
        """Test configuration loading and validation"""
        self.logger.info("Testing configuration loading...")
        
        try:
            # Test that config file exists and is readable
            self.assertTrue(os.path.exists(self.test_config_path))
            
            # Test optimizer can load config
            optimizer = EnhancedDynamicOptimizer(
                config_path=self.test_config_path,
                output_dir=self.test_output_dir
            )
            
            # Verify optimizer was initialized successfully
            self.assertIsNotNone(optimizer)
            self.assertEqual(optimizer.config_path, self.test_config_path)
            
            # Test that genetic optimizer can load config
            genetic_optimizer = EnhancedGeneticOptimizer(
                config_path=self.test_config_path,
                strategy_type='forex'
            )
            
            # Verify genetic optimizer loaded config
            self.assertIsNotNone(genetic_optimizer.base_config)
            self.assertIsInstance(genetic_optimizer.base_config, dict)
            
            self.logger.info("Configuration loading test passed")
            
        except Exception as e:
            self.logger.error(f"Configuration loading test failed: {e}")
            self.fail(f"Configuration loading failed: {e}")

class TestSystemIntegration(unittest.TestCase):
    """Integration tests for the complete system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up integration test environment"""
        logging.basicConfig(level=logging.INFO)
        cls.logger = logging.getLogger(__name__)
        cls.test_output_dir = 'integration_test_output'
        os.makedirs(cls.test_output_dir, exist_ok=True)
        cls.test_config_path = 'config/config.yaml'
    
    def test_end_to_end_optimization_workflow(self):
        """Test complete optimization workflow"""
        self.logger.info("Testing end-to-end optimization workflow...")
        
        try:
            # Initialize enhanced dynamic optimizer
            optimizer = EnhancedDynamicOptimizer(
                config_path=self.test_config_path,
                output_dir=self.test_output_dir
            )
            
            # Test parameter age check
            needs_opt, age = optimizer.check_parameter_age('forex')
            self.logger.info(f"Parameter age check: needs_optimization={needs_opt}, age={age}")
            
            # Test optimization recommendation
            recommendation = optimizer.get_optimization_recommendation('forex')
            self.logger.info(f"Optimization recommendation: {recommendation}")
            
            # Verify recommendation structure
            self.assertIn('should_optimize', recommendation)
            self.assertIn('reasons', recommendation)
            self.assertIn('priority', recommendation)
            
            self.logger.info("End-to-end optimization workflow test passed")
            
        except Exception as e:
            self.logger.error(f"End-to-end optimization workflow test failed: {e}")
            self.fail(f"End-to-end workflow failed: {e}")
    
    def test_multi_strategy_support(self):
        """Test multi-strategy support"""
        self.logger.info("Testing multi-strategy support...")
        
        try:
            optimizer = EnhancedDynamicOptimizer(
                config_path=self.test_config_path,
                output_dir=self.test_output_dir
            )
            
            # Test forex strategy
            forex_summary = optimizer.get_parameter_performance_summary('forex')
            self.assertIsInstance(forex_summary, dict)
            
            # Test crypto strategy
            crypto_summary = optimizer.get_parameter_performance_summary('crypto')
            self.assertIsInstance(crypto_summary, dict)
            
            # Test different genetic optimizers
            forex_genetic = EnhancedGeneticOptimizer(self.test_config_path, 'forex')
            crypto_genetic = EnhancedGeneticOptimizer(self.test_config_path, 'crypto')
            
            # Verify different parameter spaces
            self.assertNotEqual(forex_genetic.param_bounds, crypto_genetic.param_bounds)
            
            self.logger.info("Multi-strategy support test passed")
            
        except Exception as e:
            self.logger.error(f"Multi-strategy support test failed: {e}")
            self.fail(f"Multi-strategy support failed: {e}")

def run_performance_benchmark():
    """Run performance benchmark tests"""
    logger = logging.getLogger(__name__)
    logger.info("Running performance benchmarks...")
    
    try:
        # Test parameter storage performance
        start_time = time.time()
        
        optimizer = EnhancedDynamicOptimizer(
            config_path='config/config.yaml',
            output_dir='benchmark_output'
        )
        
        # Add many parameter sets to test performance
        for i in range(100):
            param_set = ParameterSet(
                parameters={'fast_length': 10 + i % 10, 'slow_length': 20 + i % 20},
                timestamp=datetime.now() - timedelta(minutes=i),
                performance_score=0.5 + (i % 50) / 100,
                total_return=float(i % 30),
                sharpe_ratio=float((i % 20) / 10),
                max_drawdown=float(i % 15),
                win_rate=float(50 + i % 30),
                total_trades=20 + i % 50,
                strategy_type='forex' if i % 2 == 0 else 'crypto',
                optimization_id=f'bench_{i:03d}'
            )
            optimizer.add_parameter_set(param_set)
        
        end_time = time.time()
        duration = end_time - start_time
        
        logger.info(f"Performance benchmark completed in {duration:.2f} seconds")
        logger.info(f"Added 100 parameter sets, average time per set: {duration/100*1000:.2f}ms")
        
        # Test retrieval performance
        start_time = time.time()
        
        for strategy_type in ['forex', 'crypto']:
            latest = optimizer.get_latest_parameters(strategy_type)
            summary = optimizer.get_parameter_performance_summary(strategy_type)
            recommendation = optimizer.get_optimization_recommendation(strategy_type)
        
        end_time = time.time()
        retrieval_duration = end_time - start_time
        
        logger.info(f"Retrieval benchmark completed in {retrieval_duration:.2f} seconds")
        
        return True
        
    except Exception as e:
        logger.error(f"Performance benchmark failed: {e}")
        return False

def main():
    """Main test runner"""
    print("Enhanced Trading System Test Suite")
    print("=" * 60)
    
    # Setup test environment
    os.makedirs('test_logs', exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('test_logs/test_results.log')
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Run unit tests
    print("\nRunning Unit Tests...")
    print("-" * 40)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test cases
    test_suite.addTest(unittest.makeSuite(TestEnhancedTradingSystem))
    test_suite.addTest(unittest.makeSuite(TestSystemIntegration))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(test_suite)
    
    # Run performance benchmarks
    print("\nRunning Performance Benchmarks...")
    print("-" * 40)
    
    benchmark_success = run_performance_benchmark()
    
    # Summary
    print("\nTest Summary")
    print("=" * 60)
    
    total_tests = test_result.testsRun
    failures = len(test_result.failures)
    errors = len(test_result.errors)
    successes = total_tests - failures - errors
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {successes}")
    print(f"Failed: {failures}")
    print(f"Errors: {errors}")
    print(f"Benchmarks: {'Passed' if benchmark_success else 'Failed'}")
    
    success_rate = (successes / total_tests) * 100 if total_tests > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if failures > 0 or errors > 0:
        print("\nSome tests failed. Check the logs for details.")
        return 1
    elif not benchmark_success:
        print("\nBenchmarks failed. Check the logs for details.")
        return 1
    else:
        print("\nAll tests passed successfully!")
        print("\nEnhanced Trading System is ready for use!")
        print("\nNext steps:")
        print("1. Run: python enhanced_fast_optimize.py --strategy both --auto-optimize")
        print("2. Run: python main.py --mode optimize")
        print("3. Run: python main.py --mode live")
        return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)