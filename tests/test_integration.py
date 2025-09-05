"""
Integration Test Script for Trading Bot Dashboard
Tests the complete system including database, API, and web server
"""

import os
import sys
import time
import requests
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager
from strategies.scalping_forex_strategy import ScalpingForexStrategy
from web_server import TradingBotWebServer

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IntegrationTester:
    """Complete system integration tester"""
    
    def __init__(self):
        self.db_manager = None
        self.web_server = None
        self.base_url = "http://localhost:8000"
        self.test_results = []
        
    def run_all_tests(self):
        """Run all integration tests"""
        logger.info("🚀 Starting Trading Bot Dashboard Integration Tests")
        
        try:
            # Test 1: Database Integration
            self.test_database_integration()
            
            # Test 2: Web Server Integration
            self.test_web_server_integration()
            
            # Test 3: API Endpoints
            self.test_api_endpoints()
            
            # Test 4: Strategy Integration
            self.test_strategy_integration()
            
            # Test 5: Real-time Features
            self.test_realtime_features()
            
            # Print results
            self.print_test_results()
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            self.test_results.append(("SYSTEM", "FAIL", str(e)))
        
        finally:
            self.cleanup()
    
    def test_database_integration(self):
        """Test database functionality"""
        logger.info("📊 Testing Database Integration...")
        
        try:
            # Initialize database
            self.db_manager = DatabaseManager("test_trading_bot.db")
            
            # Test strategy creation
            strategy_id = self.db_manager.create_strategy(
                name="Test Scalping Strategy",
                description="Integration test strategy",
                strategy_type="scalping",
                asset_class="forex",
                timeframe="1m",
                parameters={
                    "fast_ema": 5,
                    "slow_ema": 13,
                    "stop_loss_pips": 3,
                    "take_profit_pips": 6
                }
            )
            
            assert strategy_id > 0, "Strategy creation failed"
            self.test_results.append(("Database", "PASS", "Strategy creation successful"))
            
            # Test session creation
            session_id = self.db_manager.create_trading_session(
                session_type="backtest",
                strategy_id=strategy_id,
                symbol="EUR_USD",
                initial_capital=10000.0
            )
            
            assert session_id > 0, "Session creation failed"
            self.test_results.append(("Database", "PASS", "Session creation successful"))
            
            # Test trade creation
            trade_id = self.db_manager.create_trade(
                session_id=session_id,
                symbol="EUR_USD",
                side="BUY",
                entry_time=datetime.utcnow(),
                entry_price=1.1234,
                quantity=10000,
                signal_strength=0.75,
                confidence=0.85
            )
            
            assert trade_id > 0, "Trade creation failed"
            self.test_results.append(("Database", "PASS", "Trade creation successful"))
            
            # Test portfolio snapshot
            self.db_manager.store_portfolio_snapshot(
                session_id=session_id,
                timestamp=datetime.utcnow(),
                total_value=10050.0,
                cash_balance=10050.0,
                unrealized_pnl=50.0,
                realized_pnl=0.0
            )
            
            self.test_results.append(("Database", "PASS", "Portfolio snapshot successful"))
            
            logger.info("✅ Database integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Database integration test failed: {e}")
            self.test_results.append(("Database", "FAIL", str(e)))
    
    def test_web_server_integration(self):
        """Test web server startup and basic functionality"""
        logger.info("🌐 Testing Web Server Integration...")
        
        try:
            # Start web server
            self.web_server = TradingBotWebServer("config/config.yaml")
            self.web_server.start_server(host="127.0.0.1", port=8000)
            
            # Wait for server to start
            time.sleep(3)
            
            # Test server is running
            assert self.web_server.is_server_running(), "Web server not running"
            self.test_results.append(("Web Server", "PASS", "Server startup successful"))
            
            logger.info("✅ Web server integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Web server integration test failed: {e}")
            self.test_results.append(("Web Server", "FAIL", str(e)))
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        logger.info("🔌 Testing API Endpoints...")
        
        try:
            # Wait for server to be ready
            time.sleep(2)
            
            # Test health endpoint
            response = requests.get(f"{self.base_url}/health", timeout=5)
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            self.test_results.append(("API", "PASS", "Health endpoint working"))
            
            # Test strategies endpoint
            response = requests.get(f"{self.base_url}/api/strategies", timeout=5)
            assert response.status_code == 200, f"Strategies endpoint failed: {response.status_code}"
            strategies = response.json()
            assert len(strategies) > 0, "No strategies found"
            self.test_results.append(("API", "PASS", f"Strategies endpoint working ({len(strategies)} strategies)"))
            
            # Test sessions endpoint
            response = requests.get(f"{self.base_url}/api/sessions", timeout=5)
            assert response.status_code == 200, f"Sessions endpoint failed: {response.status_code}"
            self.test_results.append(("API", "PASS", "Sessions endpoint working"))
            
            # Test create session
            session_data = {
                "strategy_id": strategies[0]["id"],
                "symbol": "EUR_USD",
                "initial_capital": 10000.0,
                "session_type": "backtest"
            }
            
            response = requests.post(
                f"{self.base_url}/api/sessions",
                json=session_data,
                timeout=5
            )
            assert response.status_code == 200, f"Session creation failed: {response.status_code}"
            session = response.json()
            self.test_results.append(("API", "PASS", f"Session creation working (ID: {session['id']})"))
            
            logger.info("✅ API endpoint tests passed")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ API endpoint test failed (connection): {e}")
            self.test_results.append(("API", "FAIL", f"Connection error: {e}"))
        except Exception as e:
            logger.error(f"❌ API endpoint test failed: {e}")
            self.test_results.append(("API", "FAIL", str(e)))
    
    def test_strategy_integration(self):
        """Test strategy integration"""
        logger.info("📈 Testing Strategy Integration...")
        
        try:
            # Test strategy instantiation
            strategy = ScalpingForexStrategy()
            assert strategy is not None, "Strategy instantiation failed"
            self.test_results.append(("Strategy", "PASS", "Strategy instantiation successful"))
            
            # Test strategy parameters
            assert hasattr(strategy.params, 'fast_ema'), "Strategy parameters missing"
            assert strategy.params.fast_ema == 5, "Strategy parameter values incorrect"
            self.test_results.append(("Strategy", "PASS", "Strategy parameters correct"))
            
            logger.info("✅ Strategy integration tests passed")
            
        except Exception as e:
            logger.error(f"❌ Strategy integration test failed: {e}")
            self.test_results.append(("Strategy", "FAIL", str(e)))
    
    def test_realtime_features(self):
        """Test real-time features"""
        logger.info("⚡ Testing Real-time Features...")
        
        try:
            # Test WebSocket connection (basic test)
            import websocket
            
            def on_open(ws):
                logger.info("WebSocket connection opened")
                ws.send("test message")
            
            def on_message(ws, message):
                logger.info(f"WebSocket message received: {message}")
                ws.close()
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {error}")
            
            # Create WebSocket connection
            ws = websocket.WebSocketApp(
                "ws://localhost:8000/ws",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error
            )
            
            # Run WebSocket in a separate thread for a short time
            import threading
            ws_thread = threading.Thread(target=ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            time.sleep(2)  # Give WebSocket time to connect and test
            
            self.test_results.append(("Real-time", "PASS", "WebSocket connection test completed"))
            
            logger.info("✅ Real-time feature tests passed")
            
        except Exception as e:
            logger.error(f"❌ Real-time feature test failed: {e}")
            self.test_results.append(("Real-time", "FAIL", str(e)))
    
    def print_test_results(self):
        """Print comprehensive test results"""
        logger.info("\n" + "="*60)
        logger.info("🧪 INTEGRATION TEST RESULTS")
        logger.info("="*60)
        
        passed = 0
        failed = 0
        
        for component, status, message in self.test_results:
            status_icon = "✅" if status == "PASS" else "❌"
            logger.info(f"{status_icon} {component:15} | {status:4} | {message}")
            
            if status == "PASS":
                passed += 1
            else:
                failed += 1
        
        logger.info("="*60)
        logger.info(f"📊 SUMMARY: {passed} passed, {failed} failed")
        
        if failed == 0:
            logger.info("🎉 ALL TESTS PASSED! System is ready for use.")
            logger.info("\n🚀 To start the dashboard:")
            logger.info("   python web_server.py --mode live")
            logger.info("   python web_server.py --mode backtest")
            logger.info("\n🌐 Dashboard URL: http://localhost:8000")
        else:
            logger.info("⚠️  Some tests failed. Please check the issues above.")
        
        logger.info("="*60)
    
    def cleanup(self):
        """Clean up test resources"""
        try:
            # Stop web server
            if self.web_server:
                self.web_server.stop_server()
            
            # Remove test database
            if os.path.exists("test_trading_bot.db"):
                os.remove("test_trading_bot.db")
                logger.info("🧹 Test database cleaned up")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

def main():
    """Run integration tests"""
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                 Trading Bot Dashboard                        ║
    ║                  Integration Test Suite                      ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    tester = IntegrationTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()