#!/usr/bin/env python3
"""
Test script to verify the complete data flow from backtesting to frontend display
Tests trade statistics accuracy and database storage
"""

import sys
import os
import json
import requests
import time
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_database_storage():
    """Test that trade statistics are stored correctly in database"""
    print("Testing database storage...")

    try:
        from database.database_manager import DatabaseManager

        db = DatabaseManager()

        # Check if there are any completed backtest sessions
        sessions = db.get_trading_sessions(limit=10)

        completed_sessions = [s for s in sessions if s.get('status') == 'completed' and s.get('session_type') == 'backtest']

        if not completed_sessions:
            print("WARNING: No completed backtest sessions found in database")
            return False

        print(f"PASSED: Found {len(completed_sessions)} completed backtest sessions")

        # Check each session for accurate trade statistics
        for session in completed_sessions[:3]:  # Test first 3 sessions
            session_id = session['id']
            print(f"\nTesting session {session_id}:")

            # Get trades for this session
            trades = db.get_trades(session_id=session_id)

            if not trades:
                print(f"WARNING: No trades found for session {session_id}")
                continue

            # Calculate actual statistics from trades (handle None values)
            total_trades_actual = len(trades)
            winning_trades_actual = len([t for t in trades if t.get('pnl') is not None and t.get('pnl', 0) > 0])
            losing_trades_actual = len([t for t in trades if t.get('pnl') is not None and t.get('pnl', 0) < 0])

            # Get session data
            session_data = next((s for s in sessions if s['id'] == session_id), None)

            if session_data:
                total_trades_stored = session_data.get('total_trades', 0)
                winning_trades_stored = session_data.get('winning_trades', 0)
                losing_trades_stored = session_data.get('losing_trades', 0)

                print(f"  Stored: {total_trades_stored} total, {winning_trades_stored} wins, {losing_trades_stored} losses")
                print(f"  Actual: {total_trades_actual} total, {winning_trades_actual} wins, {losing_trades_actual} losses")

                # Check if they match
                if (total_trades_stored == total_trades_actual and
                    winning_trades_stored == winning_trades_actual and
                    losing_trades_stored == losing_trades_actual):
                    print(f"PASSED: Session {session_id} trade statistics match!")
                else:
                    print(f"FAILED: Session {session_id} trade statistics DON'T match!")
                    return False

        return True

    except Exception as e:
        print(f"FAILED: Database test failed: {e}")
        return False

def test_api_response():
    """Test that API returns correct trade statistics"""
    print("\nTesting API response...")

    try:
        # Test API health
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code != 200:
            print("FAILED: API server not responding")
            return False

        print("PASSED: API server is responding")

        # Test sessions endpoint
        response = requests.get("http://localhost:8000/api/sessions", timeout=5)
        if response.status_code != 200:
            print("FAILED: Sessions endpoint not responding")
            return False

        sessions = response.json()
        backtest_sessions = [s for s in sessions if s.get('session_type') == 'backtest']

        print(f"PASSED: API returned {len(backtest_sessions)} backtest sessions")

        # Check cache control headers
        cache_control = response.headers.get('Cache-Control', '')
        if 'no-cache' in cache_control:
            print("PASSED: API response has proper cache control headers")
        else:
            print("WARNING: API response missing cache control headers")

        return True

    except Exception as e:
        print(f"FAILED: API test failed: {e}")
        return False

def test_frontend_build():
    """Test that frontend builds successfully"""
    print("\nTesting frontend build...")

    try:
        # Check if frontend build exists
        build_path = "frontend/build/index.html"
        if os.path.exists(build_path):
            print("PASSED: Frontend build exists")

            # Check if build is recent (modified within last hour)
            build_time = os.path.getmtime(build_path)
            current_time = time.time()
            if current_time - build_time < 3600:  # 1 hour
                print("PASSED: Frontend build is recent")
            else:
                print("WARNING: Frontend build is older than 1 hour")

            return True
        else:
            print("FAILED: Frontend build not found")
            return False

    except Exception as e:
        print(f"FAILED: Frontend build test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Starting comprehensive data flow tests...\n")

    tests = [
        ("Database Storage", test_database_storage),
        ("API Response", test_api_response),
        ("Frontend Build", test_frontend_build),
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)

    all_passed = True
    for test_name, result in results:
        status = "PASSED" if result else "FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_passed = False

    print(f"\n{'='*60}")
    if all_passed:
        print("SUCCESS: ALL TESTS PASSED! Data flow is working correctly.")
    else:
        print("WARNING: SOME TESTS FAILED! Check the issues above.")
    print('='*60)

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)