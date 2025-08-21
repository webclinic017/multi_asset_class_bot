"""
Main Script to Run the Trading Bot

This script orchestrates the entire trading bot, including:
- Loading configuration
- Setting up logging
- Initializing data feeds, strategies, execution, and risk management components
- Running backtests or live trading
- Optimizing strategy parameters
"""

import logging
import yaml
import os
import argparse
from dotenv import load_dotenv # Import load_dotenv
import re # Import re for environment variable substitution

# Import modules from our trading bot structure
from utils.logger import setup_logging
from data.data_feed import OANDADataFeed, CCXTDataFeed, IBKRDataFeed
from data.preprocessing import DataPreprocessor
from strategies.forex_strategy import ForexStrategy
from strategies.crypto_strategy import CryptoStrategy
from strategies.futures_strategy import FuturesStrategy
from execution.order_manager import OrderManager
from execution.broker_connect import OANDABrokerConnector, CCXTBrokerConnector, IBKRBrokerConnector
from risk.risk_manager import RiskManager
from backtesting.backtest_engine import BacktestEngine
from optimization.optimizer import Optimizer

# Global logger
logger = logging.getLogger(__name__)

def load_config(config_path='config/config.yaml'):
    """
    Loads the configuration from a YAML file and substitutes environment variables.
    """
    # Load environment variables from .env file
    load_dotenv()

    def env_var_constructor(loader, node):
        """
        YAML constructor for environment variables.
        Looks for ${ENV_VAR_NAME} and replaces it with the environment variable's value.
        """
        value = loader.construct_scalar(node)
        match = re.fullmatch(r'\$\{(\w+)\}', value)
        if match:
            env_var_name = match.group(1)
            env_value = os.getenv(env_var_name)
            if env_value is None:
                logger.warning(f"Environment variable '{env_var_name}' not found. Using None.")
                return None
            # Attempt to convert to int or bool if applicable
            if env_value.lower() == 'true':
                return True
            if env_value.lower() == 'false':
                return False
            if env_value.isdigit():
                return int(env_value)
            try:
                return float(env_value)
            except ValueError:
                return env_value
        return value

    # Add the custom constructor to YAML loader
    yaml.add_constructor('!env', env_var_constructor, Loader=yaml.SafeLoader)
    yaml.add_implicit_resolver('!env', re.compile(r'\$\{\w+\}'))

    try:
        with open(config_path, 'r') as f:
            # Use the custom loader to parse YAML with environment variables
            config = yaml.safe_load(f)
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"Config file not found at {config_path}. Please ensure it exists.")
        exit(1)
    except Exception as e:
        logger.error(f"Error loading config file: {e}")
        exit(1)

def run_backtest_mode(config):
    """Runs the bot in backtesting mode."""
    logger.info("Starting trading bot in BACKTESTING mode.")
    
    # Initialize components
    data_feed = OANDADataFeed(config)
    preprocessor = DataPreprocessor()
    risk_manager = RiskManager(config)
    
    # Initialize backtest engine with new structure
    engine = BacktestEngine(
        data_feed=data_feed,
        preprocessor=preprocessor,
        risk_manager=risk_manager,
        config=config
    )

    # Get symbol info from new config structure
    if 'data' in config and 'symbols' in config['data']:
        symbol_info = config['data']['symbols'][0]
        forex_symbol = symbol_info['name']
        forex_timeframe = symbol_info['timeframe']
        asset_type = symbol_info['type']
    else:
        # Fallback to old structure
        forex_symbol = config['trading']['forex_pairs'][0]
        forex_timeframe = config['trading']['data_timeframe']
        asset_type = 'forex'
    
    try:
        forex_data = engine.load_data(forex_symbol, asset_type, forex_timeframe)
        if forex_data is not None:
            # Get strategy parameters
            strategy_params = config.get('strategy', {}).get('params', {})
            strategy_params['printlog'] = True  # Enable logging to see supply/demand signals
            
            engine.add_strategy('ForexStrategy', **strategy_params)
            results = engine.run()
            
            if results:
                logger.info("=== BACKTEST RESULTS ===")
                logger.info(f"Final Portfolio Value: {results['final_value']:.2f}")
                logger.info(f"Total Return: {results['total_return']:.2f}%")
                logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
                logger.info(f"Max Drawdown: {results['max_drawdown']:.2f}%")
                logger.info(f"Total Trades: {results['total_trades']}")
                logger.info(f"Win Rate: {results['win_rate']:.2f}%")
                logger.info(f"Average Win: {results['avg_win']:.4f}")
                logger.info(f"Average Loss: {results['avg_loss']:.4f}")
        else:
            logger.error(f"Could not load data for {forex_symbol}. Backtest aborted.")
    except NotImplementedError as e:
        logger.error(f"Backtesting error: {e}")
    except Exception as e:
        logger.error(f"An error occurred during backtesting: {e}")

