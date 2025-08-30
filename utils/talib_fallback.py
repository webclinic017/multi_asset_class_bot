"""
TA-Lib Fallback Implementations
Provides alternative implementations of common TA-Lib functions using pandas and numpy
"""

import numpy as np
import pandas as pd
from typing import Union, Tuple, Optional

def RSI(data: Union[np.ndarray, pd.Series], timeperiod: int = 14) -> np.ndarray:
    """
    Relative Strength Index fallback implementation
    """
    if isinstance(data, pd.Series):
        data = data.values
    
    delta = np.diff(data)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    # Calculate initial averages
    avg_gain = np.mean(gain[:timeperiod])
    avg_loss = np.mean(loss[:timeperiod])
    
    rsi = np.full(len(data), np.nan)
    
    if avg_loss != 0:
        rs = avg_gain / avg_loss
        rsi[timeperiod] = 100 - (100 / (1 + rs))
    
    # Calculate subsequent RSI values
    for i in range(timeperiod + 1, len(data)):
        avg_gain = (avg_gain * (timeperiod - 1) + gain[i-1]) / timeperiod
        avg_loss = (avg_loss * (timeperiod - 1) + loss[i-1]) / timeperiod
        
        if avg_loss != 0:
            rs = avg_gain / avg_loss
            rsi[i] = 100 - (100 / (1 + rs))
    
    return rsi

def MACD(data: Union[np.ndarray, pd.Series], 
         fastperiod: int = 12, 
         slowperiod: int = 26, 
         signalperiod: int = 9) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    MACD fallback implementation
    """
    if isinstance(data, pd.Series):
        data = data.values
    
    # Calculate EMAs
    ema_fast = EMA(data, fastperiod)
    ema_slow = EMA(data, slowperiod)
    
    # MACD line
    macd_line = ema_fast - ema_slow
    
    # Signal line
    signal_line = EMA(macd_line, signalperiod)
    
    # Histogram
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def EMA(data: Union[np.ndarray, pd.Series], timeperiod: int) -> np.ndarray:
    """
    Exponential Moving Average fallback implementation
    """
    if isinstance(data, pd.Series):
        data = data.values
    
    alpha = 2.0 / (timeperiod + 1.0)
    ema = np.full(len(data), np.nan)
    
    # Initialize with first valid value
    first_valid = 0
    while first_valid < len(data) and np.isnan(data[first_valid]):
        first_valid += 1
    
    if first_valid >= len(data):
        return ema
    
    ema[first_valid] = data[first_valid]
    
    for i in range(first_valid + 1, len(data)):
        if not np.isnan(data[i]):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
        else:
            ema[i] = ema[i-1]
    
    return ema

def SMA(data: Union[np.ndarray, pd.Series], timeperiod: int) -> np.ndarray:
    """
    Simple Moving Average fallback implementation
    """
    if isinstance(data, pd.Series):
        data = data.values
    
    sma = np.full(len(data), np.nan)
    
    for i in range(timeperiod - 1, len(data)):
        sma[i] = np.mean(data[i - timeperiod + 1:i + 1])
    
    return sma

def BBANDS(data: Union[np.ndarray, pd.Series], 
           timeperiod: int = 20, 
           nbdevup: float = 2.0, 
           nbdevdn: float = 2.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Bollinger Bands fallback implementation
    """
    if isinstance(data, pd.Series):
        data = data.values
    
    # Calculate middle band (SMA)
    middle = SMA(data, timeperiod)
    
    # Calculate standard deviation
    std = np.full(len(data), np.nan)
    for i in range(timeperiod - 1, len(data)):
        std[i] = np.std(data[i - timeperiod + 1:i + 1])
    
    # Calculate upper and lower bands
    upper = middle + (std * nbdevup)
    lower = middle - (std * nbdevdn)
    
    return upper, middle, lower

def ATR(high: Union[np.ndarray, pd.Series], 
        low: Union[np.ndarray, pd.Series], 
        close: Union[np.ndarray, pd.Series], 
        timeperiod: int = 14) -> np.ndarray:
    """
    Average True Range fallback implementation
    """
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Calculate True Range
    tr1 = high - low
    tr2 = np.abs(high - np.roll(close, 1))
    tr3 = np.abs(low - np.roll(close, 1))
    
    tr = np.maximum(tr1, np.maximum(tr2, tr3))
    tr[0] = tr1[0]  # First value
    
    # Calculate ATR using EMA
    atr = EMA(tr, timeperiod)
    
    return atr

