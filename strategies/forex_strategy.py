"""
Forex Strategy Module for Trading Bot

This module defines an advanced forex trading strategy combining:
- Moving average crossover signals
- Supply/demand zone analysis using pivot highs/lows
- Volume profile confirmation
"""

import backtrader as bt
import logging
import yaml
import os
import numpy as np
import sys

# Import custom indicators
from indicators.custom_indicators import PivotHighLow, SupplyDemandZones, VolumeProfile

# Import sentiment analysis
try:
    from sentiment.news_analyzer import news_analyzer
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    print("Warning: Sentiment analysis not available. Install required packages: pip install textblob feedparser beautifulsoup4")

class ForexStrategy(bt.Strategy):
    """
    Advanced forex trading strategy combining technical indicators with supply/demand analysis.
    
    Strategy Logic:
    1. Use moving average crossover for trend direction
    2. Identify supply/demand zones using pivot points
    3. Enter trades when price reacts at strong zones
    4. Use volume profile for additional confirmation
    """
    params = (
        # Moving Average Parameters - OPTIMIZED VALUES
        ('fast_length', 15),           # Optimized from 10 to 15
        ('slow_length', 35),           # Optimized from 30 to 35
        
        # Technical Indicator Parameters - OPTIMIZED VALUES
        ('rsi_period', 21),            # Optimized from 14 to 21
        ('rsi_oversold', 20),          # Optimized from 30 to 20
        ('rsi_overbought', 80),        # Optimized from 70 to 80
        ('macd_fast', 12),             # MACD fast EMA
        ('macd_slow', 26),             # MACD slow EMA
        ('macd_signal', 9),            # MACD signal line
        
        # Risk Management - OPTIMIZED VALUES
        ('stop_loss_percent', 0.015),  # Optimized from 0.005 to 0.015 (1.5% stop loss)
        ('take_profit_percent', 0.045), # Optimized from 0.01 to 0.045 (4.5% take profit)
        
        # Supply/Demand Parameters
        ('pivot_period', 5),           # Period for pivot calculation
        ('zone_lookback', 50),         # How far back to look for zones
        ('min_zone_strength', 2),      # Minimum touches to consider zone valid
        ('zone_buffer', 0.0005),       # Buffer around zones (0.05% for forex)
        ('max_zones', 10),             # Maximum zones to track
        
        # Volume Profile Parameters
        ('volume_period', 50),         # Volume profile lookback
        ('volume_levels', 20),         # Number of price levels for volume analysis
        
        # Sentiment Analysis Parameters
        ('use_sentiment_filter', True),    # Enable/disable sentiment analysis
        ('sentiment_weight', 0.3),         # Weight of sentiment in final decision (0.0-1.0)
        ('sentiment_threshold', 0.2),      # Minimum sentiment strength to consider
        ('news_lookback_hours', 12),       # Hours to look back for news
        ('sentiment_boost_multiplier', 1.3), # Boost signal strength when sentiment aligns
        ('sentiment_veto_threshold', -0.6), # Strong negative sentiment can veto trades
        ('min_sentiment_confidence', 0.3), # Minimum confidence in sentiment analysis
        
        # Strategy Filters
        ('use_supply_demand', True),   # Enable/disable supply demand logic
        ('use_volume_filter', True),   # Enable/disable volume confirmation
        ('use_rsi_filter', True),      # Enable/disable RSI confirmation
        ('use_macd_filter', True),     # Enable/disable MACD confirmation
        ('min_risk_reward', 2.0),      # Minimum risk/reward ratio
        
        # Logging
        ('printlog', False)
    )

    def log(self, txt, dt=None):
        """Logging function for this strategy"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            logging.info(f'{dt.isoformat()} {txt}')

    def __init__(self):
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        self.order = None
        self.buyprice = None
        self.buycomm = None
        self.entry_bar = None

        # Traditional Technical Indicators
        self.sma_fast = bt.indicators.SMA(self.datas[0], period=self.p.fast_length)
        self.sma_slow = bt.indicators.SMA(self.datas[0], period=self.p.slow_length)
        self.crossover = bt.indicators.CrossOver(self.sma_fast, self.sma_slow)
        
        # RSI for additional confirmation
        self.rsi = bt.indicators.RSI(self.datas[0], period=self.p.rsi_period)
        
        # MACD for trend confirmation
        self.macd = bt.indicators.MACD(
            self.datas[0],
            period_me1=self.p.macd_fast,
            period_me2=self.p.macd_slow,
            period_signal=self.p.macd_signal
        )
        self.macd_signal = self.macd.signal
        self.macd_histogram = self.macd.macd - self.macd.signal  # Calculate histogram manually
        
        # Custom Supply/Demand Indicators
        if self.p.use_supply_demand:
            self.pivot_points = PivotHighLow(period=self.p.pivot_period)
            self.supply_demand = SupplyDemandZones(
                pivot_period=self.p.pivot_period,
                zone_lookback=self.p.zone_lookback,
                min_zone_strength=self.p.min_zone_strength,
                zone_buffer=self.p.zone_buffer,
                max_zones=self.p.max_zones
            )
        
        # Volume Profile for confirmation
        if self.p.use_volume_filter:
            self.volume_profile = VolumeProfile(
                period=self.p.volume_period,
                price_levels=self.p.volume_levels
            )

        # Sentiment Analysis tracking
        self.last_sentiment_check = None
        self.current_sentiment = None
        self.sentiment_cache_duration = 300  # 5 minutes cache
        
        self.logger = logging.getLogger(__name__)
        if SENTIMENT_AVAILABLE and self.p.use_sentiment_filter:
            self.logger.info("Enhanced ForexStrategy with Supply/Demand and Sentiment Analysis initialized")
        else:
            self.logger.info("Enhanced ForexStrategy with Supply/Demand initialized (Sentiment disabled)")

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            elif order.issell():
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def get_sentiment_signal(self):
        """Get current sentiment signal with caching"""
        if not SENTIMENT_AVAILABLE or not self.p.use_sentiment_filter:
            return {
                'signal_direction': 0.0,
                'signal_strength': 0.0,
                'confidence': 0.0,
                'recommendation': 'NEUTRAL'
            }
        
        try:
            current_time = self.datas[0].datetime.datetime(0)
            
            # Check if we need to update sentiment
            if (self.last_sentiment_check is None or
                (current_time - self.last_sentiment_check).total_seconds() > self.sentiment_cache_duration):
                
                # Get fresh sentiment data
                self.current_sentiment = news_analyzer.get_trading_signal(self.p.news_lookback_hours)
                self.last_sentiment_check = current_time
                
                self.log(f'SENTIMENT UPDATE - Direction: {self.current_sentiment["signal_direction"]:.3f}, '
                        f'Strength: {self.current_sentiment["signal_strength"]:.3f}, '
                        f'Recommendation: {self.current_sentiment["recommendation"]}')
            
            return self.current_sentiment
            
        except Exception as e:
            self.logger.error(f"Error getting sentiment signal: {e}")
            return {
                'signal_direction': 0.0,
                'signal_strength': 0.0,
                'confidence': 0.0,
                'recommendation': 'NEUTRAL'
            }

    def next(self):
        self.log('Close, %.2f' % self.dataclose[0])

        if self.order:
            return

        if not self.position:  # Not in the market
            # Get current market conditions
            current_price = self.dataclose[0]
            
            # Get sentiment signal
            sentiment = self.get_sentiment_signal()
            
            # Check for sentiment veto (strong negative news can override technical signals)
            if (self.p.use_sentiment_filter and
                sentiment['signal_strength'] > 0.5 and
                sentiment['signal_direction'] < self.p.sentiment_veto_threshold):
                self.log(f'SENTIMENT VETO - Strong negative sentiment: {sentiment["signal_direction"]:.3f}')
                return
            
            # Basic trend direction from moving averages
            bullish_trend = self.crossover > 0 or self.sma_fast[0] > self.sma_slow[0]
            bearish_trend = self.crossover < 0 or self.sma_fast[0] < self.sma_slow[0]
            
            # RSI conditions
            rsi_bullish = True
            rsi_bearish = True
            if self.p.use_rsi_filter:
                rsi_bullish = (self.rsi[0] > self.p.rsi_oversold and
                              self.rsi[0] < self.p.rsi_overbought and
                              self.rsi[0] > self.rsi[-1])  # RSI rising
                rsi_bearish = (self.rsi[0] > self.p.rsi_oversold and
                              self.rsi[0] < self.p.rsi_overbought and
                              self.rsi[0] < self.rsi[-1])  # RSI falling
            
            # MACD conditions
            macd_bullish = True
            macd_bearish = True
            if self.p.use_macd_filter:
                macd_bullish = (self.macd[0] > self.macd_signal[0] and  # MACD above signal
                               self.macd_histogram[0] > 0)              # Positive histogram
                macd_bearish = (self.macd[0] < self.macd_signal[0] and  # MACD below signal
                               self.macd_histogram[0] < 0)              # Negative histogram
            
            # Calculate technical signal strength
            technical_signals = self._calculate_technical_signals(
                bullish_trend, bearish_trend, rsi_bullish, rsi_bearish,
                macd_bullish, macd_bearish, current_price
            )
            
            # Combine technical and sentiment signals
            combined_signals = self._combine_technical_sentiment_signals(technical_signals, sentiment)
            
            # Determine final buy/sell signals
            buy_signal = combined_signals['buy_signal']
            sell_signal = combined_signals['sell_signal']
            signal_strength = combined_signals['signal_strength']
            
            # Volume confirmation (if enabled)
            volume_confirmed = True
            if self.p.use_volume_filter:
                # Simple volume filter - current volume should be above average
                avg_volume = sum([self.datavolume[-i] for i in range(min(10, len(self.data)))]) / min(10, len(self.data))
                volume_confirmed = self.datavolume[0] > avg_volume * 1.2
            
            # Execute trades
            if buy_signal and volume_confirmed:
                sentiment_info = f"Sentiment: {sentiment['recommendation']} ({sentiment['signal_direction']:.3f})" if self.p.use_sentiment_filter else "No Sentiment"
                self.log(f'SENTIMENT-ENHANCED BUY CREATE - Price: {current_price:.5f}, Strength: {signal_strength:.3f}, {sentiment_info}')
                self.order = self.buy()
                self.entry_bar = len(self)
                
            elif sell_signal and volume_confirmed:
                sentiment_info = f"Sentiment: {sentiment['recommendation']} ({sentiment['signal_direction']:.3f})" if self.p.use_sentiment_filter else "No Sentiment"
                self.log(f'SENTIMENT-ENHANCED SELL CREATE - Price: {current_price:.5f}, Strength: {signal_strength:.3f}, {sentiment_info}')
                self.order = self.sell()
                self.entry_bar = len(self)
                
        else:  # Already in the market - manage position
            self._manage_position()
    
    def _calculate_technical_signals(self, bullish_trend, bearish_trend, rsi_bullish, rsi_bearish,
                                   macd_bullish, macd_bearish, current_price):
        """Calculate technical signal strength and determine buy/sell signals"""
        buy_signal = False
        sell_signal = False
        technical_strength = 0.0
        
        if self.p.use_supply_demand:
            zone_type = self.supply_demand.zone_type[0]
            zone_strength = self.supply_demand.zone_strength[0]
            
            # Buy signal: Price at demand zone + all bullish conditions
            if (zone_type == 1 and zone_strength >= self.p.min_zone_strength and
                bullish_trend and rsi_bullish and macd_bullish):
                
                demand_high = self.supply_demand.demand_zone_high[0]
                demand_low = self.supply_demand.demand_zone_low[0]
                
                if not np.isnan(demand_high) and not np.isnan(demand_low):
                    # Check if we have a good risk/reward setup
                    potential_stop = demand_low - (demand_low * 0.001)  # Stop below demand zone
                    potential_target = current_price + (current_price - potential_stop) * self.p.min_risk_reward
                    
                    if self._validate_risk_reward(current_price, potential_stop, potential_target):
                        buy_signal = True
                        technical_strength = min(zone_strength / 5.0, 1.0)  # Normalize zone strength
                        self.log(f'DEMAND ZONE TECHNICAL SIGNAL - Zone Strength: {zone_strength}, Price: {current_price:.5f}')
            
            # Sell signal: Price at supply zone + all bearish conditions
            elif (zone_type == -1 and zone_strength >= self.p.min_zone_strength and
                  bearish_trend and rsi_bearish and macd_bearish):
                
                supply_high = self.supply_demand.supply_zone_high[0]
                supply_low = self.supply_demand.supply_zone_low[0]
                
                if not np.isnan(supply_high) and not np.isnan(supply_low):
                    # Check if we have a good risk/reward setup
                    potential_stop = supply_high + (supply_high * 0.001)  # Stop above supply zone
                    potential_target = current_price - (potential_stop - current_price) * self.p.min_risk_reward
                    
                    if self._validate_risk_reward(current_price, potential_stop, potential_target):
                        sell_signal = True
                        technical_strength = min(zone_strength / 5.0, 1.0)  # Normalize zone strength
                        self.log(f'SUPPLY ZONE TECHNICAL SIGNAL - Zone Strength: {zone_strength}, Price: {current_price:.5f}')
        
        else:
            # Fallback to simple MA crossover if supply/demand disabled
            if self.crossover > 0 and rsi_bullish and macd_bullish:
                buy_signal = True
                technical_strength = 0.7  # Strong technical signal
            elif self.crossover < 0 and rsi_bearish and macd_bearish:
                sell_signal = True
                technical_strength = 0.7  # Strong technical signal
        
        return {
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'technical_strength': technical_strength
        }
    
    def _combine_technical_sentiment_signals(self, technical_signals, sentiment):
        """Combine technical analysis with sentiment analysis"""
        # Get sentiment components
        sentiment_direction = sentiment.get('signal_direction', 0.0)
        sentiment_strength = sentiment.get('signal_strength', 0.0)
        sentiment_confidence = sentiment.get('confidence', 0.0)
        
        # Check if sentiment meets minimum requirements
        sentiment_valid = (sentiment_strength >= self.p.sentiment_threshold and
                          sentiment_confidence >= self.p.min_sentiment_confidence)
        
        # Calculate weights
        technical_weight = 1.0 - self.p.sentiment_weight
        sentiment_weight = self.p.sentiment_weight if sentiment_valid else 0.0
        
        # Adjust technical weight if sentiment is not valid
        if not sentiment_valid:
            technical_weight = 1.0
        
        # Calculate combined signal strength
        buy_signal = False
        sell_signal = False
        combined_strength = 0.0
        
        if technical_signals['buy_signal']:
            # Calculate buy signal strength
            technical_component = technical_signals['technical_strength'] * technical_weight
            sentiment_component = max(0, sentiment_direction) * sentiment_strength * sentiment_weight
            combined_strength = technical_component + sentiment_component
            
            # Apply sentiment boost if sentiment strongly aligns
            if (sentiment_valid and sentiment_direction > 0.4 and sentiment_strength > 0.6):
                combined_strength *= self.p.sentiment_boost_multiplier
                self.log(f'SENTIMENT BOOST APPLIED (BUY) - New strength: {combined_strength:.3f}')
            
            buy_signal = combined_strength > 0.5  # Minimum threshold for trade execution
            
        elif technical_signals['sell_signal']:
            # Calculate sell signal strength
            technical_component = technical_signals['technical_strength'] * technical_weight
            sentiment_component = max(0, -sentiment_direction) * sentiment_strength * sentiment_weight
            combined_strength = technical_component + sentiment_component
            
            # Apply sentiment boost if sentiment strongly aligns
            if (sentiment_valid and sentiment_direction < -0.4 and sentiment_strength > 0.6):
                combined_strength *= self.p.sentiment_boost_multiplier
                self.log(f'SENTIMENT BOOST APPLIED (SELL) - New strength: {combined_strength:.3f}')
            
            sell_signal = combined_strength > 0.5  # Minimum threshold for trade execution
        
        return {
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'signal_strength': min(combined_strength, 1.0),  # Cap at 1.0
            'technical_component': technical_signals['technical_strength'],
            'sentiment_component': sentiment_strength if sentiment_valid else 0.0,
            'sentiment_direction': sentiment_direction
        }
    
    def _validate_risk_reward(self, entry_price, stop_price, target_price):
        """Validate if the trade meets minimum risk/reward criteria"""
        if entry_price == stop_price:
            return False
            
        risk = abs(entry_price - stop_price)
        reward = abs(target_price - entry_price)
        
        if risk == 0:
            return False
            
        risk_reward_ratio = reward / risk
        return risk_reward_ratio >= self.p.min_risk_reward
    
    def _manage_position(self):
        """Advanced position management with supply/demand levels and sentiment-based exits"""
        current_price = self.dataclose[0]
        
        # Get current sentiment for exit decisions
        sentiment = self.get_sentiment_signal()
        
        if self.position.size > 0:  # Long position
            # Dynamic stop loss based on supply/demand zones
            stop_loss_price = self.buyprice * (1 - self.p.stop_loss_percent)
            take_profit_price = self.buyprice * (1 + self.p.take_profit_percent)
            
            # Check for nearby supply zones that might act as resistance
            if self.p.use_supply_demand:
                supply_high = self.supply_demand.supply_zone_high[0]
                if not np.isnan(supply_high) and supply_high > current_price:
                    # Adjust take profit to just before supply zone
                    zone_target = supply_high * 0.999  # Just before the zone
                    if zone_target < take_profit_price:
                        take_profit_price = zone_target
                        self.log(f'Adjusting TP to supply zone: {take_profit_price:.5f}')
            
            # Check exit conditions
            if current_price <= stop_loss_price:
                self.log('STOP LOSS HIT (LONG), %.2f' % current_price)
                self.close()
            elif current_price >= take_profit_price:
                self.log('TAKE PROFIT HIT (LONG), %.2f' % current_price)
                self.close()
            # Sentiment-based early exit for long positions
            elif (self.p.use_sentiment_filter and
                  sentiment['signal_strength'] > 0.6 and
                  sentiment['signal_direction'] < -0.5):
                self.log(f'SENTIMENT EXIT (LONG) - Negative sentiment: {sentiment["signal_direction"]:.3f}')
                self.close()
            # Trail stop if in significant profit
            elif current_price > self.buyprice * 1.01:  # 1% profit
                trailing_stop = current_price * (1 - self.p.stop_loss_percent * 0.5)  # Tighter trailing stop
                if trailing_stop > stop_loss_price:
                    self.log(f'Trailing stop updated: {trailing_stop:.5f}')
                    
        elif self.position.size < 0:  # Short position
            # Dynamic stop loss based on supply/demand zones
            stop_loss_price = self.buyprice * (1 + self.p.stop_loss_percent)
            take_profit_price = self.buyprice * (1 - self.p.take_profit_percent)
            
            # Check for nearby demand zones that might act as support
            if self.p.use_supply_demand:
                demand_low = self.supply_demand.demand_zone_low[0]
                if not np.isnan(demand_low) and demand_low < current_price:
                    # Adjust take profit to just above demand zone
                    zone_target = demand_low * 1.001  # Just above the zone
                    if zone_target > take_profit_price:
                        take_profit_price = zone_target
                        self.log(f'Adjusting TP to demand zone: {take_profit_price:.5f}')
            
            # Check exit conditions
            if current_price >= stop_loss_price:
                self.log('STOP LOSS HIT (SHORT), %.2f' % current_price)
                self.close()
            elif current_price <= take_profit_price:
                self.log('TAKE PROFIT HIT (SHORT), %.2f' % current_price)
                self.close()
            # Sentiment-based early exit for short positions
            elif (self.p.use_sentiment_filter and
                  sentiment['signal_strength'] > 0.6 and
                  sentiment['signal_direction'] > 0.5):
                self.log(f'SENTIMENT EXIT (SHORT) - Positive sentiment: {sentiment["signal_direction"]:.3f}')
                self.close()
            # Trail stop if in significant profit
            elif current_price < self.buyprice * 0.99:  # 1% profit
                trailing_stop = current_price * (1 + self.p.stop_loss_percent * 0.5)  # Tighter trailing stop
                if trailing_stop < stop_loss_price:
                    self.log(f'Trailing stop updated: {trailing_stop:.5f}')

if __name__ == '__main__':
    # This is a placeholder for how the strategy might be used with a backtesting engine.
    # Actual backtesting setup will be in backtest_engine.py
    logging.basicConfig(level=logging.INFO)
    
    # Example of loading config (for demonstration, actual config loading will be in main.py or backtest_engine.py)
    # config_path = 'config/config.yaml'
    # with open(config_path, 'r') as f:
    #     config = yaml.safe_load(f)
    # print("Forex Strategy loaded with config:", config['trading']['forex_pairs'])
    
    print("Forex Strategy module loaded. Run backtest_engine.py or main.py to use.")