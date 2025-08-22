"""
Multi-Asset Profitability Analyzer
Compares performance between forex and crypto assets to maximize returns
"""

import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
import yaml
import os
from typing import Dict, List, Tuple, Optional

class MultiAssetAnalyzer:
    """
    Analyzes profitability across multiple asset classes (forex and crypto)
    to determine optimal trading focus
    """
    
    def __init__(self, config_path='config/config.yaml'):
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Asset performance tracking
        self.performance_history = {
            'forex': [],
            'crypto': []
        }
        
        # Current market conditions
        self.market_conditions = {
            'forex': {'volatility': 0, 'trend_strength': 0, 'volume': 0},
            'crypto': {'volatility': 0, 'trend_strength': 0, 'volume': 0}
        }
        
        self.logger.info("MultiAssetAnalyzer initialized")
    
    def analyze_asset_performance(self, asset_type: str, symbol: str, 
                                 strategy_results: Dict) -> Dict:
        """
        Analyze performance metrics for a specific asset
        
        Args:
            asset_type (str): 'forex' or 'crypto'
            symbol (str): Asset symbol (e.g., 'EUR_USD', 'SOL/USD')
            strategy_results (Dict): Results from backtesting
            
        Returns:
            Dict: Performance analysis
        """
        try:
            analysis = {
                'asset_type': asset_type,
                'symbol': symbol,
                'timestamp': datetime.now(),
                'final_value': strategy_results.get('final_value', 0),
                'total_return': strategy_results.get('total_return', 0),
                'sharpe_ratio': strategy_results.get('sharpe_ratio', 0),
                'max_drawdown': strategy_results.get('max_drawdown', 0),
                'total_trades': strategy_results.get('total_trades', 0),
                'win_rate': strategy_results.get('win_rate', 0),
                'avg_win': strategy_results.get('avg_win', 0),
                'avg_loss': strategy_results.get('avg_loss', 0),
                'profit_factor': 0,
                'risk_adjusted_return': 0,
                'consistency_score': 0,
                'overall_score': 0
            }
            
            # Calculate additional metrics
            if analysis['avg_loss'] != 0:
                analysis['profit_factor'] = abs(analysis['avg_win'] / analysis['avg_loss'])
            
            # Risk-adjusted return (return per unit of max drawdown)
            if analysis['max_drawdown'] != 0:
                analysis['risk_adjusted_return'] = analysis['total_return'] / abs(analysis['max_drawdown'])
            else:
                analysis['risk_adjusted_return'] = analysis['total_return']
            
            # Consistency score (combination of win rate and profit factor)
            analysis['consistency_score'] = (analysis['win_rate'] / 100) * analysis['profit_factor']
            
            # Overall score (weighted combination of metrics)
            analysis['overall_score'] = self._calculate_overall_score(analysis)
            
            # Store in performance history
            self.performance_history[asset_type].append(analysis)
            
            self.logger.info(f"Analyzed {asset_type} performance for {symbol}: "
                           f"Return: {analysis['total_return']:.2f}%, "
                           f"Score: {analysis['overall_score']:.2f}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing {asset_type} performance: {e}")
            return {}
    
    def _calculate_overall_score(self, analysis: Dict) -> float:
        """
        Calculate overall performance score using weighted metrics
        
        Args:
            analysis (Dict): Performance analysis data
            
        Returns:
            float: Overall score (0-100)
        """
        try:
            # Weights for different metrics
            weights = {
                'total_return': 0.30,      # 30% weight on returns
                'sharpe_ratio': 0.25,      # 25% weight on risk-adjusted returns
                'win_rate': 0.20,          # 20% weight on win rate
                'profit_factor': 0.15,     # 15% weight on profit factor
                'max_drawdown': 0.10       # 10% weight on drawdown (inverted)
            }
            
            # Normalize metrics to 0-100 scale
            normalized_metrics = {}
            
            # Total return (normalize to 0-100, assuming max expected return of 50%)
            normalized_metrics['total_return'] = min(max(analysis['total_return'] * 2, 0), 100)
            
            # Sharpe ratio (normalize to 0-100, assuming max Sharpe of 3)
            normalized_metrics['sharpe_ratio'] = min(max(analysis['sharpe_ratio'] * 33.33, 0), 100)
            
            # Win rate (already 0-100)
            normalized_metrics['win_rate'] = analysis['win_rate']
            
            # Profit factor (normalize to 0-100, assuming max profit factor of 3)
            normalized_metrics['profit_factor'] = min(max(analysis['profit_factor'] * 33.33, 0), 100)
            
            # Max drawdown (invert and normalize, assuming max acceptable drawdown of 20%)
            drawdown_score = max(0, 100 - (abs(analysis['max_drawdown']) * 5))
            normalized_metrics['max_drawdown'] = drawdown_score
            
            # Calculate weighted score
            overall_score = sum(
                normalized_metrics[metric] * weight 
                for metric, weight in weights.items()
            )
            
            return round(overall_score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating overall score: {e}")
            return 0
    
    def compare_asset_classes(self) -> Dict:
        """
        Compare performance between forex and crypto asset classes
        
        Returns:
            Dict: Comparison results with recommendations
        """
        try:
            comparison = {
                'forex': {'count': 0, 'avg_score': 0, 'avg_return': 0, 'best_asset': None},
                'crypto': {'count': 0, 'avg_score': 0, 'avg_return': 0, 'best_asset': None},
                'recommendation': 'neutral',
                'confidence': 0,
                'analysis_time': datetime.now()
            }
            
            # Analyze forex performance
            if self.performance_history['forex']:
                forex_data = self.performance_history['forex']
                comparison['forex']['count'] = len(forex_data)
                comparison['forex']['avg_score'] = np.mean([d['overall_score'] for d in forex_data])
                comparison['forex']['avg_return'] = np.mean([d['total_return'] for d in forex_data])
                comparison['forex']['best_asset'] = max(forex_data, key=lambda x: x['overall_score'])
            
            # Analyze crypto performance
            if self.performance_history['crypto']:
                crypto_data = self.performance_history['crypto']
                comparison['crypto']['count'] = len(crypto_data)
                comparison['crypto']['avg_score'] = np.mean([d['overall_score'] for d in crypto_data])
                comparison['crypto']['avg_return'] = np.mean([d['total_return'] for d in crypto_data])
                comparison['crypto']['best_asset'] = max(crypto_data, key=lambda x: x['overall_score'])
            
            # Generate recommendation
            forex_score = comparison['forex']['avg_score']
            crypto_score = comparison['crypto']['avg_score']
            
            score_diff = abs(forex_score - crypto_score)
            
            if forex_score > crypto_score and score_diff > 10:
                comparison['recommendation'] = 'forex'
                comparison['confidence'] = min(score_diff / 50 * 100, 100)
            elif crypto_score > forex_score and score_diff > 10:
                comparison['recommendation'] = 'crypto'
                comparison['confidence'] = min(score_diff / 50 * 100, 100)
            else:
                comparison['recommendation'] = 'balanced'
                comparison['confidence'] = 100 - score_diff
            
            self.logger.info(f"Asset comparison: Forex {forex_score:.1f} vs Crypto {crypto_score:.1f} "
                           f"-> Recommend: {comparison['recommendation']} "
                           f"(confidence: {comparison['confidence']:.1f}%)")
            
            return comparison
            
        except Exception as e:
            self.logger.error(f"Error comparing asset classes: {e}")
            return {}
    
    def get_optimal_asset_allocation(self) -> Dict:
        """
        Determine optimal allocation between forex and crypto based on performance
        
        Returns:
            Dict: Allocation recommendations
        """
        try:
            comparison = self.compare_asset_classes()
            
            allocation = {
                'forex_allocation': 50,  # Default 50/50
                'crypto_allocation': 50,
                'reasoning': 'Default balanced allocation',
                'risk_level': 'medium'
            }
            
            if comparison['recommendation'] == 'forex':
                # Favor forex based on confidence level
                confidence = comparison['confidence']
                forex_allocation = 50 + (confidence * 0.4)  # Max 90% allocation
                allocation['forex_allocation'] = min(forex_allocation, 90)
                allocation['crypto_allocation'] = 100 - allocation['forex_allocation']
                allocation['reasoning'] = f"Forex outperforming with {confidence:.1f}% confidence"
                allocation['risk_level'] = 'low' if confidence > 80 else 'medium'
                
            elif comparison['recommendation'] == 'crypto':
                # Favor crypto based on confidence level
                confidence = comparison['confidence']
                crypto_allocation = 50 + (confidence * 0.4)  # Max 90% allocation
                allocation['crypto_allocation'] = min(crypto_allocation, 90)
                allocation['forex_allocation'] = 100 - allocation['crypto_allocation']
                allocation['reasoning'] = f"Crypto outperforming with {confidence:.1f}% confidence"
                allocation['risk_level'] = 'high' if confidence > 80 else 'medium'
            
            else:
                allocation['reasoning'] = "Performance similar - maintaining balanced allocation"
            
            self.logger.info(f"Optimal allocation: {allocation['forex_allocation']:.1f}% Forex, "
                           f"{allocation['crypto_allocation']:.1f}% Crypto")
            
            return allocation
            
        except Exception as e:
            self.logger.error(f"Error calculating optimal allocation: {e}")
            return {'forex_allocation': 50, 'crypto_allocation': 50, 'reasoning': 'Error - using default'}
    
    def update_market_conditions(self, asset_type: str, conditions: Dict):
        """
        Update current market conditions for an asset type
        
        Args:
            asset_type (str): 'forex' or 'crypto'
            conditions (Dict): Market condition metrics
        """
        try:
            self.market_conditions[asset_type].update(conditions)
            self.logger.info(f"Updated {asset_type} market conditions: {conditions}")
        except Exception as e:
            self.logger.error(f"Error updating market conditions: {e}")
    
    def get_trading_recommendation(self) -> Dict:
        """
        Get comprehensive trading recommendation based on all analysis
        
        Returns:
            Dict: Trading recommendation
        """
        try:
            allocation = self.get_optimal_asset_allocation()
            comparison = self.compare_asset_classes()
            
            recommendation = {
                'primary_focus': comparison['recommendation'],
                'allocation': allocation,
                'next_trade_asset': None,
                'confidence': comparison['confidence'],
                'market_conditions': self.market_conditions,
                'timestamp': datetime.now()
            }
            
            # Determine next trade asset based on allocation and market conditions
            if allocation['forex_allocation'] > allocation['crypto_allocation']:
                recommendation['next_trade_asset'] = 'forex'
            elif allocation['crypto_allocation'] > allocation['forex_allocation']:
                recommendation['next_trade_asset'] = 'crypto'
            else:
                # Choose based on current market conditions
                forex_condition_score = sum(self.market_conditions['forex'].values())
                crypto_condition_score = sum(self.market_conditions['crypto'].values())
                
                if forex_condition_score > crypto_condition_score:
                    recommendation['next_trade_asset'] = 'forex'
                else:
                    recommendation['next_trade_asset'] = 'crypto'
            
            self.logger.info(f"Trading recommendation: Focus on {recommendation['primary_focus']}, "
                           f"Next trade: {recommendation['next_trade_asset']}")
            
            return recommendation
            
        except Exception as e:
            self.logger.error(f"Error generating trading recommendation: {e}")
            return {'primary_focus': 'balanced', 'next_trade_asset': 'forex'}
    
    def export_analysis_report(self, output_dir='output') -> str:
        """
        Export comprehensive analysis report to CSV
        
        Args:
            output_dir (str): Output directory
            
        Returns:
            str: Path to exported file
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Combine all performance data
            all_data = []
            for asset_type, performances in self.performance_history.items():
                for perf in performances:
                    all_data.append(perf)
            
            if not all_data:
                self.logger.warning("No performance data to export")
                return None
            
            # Create DataFrame
            df = pd.DataFrame(all_data)
            
            # Add comparison and recommendation
            comparison = self.compare_asset_classes()
            allocation = self.get_optimal_asset_allocation()
            
            # Create summary
            summary_data = {
                'analysis_timestamp': [datetime.now()],
                'forex_avg_score': [comparison['forex']['avg_score']],
                'crypto_avg_score': [comparison['crypto']['avg_score']],
                'recommendation': [comparison['recommendation']],
                'confidence': [comparison['confidence']],
                'forex_allocation': [allocation['forex_allocation']],
                'crypto_allocation': [allocation['crypto_allocation']],
                'reasoning': [allocation['reasoning']]
            }
            
            summary_df = pd.DataFrame(summary_data)
            
            # Export to CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            performance_file = os.path.join(output_dir, f'multi_asset_performance_{timestamp}.csv')
            summary_file = os.path.join(output_dir, f'multi_asset_summary_{timestamp}.csv')
            
            df.to_csv(performance_file, index=False)
            summary_df.to_csv(summary_file, index=False)
            
            self.logger.info(f"Analysis report exported to {performance_file} and {summary_file}")
            return performance_file
            
        except Exception as e:
            self.logger.error(f"Error exporting analysis report: {e}")
            return None
    
    def clear_history(self):
        """Clear performance history"""
        self.performance_history = {'forex': [], 'crypto': []}
        self.logger.info("Performance history cleared")


if __name__ == "__main__":
    # Test the multi-asset analyzer
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Create test analyzer
    analyzer = MultiAssetAnalyzer()
    
    # Test with sample data
    forex_results = {
        'final_value': 10500,
        'total_return': 5.0,
        'sharpe_ratio': 1.2,
        'max_drawdown': -3.0,
        'total_trades': 25,
        'win_rate': 60.0,
        'avg_win': 0.008,
        'avg_loss': -0.005
    }
    
    crypto_results = {
        'final_value': 11200,
        'total_return': 12.0,
        'sharpe_ratio': 0.8,
        'max_drawdown': -8.0,
        'total_trades': 18,
        'win_rate': 55.0,
        'avg_win': 0.015,
        'avg_loss': -0.012
    }
    
    # Analyze performance
    forex_analysis = analyzer.analyze_asset_performance('forex', 'EUR_USD', forex_results)
    crypto_analysis = analyzer.analyze_asset_performance('crypto', 'SOL/USD', crypto_results)
    
    # Get recommendations
    comparison = analyzer.compare_asset_classes()
    allocation = analyzer.get_optimal_asset_allocation()
    recommendation = analyzer.get_trading_recommendation()
    
    print("\n=== Multi-Asset Analysis Results ===")
    print(f"Forex Score: {forex_analysis.get('overall_score', 0):.1f}")
    print(f"Crypto Score: {crypto_analysis.get('overall_score', 0):.1f}")
    print(f"Recommendation: {comparison.get('recommendation', 'N/A')}")
    print(f"Allocation: {allocation.get('forex_allocation', 50):.1f}% Forex, {allocation.get('crypto_allocation', 50):.1f}% Crypto")
    print(f"Next Trade: {recommendation.get('next_trade_asset', 'N/A')}")