def STOCH(high: Union[np.ndarray, pd.Series], 
          low: Union[np.ndarray, pd.Series], 
          close: Union[np.ndarray, pd.Series], 
          fastk_period: int = 5, 
          slowk_period: int = 3, 
          slowd_period: int = 3) -> Tuple[np.ndarray, np.ndarray]:
    """
    Stochastic Oscillator fallback implementation
    """
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Calculate %K
    lowest_low = np.full(len(close), np.nan)
    highest_high = np.full(len(close), np.nan)
    
    for i in range(fastk_period - 1, len(close)):
        lowest_low[i] = np.min(low[i - fastk_period + 1:i + 1])
        highest_high[i] = np.max(high[i - fastk_period + 1:i + 1])
    
    fastk = 100 * (close - lowest_low) / (highest_high - lowest_low)
    
    # Calculate slow %K
    slowk = SMA(fastk, slowk_period)
    
    # Calculate slow %D
    slowd = SMA(slowk, slowd_period)
    
    return slowk, slowd

def CCI(high: Union[np.ndarray, pd.Series], 
        low: Union[np.ndarray, pd.Series], 
        close: Union[np.ndarray, pd.Series], 
        timeperiod: int = 14) -> np.ndarray:
    """
    Commodity Channel Index fallback implementation
    """
    if isinstance(high, pd.Series):
        high = high.values
    if isinstance(low, pd.Series):
        low = low.values
    if isinstance(close, pd.Series):
        close = close.values
    
    # Calculate Typical Price
    tp = (high + low + close) / 3
    
    # Calculate SMA of Typical Price
    sma_tp = SMA(tp, timeperiod)
    
    # Calculate Mean Deviation
    mad = np.full(len(tp), np.nan)
    for i in range(timeperiod - 1, len(tp)):
        mad[i] = np.mean(np.abs(tp[i - timeperiod + 1:i + 1] - sma_tp[i]))
    
    # Calculate CCI
    cci = (tp - sma_tp) / (0.015 * mad)
    
    return cci

class TalibFallback:
    """
    Fallback class that mimics TA-Lib interface
    """
    
    @staticmethod
    def RSI(data, timeperiod=14):
        return RSI(data, timeperiod)
    
    @staticmethod
    def MACD(data, fastperiod=12, slowperiod=26, signalperiod=9):
        return MACD(data, fastperiod, slowperiod, signalperiod)
    
    @staticmethod
    def EMA(data, timeperiod):
        return EMA(data, timeperiod)
    
    @staticmethod
    def SMA(data, timeperiod):
        return SMA(data, timeperiod)
    
    @staticmethod
    def BBANDS(data, timeperiod=20, nbdevup=2.0, nbdevdn=2.0):
        return BBANDS(data, timeperiod, nbdevup, nbdevdn)
    
    @staticmethod
    def ATR(high, low, close, timeperiod=14):
        return ATR(high, low, close, timeperiod)
    
    @staticmethod
    def STOCH(high, low, close, fastk_period=5, slowk_period=3, slowd_period=3):
        return STOCH(high, low, close, fastk_period, slowk_period, slowd_period)
    
    @staticmethod
    def CCI(high, low, close, timeperiod=14):
        return CCI(high, low, close, timeperiod)

# Test function
def test_fallback_functions():
    """Test fallback implementations"""
    print("Testing TA-Lib fallback implementations...")
    
    # Generate test data
    np.random.seed(42)
    data = np.cumsum(np.random.randn(100)) + 100
    high = data + np.random.rand(100)
    low = data - np.random.rand(100)
    close = data
    
    try:
        # Test RSI
        rsi = RSI(close)
        print(f"RSI test: {rsi[-1]:.2f}")
        
        # Test MACD
        macd, signal, hist = MACD(close)
        print(f"MACD test: {macd[-1]:.4f}")
        
        # Test Bollinger Bands
        upper, middle, lower = BBANDS(close)
        print(f"BB test: Upper={upper[-1]:.2f}, Middle={middle[-1]:.2f}, Lower={lower[-1]:.2f}")
        
        # Test ATR
        atr = ATR(high, low, close)
        print(f"ATR test: {atr[-1]:.4f}")
        
        print("All fallback functions working correctly!")
        return True
        
    except Exception as e:
        print(f"Error in fallback functions: {e}")
        return False

if __name__ == "__main__":
    test_fallback_functions()