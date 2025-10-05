"""
GPU-Accelerated Scalping Forex Strategy for EUR_USD
Optimized for 1M and 5M timeframes with PyTorch GPU acceleration
"""

import backtrader as bt
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from scipy import stats
from sklearn.preprocessing import StandardScaler

# GPU acceleration imports
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import DataLoader, TensorDataset
    import cupy as cp
    from numba import cuda, jit
    GPU_AVAILABLE = torch.cuda.is_available()
    CUPY_AVAILABLE = True
    print(f"GPU Acceleration Status: PyTorch CUDA: {GPU_AVAILABLE}, CuPy: {CUPY_AVAILABLE}")
    if GPU_AVAILABLE:
        print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
        print(f"CUDA Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
except ImportError as e:
    print(f"GPU libraries not available: {e}")
    GPU_AVAILABLE = False
    CUPY_AVAILABLE = False
    # Fallback to CPU
    torch = None
    cp = np
    cuda = None

class GPUTechnicalIndicators:
    """GPU-accelerated technical indicators using PyTorch and CuPy"""
    
    def __init__(self, device='cuda' if GPU_AVAILABLE else 'cpu'):
        self.device = device
        self.use_gpu = GPU_AVAILABLE and device == 'cuda'
        
    def to_tensor(self, data):
        """Convert data to PyTorch tensor on appropriate device"""
        if self.use_gpu and torch is not None:
            if isinstance(data, np.ndarray):
                return torch.from_numpy(data).float().to(self.device)
            elif isinstance(data, list):
                return torch.tensor(data, dtype=torch.float32, device=self.device)
            return data.to(self.device)
        else:
            return np.array(data, dtype=np.float32)
    
    def gpu_ema(self, prices, period):
        """GPU-accelerated Exponential Moving Average"""
        if not self.use_gpu or torch is None:
            # Fallback to numpy
            alpha = 2.0 / (period + 1)
            ema = np.zeros_like(prices)
            ema[0] = prices[0]
            for i in range(1, len(prices)):
                ema[i] = alpha * prices[i] + (1 - alpha) * ema[i-1]
            return ema
        
        prices_tensor = self.to_tensor(prices)
        alpha = 2.0 / (period + 1)
        
        # Vectorized EMA calculation on GPU
        ema = torch.zeros_like(prices_tensor)
        ema[0] = prices_tensor[0]
        
        for i in range(1, len(prices_tensor)):
            ema[i] = alpha * prices_tensor[i] + (1 - alpha) * ema[i-1]
        
        return ema.cpu().numpy() if self.use_gpu else ema
    
    def gpu_rsi(self, prices, period=14):
        """GPU-accelerated Relative Strength Index"""
        if not self.use_gpu or torch is None:
            # Fallback to numpy
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gains = np.convolve(gains, np.ones(period)/period, mode='valid')
            avg_losses = np.convolve(losses, np.ones(period)/period, mode='valid')
            
            rs = avg_gains / (avg_losses + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            return np.concatenate([np.full(period, 50), rsi])
        
        prices_tensor = self.to_tensor(prices)
        deltas = prices_tensor[1:] - prices_tensor[:-1]
        
        gains = torch.where(deltas > 0, deltas, torch.zeros_like(deltas))
        losses = torch.where(deltas < 0, -deltas, torch.zeros_like(deltas))
        
        # Use unfold for rolling window operations on GPU
        if len(gains) >= period:
            gains_windows = gains.unfold(0, period, 1)
            losses_windows = losses.unfold(0, period, 1)
            
            avg_gains = gains_windows.mean(dim=1)
            avg_losses = losses_windows.mean(dim=1)
            
            rs = avg_gains / (avg_losses + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            # Pad with initial values
            initial_rsi = torch.full((period,), 50.0, device=self.device)
            rsi = torch.cat([initial_rsi, rsi])
        else:
            rsi = torch.full_like(prices_tensor, 50.0)
        
        return rsi.cpu().numpy() if self.use_gpu else rsi
    
    def gpu_bollinger_bands(self, prices, period=20, std_dev=2):
        """GPU-accelerated Bollinger Bands"""
        if not self.use_gpu or torch is None:
            # Fallback to numpy
            sma = np.convolve(prices, np.ones(period)/period, mode='same')
            rolling_std = np.array([np.std(prices[max(0, i-period):i+1]) 
                                  for i in range(len(prices))])
            upper = sma + (rolling_std * std_dev)
            lower = sma - (rolling_std * std_dev)
            return upper, sma, lower
        
        prices_tensor = self.to_tensor(prices)
        
        # Calculate rolling mean and std using unfold
        if len(prices_tensor) >= period:
            windows = prices_tensor.unfold(0, period, 1)
            sma = windows.mean(dim=1)
            rolling_std = windows.std(dim=1)
            
            # Pad to match original length using torch.cat instead of F.pad
            pad_size = period - 1
            if pad_size > 0:
                sma_pad = sma[0].repeat(pad_size)
                std_pad = rolling_std[0].repeat(pad_size)
                sma = torch.cat([sma_pad, sma])
                rolling_std = torch.cat([std_pad, rolling_std])
        else:
            sma = prices_tensor.clone()
            rolling_std = torch.zeros_like(prices_tensor)
        
        upper = sma + (rolling_std * std_dev)
        lower = sma - (rolling_std * std_dev)
        
        if self.use_gpu:
            return upper.cpu().numpy(), sma.cpu().numpy(), lower.cpu().numpy()
        else:
            return upper, sma, lower
    
    def gpu_macd(self, prices, fast=12, slow=26, signal=9):
        """GPU-accelerated MACD"""
        ema_fast = self.gpu_ema(prices, fast)
        ema_slow = self.gpu_ema(prices, slow)
        macd_line = ema_fast - ema_slow
        signal_line = self.gpu_ema(macd_line, signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def gpu_stochastic(self, high, low, close, k_period=14, d_period=3):
        """GPU-accelerated Stochastic Oscillator"""
        if not self.use_gpu or torch is None:
            # Fallback to numpy
            lowest_low = np.array([np.min(low[max(0, i-k_period):i+1]) 
                                 for i in range(len(low))])
            highest_high = np.array([np.max(high[max(0, i-k_period):i+1]) 
                                   for i in range(len(high))])
            k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low + 1e-10)
            d_percent = np.convolve(k_percent, np.ones(d_period)/d_period, mode='same')
            return k_percent, d_percent
        
        high_tensor = self.to_tensor(high)
        low_tensor = self.to_tensor(low)
        close_tensor = self.to_tensor(close)
        
        if len(high_tensor) >= k_period:
            high_windows = high_tensor.unfold(0, k_period, 1)
            low_windows = low_tensor.unfold(0, k_period, 1)
            
            highest_high = high_windows.max(dim=1)[0]
            lowest_low = low_windows.min(dim=1)[0]
            
            # Pad to match original length using torch.cat
            pad_size = k_period - 1
            if pad_size > 0:
                high_pad = highest_high[0].repeat(pad_size)
                low_pad = lowest_low[0].repeat(pad_size)
                highest_high = torch.cat([high_pad, highest_high])
                lowest_low = torch.cat([low_pad, lowest_low])
        else:
            highest_high = high_tensor.clone()
            lowest_low = low_tensor.clone()
        
        k_percent = 100 * (close_tensor - lowest_low) / (highest_high - lowest_low + 1e-10)
        d_percent = self.gpu_ema(k_percent.cpu().numpy() if self.use_gpu else k_percent, d_period)
        
        if self.use_gpu:
            return k_percent.cpu().numpy(), d_percent
        else:
            return k_percent, d_percent

class GPUNeuralNetwork(nn.Module):
    """Neural network for signal prediction using GPU acceleration"""
    
    def __init__(self, input_size=20, hidden_size=64, output_size=3):
        super(GPUNeuralNetwork, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)  # BUY, SELL, HOLD
        self.dropout = nn.Dropout(0.2)
        self.batch_norm1 = nn.BatchNorm1d(hidden_size)
        self.batch_norm2 = nn.BatchNorm1d(hidden_size)
        
    def forward(self, x):
        x = F.relu(self.batch_norm1(self.fc1(x)))
        x = self.dropout(x)
        x = F.relu(self.batch_norm2(self.fc2(x)))
        x = self.dropout(x)
        x = F.softmax(self.fc3(x), dim=1)
        return x

class GPUScalpingForexStrategy(bt.Strategy):
    """
    GPU-Accelerated High-frequency scalping strategy optimized for EUR_USD
    Features:
    - PyTorch GPU acceleration for indicators
    - Neural network signal prediction
    - CuPy for fast array operations
    - Optimized for 1M/5M timeframes
    """
    
    params = (
        # Core Scalping Parameters
        ('fast_ema', 5),
        ('slow_ema', 13),
        ('signal_ema', 3),
        
        # RSI Parameters
        ('rsi_period', 7),
        ('rsi_oversold', 25),
        ('rsi_overbought', 75),
        
        # MACD Parameters
        ('macd_fast', 5),
        ('macd_slow', 13),
        ('macd_signal', 3),
        
        # Bollinger Bands
        ('bb_period', 10),
        ('bb_std', 1.5),
        
        # Risk Management
        ('stop_loss_pips', 3),
        ('take_profit_pips', 6),
        ('max_risk_per_trade', 0.01),
        ('position_size_percent', 0.02),
        
        # GPU Settings
        ('use_gpu', True),
        ('batch_size', 32),
        ('lookback_period', 100),
        
        # Neural Network
        ('use_neural_network', True),
        ('nn_confidence_threshold', 0.7),
        
        # Logging
        ('printlog', True)
    )

    def __init__(self):
        """Initialize GPU-accelerated scalping strategy"""
        self.logger = logging.getLogger(__name__)
        
        # Initialize portfolio value tracker for accurate portfolio tracking
        from execution.portfolio_value_tracker import get_portfolio_tracker
        self.portfolio_tracker = get_portfolio_tracker(100000.0)
        
        # Basic price data
        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low
        self.datavolume = self.datas[0].volume
        
        # Order management
        self.order = None
        self.buyprice = None
        self.buycomm = None
        
        # Performance tracking
        self.trade_count = 0
        self.winning_trades = 0
        self.initial_capital = self.broker.get_cash()  # Store initial capital for profit/loss calculations
        self.last_completed_portfolio_value = self.broker.get_cash()  # Initialize reference capital
        
        # GPU setup
        self.device = 'cuda' if (GPU_AVAILABLE and self.p.use_gpu) else 'cpu'
        self.gpu_indicators = GPUTechnicalIndicators(self.device)
        
        # Initialize neural network if enabled
        if self.p.use_neural_network and torch is not None:
            self.neural_net = GPUNeuralNetwork().to(self.device)
            self.neural_net.eval()  # Set to evaluation mode
        else:
            self.neural_net = None
        
        # Data buffers for GPU processing
        self.price_buffer = []
        self.high_buffer = []
        self.low_buffer = []
        self.volume_buffer = []
        
        self.logger.info(f"GPU Scalping Strategy initialized - Device: {self.device}")
        if GPU_AVAILABLE:
            self.logger.info(f"GPU Memory Available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

    def update_buffers(self):
        """Update price buffers for GPU processing"""
        current_close = float(self.dataclose[0])
        current_high = float(self.datahigh[0])
        current_low = float(self.datalow[0])
        current_volume = float(self.datavolume[0]) if self.datavolume[0] else 1.0
        
        self.price_buffer.append(current_close)
        self.high_buffer.append(current_high)
        self.low_buffer.append(current_low)
        self.volume_buffer.append(current_volume)
        
        # Keep only recent data for GPU processing
        max_buffer_size = self.p.lookback_period
        if len(self.price_buffer) > max_buffer_size:
            self.price_buffer = self.price_buffer[-max_buffer_size:]
            self.high_buffer = self.high_buffer[-max_buffer_size:]
            self.low_buffer = self.low_buffer[-max_buffer_size:]
            self.volume_buffer = self.volume_buffer[-max_buffer_size:]

    def calculate_gpu_indicators(self) -> Dict[str, Any]:
        """Calculate technical indicators using GPU acceleration"""
        if len(self.price_buffer) < max(self.p.slow_ema, self.p.rsi_period):
            return {}
        
        try:
            # Convert to numpy arrays
            prices = np.array(self.price_buffer, dtype=np.float32)
            highs = np.array(self.high_buffer, dtype=np.float32)
            lows = np.array(self.low_buffer, dtype=np.float32)
            
            # Calculate indicators using GPU
            ema_fast = self.gpu_indicators.gpu_ema(prices, self.p.fast_ema)
            ema_slow = self.gpu_indicators.gpu_ema(prices, self.p.slow_ema)
            rsi = self.gpu_indicators.gpu_rsi(prices, self.p.rsi_period)
            
            macd_line, macd_signal, macd_hist = self.gpu_indicators.gpu_macd(
                prices, self.p.macd_fast, self.p.macd_slow, self.p.macd_signal
            )
            
            bb_upper, bb_middle, bb_lower = self.gpu_indicators.gpu_bollinger_bands(
                prices, self.p.bb_period, self.p.bb_std
            )
            
            stoch_k, stoch_d = self.gpu_indicators.gpu_stochastic(
                highs, lows, prices, 14, 3
            )
            
            return {
                'ema_fast': ema_fast[-1],
                'ema_slow': ema_slow[-1],
                'rsi': rsi[-1],
                'macd_line': macd_line[-1],
                'macd_signal': macd_signal[-1],
                'macd_hist': macd_hist[-1],
                'bb_upper': bb_upper[-1],
                'bb_middle': bb_middle[-1],
                'bb_lower': bb_lower[-1],
                'stoch_k': stoch_k[-1],
                'stoch_d': stoch_d[-1],
                'current_price': prices[-1]
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating GPU indicators: {e}")
            return {}

    def neural_network_prediction(self, indicators: Dict[str, Any]) -> Dict[str, float]:
        """Use neural network for signal prediction"""
        if not self.neural_net or not indicators:
            return {'buy_prob': 0.33, 'sell_prob': 0.33, 'hold_prob': 0.34}
        
        try:
            # Prepare input features
            features = [
                indicators.get('ema_fast', 0) / indicators.get('current_price', 1),
                indicators.get('ema_slow', 0) / indicators.get('current_price', 1),
                indicators.get('rsi', 50) / 100.0,
                indicators.get('macd_line', 0),
                indicators.get('macd_signal', 0),
                indicators.get('macd_hist', 0),
                (indicators.get('current_price', 0) - indicators.get('bb_lower', 0)) / 
                (indicators.get('bb_upper', 1) - indicators.get('bb_lower', 0) + 1e-10),
                indicators.get('stoch_k', 50) / 100.0,
                indicators.get('stoch_d', 50) / 100.0
            ]
            
            # Pad features to match network input size
            while len(features) < 20:
                features.append(0.0)
            
            # Convert to tensor and predict
            input_tensor = torch.tensor([features], dtype=torch.float32, device=self.device)
            
            with torch.no_grad():
                predictions = self.neural_net(input_tensor)
                probs = predictions.cpu().numpy()[0]
            
            return {
                'buy_prob': float(probs[0]),
                'sell_prob': float(probs[1]),
                'hold_prob': float(probs[2])
            }
            
        except Exception as e:
            self.logger.error(f"Error in neural network prediction: {e}")
            return {'buy_prob': 0.33, 'sell_prob': 0.33, 'hold_prob': 0.34}

    def generate_gpu_signals(self) -> Dict[str, Any]:
        """Generate trading signals using GPU-accelerated indicators"""
        indicators = self.calculate_gpu_indicators()
        if not indicators:
            return {'signal': 'HOLD', 'strength': 0.0, 'confidence': 0.0}
        
        # Traditional technical analysis signals
        signals = {
            'buy_score': 0.0,
            'sell_score': 0.0
        }
        
        current_price = indicators['current_price']
        
        # EMA signals
        if indicators['ema_fast'] > indicators['ema_slow']:
            signals['buy_score'] += 0.2
        else:
            signals['sell_score'] += 0.2
        
        # RSI signals
        if indicators['rsi'] < self.p.rsi_oversold:
            signals['buy_score'] += 0.3
        elif indicators['rsi'] > self.p.rsi_overbought:
            signals['sell_score'] += 0.3
        
        # MACD signals
        if indicators['macd_line'] > indicators['macd_signal']:
            signals['buy_score'] += 0.2
        else:
            signals['sell_score'] += 0.2
        
        # Bollinger Bands signals
        bb_position = (current_price - indicators['bb_lower']) / (indicators['bb_upper'] - indicators['bb_lower'])
        if bb_position < 0.2:
            signals['buy_score'] += 0.2
        elif bb_position > 0.8:
            signals['sell_score'] += 0.2
        
        # Stochastic signals
        if indicators['stoch_k'] < 20 and indicators['stoch_k'] > indicators['stoch_d']:
            signals['buy_score'] += 0.1
        elif indicators['stoch_k'] > 80 and indicators['stoch_k'] < indicators['stoch_d']:
            signals['sell_score'] += 0.1
        
        # Neural network enhancement
        if self.p.use_neural_network:
            nn_predictions = self.neural_network_prediction(indicators)
            signals['buy_score'] += nn_predictions['buy_prob'] * 0.4
            signals['sell_score'] += nn_predictions['sell_prob'] * 0.4
        
        # Determine final signal
        if signals['buy_score'] > signals['sell_score'] and signals['buy_score'] > 0.6:
            return {
                'signal': 'BUY',
                'strength': signals['buy_score'],
                'confidence': min(signals['buy_score'], 0.95)
            }
        elif signals['sell_score'] > signals['buy_score'] and signals['sell_score'] > 0.6:
            return {
                'signal': 'SELL',
                'strength': signals['sell_score'],
                'confidence': min(signals['sell_score'], 0.95)
            }
        else:
            return {
                'signal': 'HOLD',
                'strength': max(signals['buy_score'], signals['sell_score']),
                'confidence': 0.5
            }

    def next(self):
        """Main trading logic with GPU acceleration"""
        if self.order:
            return
        
        # Update data buffers
        self.update_buffers()
        
        # Generate signals using GPU
        signal_data = self.generate_gpu_signals()
        
        current_price = float(self.dataclose[0])
        
        if not self.position:  # No position
            if signal_data['signal'] == 'BUY' and signal_data['confidence'] > 0.7:
                # Calculate position size
                position_size = self.p.position_size_percent * signal_data['strength']
                
                # Calculate stops and targets
                stop_loss_price = current_price - (self.p.stop_loss_pips * 0.0001)
                take_profit_price = current_price + (self.p.take_profit_pips * 0.0001)
                
                self.log(f'GPU BUY SIGNAL - Price: {current_price:.5f}, '
                        f'Strength: {signal_data["strength"]:.3f}, '
                        f'Confidence: {signal_data["confidence"]:.3f}, '
                        f'Size: {position_size:.3f}')
                
                self.order = self.buy(size=position_size)
                
                # Add portfolio value change and profit/loss information
                current_portfolio_value = self.broker.get_value()
                portfolio_change = current_portfolio_value - self.initial_capital
                portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
                
                # Get portfolio summary from tracker
                portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                
                self.logger.info(f"*** GPU SCALPING PORTFOLIO VALUE AFTER BUY ORDER ***")
                self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                
                if portfolio_change > 0:
                    self.logger.info(f"*** GPU SCALPING PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                elif portfolio_change < 0:
                    self.logger.info(f"*** GPU SCALPING LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
                else:
                    self.logger.info(f"*** GPU SCALPING BREAK EVEN: ${portfolio_change:.2f} (0.00%) ***")
                
            elif signal_data['signal'] == 'SELL' and signal_data['confidence'] > 0.7:
                # Calculate position size
                position_size = self.p.position_size_percent * signal_data['strength']
                
                # Calculate stops and targets
                stop_loss_price = current_price + (self.p.stop_loss_pips * 0.0001)
                take_profit_price = current_price - (self.p.take_profit_pips * 0.0001)
                
                self.log(f'GPU SELL SIGNAL - Price: {current_price:.5f}, '
                        f'Strength: {signal_data["strength"]:.3f}, '
                        f'Confidence: {signal_data["confidence"]:.3f}, '
                        f'Size: {position_size:.3f}')
                
                self.order = self.sell(size=position_size)
                
                # Add portfolio value change and profit/loss information
                current_portfolio_value = self.broker.get_value()
                portfolio_change = current_portfolio_value - self.initial_capital
                portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
                
                # Get portfolio summary from tracker
                portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
                
                self.logger.info(f"*** GPU SCALPING PORTFOLIO VALUE AFTER SELL ORDER ***")
                self.logger.info(f"  Initial Capital: ${self.initial_capital:.2f}")
                self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
                self.logger.info(f"  Portfolio Change: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
                self.logger.info(f"  Realized P&L: ${portfolio_summary['realized_pnl']:.2f}")
                self.logger.info(f"  Unrealized P&L: ${portfolio_summary['unrealized_pnl']:.2f}")
                self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
                
                if portfolio_change > 0:
                    self.logger.info(f"*** GPU SCALPING PROFIT: ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
                elif portfolio_change < 0:
                    self.logger.info(f"*** GPU SCALPING LOSS: ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
    def notify_order(self, order):
        """Enhanced order notification with portfolio tracking"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            
            # Update portfolio tracker
            if order.isbuy():
                self.portfolio_tracker.update_cash(self.broker.get_cash())
                self.portfolio_tracker.add_position(
                    symbol="EUR_USD",
                    size=order.executed.size,
                    entry_price=order.executed.price,
                    commission=order.executed.comm
                )
            else:
                self.portfolio_tracker.close_position(
                    symbol="EUR_USD",
                    exit_price=order.executed.price,
                    commission=order.executed.comm
                )
            
            # Calculate portfolio change since start
            current_portfolio_value = self.broker.get_value()
            portfolio_change = current_portfolio_value - self.initial_capital
            portfolio_change_pct = (portfolio_change / self.initial_capital) * 100
            
            # Get portfolio summary from tracker
            portfolio_summary = self.portfolio_tracker.get_portfolio_summary()
            
            self.logger.info(f"*** GPU SCALPING FINAL PORTFOLIO VALUE CHANGE AFTER ORDER EXECUTION ***")
            self.logger.info(f"  Previous Reference Capital: ${self.initial_capital:.2f}")
            self.logger.info(f"  Current Portfolio Value: ${current_portfolio_value:.2f}")
            self.logger.info(f"  Trade P&L: ${portfolio_change:.2f} ({portfolio_change_pct:+.2f}%)")
            self.logger.info(f"  Net P&L: ${portfolio_summary['net_pnl']:.2f}")
            
            if portfolio_change > 0:
                self.logger.info(f"*** GPU SCALPING TRADE RESULT: PROFIT ${portfolio_change:.2f} (+{portfolio_change_pct:.2f}%) ***")
            elif portfolio_change < 0:
                self.logger.info(f"*** GPU SCALPING TRADE RESULT: LOSS ${portfolio_change:.2f} ({portfolio_change_pct:.2f}%) ***")
            else:
                self.logger.info(f"*** GPU SCALPING TRADE RESULT: BREAK EVEN ${portfolio_change:.2f} (0.00%) ***")
            
            # Update reference capital for next trade
            self.initial_capital = current_portfolio_value
            self.logger.info(f"*** UPDATED REFERENCE CAPITAL FOR NEXT TRADE: ${self.initial_capital:.2f} ***")
            
            self.log(f'GPU SCALPING ORDER EXECUTED - {order.getstatusname()} at {order.executed.price:.5f}')
            self.order = None
            
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log(f'GPU SCALPING ORDER FAILED - {order.getstatusname()}')
            self.order = None

        else:  # In position - manage with tight stops
            self._manage_position()

    def _manage_position(self):
        """Position management with tight scalping stops"""
        current_price = float(self.dataclose[0])
        
        if self.position.size > 0:  # Long position
            stop_loss_price = self.buyprice - (self.p.stop_loss_pips * 0.0001)
            take_profit_price = self.buyprice + (self.p.take_profit_pips * 0.0001)
            
            if current_price <= stop_loss_price:
                self.log(f'GPU STOP LOSS (LONG) - Price: {current_price:.5f}')
                self.close()
            elif current_price >= take_profit_price:
                self.log(f'GPU TAKE PROFIT (LONG) - Price: {current_price:.5f}')
                self.close()
                
        elif self.position.size < 0:  # Short position
            stop_loss_price = self.buyprice + (self.p.stop_loss_pips * 0.0001)
            take_profit_price = self.buyprice - (self.p.take_profit_pips * 0.0001)
            
            if current_price >= stop_loss_price:
                self.log(f'GPU STOP LOSS (SHORT) - Price: {current_price:.5f}')
                self.close()
            elif current_price <= take_profit_price:
                self.log(f'GPU TAKE PROFIT (SHORT) - Price: {current_price:.5f}')
                self.close()

    def log(self, txt, dt=None):
        """Enhanced logging for GPU scalping"""
        if self.p.printlog:
            dt = dt or self.datas[0].datetime.date(0)
            time = self.datas[0].datetime.time(0)
            current_value = self.broker.get_value()
            
            self.logger.info(f'{dt} {time} [GPU] {txt} | Value: {current_value:.2f}')

    def notify_trade(self, trade):
        """Track GPU scalping trade performance"""
        if not trade.isclosed:
            return
            
        self.trade_count += 1
        trade_pnl = trade.pnl
        
        if trade_pnl > 0:
            self.winning_trades += 1
            
        win_rate = (self.winning_trades / self.trade_count) * 100 if self.trade_count > 0 else 0
        
        self.log(f'GPU TRADE CLOSED - PnL: {trade_pnl:.2f} | '
                f'Win Rate: {win_rate:.1f}% | '
                f'Total Trades: {self.trade_count}')

if __name__ == '__main__':
    print("GPU-Accelerated Scalping Forex Strategy loaded successfully")
    if GPU_AVAILABLE:
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
    else:
        print("Running in CPU mode - install PyTorch with CUDA for GPU acceleration")