def run_live_trading_mode(config):
    """Runs the bot in live trading mode."""
    logger.info("Starting trading bot in LIVE TRADING mode.")
    
    # Initialize components for live trading
    # Choose broker connector based on configuration or strategy
    broker_type = "oanda" # Example: could be dynamic based on config
    
    broker_connector = None
    if broker_type == "oanda":
        broker_connector = OANDABrokerConnector(config=config)
    elif broker_type == "ccxt":
        broker_connector = CCXTBrokerConnector(config=config, exchange_id='binance') # Or other exchange
    elif broker_type == "ibkr":
        broker_connector = IBKRBrokerConnector(config=config)
    else:
        logger.error(f"Unsupported broker type for live trading: {broker_type}")
        return

    if not broker_connector:
        logger.error("Broker connector could not be initialized.")
        return

    try:
        broker_connector.connect()
        order_manager = OrderManager(broker_connector, config=config)
        risk_manager = RiskManager(config=config)
        
        # Get initial balance
        balance_info = broker_connector.get_balance()
        if balance_info:
            initial_capital = balance_info.get('total', 0.0)
            risk_manager.set_initial_capital(initial_capital)
            logger.info(f"Live trading starting with capital: {initial_capital}")
        else:
            logger.warning("Could not retrieve initial account balance.")

        # Example: Live trading loop (simplified)
        # In a real scenario, this would involve continuous data fetching,
        # strategy signal generation, and order execution.
        
        # For demonstration, let's just get a price and balance
        forex_symbol = config['trading']['forex_pairs'][0]
        current_price = broker_connector.get_current_price(forex_symbol)
        if current_price:
            logger.info(f"Current price for {forex_symbol}: {current_price}")
        
        # This loop would typically run indefinitely, checking for signals
        # while True:
        #     # Fetch latest data
        #     # Generate signals from strategy
        #     # Evaluate trade with risk manager
        #     # Place orders via order manager
        #     time.sleep(config['trading']['live_data_fetch_interval']) # e.g., 60 seconds
        
    except Exception as e:
        logger.critical(f"An error occurred during live trading: {e}")
    finally:
        if broker_connector:
            broker_connector.disconnect()
            logger.info("Disconnected from broker.")

def run_optimization_mode(config):
    """Runs the bot in strategy optimization mode."""
    logger.info("Starting trading bot in OPTIMIZATION mode.")
    
    optimizer = Optimizer(config=config)
    engine = BacktestEngine(config=config) # Re-use BacktestEngine for data loading

    # Example: Optimize ForexStrategy
    forex_symbol = config['trading']['forex_pairs'][0]
    forex_timeframe = config['trading']['data_timeframe']
    
    try:
        forex_data = engine.load_data(forex_symbol, 'forex', forex_timeframe)
        if forex_data is not None:
            # The optimizer expects a backtrader data feed
            optimization_results = optimizer.optimize(ForexStrategy, forex_data) # Optimize ForexStrategy
            logger.info("Optimization Results:")
            print(optimization_results)
            
            # Optionally, save results to a file
            # optimization_results.to_csv('optimization_results.csv')
        else:
            logger.error(f"Could not load data for {forex_symbol}. Optimization aborted.")
    except NotImplementedError as e:
        logger.error(f"Optimization error: {e}")
    except Exception as e:
        logger.error(f"An error occurred during optimization: {e}")

def main():
    parser = argparse.ArgumentParser(description="Trading Bot Main Script")
    parser.add_argument('--mode', type=str, required=True,
                        choices=['backtest', 'live', 'optimize'],
                        help='Operation mode: backtest, live, or optimize')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='Path to the configuration file (default: config/config.yaml)')
    
    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 2: # Error code for missing required arguments
            logger.error("Missing required arguments. Please specify --mode.")
            parser.print_help()
            return # Exit gracefully
        else:
            raise # Re-raise other SystemExit errors

    # Setup logging first
    # Pass the config object directly to setup_logging
    # First, load a minimal config to get logging settings if needed, or default
    temp_config = {}
    try:
        with open(args.config, 'r') as f:
            temp_config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found at {args.config}. Using default logging settings.")
    
    setup_logging(config=temp_config) # Pass the temporary config for logging setup
    
    # Load full configuration with environment variable substitution
    config = load_config(config_path=args.config)

    if args.mode == 'backtest':
        run_backtest_mode(config)
    elif args.mode == 'live':
        run_live_trading_mode(config)
    elif args.mode == 'optimize':
        run_optimization_mode(config)
    else:
        logger.error(f"Invalid mode specified: {args.mode}")
        parser.print_help()

if __name__ == "__main__":
    main()