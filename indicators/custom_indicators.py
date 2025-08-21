"""
Custom Indicators Module for Trading Bot

This module contains custom indicators for supply/demand analysis,
including pivot highs/lows and supply/demand zone detection.
"""

import backtrader as bt
import numpy as np
from collections import deque


class PivotHighLow(bt.Indicator):
    """
    Custom indicator to identify pivot highs and pivot lows
    
    A pivot high is a high that is higher than the specified number of highs before and after it.
    A pivot low is a low that is lower than the specified number of lows before and after it.
    """
    
    lines = ('pivot_high', 'pivot_low')
    params = (
        ('period', 5),  # Number of bars to look back and forward
    )
    
    plotinfo = dict(
        plot=True,
        plotname='Pivot Points',
        subplot=False,
        plotlinelabels=True
    )
    
    plotlines = dict(
        pivot_high=dict(marker='v', markersize=8.0, color='red', fillstyle='full'),
        pivot_low=dict(marker='^', markersize=8.0, color='green', fillstyle='full')
    )
    
    def __init__(self):
        self.addminperiod(self.p.period * 2 + 1)
        
    def next(self):
        # Initialize pivot values
        self.lines.pivot_high[0] = float('nan')
        self.lines.pivot_low[0] = float('nan')
        
        # Need enough data points (we can only look back, not forward in real-time)
        if len(self.data.high) < self.p.period + 1:
            return
            
        # We'll identify pivots with a delay (looking back only)
        # Check if the point 'period' bars ago was a pivot
        if len(self.data.high) >= self.p.period * 2 + 1:
            pivot_index = -self.p.period  # Look at the middle point
            
            # Check for pivot high
            pivot_high = self.data.high[pivot_index]
            is_pivot_high = True
            
            # Check if this high is higher than surrounding highs
            for i in range(1, self.p.period + 1):
                if (pivot_high <= self.data.high[pivot_index - i] or
                    pivot_high <= self.data.high[pivot_index + i]):
                    is_pivot_high = False
                    break
                    
            if is_pivot_high:
                self.lines.pivot_high[pivot_index] = pivot_high
                
            # Check for pivot low
            pivot_low = self.data.low[pivot_index]
            is_pivot_low = True
            
            # Check if this low is lower than surrounding lows
            for i in range(1, self.p.period + 1):
                if (pivot_low >= self.data.low[pivot_index - i] or
                    pivot_low >= self.data.low[pivot_index + i]):
                    is_pivot_low = False
                    break
                    
            if is_pivot_low:
                self.lines.pivot_low[pivot_index] = pivot_low


