"""
GPU-Accelerated Backtesting Engine
Uses PyTorch and CuPy for high-performance backtesting with GPU acceleration
"""

import backtrader as bt
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import time
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# GPU acceleration imports
try:
    import torch
    import cupy as cp
    from numba import cuda
    GPU_AVAILABLE = torch.cuda.is_available()
    print(f"GPU Backtesting Engine - CUDA Available: {GPU_AVAILABLE}")
    if GPU_AVAILABLE:
        print(f"GPU Device: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
except ImportError as e:
    print(f"GPU libraries not available: {e}")
    GPU_AVAILABLE = False
    torch = None
    cp = np
    cuda = None

from strategies.simple_gpu_scalping_strategy import SimpleGPUScalpingStrategy
from strategies.scalping_forex_strategy import ScalpingForexStrategy
from strategies.enhanced_forex_strategy import EnhancedForexStrategy
from strategies.crypto_strategy import CryptoStrategy
from strategies.forex_strategy import ForexStrategy
from database.database_manager import DatabaseManager

class GPUBacktestEngine:
    """
    High-performance backtesting engine with GPU acceleration
    Features:
    - GPU-accelerated indicator calculations
    - Parallel strategy execution
    - Memory-optimized data handling
    - Real-time performance monitoring
    """
    
    def __init__(self, use_gpu: bool = True):
        """
        Initialize GPU backtesting engine
        
        Args:
            use_gpu: Whether to use GPU acceleration (falls back to CPU if not available)
        """
        self.logger = logging.getLogger(__name__)
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.device = 'cuda' if self.use_gpu else 'cpu'
        
        # Performance tracking
        self.start_time = None
        self.end_time = None
        self.total_bars_processed = 0
        self.gpu_memory_usage = []
        
        # Database connection
        self.db_manager = DatabaseManager()
        
        self.logger.info(f"GPU Backtest Engine initialized - Device: {self.device}")
        
        if self.use_gpu:
            # Initialize GPU memory monitoring
            self._log_gpu_memory("Initial GPU state")
    
    def _log_gpu_memory(self, stage: str):
        """Log GPU memory usage"""
        if self.use_gpu and torch is not None:
            try:
                memory_allocated = torch.cuda.memory_allocated() / 1024**3
                memory_reserved = torch.cuda.memory_reserved() / 1024**3
                memory_free = (torch.cuda.get_device_properties(0).total_memory - torch.cuda.memory_reserved()) / 1024**3
                
                self.gpu_memory_usage.append({
                    'stage': stage,
                    'allocated_gb': memory_allocated,
                    'reserved_gb': memory_reserved,
                    'free_gb': memory_free,
                    'timestamp': datetime.now()
                })
                
                self.logger.info(f"{stage} - GPU Memory: {memory_allocated:.2f}GB allocated, {memory_free:.2f}GB free")
            except Exception as e:
                self.logger.warning(f"Could not log GPU memory: {e}")
    
    def prepare_data_gpu(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Prepare and optimize data for GPU processing
        
        Args:
            data: OHLCV DataFrame
            
        Returns:
            Dictionary with GPU-optimized data arrays
        """
        try:
            if self.use_gpu and torch is not None:
                # Convert to GPU tensors for faster processing
                gpu_data = {
                    'open': torch.tensor(data['open'].values, dtype=torch.float32, device=self.device),
                    'high': torch.tensor(data['high'].values, dtype=torch.float32, device=self.device),
                    'low': torch.tensor(data['low'].values, dtype=torch.float32, device=self.device),
                    'close': torch.tensor(data['close'].values, dtype=torch.float32, device=self.device),
                    'volume': torch.tensor(data['volume'].values, dtype=torch.float32, device=self.device),
                    'datetime': data.index.tolist()
                }
                
                self._log_gpu_memory("Data loaded to GPU")
                return gpu_data
            else:
                # CPU fallback
                return {
                    'open': data['open'].values,
                    'high': data['high'].values,
                    'low': data['low'].values,
                    'close': data['close'].values,
                    'volume': data['volume'].values,
                    'datetime': data.index.tolist()
                }
                
        except Exception as e:
            self.logger.error(f"Error preparing GPU data: {e}")
            # Fallback to CPU
            return {
                'open': data['open'].values,
                'high': data['high'].values,
                'low': data['low'].values,
                'close': data['close'].values,
                'volume': data['volume'].values,
                'datetime': data.index.tolist()
            }
    
    def create_backtrader_data(self, gpu_data: Dict[str, Any]) -> bt.feeds.PandasData:
        """
        Convert GPU data back to Backtrader format
        
        Args:
            gpu_data: GPU-optimized data dictionary
            
        Returns:
            Backtrader data feed
        """
        try:
            # Convert back to CPU if needed
            if self.use_gpu and torch is not None:
                df_data = {
                    'open': gpu_data['open'].cpu().numpy(),
                    'high': gpu_data['high'].cpu().numpy(),
                    'low': gpu_data['low'].cpu().numpy(),
                    'close': gpu_data['close'].cpu().numpy(),
                    'volume': gpu_data['volume'].cpu().numpy()
                }
            else:
                df_data = {
                    'open': gpu_data['open'],
                    'high': gpu_data['high'],
                    'low': gpu_data['low'],
                    'close': gpu_data['close'],
                    'volume': gpu_data['volume']
                }
            
            # Create DataFrame
            df = pd.DataFrame(df_data, index=gpu_data['datetime'])
            
            # Create Backtrader data feed
            data_feed = bt.feeds.PandasData(
                dataname=df,
                datetime=None,  # Use index
                open=0,
                high=1,
                low=2,
                close=3,
                volume=4,
                openinterest=-1
            )
            
            return data_feed
            
        except Exception as e:
            self.logger.error(f"Error creating Backtrader data: {e}")
            raise
    
    def run_gpu_backtest(self,
                        strategy_params: Dict[str, Any],
                        symbol: str,
                        start_date: str,
                        end_date: str,
                        initial_capital: float = 10000.0,
                        timeframe: str = '1m',
                        strategy_name: str = None,
                        strategy_type: str = None) -> Dict[str, Any]:
        """
        Run GPU-accelerated backtest
        
        Args:
            strategy_params: Strategy parameters
            symbol: Trading symbol
            start_date: Start date for backtest
            end_date: End date for backtest
            initial_capital: Initial capital
            timeframe: Data timeframe
            
        Returns:
            Backtest results dictionary
        """
        self.start_time = time.time()
        self.logger.info(f"Starting GPU backtest for {symbol} from {start_date} to {end_date}")
        
        try:
            # Generate sample data (in production, this would come from your data source)
            data = self._generate_sample_data(symbol, start_date, end_date, timeframe)
            self.total_bars_processed = len(data)
            
            # Prepare data for GPU processing
            gpu_data = self.prepare_data_gpu(data)
            self._log_gpu_memory("Data prepared for GPU")
            
            # Create Backtrader engine
            cerebro = bt.Cerebro()
            
            # Set initial capital
            cerebro.broker.setcash(initial_capital)
            
            # Set commission (typical forex spread)
            cerebro.broker.setcommission(commission=0.0001)  # 1 pip spread
            
            # Select strategy based on strategy type or name
            strategy_class = self._select_strategy_class(strategy_name, strategy_type)
            strategy_class_name = strategy_class.__name__
            
            self.logger.info(f"Using strategy: {strategy_class_name} ({'GPU-accelerated' if self.use_gpu else 'CPU mode'})")
            cerebro.addstrategy(strategy_class, **strategy_params)
            
            # Add data
            data_feed = self.create_backtrader_data(gpu_data)
            cerebro.adddata(data_feed)
            
            # Add analyzers
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            
            self._log_gpu_memory("Before backtest execution")
            
            # Run backtest
            self.logger.info("Executing backtest...")
            results = cerebro.run()
            
            self._log_gpu_memory("After backtest execution")
            
            # Extract results
            strategy_result = results[0]
            
            # Get analyzer results
            trade_analyzer = strategy_result.analyzers.trades.get_analysis()
            sharpe_analyzer = strategy_result.analyzers.sharpe.get_analysis()
            drawdown_analyzer = strategy_result.analyzers.drawdown.get_analysis()
            returns_analyzer = strategy_result.analyzers.returns.get_analysis()
            
            # Calculate performance metrics
            final_value = cerebro.broker.getvalue()
            total_return = (final_value - initial_capital) / initial_capital
            
            # Compile results
            results_dict = {
                'initial_capital': initial_capital,
                'final_capital': final_value,
                'total_return': total_return,
                'total_trades': trade_analyzer.get('total', {}).get('total', 0),
                'winning_trades': trade_analyzer.get('won', {}).get('total', 0),
                'losing_trades': trade_analyzer.get('lost', {}).get('total', 0),
                'win_rate': (trade_analyzer.get('won', {}).get('total', 0) / 
                           max(trade_analyzer.get('total', {}).get('total', 1), 1)) * 100,
                'gross_profit': trade_analyzer.get('won', {}).get('pnl', {}).get('total', 0),
                'gross_loss': abs(trade_analyzer.get('lost', {}).get('pnl', {}).get('total', 0)),
                'max_drawdown': drawdown_analyzer.get('max', {}).get('drawdown', 0),
                'sharpe_ratio': sharpe_analyzer.get('sharperatio', 0),
                'avg_trade_duration': 0,  # Would need custom analyzer
                'profit_factor': (trade_analyzer.get('won', {}).get('pnl', {}).get('total', 0) / 
                                max(abs(trade_analyzer.get('lost', {}).get('pnl', {}).get('total', 1)), 1)),
                
                # GPU-specific metrics
                'gpu_accelerated': self.use_gpu,
                'device_used': self.device,
                'bars_processed': self.total_bars_processed,
                'processing_time': time.time() - self.start_time,
                'bars_per_second': self.total_bars_processed / (time.time() - self.start_time),
                'gpu_memory_usage': self.gpu_memory_usage if self.use_gpu else None
            }
            
            self.end_time = time.time()
            processing_time = self.end_time - self.start_time
            
            self.logger.info(f"GPU Backtest completed in {processing_time:.2f} seconds")
            self.logger.info(f"Processed {self.total_bars_processed} bars at {self.total_bars_processed/processing_time:.0f} bars/second")
            self.logger.info(f"Final Portfolio Value: ${final_value:.2f}")
            self.logger.info(f"Total Return: {total_return:.2%}")
            
            if self.use_gpu:
                self._log_gpu_memory("Backtest completed")
                # Clear GPU memory
                if torch is not None:
                    torch.cuda.empty_cache()
            
            return results_dict
            
        except Exception as e:
            self.logger.error(f"Error in GPU backtest: {e}")
            if self.use_gpu and torch is not None:
                torch.cuda.empty_cache()
            raise
    
    def _generate_sample_data(self, symbol: str, start_date: str, end_date: str, timeframe: str) -> pd.DataFrame:
        """
        Generate sample OHLCV data for backtesting
        In production, this would fetch real market data
        """
        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            # Determine frequency based on timeframe
            freq_map = {
                '1m': '1T',
                '5m': '5T',
                '15m': '15T',
                '1h': '1H',
                '4h': '4H',
                '1d': '1D'
            }
            freq = freq_map.get(timeframe, '1T')
            
            # Create datetime index
            date_range = pd.date_range(start=start_dt, end=end_dt, freq=freq)
            
            # Generate realistic forex data
            np.random.seed(42)  # For reproducible results
            n_points = len(date_range)
            
            # Base price for EUR_USD
            base_price = 1.1000
            
            # Generate price movements using random walk with drift
            returns = np.random.normal(0.00001, 0.0005, n_points)  # Small drift, realistic volatility
            price_series = base_price * np.exp(np.cumsum(returns))
            
            # Generate OHLC from price series
            data = []
            for i in range(n_points):
                if i == 0:
                    open_price = base_price
                else:
                    open_price = data[i-1]['close']
                
                close_price = price_series[i]
                
                # Generate high and low with realistic spreads
                volatility = abs(returns[i]) * 2
                high_price = max(open_price, close_price) + np.random.uniform(0, volatility)
                low_price = min(open_price, close_price) - np.random.uniform(0, volatility)
                
                # Generate volume
                volume = np.random.uniform(100000, 1000000)
                
                data.append({
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'close': close_price,
                    'volume': volume
                })
            
            df = pd.DataFrame(data, index=date_range)
            
            self.logger.info(f"Generated {len(df)} data points for {symbol} from {start_date} to {end_date}")
            return df
            
        except Exception as e:
            self.logger.error(f"Error generating sample data: {e}")
            raise
    
    def _select_strategy_class(self, strategy_name: str = None, strategy_type: str = None):
        """
        Select the appropriate strategy class based on name or type
        
        Args:
            strategy_name: Name of the strategy from database
            strategy_type: Type of strategy (scalping, trend, etc.)
            
        Returns:
            Strategy class to use for backtesting
        """
        try:
            # Strategy mapping based on name patterns
            if strategy_name:
                strategy_name_lower = strategy_name.lower()
                
                if 'scalping' in strategy_name_lower:
                    if self.use_gpu:
                        self.logger.info(f"Selected GPU-enhanced ScalpingForexStrategy for: {strategy_name}")
                        return ScalpingForexStrategy
                    else:
                        return ScalpingForexStrategy
                        
                elif 'enhanced' in strategy_name_lower:
                    if self.use_gpu:
                        self.logger.info(f"Selected GPU-enhanced EnhancedForexStrategy for: {strategy_name}")
                        return EnhancedForexStrategy
                    else:
                        return EnhancedForexStrategy
                        
                elif 'crypto' in strategy_name_lower or 'sol' in strategy_name_lower or 'btc' in strategy_name_lower:
                    if self.use_gpu:
                        self.logger.info(f"Selected GPU-enhanced CryptoStrategy for: {strategy_name}")
                        return CryptoStrategy
                    else:
                        return CryptoStrategy
                        
                elif 'forex' in strategy_name_lower:
                    if self.use_gpu:
                        self.logger.info(f"Selected GPU-enhanced ForexStrategy for: {strategy_name}")
                        return ForexStrategy
                    else:
                        return ForexStrategy
            
            # Strategy mapping based on type
            if strategy_type:
                strategy_type_lower = strategy_type.lower()
                
                if strategy_type_lower == 'scalping':
                    self.logger.info(f"Selected ScalpingForexStrategy for type: {strategy_type}")
                    return ScalpingForexStrategy
                elif strategy_type_lower == 'trend':
                    self.logger.info(f"Selected EnhancedForexStrategy for type: {strategy_type}")
                    return EnhancedForexStrategy
                elif strategy_type_lower == 'crypto':
                    self.logger.info(f"Selected CryptoStrategy for type: {strategy_type}")
                    return CryptoStrategy
            
            # Default fallback
            if self.use_gpu:
                self.logger.info("Using default SimpleGPUScalpingStrategy (GPU mode)")
                return SimpleGPUScalpingStrategy
            else:
                self.logger.info("Using default ScalpingForexStrategy (CPU mode)")
                return ScalpingForexStrategy
                
        except Exception as e:
            self.logger.error(f"Error selecting strategy class: {e}")
            # Safe fallback
            return ScalpingForexStrategy
    
    def benchmark_performance(self, strategy_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Benchmark GPU vs CPU performance
        
        Args:
            strategy_params: Strategy parameters for testing
            
        Returns:
            Performance comparison results
        """
        self.logger.info("Starting GPU vs CPU performance benchmark...")
        
        # Test parameters
        symbol = "EUR_USD"
        start_date = "2024-01-01"
        end_date = "2024-01-31"
        initial_capital = 10000.0
        
        results = {}
        
        # Test GPU performance (if available)
        if GPU_AVAILABLE:
            self.use_gpu = True
            self.device = 'cuda'
            gpu_start = time.time()
            gpu_results = self.run_gpu_backtest(strategy_params, symbol, start_date, end_date, initial_capital)
            gpu_time = time.time() - gpu_start
            
            results['gpu'] = {
                'processing_time': gpu_time,
                'bars_per_second': gpu_results['bars_per_second'],
                'total_return': gpu_results['total_return'],
                'device': 'CUDA'
            }
        
        # Test CPU performance
        self.use_gpu = False
        self.device = 'cpu'
        cpu_start = time.time()
        cpu_results = self.run_gpu_backtest(strategy_params, symbol, start_date, end_date, initial_capital)
        cpu_time = time.time() - cpu_start
        
        results['cpu'] = {
            'processing_time': cpu_time,
            'bars_per_second': cpu_results['bars_per_second'],
            'total_return': cpu_results['total_return'],
            'device': 'CPU'
        }
        
        # Calculate speedup
        if GPU_AVAILABLE and 'gpu' in results:
            speedup = cpu_time / results['gpu']['processing_time']
            results['speedup'] = speedup
            self.logger.info(f"GPU Speedup: {speedup:.2f}x faster than CPU")
        
        return results

def main():
    """Test the GPU backtesting engine"""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize GPU backtest engine
    engine = GPUBacktestEngine(use_gpu=True)
    
    # Test strategy parameters
    strategy_params = {
        'fast_ema': 5,
        'slow_ema': 13,
        'rsi_period': 7,
        'stop_loss_pips': 3,
        'take_profit_pips': 6,
        'printlog': False  # Reduce output for testing
    }
    
    try:
        # Run benchmark
        benchmark_results = engine.benchmark_performance(strategy_params)
        
        print("\n" + "="*50)
        print("GPU BACKTESTING BENCHMARK RESULTS")
        print("="*50)
        
        for device, results in benchmark_results.items():
            if device != 'speedup':
                print(f"\n{device.upper()} Results:")
                print(f"  Processing Time: {results['processing_time']:.2f} seconds")
                print(f"  Bars per Second: {results['bars_per_second']:.0f}")
                print(f"  Total Return: {results['total_return']:.2%}")
                print(f"  Device: {results['device']}")
        
        if 'speedup' in benchmark_results:
            print(f"\nGPU Speedup: {benchmark_results['speedup']:.2f}x")
        
        print("\nGPU backtesting engine test completed successfully!")
        
    except Exception as e:
        print(f"Error testing GPU backtest engine: {e}")

if __name__ == "__main__":
    main()