# Test Suite

This directory contains all test files for the Enhanced Trading Bot system.

## Test Files

### Core System Tests
- **`test_enhanced_system.py`** - Comprehensive test suite for the enhanced trading system
  - Tests enhanced dynamic optimizer initialization
  - Tests enhanced genetic optimizer functionality
  - Tests parameter validation and management
  - Tests multi-strategy support
  - Includes performance benchmarks

### Strategy Tests
- **`test_enhanced_forex_strategy.py`** - Tests for the enhanced forex strategy with sentiment analysis
- **`test_crypto_sentiment.py`** - Tests for the enhanced crypto strategy with sentiment analysis integration
- **`test_profitable_strategy.py`** - Tests for profitable trading strategies
- **`test_genetic_optimizer.py`** - Tests for genetic algorithm optimization

### Sentiment Analysis Tests
- **`test_sentiment.py`** - Core sentiment analysis functionality tests
- **`test_sentiment_simple.py`** - Simple sentiment analysis integration tests
- **`test_sentiment_backtest.py`** - Sentiment-enhanced strategy backtesting tests

## Running Tests

### Run All Tests
```bash
# From the multi_asset_bot directory
cd tests
python test_enhanced_system.py
```

### Run Individual Tests
```bash
# Test enhanced system
python tests/test_enhanced_system.py

# Test crypto sentiment integration
python tests/test_crypto_sentiment.py

# Test sentiment analysis
python tests/test_sentiment.py

# Test genetic optimizer
python tests/test_genetic_optimizer.py
```

### Run Specific Test Categories

#### Core System Tests
```bash
python tests/test_enhanced_system.py
```

#### Sentiment Analysis Tests
```bash
python tests/test_sentiment.py
python tests/test_sentiment_simple.py
python tests/test_sentiment_backtest.py
```

#### Strategy Tests
```bash
python tests/test_enhanced_forex_strategy.py
python tests/test_crypto_sentiment.py
python tests/test_profitable_strategy.py
```

## Test Results

All tests should pass with a 100% success rate. The enhanced system test includes:
- 12 unit tests covering all core functionality
- Performance benchmarks
- Integration tests

Expected output:
```
Test Summary
============================================================
Total Tests: 12
Passed: 12
Failed: 0
Errors: 0
Benchmarks: Passed
Success Rate: 100.0%
```

## Test Environment

Tests are designed to run independently and do not require external dependencies beyond the project requirements. Some tests may show warnings if optional components (like news sources) are not configured, but this is expected behavior.