class SupplyDemandZones(bt.Indicator):
    """
    Custom indicator to identify supply and demand zones based on pivot points
    
    Supply zones are areas where price previously fell from (resistance)
    Demand zones are areas where price previously rose from (support)
    """
    
    lines = ('supply_zone_high', 'supply_zone_low', 'demand_zone_high', 'demand_zone_low', 
             'zone_strength', 'zone_type')
    
    params = (
        ('pivot_period', 5),      # Period for pivot calculation
        ('zone_lookback', 50),    # How far back to look for zones
        ('min_zone_strength', 2), # Minimum touches to consider a zone valid
        ('zone_buffer', 0.0005),  # Buffer around zones (0.05% for forex)
        ('max_zones', 10),        # Maximum number of zones to track
    )
    
    plotinfo = dict(
        plot=True,
        plotname='Supply/Demand Zones',
        subplot=False
    )
    
    def __init__(self):
        self.pivot_indicator = PivotHighLow(period=self.p.pivot_period)
        self.supply_zones = deque(maxlen=self.p.max_zones)
        self.demand_zones = deque(maxlen=self.p.max_zones)
        self.addminperiod(self.p.pivot_period * 2 + self.p.zone_lookback)
        
    def next(self):
        # Initialize zone values
        self.lines.supply_zone_high[0] = float('nan')
        self.lines.supply_zone_low[0] = float('nan')
        self.lines.demand_zone_high[0] = float('nan')
        self.lines.demand_zone_low[0] = float('nan')
        self.lines.zone_strength[0] = 0
        self.lines.zone_type[0] = 0  # 0=none, 1=demand, -1=supply
        
        # Check for new pivot highs (potential supply zones)
        if not np.isnan(self.pivot_indicator.pivot_high[0]):
            pivot_high = self.pivot_indicator.pivot_high[0]
            # Create supply zone around the pivot high
            zone_high = pivot_high + (pivot_high * self.p.zone_buffer)
            zone_low = pivot_high - (pivot_high * self.p.zone_buffer)
            
            # Look for the base of the move (demand that created this supply)
            base_low = float('inf')
            for i in range(1, min(self.p.zone_lookback, len(self.data.low))):
                if self.data.low[-i] < base_low:
                    base_low = self.data.low[-i]
                    
            supply_zone = {
                'high': zone_high,
                'low': zone_low,
                'pivot_price': pivot_high,
                'base_price': base_low,
                'strength': 1,
                'last_test': len(self.data),
                'broken': False
            }
            self.supply_zones.append(supply_zone)
            
        # Check for new pivot lows (potential demand zones)
        if not np.isnan(self.pivot_indicator.pivot_low[0]):
            pivot_low = self.pivot_indicator.pivot_low[0]
            # Create demand zone around the pivot low
            zone_high = pivot_low + (pivot_low * self.p.zone_buffer)
            zone_low = pivot_low - (pivot_low * self.p.zone_buffer)
            
            # Look for the top of the move (supply that created this demand)
            base_high = 0
            for i in range(1, min(self.p.zone_lookback, len(self.data.high))):
                if self.data.high[-i] > base_high:
                    base_high = self.data.high[-i]
                    
            demand_zone = {
                'high': zone_high,
                'low': zone_low,
                'pivot_price': pivot_low,
                'base_price': base_high,
                'strength': 1,
                'last_test': len(self.data),
                'broken': False
            }
            self.demand_zones.append(demand_zone)
            
        # Update zone strengths and check for tests
        current_high = self.data.high[0]
        current_low = self.data.low[0]
        
        # Check supply zones
        strongest_supply = None
        max_supply_strength = 0
        
        for zone in list(self.supply_zones):
            if zone['broken']:
                continue
                
            # Check if price is testing the zone
            if current_low <= zone['high'] and current_high >= zone['low']:
                zone['strength'] += 1
                zone['last_test'] = len(self.data)
                
            # Check if zone is broken (price closes above supply zone)
            if self.data.close[0] > zone['high']:
                zone['broken'] = True
                
            # Track strongest active zone
            if not zone['broken'] and zone['strength'] > max_supply_strength:
                max_supply_strength = zone['strength']
                strongest_supply = zone
                
        # Check demand zones
        strongest_demand = None
        max_demand_strength = 0
        
        for zone in list(self.demand_zones):
            if zone['broken']:
                continue
                
            # Check if price is testing the zone
            if current_high >= zone['low'] and current_low <= zone['high']:
                zone['strength'] += 1
                zone['last_test'] = len(self.data)
                
            # Check if zone is broken (price closes below demand zone)
            if self.data.close[0] < zone['low']:
                zone['broken'] = True
                
            # Track strongest active zone
            if not zone['broken'] and zone['strength'] > max_demand_strength:
                max_demand_strength = zone['strength']
                strongest_demand = zone
                
        # Set current zone information
        if strongest_supply and max_supply_strength >= self.p.min_zone_strength:
            if current_low <= strongest_supply['high'] and current_high >= strongest_supply['low']:
                self.lines.supply_zone_high[0] = strongest_supply['high']
                self.lines.supply_zone_low[0] = strongest_supply['low']
                self.lines.zone_strength[0] = strongest_supply['strength']
                self.lines.zone_type[0] = -1
                
        if strongest_demand and max_demand_strength >= self.p.min_zone_strength:
            if current_high >= strongest_demand['low'] and current_low <= strongest_demand['high']:
                self.lines.demand_zone_high[0] = strongest_demand['high']
                self.lines.demand_zone_low[0] = strongest_demand['low']
                self.lines.zone_strength[0] = strongest_demand['strength']
                self.lines.zone_type[0] = 1


class VolumeProfile(bt.Indicator):
    """
    Simple volume profile indicator to identify high volume areas
    which often act as support/resistance
    """
    
    lines = ('volume_high', 'volume_low', 'poc')  # Point of Control
    
    params = (
        ('period', 50),        # Lookback period
        ('price_levels', 20),  # Number of price levels to analyze
    )
    
    def __init__(self):
        self.addminperiod(self.p.period)
        
    def next(self):
        # Initialize values
        self.lines.volume_high[0] = float('nan')
        self.lines.volume_low[0] = float('nan')
        self.lines.poc[0] = float('nan')
        
        if len(self.data) < self.p.period:
            return
            
        # Get price range for the period
        highs = [self.data.high[-i] for i in range(self.p.period)]
        lows = [self.data.low[-i] for i in range(self.p.period)]
        volumes = [self.data.volume[-i] for i in range(self.p.period)]
        
        price_high = max(highs)
        price_low = min(lows)
        price_range = price_high - price_low
        
        if price_range == 0:
            return
            
        # Create price levels
        level_size = price_range / self.p.price_levels
        volume_at_price = {}
        
        # Distribute volume across price levels
        for i in range(self.p.period):
            high = highs[i]
            low = lows[i]
            volume = volumes[i]
            
            # Simple distribution - could be more sophisticated
            mid_price = (high + low) / 2
            level_index = int((mid_price - price_low) / level_size)
            level_index = max(0, min(level_index, self.p.price_levels - 1))
            
            level_price = price_low + (level_index * level_size)
            
            if level_price not in volume_at_price:
                volume_at_price[level_price] = 0
            volume_at_price[level_price] += volume
            
        # Find Point of Control (highest volume level)
        if volume_at_price:
            poc_price = max(volume_at_price.keys(), key=lambda x: volume_at_price[x])
            self.lines.poc[0] = poc_price
            
            # Set volume high/low areas
            sorted_levels = sorted(volume_at_price.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_levels) >= 3:
                # Top 3 volume areas
                high_volume_prices = [level[0] for level in sorted_levels[:3]]
                self.lines.volume_high[0] = max(high_volume_prices)
                self.lines.volume_low[0] = min(high_volume_prices)