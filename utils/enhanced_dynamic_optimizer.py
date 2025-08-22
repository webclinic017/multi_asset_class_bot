"""
Enhanced Dynamic Parameter Optimization System
Advanced parameter management with age checking, automatic optimization, and performance monitoring
"""

import os
import glob
import subprocess
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yaml
import time
import json
import hashlib
from typing import Dict, Any, Optional, Tuple, List
from pathlib import Path
import threading
import queue
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class OptimizationStatus(Enum):
    """Optimization status enumeration"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SCHEDULED = "scheduled"

@dataclass
class ParameterSet:
    """Data class for parameter sets with metadata"""
    parameters: Dict[str, Any]
    timestamp: datetime
    performance_score: float
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    strategy_type: str
    optimization_id: str
    is_active: bool = True

class EnhancedDynamicOptimizer:
    """
    Enhanced dynamic optimizer with advanced parameter management
    """
    
    def __init__(self, config_path: str = 'config/config.yaml', output_dir: str = 'output'):
        self.config_path = config_path
        self.output_dir = output_dir
        self.parameter_store_path = os.path.join(output_dir, 'parameter_store.json')
        self.optimization_log_path = os.path.join(output_dir, 'optimization_log.json')
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Parameter management
        self.parameter_store: List[ParameterSet] = []
        self.optimization_history: List[Dict[str, Any]] = []
        self.current_optimization_status = OptimizationStatus.IDLE
        
        # Configuration
        self.max_age_minutes = 1440  # 24 hours default
        self.min_performance_improvement = 0.05  # 5% minimum improvement
        self.optimization_cooldown_minutes = 60  # 1 hour cooldown between optimizations
        self.max_stored_parameter_sets = 50  # Maximum parameter sets to store
        
        # Performance monitoring
        self.performance_threshold = {
            'min_sharpe_ratio': 0.5,
            'min_total_return': 2.0,
            'max_drawdown': 20.0,
            'min_win_rate': 45.0,
            'min_trades': 10
        }
        
        # Load existing data
        self._load_parameter_store()
        self._load_optimization_history()
        
        logger.info("Enhanced Dynamic Optimizer initialized")
        
    def _load_parameter_store(self):
        """Load parameter store from disk"""
        try:
            if os.path.exists(self.parameter_store_path):
                with open(self.parameter_store_path, 'r') as f:
                    data = json.load(f)
                    
                self.parameter_store = []
                for item in data:
                    # Convert timestamp string back to datetime
                    item['timestamp'] = datetime.fromisoformat(item['timestamp'])
                    self.parameter_store.append(ParameterSet(**item))
                    
                logger.info(f"Loaded {len(self.parameter_store)} parameter sets from store")
            else:
                logger.info("No existing parameter store found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading parameter store: {e}")
            self.parameter_store = []
            
    def _save_parameter_store(self):
        """Save parameter store to disk"""
        try:
            # Convert to serializable format
            data = []
            for param_set in self.parameter_store:
                item = asdict(param_set)
                item['timestamp'] = item['timestamp'].isoformat()
                data.append(item)
                
            with open(self.parameter_store_path, 'w') as f:
                json.dump(data, f, indent=2)
                
            logger.debug(f"Saved {len(self.parameter_store)} parameter sets to store")
            
        except Exception as e:
            logger.error(f"Error saving parameter store: {e}")
            
    def _load_optimization_history(self):
        """Load optimization history from disk"""
        try:
            if os.path.exists(self.optimization_log_path):
                with open(self.optimization_log_path, 'r') as f:
                    self.optimization_history = json.load(f)
                    
                logger.info(f"Loaded {len(self.optimization_history)} optimization records")
            else:
                self.optimization_history = []
                
        except Exception as e:
            logger.error(f"Error loading optimization history: {e}")
            self.optimization_history = []
            
    def _save_optimization_history(self):
        """Save optimization history to disk"""
        try:
            with open(self.optimization_log_path, 'w') as f:
                json.dump(self.optimization_history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving optimization history: {e}")
            
    def get_latest_parameters(self, strategy_type: str = 'forex') -> Optional[ParameterSet]:
        """
        Get the latest active parameter set for a strategy type
        """
        try:
            # Filter by strategy type and active status
            active_params = [p for p in self.parameter_store 
                           if p.strategy_type == strategy_type and p.is_active]
            
            if not active_params:
                return None
                
            # Sort by timestamp and return the latest
            latest = max(active_params, key=lambda x: x.timestamp)
            
            logger.info(f"Retrieved latest {strategy_type} parameters from {latest.timestamp}")
            return latest
            
        except Exception as e:
            logger.error(f"Error getting latest parameters: {e}")
            return None
            
    def check_parameter_age(self, strategy_type: str = 'forex') -> Tuple[bool, float]:
        """
        Check if parameters are older than the maximum age
        
        Returns:
            (needs_optimization, age_in_minutes)
        """
        try:
            latest_params = self.get_latest_parameters(strategy_type)
            
            if latest_params is None:
                logger.info(f"No parameters found for {strategy_type}, optimization needed")
                return True, float('inf')
                
            # Calculate age
            age_minutes = (datetime.now() - latest_params.timestamp).total_seconds() / 60
            needs_optimization = age_minutes > self.max_age_minutes
            
            logger.info(f"{strategy_type} parameters age: {age_minutes:.1f} minutes "
                       f"(max: {self.max_age_minutes})")
            
            return needs_optimization, age_minutes
            
        except Exception as e:
            logger.error(f"Error checking parameter age: {e}")
            return True, float('inf')
            
    def check_performance_degradation(self, strategy_type: str = 'forex') -> bool:
        """
        Check if current parameters show performance degradation
        """
        try:
            # Get recent parameter sets
            recent_params = [p for p in self.parameter_store 
                           if p.strategy_type == strategy_type and p.is_active]
            
            if len(recent_params) < 2:
                return False
                
            # Sort by timestamp
            recent_params.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Compare latest with previous
            latest = recent_params[0]
            previous = recent_params[1]
            
            # Check for significant performance degradation
            performance_drop = (previous.performance_score - latest.performance_score) / previous.performance_score
            
            if performance_drop > self.min_performance_improvement:
                logger.warning(f"Performance degradation detected: {performance_drop:.2%}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking performance degradation: {e}")
            return False
            
    def can_run_optimization(self) -> Tuple[bool, str]:
        """
        Check if optimization can be run (cooldown, status, etc.)
        """
        try:
            # Check current status
            if self.current_optimization_status == OptimizationStatus.RUNNING:
                return False, "Optimization already running"
                
            # Check cooldown
            if self.optimization_history:
                last_optimization = max(self.optimization_history, 
                                      key=lambda x: datetime.fromisoformat(x['timestamp']))
                
                last_time = datetime.fromisoformat(last_optimization['timestamp'])
                cooldown_remaining = self.optimization_cooldown_minutes - \
                                   (datetime.now() - last_time).total_seconds() / 60
                
                if cooldown_remaining > 0:
                    return False, f"Cooldown active: {cooldown_remaining:.1f} minutes remaining"
                    
            return True, "Ready for optimization"
            
        except Exception as e:
            logger.error(f"Error checking optimization readiness: {e}")
            return False, f"Error: {e}"
            
    def run_enhanced_optimization(self, 
                                strategy_type: str = 'forex',
                                generations: int = 50,
                                population: int = 24,
                                force: bool = False) -> Dict[str, Any]:
        """
        Run enhanced optimization with advanced parameter spaces
        """
        try:
            # Check if optimization can run
            if not force:
                can_run, reason = self.can_run_optimization()
                if not can_run:
                    logger.warning(f"Cannot run optimization: {reason}")
                    return {'success': False, 'reason': reason}
                    
            # Update status
            self.current_optimization_status = OptimizationStatus.RUNNING
            
            # Generate optimization ID
            optimization_id = hashlib.md5(
                f"{strategy_type}_{datetime.now().isoformat()}".encode()
            ).hexdigest()[:8]
            
            logger.info(f"Starting enhanced optimization for {strategy_type} (ID: {optimization_id})")
            
            # Record optimization start
            optimization_record = {
                'id': optimization_id,
                'strategy_type': strategy_type,
                'timestamp': datetime.now().isoformat(),
                'status': 'started',
                'generations': generations,
                'population': population,
                'parameters': None,
                'results': None
            }
            
            start_time = time.time()
            
            try:
                # Import and run enhanced optimizer
                from optimization.enhanced_genetic_optimizer import EnhancedGeneticOptimizer
                
                optimizer = EnhancedGeneticOptimizer(self.config_path, strategy_type)
                results = optimizer.optimize(
                    num_generations=generations,
                    sol_per_pop=population,
                    early_stopping=True
                )
                
                # Export results to CSV
                csv_path = optimizer.export_results_to_csv(self.output_dir)
                
                end_time = time.time()
                optimization_time = end_time - start_time
                
                # Extract best results
                best_params = results['best_params']
                best_fitness = results['best_fitness']
                
                # Get performance metrics from the best result
                if results['all_results']:
                    best_result = max(results['all_results'], key=lambda x: x['fitness_score'])
                    performance_metrics = {
                        'total_return': best_result.get('total_return', 0.0),
                        'sharpe_ratio': best_result.get('sharpe_ratio', 0.0),
                        'max_drawdown': best_result.get('max_drawdown', 100.0),
                        'win_rate': best_result.get('win_rate', 0.0),
                        'total_trades': best_result.get('total_trades', 0)
                    }
                else:
                    performance_metrics = {
                        'total_return': 0.0,
                        'sharpe_ratio': 0.0,
                        'max_drawdown': 100.0,
                        'win_rate': 0.0,
                        'total_trades': 0
                    }
                
                # Create new parameter set
                new_param_set = ParameterSet(
                    parameters=best_params,
                    timestamp=datetime.now(),
                    performance_score=best_fitness,
                    total_return=performance_metrics['total_return'],
                    sharpe_ratio=performance_metrics['sharpe_ratio'],
                    max_drawdown=performance_metrics['max_drawdown'],
                    win_rate=performance_metrics['win_rate'],
                    total_trades=performance_metrics['total_trades'],
                    strategy_type=strategy_type,
                    optimization_id=optimization_id,
                    is_active=True
                )
                
                # Add to parameter store
                self.add_parameter_set(new_param_set)
                
                # Update optimization record
                optimization_record.update({
                    'status': 'completed',
                    'duration_seconds': optimization_time,
                    'best_fitness': best_fitness,
                    'parameters': best_params,
                    'results': performance_metrics,
                    'csv_path': csv_path,
                    'convergence_achieved': results.get('convergence_achieved', False),
                    'total_evaluations': results.get('total_evaluations', 0)
                })
                
                self.current_optimization_status = OptimizationStatus.COMPLETED
                
                logger.info(f"Enhanced optimization completed successfully!")
                logger.info(f"Best fitness: {best_fitness:.4f}")
                logger.info(f"Total return: {performance_metrics['total_return']:.2f}%")
                logger.info(f"Sharpe ratio: {performance_metrics['sharpe_ratio']:.2f}")
                logger.info(f"Results saved to: {csv_path}")
                
                return {
                    'success': True,
                    'optimization_id': optimization_id,
                    'best_parameters': best_params,
                    'performance_metrics': performance_metrics,
                    'csv_path': csv_path,
                    'optimization_time': optimization_time
                }
                
            except Exception as e:
                # Handle optimization failure
                optimization_record.update({
                    'status': 'failed',
                    'error': str(e),
                    'duration_seconds': time.time() - start_time
                })
                
                self.current_optimization_status = OptimizationStatus.FAILED
                logger.error(f"Optimization failed: {e}")
                
                return {
                    'success': False,
                    'error': str(e),
                    'optimization_id': optimization_id
                }
                
            finally:
                # Always save optimization record
                self.optimization_history.append(optimization_record)
                self._save_optimization_history()
                
        except Exception as e:
            logger.error(f"Error in enhanced optimization: {e}")
            self.current_optimization_status = OptimizationStatus.FAILED
            return {'success': False, 'error': str(e)}
            
    def add_parameter_set(self, param_set: ParameterSet):
        """
        Add a new parameter set to the store
        """
        try:
            # Deactivate old parameters of the same strategy type
            for existing in self.parameter_store:
                if existing.strategy_type == param_set.strategy_type:
                    existing.is_active = False
                    
            # Add new parameter set
            self.parameter_store.append(param_set)
            
            # Cleanup old parameter sets (keep only the most recent ones)
            self._cleanup_parameter_store()
            
            # Save to disk
            self._save_parameter_store()
            
            logger.info(f"Added new {param_set.strategy_type} parameter set with score {param_set.performance_score:.4f}")
            
        except Exception as e:
            logger.error(f"Error adding parameter set: {e}")
            
    def _cleanup_parameter_store(self):
        """
        Clean up old parameter sets to maintain storage limits
        """
        try:
            if len(self.parameter_store) <= self.max_stored_parameter_sets:
                return
                
            # Sort by timestamp (newest first)
            self.parameter_store.sort(key=lambda x: x.timestamp, reverse=True)
            
            # Keep only the most recent sets
            self.parameter_store = self.parameter_store[:self.max_stored_parameter_sets]
            
            logger.info(f"Cleaned up parameter store, kept {len(self.parameter_store)} sets")
            
        except Exception as e:
            logger.error(f"Error cleaning up parameter store: {e}")
            
    def get_optimization_recommendation(self, strategy_type: str = 'forex') -> Dict[str, Any]:
        """
        Get recommendation on whether optimization should be run
        """
        try:
            recommendation = {
                'should_optimize': False,
                'reasons': [],
                'priority': 'low',
                'estimated_benefit': 0.0
            }
            
            # Check parameter age
            needs_age_optimization, age_minutes = self.check_parameter_age(strategy_type)
            if needs_age_optimization:
                recommendation['should_optimize'] = True
                recommendation['reasons'].append(f"Parameters are {age_minutes:.1f} minutes old (max: {self.max_age_minutes})")
                recommendation['priority'] = 'high' if age_minutes > self.max_age_minutes * 2 else 'medium'
                
            # Check performance degradation
            if self.check_performance_degradation(strategy_type):
                recommendation['should_optimize'] = True
                recommendation['reasons'].append("Performance degradation detected")
                recommendation['priority'] = 'high'
                
            # Check if parameters meet performance thresholds
            latest_params = self.get_latest_parameters(strategy_type)
            if latest_params:
                performance_issues = []
                
                if latest_params.sharpe_ratio < self.performance_threshold['min_sharpe_ratio']:
                    performance_issues.append(f"Low Sharpe ratio: {latest_params.sharpe_ratio:.2f}")
                    
                if latest_params.total_return < self.performance_threshold['min_total_return']:
                    performance_issues.append(f"Low return: {latest_params.total_return:.2f}%")
                    
                if latest_params.max_drawdown > self.performance_threshold['max_drawdown']:
                    performance_issues.append(f"High drawdown: {latest_params.max_drawdown:.1f}%")
                    
                if latest_params.win_rate < self.performance_threshold['min_win_rate']:
                    performance_issues.append(f"Low win rate: {latest_params.win_rate:.1f}%")
                    
                if performance_issues:
                    recommendation['should_optimize'] = True
                    recommendation['reasons'].extend(performance_issues)
                    recommendation['priority'] = 'medium'
                    
            # Estimate potential benefit
            if recommendation['should_optimize']:
                # Simple heuristic based on current performance gap
                if latest_params:
                    performance_gap = max(0, self.performance_threshold['min_total_return'] - latest_params.total_return)
                    recommendation['estimated_benefit'] = min(performance_gap * 0.5, 10.0)  # Cap at 10%
                else:
                    recommendation['estimated_benefit'] = 5.0  # Default for no parameters
                    
            return recommendation
            
        except Exception as e:
            logger.error(f"Error getting optimization recommendation: {e}")
            return {
                'should_optimize': True,
                'reasons': [f"Error in analysis: {e}"],
                'priority': 'medium',
                'estimated_benefit': 0.0
            }
            
    def auto_optimize_if_needed(self, strategy_type: str = 'forex') -> Dict[str, Any]:
        """
        Automatically run optimization if needed based on recommendations
        """
        try:
            # Get recommendation
            recommendation = self.get_optimization_recommendation(strategy_type)
            
            if not recommendation['should_optimize']:
                logger.info(f"No optimization needed for {strategy_type}")
                return {
                    'optimization_run': False,
                    'reason': 'No optimization needed',
                    'recommendation': recommendation
                }
                
            # Check if we can run optimization
            can_run, reason = self.can_run_optimization()
            if not can_run:
                logger.info(f"Cannot auto-optimize: {reason}")
                return {
                    'optimization_run': False,
                    'reason': reason,
                    'recommendation': recommendation
                }
                
            # Determine optimization parameters based on priority
            if recommendation['priority'] == 'high':
                generations = 60
                population = 30
            elif recommendation['priority'] == 'medium':
                generations = 40
                population = 24
            else:
                generations = 30
                population = 20
                
            logger.info(f"Auto-optimization triggered for {strategy_type} (priority: {recommendation['priority']})")
            
            # Run optimization
            result = self.run_enhanced_optimization(
                strategy_type=strategy_type,
                generations=generations,
                population=population
            )
            
            result['optimization_run'] = True
            result['recommendation'] = recommendation
            
            return result
            
        except Exception as e:
            logger.error(f"Error in auto-optimization: {e}")
            return {
                'optimization_run': False,
                'reason': f"Error: {e}",
                'recommendation': {}
            }
            
    def get_parameter_performance_summary(self, strategy_type: str = 'forex') -> Dict[str, Any]:
        """
        Get performance summary of current parameters
        """
        try:
            latest_params = self.get_latest_parameters(strategy_type)
            
            if not latest_params:
                return {
                    'has_parameters': False,
                    'message': f'No parameters found for {strategy_type}'
                }
                
            age_minutes = (datetime.now() - latest_params.timestamp).total_seconds() / 60
            
            return {
                'has_parameters': True,
                'strategy_type': strategy_type,
                'age_minutes': age_minutes,
                'age_hours': age_minutes / 60,
                'performance_score': latest_params.performance_score,
                'total_return': latest_params.total_return,
                'sharpe_ratio': latest_params.sharpe_ratio,
                'max_drawdown': latest_params.max_drawdown,
                'win_rate': latest_params.win_rate,
                'total_trades': latest_params.total_trades,
                'optimization_id': latest_params.optimization_id,
                'timestamp': latest_params.timestamp.isoformat(),
                'meets_thresholds': {
                    'sharpe_ratio': latest_params.sharpe_ratio >= self.performance_threshold['min_sharpe_ratio'],
                    'total_return': latest_params.total_return >= self.performance_threshold['min_total_return'],
                    'max_drawdown': latest_params.max_drawdown <= self.performance_threshold['max_drawdown'],
                    'win_rate': latest_params.win_rate >= self.performance_threshold['min_win_rate'],
                    'total_trades': latest_params.total_trades >= self.performance_threshold['min_trades']
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting parameter summary: {e}")
            return {
                'has_parameters': False,
                'error': str(e)
            }

def main():
    """Test the enhanced dynamic optimizer"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Enhanced Dynamic Parameter Optimizer')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--strategy', choices=['forex', 'crypto'], default='forex', help='Strategy type')
    parser.add_argument('--action', choices=['check', 'optimize', 'auto', 'summary'], 
                       default='check', help='Action to perform')
    parser.add_argument('--force', action='store_true', help='Force optimization')
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize optimizer
    optimizer = EnhancedDynamicOptimizer(args.config)
    
    if args.action == 'check':
        # Check parameter age and get recommendation
        needs_opt, age = optimizer.check_parameter_age(args.strategy)
        recommendation = optimizer.get_optimization_recommendation(args.strategy)
        
        print(f"\n📊 {args.strategy.upper()} Parameter Status:")
        print(f"Age: {age:.1f} minutes")
        print(f"Needs optimization: {'Yes' if needs_opt else 'No'}")
        print(f"Recommendation: {'Optimize' if recommendation['should_optimize'] else 'No action needed'}")
        print(f"Priority: {recommendation['priority']}")
        print(f"Reasons: {', '.join(recommendation['reasons'])}")
        
    elif args.action == 'optimize':
        # Run optimization
        result = optimizer.run_enhanced_optimization(args.strategy, force=args.force)
        
        if result['success']:
            print(f"\n✅ Optimization completed successfully!")
            print(f"Best return: {result['performance_metrics']['total_return']:.2f}%")
            print(f"Sharpe ratio: {result['performance_metrics']['sharpe_ratio']:.2f}")
        else:
            print(f"\n❌ Optimization failed: {result.get('error', 'Unknown error')}")
            
    elif args.action == 'auto':
        # Auto-optimize if needed
        result = optimizer.auto_optimize_if_needed(args.strategy)
        
        if result['optimization_run']:
            print(f"\n🚀 Auto-optimization completed!")
        else:
            print(f"\n⏸️  Auto-optimization skipped: {result['reason']}")
            
    elif args.action == 'summary':
        # Get parameter summary
        summary = optimizer.get_parameter_performance_summary(args.strategy)
        
        if summary['has_parameters']:
            print(f"\n📈 {args.strategy.upper()} Parameter Summary:")
            print(f"Age: {summary['age_hours']:.1f} hours")
            print(f"Performance Score: {summary['performance_score']:.4f}")
            print(f"Total Return: {summary['total_return']:.2f}%")
            print(f"Sharpe Ratio: {summary['sharpe_ratio']:.2f}")
            print(f"Max Drawdown: {summary['max_drawdown']:.1f}%")
            print(f"Win Rate: {summary['win_rate']:.1f}%")
        else:
            print(f"\n❌ No parameters found for {args.strategy}")

if __name__ == "__main__":
    main()