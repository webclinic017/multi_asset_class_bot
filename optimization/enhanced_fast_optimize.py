#!/usr/bin/env python3
"""
Enhanced Fast Optimization Script with Advanced Parameter Management
Optimized for maximum returns with automatic CSV storage and parameter management
"""

import sys
import os
import time
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.enhanced_dynamic_optimizer import EnhancedDynamicOptimizer
from optimization.enhanced_genetic_optimizer import EnhancedGeneticOptimizer

def setup_logging(log_level=logging.INFO):
    """Setup comprehensive logging configuration"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler for detailed logs
    file_handler = logging.FileHandler('logs/enhanced_optimization.log')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Separate file for optimization results
    results_handler = logging.FileHandler('logs/optimization_results.log')
    results_handler.setLevel(logging.INFO)
    results_handler.setFormatter(simple_formatter)
    
    # Create results logger
    results_logger = logging.getLogger('optimization_results')
    results_logger.addHandler(results_handler)
    results_logger.setLevel(logging.INFO)
    results_logger.propagate = False

def print_banner():
    """Print optimization banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ENHANCED FAST OPTIMIZATION SYSTEM                        ║
║                     Maximum Returns Optimization                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  🚀 Advanced Genetic Algorithm with Multi-Objective Optimization           ║
║  📊 Dynamic Parameter Management with Age Checking                          ║
║  💾 Automatic CSV Storage and Performance Tracking                          ║
║  🎯 Optimized for Maximum Risk-Adjusted Returns                            ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def validate_config(config_path):
    """Validate configuration file exists and is readable"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Basic validation
        required_sections = ['data', 'strategy', 'backtesting']
        for section in required_sections:
            if section not in config:
                raise ValueError(f"Missing required configuration section: {section}")
                
        return config
        
    except Exception as e:
        raise ValueError(f"Invalid configuration file: {e}")

def create_output_directory(output_dir):
    """Create output directory structure"""
    try:
        os.makedirs(output_dir, exist_ok=True)
        
        # Create subdirectories
        subdirs = ['csv_results', 'parameter_store', 'optimization_logs', 'performance_reports']
        for subdir in subdirs:
            os.makedirs(os.path.join(output_dir, subdir), exist_ok=True)
            
        return True
        
    except Exception as e:
        logging.error(f"Failed to create output directory structure: {e}")
        return False

def run_optimization_with_monitoring(optimizer, strategy_type, generations, population, force=False):
    """Run optimization with comprehensive monitoring and error handling"""
    logger = logging.getLogger(__name__)
    results_logger = logging.getLogger('optimization_results')
    
    try:
        logger.info(f"Starting optimization for {strategy_type} strategy")
        logger.info(f"Parameters: {generations} generations, {population} population")
        
        # Check if optimization is needed
        if not force:
            recommendation = optimizer.get_optimization_recommendation(strategy_type)
            if not recommendation['should_optimize']:
                logger.info("Optimization not recommended based on current parameters")
                return {
                    'success': True,
                    'skipped': True,
                    'reason': 'Optimization not needed',
                    'recommendation': recommendation
                }
        
        # Run the optimization
        start_time = time.time()
        result = optimizer.run_enhanced_optimization(
            strategy_type=strategy_type,
            generations=generations,
            population=population,
            force=force
        )
        
        end_time = time.time()
        total_time = end_time - start_time
        
        if result['success']:
            # Log successful optimization
            results_logger.info(f"✅ {strategy_type.upper()} OPTIMIZATION COMPLETED")
            results_logger.info(f"⏱️  Duration: {total_time:.2f} seconds")
            results_logger.info(f"🎯 Best Fitness: {result.get('best_fitness', 0):.4f}")
            results_logger.info(f"📈 Total Return: {result['performance_metrics']['total_return']:.2f}%")
            results_logger.info(f"📊 Sharpe Ratio: {result['performance_metrics']['sharpe_ratio']:.2f}")
            results_logger.info(f"📉 Max Drawdown: {result['performance_metrics']['max_drawdown']:.1f}%")
            results_logger.info(f"🎲 Win Rate: {result['performance_metrics']['win_rate']:.1f}%")
            results_logger.info(f"💾 Results saved to: {result.get('csv_path', 'N/A')}")
            
            # Add timing information
            result['total_optimization_time'] = total_time
            result['skipped'] = False
            
        else:
            results_logger.error(f"❌ {strategy_type.upper()} OPTIMIZATION FAILED")
            results_logger.error(f"Error: {result.get('error', 'Unknown error')}")
            
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error during optimization: {e}")
        results_logger.error(f"❌ OPTIMIZATION CRASHED: {e}")
        return {
            'success': False,
            'error': str(e),
            'skipped': False
        }

def generate_performance_report(results, output_dir):
    """Generate comprehensive performance report"""
    try:
        report_path = os.path.join(output_dir, 'performance_reports', 
                                  f'optimization_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
        
        with open(report_path, 'w') as f:
            f.write("ENHANCED OPTIMIZATION PERFORMANCE REPORT\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")
            
            for strategy_type, result in results.items():
                f.write(f"{strategy_type.upper()} STRATEGY RESULTS:\n")
                f.write("-" * 30 + "\n")
                
                if result.get('skipped'):
                    f.write(f"Status: SKIPPED\n")
                    f.write(f"Reason: {result.get('reason', 'N/A')}\n")
                elif result.get('success'):
                    f.write(f"Status: SUCCESS\n")
                    f.write(f"Optimization Time: {result.get('total_optimization_time', 0):.2f} seconds\n")
                    f.write(f"Best Fitness Score: {result.get('best_fitness', 0):.4f}\n")
                    
                    metrics = result.get('performance_metrics', {})
                    f.write(f"Total Return: {metrics.get('total_return', 0):.2f}%\n")
                    f.write(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}\n")
                    f.write(f"Max Drawdown: {metrics.get('max_drawdown', 0):.1f}%\n")
                    f.write(f"Win Rate: {metrics.get('win_rate', 0):.1f}%\n")
                    f.write(f"Total Trades: {metrics.get('total_trades', 0)}\n")
                    f.write(f"CSV Results: {result.get('csv_path', 'N/A')}\n")
                else:
                    f.write(f"Status: FAILED\n")
                    f.write(f"Error: {result.get('error', 'Unknown error')}\n")
                    
                f.write("\n")
                
        logging.info(f"Performance report saved to: {report_path}")
        return report_path
        
    except Exception as e:
        logging.error(f"Failed to generate performance report: {e}")
        return None

def main():
    """Main function for enhanced fast optimization"""
    parser = argparse.ArgumentParser(
        description='Enhanced Fast Optimization with Maximum Returns Focus',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --strategy forex --generations 50 --population 24
  %(prog)s --strategy crypto --generations 40 --population 20 --force
  %(prog)s --strategy both --auto-optimize
  %(prog)s --check-only  # Just check parameter status
        """
    )
    
    parser.add_argument('--config', default='config/config.yaml', 
                       help='Path to configuration file (default: config/config.yaml)')
    parser.add_argument('--strategy', choices=['forex', 'crypto', 'both'], default='both',
                       help='Strategy type to optimize (default: both)')
    parser.add_argument('--generations', type=int, default=50, 
                       help='Number of generations (default: 50)')
    parser.add_argument('--population', type=int, default=24, 
                       help='Population size (default: 24)')
    parser.add_argument('--output-dir', default='output', 
                       help='Output directory for results (default: output)')
    parser.add_argument('--force', action='store_true', 
                       help='Force optimization even if not recommended')
    parser.add_argument('--auto-optimize', action='store_true',
                       help='Use automatic optimization with intelligent parameter selection')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check parameter status without optimizing')
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--max-age-hours', type=float, default=24.0,
                       help='Maximum parameter age in hours before optimization (default: 24)')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    
    # Print banner
    print_banner()
    
    print(f"🔧 Configuration: {args.config}")
    print(f"📊 Strategy: {args.strategy}")
    print(f"📁 Output Directory: {args.output_dir}")
    print(f"⏰ Max Parameter Age: {args.max_age_hours} hours")
    print("=" * 80)
    
    try:
        # Validate configuration
        logger.info("Validating configuration...")
        config = validate_config(args.config)
        print("✅ Configuration validated")
        
        # Create output directory structure
        logger.info("Setting up output directory structure...")
        if not create_output_directory(args.output_dir):
            raise RuntimeError("Failed to create output directory structure")
        print("✅ Output directory structure created")
        
        # Initialize enhanced dynamic optimizer
        logger.info("Initializing Enhanced Dynamic Optimizer...")
        optimizer = EnhancedDynamicOptimizer(args.config, args.output_dir)
        
        # Set maximum age
        optimizer.max_age_minutes = args.max_age_hours * 60
        
        print("✅ Enhanced Dynamic Optimizer initialized")
        
        # Determine strategies to process
        strategies = []
        if args.strategy == 'both':
            strategies = ['forex', 'crypto']
        else:
            strategies = [args.strategy]
            
        # Check-only mode
        if args.check_only:
            print("\n📋 PARAMETER STATUS CHECK")
            print("=" * 40)
            
            for strategy_type in strategies:
                print(f"\n{strategy_type.upper()} Strategy:")
                
                # Get parameter summary
                summary = optimizer.get_parameter_performance_summary(strategy_type)
                
                if summary['has_parameters']:
                    print(f"  Age: {summary['age_hours']:.1f} hours")
                    print(f"  Performance Score: {summary['performance_score']:.4f}")
                    print(f"  Total Return: {summary['total_return']:.2f}%")
                    print(f"  Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
                    print(f"  Max Drawdown: {summary['max_drawdown']:.1f}%")
                    print(f"  Win Rate: {summary['win_rate']:.1f}%")
                    
                    # Check thresholds
                    thresholds = summary['meets_thresholds']
                    failing_thresholds = [k for k, v in thresholds.items() if not v]
                    
                    if failing_thresholds:
                        print(f"  ⚠️  Failing thresholds: {', '.join(failing_thresholds)}")
                    else:
                        print(f"  ✅ All thresholds met")
                else:
                    print(f"  ❌ No parameters found")
                    
                # Get recommendation
                recommendation = optimizer.get_optimization_recommendation(strategy_type)
                print(f"  Recommendation: {'Optimize' if recommendation['should_optimize'] else 'No action needed'}")
                print(f"  Priority: {recommendation['priority']}")
                
            return
            
        # Run optimizations
        results = {}
        total_start_time = time.time()
        
        print(f"\n🚀 STARTING OPTIMIZATION")
        print("=" * 40)
        
        for strategy_type in strategies:
            print(f"\n📈 Processing {strategy_type.upper()} strategy...")
            
            if args.auto_optimize:
                # Use auto-optimization with intelligent parameters
                result = optimizer.auto_optimize_if_needed(strategy_type)
            else:
                # Use manual parameters
                result = run_optimization_with_monitoring(
                    optimizer, strategy_type, args.generations, args.population, args.force
                )
                
            results[strategy_type] = result
            
            # Print immediate results
            if result.get('skipped'):
                print(f"  ⏸️  Skipped: {result.get('reason', 'Unknown reason')}")
            elif result.get('success'):
                metrics = result.get('performance_metrics', {})
                print(f"  ✅ Success! Return: {metrics.get('total_return', 0):.2f}%, "
                      f"Sharpe: {metrics.get('sharpe_ratio', 0):.2f}")
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        # Generate performance report
        print(f"\n📊 GENERATING PERFORMANCE REPORT")
        print("=" * 40)
        
        report_path = generate_performance_report(results, args.output_dir)
        if report_path:
            print(f"✅ Performance report saved to: {report_path}")
            
        # Final summary
        print(f"\n🏁 OPTIMIZATION COMPLETE")
        print("=" * 40)
        print(f"⏱️  Total Duration: {total_duration:.2f} seconds")
        
        successful_optimizations = sum(1 for r in results.values() if r.get('success') and not r.get('skipped'))
        skipped_optimizations = sum(1 for r in results.values() if r.get('skipped'))
        failed_optimizations = sum(1 for r in results.values() if not r.get('success') and not r.get('skipped'))
        
        print(f"✅ Successful: {successful_optimizations}")
        print(f"⏸️  Skipped: {skipped_optimizations}")
        print(f"❌ Failed: {failed_optimizations}")
        
        # Show CSV locations
        csv_files = [r.get('csv_path') for r in results.values() if r.get('csv_path')]
        if csv_files:
            print(f"\n💾 CSV Results saved to:")
            for csv_file in csv_files:
                print(f"  📄 {csv_file}")
                
        # Performance tips
        if total_duration > 600:  # 10 minutes
            print(f"\n💡 PERFORMANCE TIPS:")
            print(f"  - Consider reducing population size or generations for faster optimization")
            print(f"  - Use --auto-optimize for intelligent parameter selection")
            print(f"  - Install GPU acceleration libraries for faster computation")
            
        print(f"\n🎉 Enhanced optimization completed successfully!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️  Optimization interrupted by user")
        logger.info("Optimization interrupted by user")
        sys.exit(1)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        logger.error(f"Optimization failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()