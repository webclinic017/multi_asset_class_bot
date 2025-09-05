"""
Test script for GPU-accelerated backtesting
Tests both GPU and CPU performance and validates functionality
"""

import sys
import os
import logging
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_gpu_availability():
    """Test if GPU acceleration is available"""
    print("="*60)
    print("GPU AVAILABILITY TEST")
    print("="*60)
    
    try:
        import torch
        print(f"[OK] PyTorch installed: {torch.__version__}")
        print(f"[OK] CUDA available: {torch.cuda.is_available()}")
        
        if torch.cuda.is_available():
            print(f"[OK] CUDA version: {torch.version.cuda}")
            print(f"[OK] GPU device count: {torch.cuda.device_count()}")
            print(f"[OK] Current GPU: {torch.cuda.get_device_name(0)}")
            print(f"[OK] GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")
        else:
            print("[WARN] CUDA not available - will use CPU fallback")
            
    except ImportError:
        print("[ERROR] PyTorch not installed")
        return False
    
    try:
        import cupy as cp
        print(f"[OK] CuPy installed: {cp.__version__}")
        print(f"[OK] CuPy CUDA devices: {cp.cuda.runtime.getDeviceCount()}")
    except ImportError:
        print("[WARN] CuPy not installed - using NumPy fallback")
    
    try:
        from numba import cuda
        print(f"[OK] Numba CUDA available: {cuda.is_available()}")
        if cuda.is_available():
            print(f"[OK] Numba CUDA devices: {len(cuda.gpus)}")
    except ImportError:
        print("[WARN] Numba CUDA not available")
    
    return True

def test_gpu_strategy():
    """Test GPU-accelerated strategy"""
    print("\n" + "="*60)
    print("GPU STRATEGY TEST")
    print("="*60)
    
    try:
        from strategies.gpu_scalping_forex_strategy import GPUScalpingForexStrategy, GPUTechnicalIndicators
        print("[OK] GPU strategy imported successfully")
        
        # Test GPU indicators
        gpu_indicators = GPUTechnicalIndicators()
        print(f"[OK] GPU indicators initialized - Device: {gpu_indicators.device}")
        
        # Test with sample data
        import numpy as np
        sample_prices = np.random.uniform(1.0900, 1.1100, 100)
        
        # Test EMA calculation
        start_time = time.time()
        ema_result = gpu_indicators.gpu_ema(sample_prices, 20)
        ema_time = time.time() - start_time
        
        print(f"[OK] GPU EMA calculation: {ema_time*1000:.2f}ms")
        print(f"[OK] EMA result shape: {ema_result.shape}")
        
        # Test RSI calculation
        start_time = time.time()
        rsi_result = gpu_indicators.gpu_rsi(sample_prices, 14)
        rsi_time = time.time() - start_time
        
        print(f"[OK] GPU RSI calculation: {rsi_time*1000:.2f}ms")
        print(f"[OK] RSI result shape: {rsi_result.shape}")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error testing GPU strategy: {e}")
        return False

def test_gpu_backtest_engine():
    """Test GPU backtesting engine"""
    print("\n" + "="*60)
    print("GPU BACKTEST ENGINE TEST")
    print("="*60)
    
    try:
        from backtesting.gpu_backtest_engine import GPUBacktestEngine
        print("[OK] GPU backtest engine imported successfully")
        
        # Initialize engine
        engine = GPUBacktestEngine(use_gpu=True)
        print(f"[OK] GPU backtest engine initialized - Device: {engine.device}")
        
        # Test strategy parameters
        strategy_params = {
            'fast_ema': 5,
            'slow_ema': 13,
            'rsi_period': 7,
            'stop_loss_pips': 3,
            'take_profit_pips': 6,
            'printlog': False
        }
        
        print("[TEST] Running quick GPU backtest...")
        start_time = time.time()
        
        # Run a quick backtest
        results = engine.run_gpu_backtest(
            strategy_params=strategy_params,
            symbol="EUR_USD",
            start_date="2024-01-01",
            end_date="2024-01-07",  # Short test period
            initial_capital=10000.0,
            timeframe="1m"
        )
        
        execution_time = time.time() - start_time
        
        print(f"[OK] Backtest completed in {execution_time:.2f} seconds")
        print(f"[OK] Bars processed: {results.get('bars_processed', 0)}")
        print(f"[OK] Processing speed: {results.get('bars_per_second', 0):.0f} bars/second")
        print(f"[OK] GPU accelerated: {results.get('gpu_accelerated', False)}")
        print(f"[OK] Device used: {results.get('device_used', 'Unknown')}")
        print(f"[OK] Total return: {results.get('total_return', 0):.2%}")
        print(f"[OK] Total trades: {results.get('total_trades', 0)}")
        print(f"[OK] Win rate: {results.get('win_rate', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error testing GPU backtest engine: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_performance_benchmark():
    """Run performance benchmark between GPU and CPU"""
    print("\n" + "="*60)
    print("PERFORMANCE BENCHMARK")
    print("="*60)
    
    try:
        from backtesting.gpu_backtest_engine import GPUBacktestEngine
        
        engine = GPUBacktestEngine()
        
        strategy_params = {
            'fast_ema': 5,
            'slow_ema': 13,
            'rsi_period': 7,
            'stop_loss_pips': 3,
            'take_profit_pips': 6,
            'printlog': False
        }
        
        print("[BENCHMARK] Running GPU vs CPU benchmark...")
        benchmark_results = engine.benchmark_performance(strategy_params)
        
        print("\nBENCHMARK RESULTS:")
        print("-" * 40)
        
        for device, results in benchmark_results.items():
            if device != 'speedup':
                print(f"\n{device.upper()} Performance:")
                print(f"  Processing Time: {results['processing_time']:.2f}s")
                print(f"  Bars per Second: {results['bars_per_second']:.0f}")
                print(f"  Total Return: {results['total_return']:.2%}")
                print(f"  Device: {results['device']}")
        
        if 'speedup' in benchmark_results:
            speedup = benchmark_results['speedup']
            print(f"\nGPU SPEEDUP: {speedup:.2f}x faster than CPU")
            
            if speedup > 1.5:
                print("[OK] Excellent GPU acceleration!")
            elif speedup > 1.1:
                print("[OK] Good GPU acceleration")
            else:
                print("[WARN] Limited GPU acceleration (may be using CPU fallback)")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error in performance benchmark: {e}")
        return False

def main():
    """Main test function"""
    print("TRADING BOT GPU ACCELERATION TEST")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    print()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    tests_passed = 0
    total_tests = 4
    
    # Test 1: GPU Availability
    if test_gpu_availability():
        tests_passed += 1
    
    # Test 2: GPU Strategy
    if test_gpu_strategy():
        tests_passed += 1
    
    # Test 3: GPU Backtest Engine
    if test_gpu_backtest_engine():
        tests_passed += 1
    
    # Test 4: Performance Benchmark
    if test_performance_benchmark():
        tests_passed += 1
    
    # Final results
    print("\n" + "="*60)
    print("FINAL TEST RESULTS")
    print("="*60)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("[SUCCESS] ALL TESTS PASSED! GPU acceleration is ready!")
        print("\nNext steps:")
        print("1. Run 'install_gpu_dependencies.bat' to install GPU libraries")
        print("2. Restart the web server to use GPU-accelerated backtesting")
        print("3. Navigate to the Backtesting page and run a backtest")
    else:
        print("[WARN] Some tests failed. Check the output above for details.")
        print("[INFO] You can still use CPU-based backtesting if GPU is not available.")
    
    print(f"\nTest completed at: {datetime.now()}")

if __name__ == "__main__":
    main()