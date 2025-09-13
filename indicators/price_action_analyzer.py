"""
Price Action Analysis Module for Trading Strategies
Implements candlestick patterns, support/resistance, trend lines, and volume-price analysis
"""

import backtrader as bt
import numpy as np
import pandas as pd
import logging
from typing import Dict, List, Tuple, Optional
from scipy import stats
from scipy.signal import find_peaks, find_peaks_cwt

class PriceActionAnalyzer:
    """
    Comprehensive price action analysis for trading strategies
    Provides candlestick patterns, support/resistance, trend lines, and volume analysis
    """
    
    def __init__(self, strategy_instance):
        """
        Initialize price action analyzer
        
        Args:
            strategy_instance: The strategy instance with data feeds
        """
        self.strategy = strategy_instance
        self.logger = logging.getLogger(__name__)
        
        # Data references
        self.data_open = strategy_instance.datas[0].open
        self.data_high = strategy_instance.datas[0].high
        self.data_low = strategy_instance.datas[0].low
        self.data_close = strategy_instance.datas[0].close
        self.data_volume = strategy_instance.datas[0].volume
        
        # Price action tracking
        self.support_levels = []
        self.resistance_levels = []
        self.trend_lines = []
        self.last_pattern_bar = 0
        
        # Volume analysis
        self.volume_profile = {}
        self.volume_clusters = []
        
    def analyze_candlestick_patterns(self, lookback: int = 5) -> Dict[str, float]:
        """
        Analyze candlestick patterns for the last few bars
        Returns confidence scores for bullish/bearish patterns
        """
        patterns = {
            'bullish_score': 0.0,
            'bearish_score': 0.0,
            'patterns_detected': []
        }
        
        try:
            if len(self.strategy.data) < lookback + 1:
                return patterns
                
            # Get recent OHLC data
            recent_bars = []
            for i in range(lookback, 0, -1):
                bar = {
                    'open': float(self.data_open[-i]),
                    'high': float(self.data_high[-i]),
                    'low': float(self.data_low[-i]),
                    'close': float(self.data_close[-i]),
                    'volume': float(self.data_volume[-i]) if len(self.data_volume) > i else 0
                }
                recent_bars.append(bar)
            
            # Current bar
            current_bar = {
                'open': float(self.data_open[0]),
                'high': float(self.data_high[0]),
                'low': float(self.data_low[0]),
                'close': float(self.data_close[0]),
                'volume': float(self.data_volume[0]) if len(self.data_volume) > 0 else 0
            }
            recent_bars.append(current_bar)
            
            # Single candlestick patterns
            patterns.update(self._analyze_single_patterns(current_bar))
            
            # Multi-candlestick patterns
            if len(recent_bars) >= 2:
                patterns.update(self._analyze_multi_patterns(recent_bars))
                
            # Three-bar patterns
            if len(recent_bars) >= 3:
                patterns.update(self._analyze_three_bar_patterns(recent_bars))
                
        except Exception as e:
            self.logger.error(f"Error analyzing candlestick patterns: {e}")
            
        return patterns
    
    def _analyze_single_patterns(self, bar: Dict) -> Dict[str, float]:
        """Analyze single candlestick patterns"""
        patterns = {'bullish_score': 0.0, 'bearish_score': 0.0, 'patterns_detected': []}
        
        body = abs(bar['close'] - bar['open'])
        upper_shadow = bar['high'] - max(bar['open'], bar['close'])
        lower_shadow = min(bar['open'], bar['close']) - bar['low']
        total_range = bar['high'] - bar['low']
        
        if total_range == 0:
            return patterns
            
        body_ratio = body / total_range
        upper_shadow_ratio = upper_shadow / total_range
        lower_shadow_ratio = lower_shadow / total_range
        
        # Doji patterns
        if body_ratio < 0.1:
            if upper_shadow_ratio > 0.6:
                patterns['bearish_score'] += 0.3  # Gravestone doji
                patterns['patterns_detected'].append('gravestone_doji')
            elif lower_shadow_ratio > 0.6:
                patterns['bullish_score'] += 0.3  # Dragonfly doji
                patterns['patterns_detected'].append('dragonfly_doji')
            else:
                patterns['bullish_score'] += 0.1  # Regular doji (neutral but slight bullish bias)
                patterns['bearish_score'] += 0.1
                patterns['patterns_detected'].append('doji')
        
        # Hammer patterns
        elif body_ratio < 0.3 and lower_shadow_ratio > 0.5 and upper_shadow_ratio < 0.1:
            if bar['close'] > bar['open']:
                patterns['bullish_score'] += 0.4  # Hammer
                patterns['patterns_detected'].append('hammer')
            else:
                patterns['bullish_score'] += 0.3  # Hanging man (context dependent)
                patterns['patterns_detected'].append('hanging_man')
        
        # Shooting star
        elif body_ratio < 0.3 and upper_shadow_ratio > 0.5 and lower_shadow_ratio < 0.1:
            patterns['bearish_score'] += 0.4
            patterns['patterns_detected'].append('shooting_star')
        
        # Marubozu patterns
        elif body_ratio > 0.8:
            if bar['close'] > bar['open']:
                patterns['bullish_score'] += 0.5  # Bullish marubozu
                patterns['patterns_detected'].append('bullish_marubozu')
            else:
                patterns['bearish_score'] += 0.5  # Bearish marubozu
                patterns['patterns_detected'].append('bearish_marubozu')
        
        # Spinning tops
        elif body_ratio < 0.3 and upper_shadow_ratio > 0.2 and lower_shadow_ratio > 0.2:
            patterns['bullish_score'] += 0.1  # Indecision, slight bullish bias
            patterns['bearish_score'] += 0.1
            patterns['patterns_detected'].append('spinning_top')
            
        return patterns
    
    def _analyze_multi_patterns(self, bars: List[Dict]) -> Dict[str, float]:
        """Analyze two-bar patterns"""
        patterns = {'bullish_score': 0.0, 'bearish_score': 0.0, 'patterns_detected': []}
        
        if len(bars) < 2:
            return patterns
            
        prev_bar = bars[-2]
        curr_bar = bars[-1]
        
        # Bullish engulfing
        if (prev_bar['close'] < prev_bar['open'] and  # Previous bearish
            curr_bar['close'] > curr_bar['open'] and  # Current bullish
            curr_bar['open'] < prev_bar['close'] and  # Gap down open
            curr_bar['close'] > prev_bar['open']):     # Engulfs previous body
            patterns['bullish_score'] += 0.6
            patterns['patterns_detected'].append('bullish_engulfing')
        
        # Bearish engulfing
        elif (prev_bar['close'] > prev_bar['open'] and  # Previous bullish
              curr_bar['close'] < curr_bar['open'] and  # Current bearish
              curr_bar['open'] > prev_bar['close'] and  # Gap up open
              curr_bar['close'] < prev_bar['open']):     # Engulfs previous body
            patterns['bearish_score'] += 0.6
            patterns['patterns_detected'].append('bearish_engulfing')
        
        # Piercing pattern
        elif (prev_bar['close'] < prev_bar['open'] and  # Previous bearish
              curr_bar['close'] > curr_bar['open'] and  # Current bullish
              curr_bar['open'] < prev_bar['low'] and    # Gap down
              curr_bar['close'] > (prev_bar['open'] + prev_bar['close']) / 2):  # Pierces halfway
            patterns['bullish_score'] += 0.4
            patterns['patterns_detected'].append('piercing_pattern')
        
        # Dark cloud cover
        elif (prev_bar['close'] > prev_bar['open'] and  # Previous bullish
              curr_bar['close'] < curr_bar['open'] and  # Current bearish
              curr_bar['open'] > prev_bar['high'] and   # Gap up
              curr_bar['close'] < (prev_bar['open'] + prev_bar['close']) / 2):  # Covers halfway
            patterns['bearish_score'] += 0.4
            patterns['patterns_detected'].append('dark_cloud_cover')
            
        return patterns
    
    def _analyze_three_bar_patterns(self, bars: List[Dict]) -> Dict[str, float]:
        """Analyze three-bar patterns"""
        patterns = {'bullish_score': 0.0, 'bearish_score': 0.0, 'patterns_detected': []}
        
        if len(bars) < 3:
            return patterns
            
        bar1 = bars[-3]
        bar2 = bars[-2]
        bar3 = bars[-1]
        
        # Morning star
        if (bar1['close'] < bar1['open'] and  # First bar bearish
            abs(bar2['close'] - bar2['open']) < (bar1['high'] - bar1['low']) * 0.3 and  # Second bar small
            bar3['close'] > bar3['open'] and  # Third bar bullish
            bar3['close'] > (bar1['open'] + bar1['close']) / 2):  # Third closes above first midpoint
            patterns['bullish_score'] += 0.7
            patterns['patterns_detected'].append('morning_star')
        
        # Evening star
        elif (bar1['close'] > bar1['open'] and  # First bar bullish
              abs(bar2['close'] - bar2['open']) < (bar1['high'] - bar1['low']) * 0.3 and  # Second bar small
              bar3['close'] < bar3['open'] and  # Third bar bearish
              bar3['close'] < (bar1['open'] + bar1['close']) / 2):  # Third closes below first midpoint
            patterns['bearish_score'] += 0.7
            patterns['patterns_detected'].append('evening_star')
        
        # Three white soldiers
        elif (all(bar['close'] > bar['open'] for bar in [bar1, bar2, bar3]) and  # All bullish
              bar2['close'] > bar1['close'] and bar3['close'] > bar2['close']):  # Progressive highs
            patterns['bullish_score'] += 0.5
            patterns['patterns_detected'].append('three_white_soldiers')
        
        # Three black crows
        elif (all(bar['close'] < bar['open'] for bar in [bar1, bar2, bar3]) and  # All bearish
              bar2['close'] < bar1['close'] and bar3['close'] < bar2['close']):  # Progressive lows
            patterns['bearish_score'] += 0.5
            patterns['patterns_detected'].append('three_black_crows')
            
        return patterns
    
    def analyze_support_resistance(self, lookback: int = 50, min_touches: int = 2) -> Dict[str, List[float]]:
        """
        Analyze support and resistance levels using pivot points
        """
        levels = {'support': [], 'resistance': [], 'current_analysis': {}}
        
        try:
            if len(self.strategy.data) < lookback:
                return levels
                
            # Get recent price data
            highs = np.array([float(self.data_high[-i]) for i in range(lookback, 0, -1)])
            lows = np.array([float(self.data_low[-i]) for i in range(lookback, 0, -1)])
            closes = np.array([float(self.data_close[-i]) for i in range(lookback, 0, -1)])
            
            # Find pivot highs and lows
            resistance_peaks, _ = find_peaks(highs, distance=5, prominence=np.std(highs) * 0.5)
            support_peaks, _ = find_peaks(-lows, distance=5, prominence=np.std(lows) * 0.5)
            
            # Convert support peaks back to actual lows
            support_valleys = support_peaks
            
            # Group similar levels
            resistance_levels = self._group_similar_levels([highs[i] for i in resistance_peaks])
            support_levels = self._group_similar_levels([lows[i] for i in support_valleys])
            
            # Filter by minimum touches
            current_price = float(self.data_close[0])
            
            for level in resistance_levels:
                if self._count_level_touches(level, highs, tolerance=0.001) >= min_touches:
                    levels['resistance'].append(level)
                    
            for level in support_levels:
                if self._count_level_touches(level, lows, tolerance=0.001) >= min_touches:
                    levels['support'].append(level)
            
            # Analyze current price relative to levels
            levels['current_analysis'] = self._analyze_current_position(current_price, levels)
            
        except Exception as e:
            self.logger.error(f"Error analyzing support/resistance: {e}")
            
        return levels
    
    def _group_similar_levels(self, levels: List[float], tolerance: float = 0.002) -> List[float]:
        """Group similar price levels together"""
        if not levels:
            return []
            
        grouped = []
        sorted_levels = sorted(levels)
        
        current_group = [sorted_levels[0]]
        
        for level in sorted_levels[1:]:
            if abs(level - current_group[-1]) / current_group[-1] <= tolerance:
                current_group.append(level)
            else:
                # Finalize current group
                grouped.append(np.mean(current_group))
                current_group = [level]
        
        # Add last group
        if current_group:
            grouped.append(np.mean(current_group))
            
        return grouped
    
    def _count_level_touches(self, level: float, prices: np.ndarray, tolerance: float = 0.001) -> int:
        """Count how many times price touched a level"""
        touches = 0
        for price in prices:
            if abs(price - level) / level <= tolerance:
                touches += 1
        return touches
    
    def _analyze_current_position(self, current_price: float, levels: Dict) -> Dict[str, float]:
        """Analyze current price position relative to support/resistance"""
        analysis = {
            'nearest_support': 0.0,
            'nearest_resistance': 0.0,
            'support_distance': float('inf'),
            'resistance_distance': float('inf'),
            'between_levels': False,
            'support_strength': 0.0,
            'resistance_strength': 0.0
        }
        
        # Find nearest support below current price
        supports_below = [s for s in levels['support'] if s < current_price]
        if supports_below:
            nearest_support = max(supports_below)
            analysis['nearest_support'] = nearest_support
            analysis['support_distance'] = (current_price - nearest_support) / current_price
            analysis['support_strength'] = 1.0 / (1.0 + analysis['support_distance'] * 100)
        
        # Find nearest resistance above current price
        resistances_above = [r for r in levels['resistance'] if r > current_price]
        if resistances_above:
            nearest_resistance = min(resistances_above)
            analysis['nearest_resistance'] = nearest_resistance
            analysis['resistance_distance'] = (nearest_resistance - current_price) / current_price
            analysis['resistance_strength'] = 1.0 / (1.0 + analysis['resistance_distance'] * 100)
        
        # Check if price is between significant levels
        if analysis['support_distance'] < 0.01 and analysis['resistance_distance'] < 0.01:
            analysis['between_levels'] = True
            
        return analysis
    
    def analyze_trend_lines(self, lookback: int = 30) -> Dict[str, Any]:
        """
        Analyze trend line breaks and trend strength
        """
        trend_analysis = {
            'uptrend_line': None,
            'downtrend_line': None,
            'trend_break': False,
            'trend_strength': 0.0,
            'trend_direction': 'neutral'
        }
        
        try:
            if len(self.strategy.data) < lookback:
                return trend_analysis
                
            # Get recent price data
            highs = np.array([float(self.data_high[-i]) for i in range(lookback, 0, -1)])
            lows = np.array([float(self.data_low[-i]) for i in range(lookback, 0, -1)])
            closes = np.array([float(self.data_close[-i]) for i in range(lookback, 0, -1)])
            
            # Find trend line for uptrend (connecting lows)
            uptrend_line = self._calculate_trend_line(lows, 'up')
            
            # Find trend line for downtrend (connecting highs)
            downtrend_line = self._calculate_trend_line(highs, 'down')
            
            current_price = float(self.data_close[0])
            
            # Check for trend line breaks
            if uptrend_line and current_price < uptrend_line['current_value']:
                trend_analysis['trend_break'] = True
                trend_analysis['trend_direction'] = 'bearish_break'
                
            elif downtrend_line and current_price > downtrend_line['current_value']:
                trend_analysis['trend_break'] = True
                trend_analysis['trend_direction'] = 'bullish_break'
            
            # Calculate overall trend strength
            x = np.arange(len(closes))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, closes)
            
            trend_analysis['trend_strength'] = abs(r_value)
            if slope > 0:
                trend_analysis['trend_direction'] = 'bullish' if not trend_analysis['trend_break'] else trend_analysis['trend_direction']
            else:
                trend_analysis['trend_direction'] = 'bearish' if not trend_analysis['trend_break'] else trend_analysis['trend_direction']
            
            trend_analysis['uptrend_line'] = uptrend_line
            trend_analysis['downtrend_line'] = downtrend_line
            
        except Exception as e:
            self.logger.error(f"Error analyzing trend lines: {e}")
            
        return trend_analysis
    
    def _calculate_trend_line(self, prices: np.ndarray, direction: str) -> Optional[Dict]:
        """Calculate trend line using linear regression on pivot points"""
        try:
            if direction == 'up':
                # Find pivot lows for uptrend line
                peaks, _ = find_peaks(-prices, distance=3)
            else:
                # Find pivot highs for downtrend line
                peaks, _ = find_peaks(prices, distance=3)
            
            if len(peaks) < 2:
                return None
                
            # Use last few pivot points for trend line
            recent_peaks = peaks[-min(4, len(peaks)):]
            peak_prices = prices[recent_peaks]
            peak_indices = recent_peaks
            
            # Linear regression on pivot points
            slope, intercept, r_value, p_value, std_err = stats.linregress(peak_indices, peak_prices)
            
            # Calculate current trend line value
            current_index = len(prices) - 1
            current_value = slope * current_index + intercept
            
            return {
                'slope': slope,
                'intercept': intercept,
                'r_value': r_value,
                'current_value': current_value,
                'strength': abs(r_value)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating trend line: {e}")
            return None
    
    def analyze_volume_price_relationship(self, lookback: int = 20) -> Dict[str, float]:
        """
        Analyze volume-price relationship for confirmation signals
        """
        analysis = {
            'volume_trend_alignment': 0.0,
            'volume_breakout_confirmation': 0.0,
            'volume_divergence': 0.0,
            'price_volume_correlation': 0.0
        }
        
        try:
            if len(self.strategy.data) < lookback:
                return analysis
                
            # Get recent data
            prices = np.array([float(self.data_close[-i]) for i in range(lookback, 0, -1)])
            volumes = np.array([float(self.data_volume[-i]) for i in range(lookback, 0, -1) if len(self.data_volume) > i])
            
            if len(volumes) < lookback:
                # Pad with average volume if not enough volume data
                avg_volume = np.mean(volumes) if len(volumes) > 0 else 1000
                volumes = np.pad(volumes, (lookback - len(volumes), 0), 'constant', constant_values=avg_volume)
            
            # Calculate price and volume trends
            price_trend = np.polyfit(range(len(prices)), prices, 1)[0]
            volume_trend = np.polyfit(range(len(volumes)), volumes, 1)[0]
            
            # Volume-trend alignment
            if price_trend > 0 and volume_trend > 0:
                analysis['volume_trend_alignment'] = 0.5  # Bullish with volume support
            elif price_trend < 0 and volume_trend > 0:
                analysis['volume_trend_alignment'] = -0.3  # Bearish but volume increasing (potential reversal)
            elif price_trend > 0 and volume_trend < 0:
                analysis['volume_trend_alignment'] = -0.2  # Bullish but volume decreasing (weakening)
            elif price_trend < 0 and volume_trend < 0:
                analysis['volume_trend_alignment'] = 0.3  # Bearish with volume support
            
            # Volume breakout confirmation
            current_volume = float(self.data_volume[0]) if len(self.data_volume) > 0 else np.mean(volumes)
            avg_volume = np.mean(volumes)
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            if volume_ratio > 1.5:
                analysis['volume_breakout_confirmation'] = 0.4
            elif volume_ratio > 1.2:
                analysis['volume_breakout_confirmation'] = 0.2
            elif volume_ratio < 0.7:
                analysis['volume_breakout_confirmation'] = -0.2
            
            # Price-volume correlation
            if len(prices) == len(volumes):
                correlation = np.corrcoef(prices, volumes)[0, 1]
                if not np.isnan(correlation):
                    analysis['price_volume_correlation'] = correlation * 0.3
            
            # Volume divergence analysis
            recent_price_change = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0
            recent_volume_change = (volumes[-1] - volumes[-5]) / volumes[-5] if len(volumes) >= 5 and volumes[-5] > 0 else 0
            
            # Bullish divergence: price down, volume up
            if recent_price_change < -0.01 and recent_volume_change > 0.2:
                analysis['volume_divergence'] = 0.3
            # Bearish divergence: price up, volume down
            elif recent_price_change > 0.01 and recent_volume_change < -0.2:
                analysis['volume_divergence'] = -0.3
                
        except Exception as e:
            self.logger.error(f"Error analyzing volume-price relationship: {e}")
            
        return analysis
    
    def calculate_price_action_score(self, lookback: int = 30) -> Dict[str, float]:
        """
        Calculate comprehensive price action score
        Combines candlestick patterns, S/R levels, trend lines, and volume analysis
        """
        score = {
            'bullish_score': 0.0,
            'bearish_score': 0.0,
            'confidence': 0.0,
            'components': {}
        }
        
        try:
            # Candlestick patterns (25% weight)
            patterns = self.analyze_candlestick_patterns()
            pattern_bullish = patterns['bullish_score'] * 0.25
            pattern_bearish = patterns['bearish_score'] * 0.25
            
            score['components']['candlestick_bullish'] = pattern_bullish
            score['components']['candlestick_bearish'] = pattern_bearish
            
            # Support/Resistance analysis (30% weight)
            sr_levels = self.analyze_support_resistance(lookback)
            sr_analysis = sr_levels['current_analysis']
            
            sr_bullish = 0.0
            sr_bearish = 0.0
            
            # Price near support = bullish
            if sr_analysis.get('support_distance', float('inf')) < 0.005:  # Within 0.5%
                sr_bullish += sr_analysis.get('support_strength', 0) * 0.3
            
            # Price near resistance = bearish
            if sr_analysis.get('resistance_distance', float('inf')) < 0.005:  # Within 0.5%
                sr_bearish += sr_analysis.get('resistance_strength', 0) * 0.3
            
            score['components']['support_resistance_bullish'] = sr_bullish
            score['components']['support_resistance_bearish'] = sr_bearish
            
            # Trend line analysis (25% weight)
            trend_analysis = self.analyze_trend_lines(lookback)
            trend_bullish = 0.0
            trend_bearish = 0.0
            
            if trend_analysis['trend_break']:
                if trend_analysis['trend_direction'] == 'bullish_break':
                    trend_bullish += trend_analysis['trend_strength'] * 0.25
                elif trend_analysis['trend_direction'] == 'bearish_break':
                    trend_bearish += trend_analysis['trend_strength'] * 0.25
            else:
                # No break, trend continuation
                if trend_analysis['trend_direction'] == 'bullish':
                    trend_bullish += trend_analysis['trend_strength'] * 0.15
                elif trend_analysis['trend_direction'] == 'bearish':
                    trend_bearish += trend_analysis['trend_strength'] * 0.15
            
            score['components']['trend_line_bullish'] = trend_bullish
            score['components']['trend_line_bearish'] = trend_bearish
            
            # Volume-price relationship (20% weight)
            volume_analysis = self.analyze_volume_price_relationship(lookback)
            volume_bullish = 0.0
            volume_bearish = 0.0
            
            # Volume trend alignment
            if volume_analysis['volume_trend_alignment'] > 0:
                volume_bullish += volume_analysis['volume_trend_alignment'] * 0.1
            else:
                volume_bearish += abs(volume_analysis['volume_trend_alignment']) * 0.1
            
            # Volume breakout confirmation
            if volume_analysis['volume_breakout_confirmation'] > 0:
                volume_bullish += volume_analysis['volume_breakout_confirmation'] * 0.05
                volume_bearish += volume_analysis['volume_breakout_confirmation'] * 0.05  # Benefits both directions
            
            # Volume divergence
            if volume_analysis['volume_divergence'] > 0:
                volume_bullish += volume_analysis['volume_divergence'] * 0.05
            else:
                volume_bearish += abs(volume_analysis['volume_divergence']) * 0.05
            
            score['components']['volume_price_bullish'] = volume_bullish
            score['components']['volume_price_bearish'] = volume_bearish
            
            # Calculate final scores
            score['bullish_score'] = (pattern_bullish + sr_bullish + trend_bullish + volume_bullish)
            score['bearish_score'] = (pattern_bearish + sr_bearish + trend_bearish + volume_bearish)
            
            # Calculate confidence based on signal strength and component agreement
            max_score = max(score['bullish_score'], score['bearish_score'])
            component_agreement = self._calculate_component_agreement(score['components'])
            
            score['confidence'] = min(max_score * component_agreement, 1.0)
            
            # Add pattern details for logging
            score['patterns_detected'] = patterns.get('patterns_detected', [])
            score['support_resistance'] = sr_levels
            score['trend_analysis'] = trend_analysis
            score['volume_analysis'] = volume_analysis
            
        except Exception as e:
            self.logger.error(f"Error calculating price action score: {e}")
            
        return score
    
    def _calculate_component_agreement(self, components: Dict[str, float]) -> float:
        """Calculate how well different price action components agree"""
        bullish_components = [v for k, v in components.items() if 'bullish' in k and v > 0]
        bearish_components = [v for k, v in components.items() if 'bearish' in k and v > 0]
        
        if not bullish_components and not bearish_components:
            return 0.5
            
        # Calculate agreement strength
        bullish_strength = sum(bullish_components)
        bearish_strength = sum(bearish_components)
        
        if bullish_strength > bearish_strength:
            # More bullish components
            agreement = len(bullish_components) / (len(bullish_components) + len(bearish_components))
        else:
            # More bearish components
            agreement = len(bearish_components) / (len(bullish_components) + len(bearish_components))
        
        return min(agreement * 1.5, 1.0)  # Boost agreement score
    
    def get_price_action_summary(self) -> Dict[str, Any]:
        """Get comprehensive price action summary for logging"""
        try:
            price_action_score = self.calculate_price_action_score()
            
            summary = {
                'price_action_bullish': price_action_score['bullish_score'],
                'price_action_bearish': price_action_score['bearish_score'],
                'price_action_confidence': price_action_score['confidence'],
                'patterns_detected': price_action_score['patterns_detected'],
                'components': price_action_score['components'],
                'current_price': float(self.data_close[0]),
                'analysis_timestamp': self.strategy.datas[0].datetime.datetime(0).isoformat()
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"Error getting price action summary: {e}")
            return {
                'price_action_bullish': 0.0,
                'price_action_bearish': 0.0,
                'price_action_confidence': 0.0,
                'patterns_detected': [],
                'components': {},
                'current_price': 0.0,
                'analysis_timestamp': ''
            }

if __name__ == '__main__':
    print("Price Action Analyzer module loaded successfully")