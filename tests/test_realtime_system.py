"""
Comprehensive Test for Real-time Trading System
Tests all components: enhanced broker, signal logging, strategies, and API endpoints
"""

import unittest
import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock
import pandas as pd
import numpy as np

# Import our components
from backtesting.enhanced_realtime_broker import create_enhanced_realtime_broker, SignalType
from utils.realtime_signal_logger import RealTimeSignalLogger, SignalSource, SignalPriority
from strategies.enhanced_realtime_scalping_1m_strategy import EnhancedRealtimeScalping1MStrategy
from strategies.enhanced_realtime_scalping_5m_strategy import EnhancedRealtimeScalping5MStrategy
from backtesting.realtime_trading_engine import create_realtime_trading_engine
from database.database_manager import DatabaseManager

class TestRealTimeSystem(unittest.TestCase):
    """Test suite for the complete real-time trading system"""
    
    def setUp(self):
        """Set up test environment"""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Create test database manager
        self.db_manager = DatabaseManager("test_realtime.db")
        
        # Create mock WebSocket manager
        self.websocket_manager = Mock()
        self.websocket_manager.broadcast = AsyncMock()
        
        # Create test session
        self.session_id = self.db_manager.create_trading_session(
            "test", 1, "EUR_USD", 10000.0
        )
        
        self.logger.info(f"Test setup completed with session ID: {self.session_id}")
    
    def test_enhanced_broker_creation(self):
        """Test enhanced real-time broker creation and basic functionality"""
        self.logger.info("Testing enhanced broker creation...")
        
        broker = create_enhanced_realtime_broker(10000.0, 0.001, symbol='EUR_USD')
        broker.set_websocket_manager(self.websocket_manager)
        broker.set_database_manager(self.db_manager)
        broker.set_session_id(self.session_id)
        
        # Test basic broker functionality
        self.assertEqual(broker.get_cash(), 10000.0)
        self.assertEqual(broker.get_value(), 10000.0)
        
        # Test signal logging
        signal_id = broker.log_trading_signal(
            SignalType.BUY,
            0.75,
            0.85,
            1.1234,
            {
                "ema_fast": 1.1230,
                "ema_slow": 1.1220,
                "rsi": 35.5
            }
        )
        
        self.assertIsNotNone(signal_id)
        
        # Test broker statistics
        stats = broker.get_broker_stats()
        self.assertIn('total_signals', stats)
        self.assertEqual(stats['total_signals'], 1)
        
        self.logger.info("✅ Enhanced broker test passed")
    
    def test_signal_logger(self):
        """Test real-time signal logger functionality"""
        self.logger.info("Testing signal logger...")
        
        signal_logger = RealTimeSignalLogger(self.websocket_manager, self.db_manager)
        signal_logger.start()
        
        # Log a test signal
        signal_id = signal_logger.log_signal(
            session_id=self.session_id,
            symbol="EUR_USD",
            timeframe="1m",
            signal_type="BUY",
            signal_strength=0.75,
            confidence=0.85,
            price=1.1234,
            strategy_name="TestStrategy",
            indicators={
                "ema_fast": 1.1230,
                "ema_slow": 1.1220,
                "rsi": 35.5
            },
            market_conditions={
                "volatility": 0.0015,
                "trend": "bullish"
            },
            risk_metrics={
                "position_size": 0.02,
                "risk_reward_ratio": 2.5
            },
            priority=SignalPriority.HIGH
        )
        
        self.assertIsNotNone(signal_id)
        
        # Wait for processing
        time.sleep(2)
        
        # Test signal retrieval
        signals = signal_logger.get_signals(session_id=self.session_id)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]['signal_type'], 'BUY')
        
        # Test signal execution marking
        signal_logger.mark_signal_executed(
            signal_id,
            datetime.utcnow(),
            1.1235,
            123
        )
        
        # Test statistics
        stats = signal_logger.get_stats()
        self.assertGreater(stats['total_signals'], 0)
        
        signal_logger.stop()
        self.logger.info("✅ Signal logger test passed")
    
    def test_enhanced_strategies(self):
        """Test enhanced scalping strategies"""
        self.logger.info("Testing enhanced strategies...")
        
        # Test 1M strategy
        strategy_1m = EnhancedRealtimeScalping1MStrategy()
        strategy_1m.session_id = self.session_id
        
        # Test signal generation (mock data)
        with patch.object(strategy_1m, 'dataclose') as mock_close, \
             patch.object(strategy_1m, 'ema_fast') as mock_ema_fast, \
             patch.object(strategy_1m, 'ema_slow') as mock_ema_slow, \
             patch.object(strategy_1m, 'rsi') as mock_rsi, \
             patch.object(strategy_1m, 'atr') as mock_atr:
            
            # Mock indicator values
            mock_close.__getitem__.return_value = 1.1234
            mock_ema_fast.__getitem__.return_value = 1.1230
            mock_ema_slow.__getitem__.return_value = 1.1220
            mock_rsi.__getitem__.return_value = 35.5
            mock_atr.__getitem__.return_value = 0.0015
            
            # Test signal generation
            signals = strategy_1m.generate_enhanced_scalping_signals()
            
            self.assertIn('buy_score', signals)
            self.assertIn('sell_score', signals)
            self.assertIn('indicators', signals)
            self.assertIn('market_conditions', signals)
            self.assertIn('risk_metrics', signals)
        
        # Test 5M strategy
        strategy_5m = EnhancedRealtimeScalping5MStrategy()
        strategy_5m.session_id = self.session_id
        
        # Similar test for 5M strategy
        with patch.object(strategy_5m, 'dataclose') as mock_close, \
             patch.object(strategy_5m, 'ema_fast') as mock_ema_fast, \
             patch.object(strategy_5m, 'ema_slow') as mock_ema_slow, \
             patch.object(strategy_5m, 'rsi') as mock_rsi, \
             patch.object(strategy_5m, 'atr') as mock_atr:
            
            # Mock indicator values
            mock_close.__getitem__.return_value = 1.1234
            mock_ema_fast.__getitem__.return_value = 1.1230
            mock_ema_slow.__getitem__.return_value = 1.1220
            mock_rsi.__getitem__.return_value = 35.5
            mock_atr.__getitem__.return_value = 0.0015
            
            # Test signal generation
            signals = strategy_5m.generate_enhanced_scalping_signals()
            
            self.assertIn('buy_score', signals)
            self.assertIn('sell_score', signals)
            self.assertIn('indicators', signals)
            self.assertIn('market_conditions', signals)
            self.assertIn('risk_metrics', signals)
        
        self.logger.info("✅ Enhanced strategies test passed")
    
    def test_database_operations(self):
        """Test database operations for real-time logging"""
        self.logger.info("Testing database operations...")
        
        # Test signal logging
        signal_id = "test_signal_123"
        self.db_manager.store_realtime_signal_log(
            signal_id=signal_id,
            session_id=self.session_id,
            symbol="EUR_USD",
            timeframe="1m",
            timestamp=datetime.utcnow(),
            signal_type="BUY",
            signal_strength=0.75,
            confidence=0.85,
            price=1.1234,
            source="strategy",
            priority=3,
            strategy_name="TestStrategy",
            indicators={"rsi": 35.5, "ema_fast": 1.1230},
            market_conditions={"volatility": 0.0015},
            risk_metrics={"position_size": 0.02}
        )
        
        # Test signal retrieval
        signals = self.db_manager.get_realtime_signal_logs(session_id=self.session_id)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]['signal_id'], signal_id)
        
        # Test order activity logging
        activity_id = "test_activity_123"
        self.db_manager.store_realtime_order_activity(
            activity_id=activity_id,
            session_id=self.session_id,
            order_id=123,
            symbol="EUR_USD",
            timestamp=datetime.utcnow(),
            order_type="Market",
            side="BUY",
            size=0.02,
            price=1.1234,
            status="completed",
            message="Order executed successfully",
            execution_price=1.1235,
            execution_size=0.02,
            commission=0.001,
            strategy_name="TestStrategy",
            signal_id=signal_id
        )
        
        # Test activity retrieval
        activities = self.db_manager.get_realtime_order_activities(session_id=self.session_id)
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0]['activity_id'], activity_id)
        
        # Test broker stats logging
        self.db_manager.store_realtime_broker_stats(
            session_id=self.session_id,
            timestamp=datetime.utcnow(),
            cash=9950.0,
            portfolio_value=10025.0,
            total_signals=1,
            total_orders=1,
            executions=1,
            buy_signals=1,
            sell_signals=0,
            completed_orders=1,
            rejected_orders=0
        )
        
        # Test stats retrieval
        stats = self.db_manager.get_realtime_broker_stats(session_id=self.session_id)
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0]['total_signals'], 1)
        
        # Test analytics
        signal_analytics = self.db_manager.get_realtime_signal_analytics(session_id=self.session_id)
        self.assertIn('signal_counts', signal_analytics)
        self.assertIn('execution_rate', signal_analytics)
        
        order_analytics = self.db_manager.get_realtime_order_analytics(session_id=self.session_id)
        self.assertIn('status_counts', order_analytics)
        self.assertIn('side_counts', order_analytics)
        
        self.logger.info("✅ Database operations test passed")
    
    def test_trading_engine(self):
        """Test real-time trading engine"""
        self.logger.info("Testing trading engine...")
        
        config = {
            "initial_capital": 10000.0,
            "commission": 0.001,
            "strategy": "EnhancedRealtimeScalping1MStrategy",
            "symbol": "EUR_USD",
            "timeframe": "1m"
        }
        
        engine = create_realtime_trading_engine(
            config, 
            self.session_id, 
            self.websocket_manager, 
            self.db_manager
        )
        
        # Test engine setup
        strategy_params = {
            "fast_length": 5,
            "slow_length": 13,
            "signal_strength_threshold": 0.1,
            "printlog": False
        }
        
        setup_success = engine.setup_engine(
            "EnhancedRealtimeScalping1MStrategy", 
            strategy_params
        )
        self.assertTrue(setup_success)
        
        # Test status retrieval
        status = engine.get_current_status()
        self.assertEqual(status['session_id'], self.session_id)
        self.assertFalse(status['is_running'])
        
        self.logger.info("✅ Trading engine test passed")
    
    def test_integration_flow(self):
        """Test complete integration flow"""
        self.logger.info("Testing complete integration flow...")
        
        # 1. Create enhanced broker
        broker = create_enhanced_realtime_broker(10000.0, 0.001, symbol='EUR_USD')
        broker.set_websocket_manager(self.websocket_manager)
        broker.set_database_manager(self.db_manager)
        broker.set_session_id(self.session_id)
        
        # 2. Create signal logger
        signal_logger = RealTimeSignalLogger(self.websocket_manager, self.db_manager)
        signal_logger.start()
        
        # 3. Log a signal
        signal_id = signal_logger.log_signal(
            session_id=self.session_id,
            symbol="EUR_USD",
            timeframe="1m",
            signal_type="BUY",
            signal_strength=0.8,
            confidence=0.9,
            price=1.1234,
            strategy_name="IntegrationTest",
            indicators={"rsi": 30, "ema_fast": 1.1230},
            priority=SignalPriority.HIGH
        )
        
        # 4. Log broker signal
        broker_signal_id = broker.log_trading_signal(
            SignalType.BUY,
            0.8,
            0.9,
            1.1234,
            {"rsi": 30, "ema_fast": 1.1230}
        )
        
        # 5. Wait for processing
        time.sleep(2)
        
        # 6. Verify data in database
        signals = self.db_manager.get_realtime_signal_logs(session_id=self.session_id)
        self.assertGreater(len(signals), 0)
        
        # 7. Test WebSocket broadcasting was called
        self.websocket_manager.broadcast.assert_called()
        
        # 8. Get broker stats
        stats = broker.get_broker_stats()
        self.assertGreater(stats['total_signals'], 0)
        
        signal_logger.stop()
        self.logger.info("✅ Integration flow test passed")
    
    def tearDown(self):
        """Clean up test environment"""
        try:
            # Clean up test database
            import os
            if os.path.exists("test_realtime.db"):
                os.remove("test_realtime.db")
            self.logger.info("Test cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints for real-time data"""
    
    def setUp(self):
        """Set up API test environment"""
        self.db_manager = DatabaseManager("test_api.db")
        self.session_id = self.db_manager.create_trading_session(
            "test", 1, "EUR_USD", 10000.0
        )
        
        # Add test data
        self.db_manager.store_realtime_signal_log(
            signal_id="api_test_signal",
            session_id=self.session_id,
            symbol="EUR_USD",
            timeframe="1m",
            timestamp=datetime.utcnow(),
            signal_type="BUY",
            signal_strength=0.75,
            confidence=0.85,
            price=1.1234,
            source="strategy",
            priority=3,
            strategy_name="APITestStrategy",
            indicators={"rsi": 35.5}
        )
    
    def test_signal_retrieval_logic(self):
        """Test signal retrieval logic (simulating API endpoint)"""
        signals = self.db_manager.get_realtime_signal_logs(session_id=self.session_id)
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0]['signal_type'], 'BUY')
        
        # Test filtering
        buy_signals = self.db_manager.get_realtime_signal_logs(
            session_id=self.session_id, 
            signal_type='BUY'
        )
        self.assertEqual(len(buy_signals), 1)
        
        sell_signals = self.db_manager.get_realtime_signal_logs(
            session_id=self.session_id, 
            signal_type='SELL'
        )
        self.assertEqual(len(sell_signals), 0)
    
    def tearDown(self):
        """Clean up API test environment"""
        import os
        if os.path.exists("test_api.db"):
            os.remove("test_api.db")

def run_comprehensive_test():
    """Run comprehensive test suite"""
    print("🚀 Starting Comprehensive Real-time Trading System Test")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test cases
    suite.addTest(unittest.makeSuite(TestRealTimeSystem))
    suite.addTest(unittest.makeSuite(TestAPIEndpoints))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED! Real-time trading system is working correctly.")
        print(f"✅ Ran {result.testsRun} tests successfully")
    else:
        print("❌ SOME TESTS FAILED!")
        print(f"❌ Failures: {len(result.failures)}")
        print(f"❌ Errors: {len(result.errors)}")
        
        for test, error in result.failures + result.errors:
            print(f"❌ {test}: {error}")
    
    print("=" * 60)
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)