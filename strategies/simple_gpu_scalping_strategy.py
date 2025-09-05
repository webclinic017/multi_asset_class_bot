"""
Simplified GPU-Accelerated Scalping Strategy
Uses PyTorch for basic computations with robust fallbacks
"""

import backtrader as bt
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

# GPU acceleration imports with robust fallbacks
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        print(f"GPU Available: {torch.cuda.get_device_name(0)}")
    else:
        print("GPU not available, using CPU")
except ImportError:
    print("PyTorch not available, using CPU fallback")
    GPU_AVAILABLE = False
    torch = None

class SimpleGPUIndicators:
    """Simplified GPU indicators with robust fallbacks"""
    
    def __init__(self, use_gpu=True):
        self.use_gpu = use_gpu and GPU_AVAILABLE and torch is not None
        self.device = 'cuda' if self.use_gpu else 'cpu'
        
    def gpu_ema(self, prices, period):
        """Simple GPU EMA calculation"""
        try:
            if self.use_gpu:
                # Convert to tensor
                prices_tensor = torch.tensor(prices, dtype=torch.float32, device=self.device)
                alpha = 2.0 / (period + 1)
                
                # Simple EMA calculation
                ema = torch.zeros_like(prices_tensor)
                ema[0] = prices_tensor[0]
                
                for i in range(1, len(prices_tensor)):
                    ema[i] = alpha * prices_tensor[i] + (1 - alpha) * ema[i-1]
                
                return ema.cpu().numpy()
            else:
                # CPU fallback
                alpha = 2.0 / (period + 1)
                ema = np.zeros_like(prices)
                ema[0] = prices[0]
                for i in range(1, len(prices)):
                    ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
                return ema
                
        except Exception as e:
            # Always fallback to CPU on error
            alpha = 2.0 / (period + 1)
            ema = np.zeros_like(prices)
            ema[0] = prices[0]
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            return ema
    
    def gpu_rsi(self, prices, period=14):
        """Simple GPU RSI calculation"""
        try:
            if self.use_gpu:
                prices_tensor = torch.tensor(prices, dtype=torch.float32, device=self.device)
                deltas = prices_tensor[1:] - prices_tensor[:-1]
                
                gains = torch.where(deltas > 0, deltas, torch.zeros_like(deltas))
                losses = torch.where(deltas < 0, -deltas, torch.zeros_like(deltas))
                
                # Simple moving average for gains and losses
                avg_gains = torch.zeros(len(gains))
                avg_losses = torch.zeros(len(losses))
                
                if len(gains) >= period:
                    for i in range(period-1, len(gains)):
                        avg_gains[i] = gains[max(0, i-period+1):i+1].mean()
                        avg_losses[i] = losses[max(0, i-period+1):i+1].mean()
                
                rs = avg_gains / (avg_losses + 1e-10)
                rsi = 100 - (100 / (1 + rs))
                
                # Pad with initial value
                rsi_padded = torch.full((len(prices),), 50.0, device=self.device)
                rsi_padded[1:] = rsi
                
                return rsi_padded.cpu().numpy()
            else:
                # CPU fallback
                deltas = np.diff(prices)
                gains = np.where(deltas > 0, deltas, 0)
                losses = np.where(deltas < 0, -deltas, 0)
                
                avg_gains = np.zeros(len(gains))
                avg_losses = np.zeros(len(losses))
                
                for i in range(period-1, len(gains)):
                    avg_gains[i] = np.mean(gains[max(0, i-period+1):i+1])
                    avg_losses[i] = np.mean(losses[max(0, i-period+1):i+1])
                
                rs = avg_gains / (avg_losses + 1e-10)
                rsi = 100 - (100 / (1 + rs))
                
                # Pad with initial value
                rsi_padded = np.full(len(prices), 50.0)
                rsi_padded[1:] = rsi
                return rsi_padded
                
        except Exception as e:
            # CPU fallback on error
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gains = np.zeros(len(gains))
            avg_losses = np.zeros(len(losses))
            
            for i in range(period-1, len(gains)):
                avg_gains[i] = np.mean(gains[max(0, i-period+1):i+1])
                avg_losses[i] = np.mean(losses[max(0, i-period+1):i+1])
            
            rs = avg_gains / (avg_losses + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            rsi_padded = np.full(len(prices), 50.0)
            rsi_padded[1:] = rsi
            return rsi_padded

class SimpleGPUScalpingStrategy(bt.Strategy):
    """
    Simplified GPU-accelerated scalping strategy
    Focuses on core functionality with robust GPU/CPU fallbacks
    """
    
    params = (
        # Core parameters (compatible with database strategies)
        ('fast_ema', 5),
        ('slow_ema', 13),
        ('fast_length', 5),        # Alias for fast_ema (database compatibility)
        ('slow_length', 13),       # Alias for slow_ema (database compatibility)
        ('rsi_period', 7),
        ('rsi_oversold', 30),
        ('rsi_overbought', 70),
        ('stop_loss_pips', 3),
        ('take_profit_pips', 6),
        ('position_size_percent', 0.02),
        
        # Additional common parameters for database compatibility
        ('macd_fast', 5),
        ('macd_slow', 13),
        ('macd_signal', 3),
        ('bb_period', 10),
        ('bb_std', 1.5),
        ('atr_period', 7),
        ('max_risk_per_trade', 0.01),
        ('signal_ema', 3),
        ('signal_length', 5),
        ('dynamic_sizing', True),
        
        # GPU parameters
        ('use_gpu', True),
        ('lookback_period', 50),
        ('printlog', True)
    )

    def __init__(self):
        """Initialize simplified GPU strategy"""
        self.logger = logging.getLogger(__name__)
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        
        # Order management
        self.order = None
        self.buyprice = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        
        # GPU setup
        self.gpu_indicators = SimpleGPUIndicators(self.p.use_gpu)
        
        # Data buffers
        self.price_buffer = []
        
        self.logger.info(f"Simple GPU Strategy initialized - Device: {self.gpu_indicators.device}")

    def update_buffers(self):
        """Update price buffers"""
        current_close = float(self.dataclose[0])
        self.price_buffer.append(current_close)
        
        # Keep only recent data
        if len(self.price_buffer) > self.p.lookback_period:
            self.price_buffer = self.price_buffer[-self.p.lookback_period:]

    def generate_signals(self) -> Dict[str, Any]:
        """Generate trading signals using GPU indicators"""
        if len(self.price_buffer) < max(self.p.slow_ema, self.p.rsi_period):
            return {'signal': 'HOLD', 'strength': 0.0}
        
        try:
            # Calculate indicators
            prices = np.array(self.price_buffer)
            ema_fast = self.gpu_indicators.gpu_ema(prices, self.p.fast_ema)
            ema_slow = self.gpu_indicators.gpu_ema(prices, self.p.slow_ema)
            rsi = self.gpu_indicators.gpu_rsi(prices, self.p.rsi_period)
            
            # Current values
            current_ema_fast = ema_fast[-1]
            current_ema_slow = ema_slow[-1]
            current_rsi = rsi[-1]
            
            # Generate signals
            buy_score = 0.0
            sell_score = 0.0
            
            # EMA crossover
            if current_ema_fast > current_ema_slow:
                buy_score += 0.4
            else:
                sell_score += 0.4
            
            # RSI signals
            if current_rsi < self.p.rsi_oversold:
                buy_score += 0.6
            elif current_rsi > self.p.rsi_overbought:
                sell_score += 0.6
            
            # Determine signal
            if buy_score > sell_score and buy_score > 0.7:
                return {'signal': 'BUY', 'strength': buy_score}
            elif sell_score > buy_score and sell_score > 0.7:
                return {'signal': 'SELL', 'strength': sell_score}
            else:
                return {'signal': 'HOLD', 'strength': max(buy_score, sell_score)}
                
        except Exception as e:
            self.logger.error(f"Error generating signals: {e}")
            return {'signal': 'HOLD', 'strength': 0.0}

    def next(self):
        """Main trading logic"""
        if self.order:
            return
        
        # Update buffers
        self.update_buffers()
        
        # Generate signals
        signal_data = self.generate_signals()
        
        current_price = float(self.dataclose[0])
        
        if not self.position:  # No position
            if signal_data['signal'] == 'BUY':
                position_size = self.p.position_size_percent
                self.log(f'GPU BUY - Price: {current_price:.5f}, Strength: {signal_data["strength"]:.3f}')
                self.order = self.buy(size=position_size)
                
            elif signal_data['signal'] == 'SELL':
                position_size = self.p.position_size_percent
                self.log(f'GPU SELL - Price: {current_price:.5f}, Strength: {signal_data["strength"]:.3f}')
                self.order = self.sell(size=position_size)
        
        else:  # In position
            self._manage_position()

    def _manage_position(self):
        """Simple position management"""
        current_price = float(self.dataclose[0])
        
        if self.position.size > 0:  # Long position
            stop_loss = self.buyprice - (self.p.stop_loss_pips * 0.0001)
            take_profit = self.buyprice + (self.p.take_profit_pips * 0.0001)
            
            if current_price <= stop_loss:
                self.log(f'STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
            elif current_price >= take_profit:
                self.log(f'TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            stop_loss = self.buyprice + (self.p.stop_loss_pips * 0.0001)
            take_profit = self.buyprice - (self.p.take_profit_pips * 0.0001)
            
            if current_price >= stop_loss:
                self.log(f'STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
            elif current_price <= take_profit:
                self.log(f'TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()

    def log(self, txt, dt=None):
        """Enhanced logging"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            time = self.datas[0].datetime.time(0)
            current_value = self.broker.get_value()
            self.logger.info(f'{dt} {time} [GPU] {txt} | Value: {current_value:.2f}')

    def notify_trade(self, trade):
        """Track trade performance"""
        if not trade.isclosed:
            return
            
        self.trade_count += 1
        if trade.pnl > 0:
            self.winning_trades += 1
            
        win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
        
        self.log(f'TRADE CLOSED - PnL: {trade.pnl:.2f} | Win Rate: {win_rate:.1f}% | Total: {self.trade_count}')

if __name__ == '__main__':
    print("Simple GPU Scalping Strategy loaded successfully")
    if GPU_AVAILABLE:
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    else:
        print("Running in CPU mode")