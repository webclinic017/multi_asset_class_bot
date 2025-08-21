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
    """Runs the bot in live trading mode with dynamic optimization and actual signal generation."""
    import time
    import pandas as pd
    from datetime import datetime, timedelta
    from utils.dynamic_optimizer import DynamicOptimizer
    
    logger.info("Starting trading bot in LIVE TRADING mode with DYNAMIC OPTIMIZATION.")
    
    # Initialize dynamic optimizer
    logger.info("=== INITIALIZING DYNAMIC OPTIMIZATION ===")
    dynamic_optimizer = DynamicOptimizer(
        config_path='config/config.yaml',
        output_dir='output'
    )
    
    # Get optimized parameters (will run optimization if needed)
    optimized_params = dynamic_optimizer.get_optimized_parameters(
        max_age_minutes=5,  # Run optimization if CSV is older than 5 minutes
        auto_optimize=True,  # Automatically run optimization if needed
        generations=40,      # Use 40 generations for optimization
        population=60        # Use population of 60
    )
    
    if optimized_params:
        logger.info("=== OPTIMIZED PARAMETERS LOADED ===")
        for param, value in optimized_params.items():
            logger.info(f"  {param}: {value}")
    else:
        logger.warning("Could not load optimized parameters - using default config values")
    
    # Initialize components for live trading
    broker_type = "oanda"
    
    broker_connector = None
    if broker_type == "oanda":
        broker_connector = OANDABrokerConnector(config=config)
    elif broker_type == "ccxt":
        broker_connector = CCXTBrokerConnector(config=config, exchange_id='binance')
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
        
        # Initialize data feed and preprocessor for live data
        data_feed = OANDADataFeed(config)
        preprocessor = DataPreprocessor()
        
        # Get initial balance
        balance_info = broker_connector.get_balance()
        if balance_info:
            initial_capital = balance_info.get('total', 0.0)
            risk_manager.set_initial_capital(initial_capital)
            logger.info(f"Live trading starting with capital: {initial_capital}")
        else:
            logger.warning("Could not retrieve initial account balance.")

        # Get symbol info from config structure
        if 'data' in config and 'symbols' in config['data']:
            symbol_info = config['data']['symbols'][0]
            forex_symbol = symbol_info['name']
            timeframe = symbol_info['timeframe']
        else:
            # Fallback to old structure
            forex_symbol = config['trading']['forex_pairs'][0]
            timeframe = config['trading']['data_timeframe']
            
        logger.info(f"Starting live trading for {forex_symbol} on {timeframe} timeframe")
        
        # Initialize strategy with parameters (use optimized if available)
        strategy_params = config.get('strategy', {}).get('params', {})
        
        # Override with optimized parameters if available
        if optimized_params:
            logger.info("Using dynamically optimized parameters for live trading")
            strategy_params.update(optimized_params)
        
        logger.info(f"Final strategy parameters for live trading: {strategy_params}")
        
        # Live trading loop
        iteration = 0
        max_iterations = 10  # Limit for demonstration
        
        logger.info("=== STARTING LIVE TRADING LOOP ===")
        logger.info(f"Will run for {max_iterations} iterations with 30-second intervals")
        
        while iteration < max_iterations:
            try:
                iteration += 1
                logger.info(f"\n--- Live Trading Iteration {iteration}/{max_iterations} ---")
                
                # Get current price
                current_price = broker_connector.get_current_price(forex_symbol)
                if current_price:
                    logger.info(f"Current {forex_symbol} price: {current_price}")
                else:
                    logger.warning(f"Could not get current price for {forex_symbol}")
                    time.sleep(30)
                    continue
                
                # Fetch recent historical data for signal generation
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=30)  # Get 30 days of data
                
                logger.info(f"Fetching historical data from {start_time} to {end_time}")
                historical_data = data_feed.get_forex_data(
                    symbol=forex_symbol,
                    timeframe=timeframe,
                    start_date=start_time.strftime('%Y-%m-%d'),
                    end_date=end_time.strftime('%Y-%m-%d')
                )
                
                if historical_data is not None and len(historical_data) > 100:
                    logger.info(f"Retrieved {len(historical_data)} historical data points")
                    
                    # Preprocess the data
                    processed_data = preprocessor.preprocess(historical_data)
                    logger.info(f"Processed data shape: {processed_data.shape}")
                    
                    # Create a simple signal generator based on our strategy logic
                    # Get the latest data point for signal generation
                    latest_data = processed_data.tail(50).copy()  # Use last 50 points for analysis
                    
                    # Simple moving average crossover signal
                    fast_ma = strategy_params.get('fast_length', 10)
                    slow_ma = strategy_params.get('slow_length', 30)
                    
                    if len(latest_data) >= slow_ma:
                        latest_data[f'MA_{fast_ma}'] = latest_data['close'].rolling(fast_ma).mean()
                        latest_data[f'MA_{slow_ma}'] = latest_data['close'].rolling(slow_ma).mean()
                        
                        # Get current values
                        current_fast_ma = latest_data[f'MA_{fast_ma}'].iloc[-1]
                        current_slow_ma = latest_data[f'MA_{slow_ma}'].iloc[-1]
                        prev_fast_ma = latest_data[f'MA_{fast_ma}'].iloc[-2]
                        prev_slow_ma = latest_data[f'MA_{slow_ma}'].iloc[-2]
                        
                        # Generate signals
                        signal = None
                        if current_fast_ma > current_slow_ma and prev_fast_ma <= prev_slow_ma:
                            signal = "BUY"
                            logger.info(f"[BUY SIGNAL] Generated!")
                            logger.info(f"   Fast MA ({fast_ma}): {current_fast_ma:.5f}")
                            logger.info(f"   Slow MA ({slow_ma}): {current_slow_ma:.5f}")
                            logger.info(f"   Current Price: {current_price}")
                        elif current_fast_ma < current_slow_ma and prev_fast_ma >= prev_slow_ma:
                            signal = "SELL"
                            logger.info(f"[SELL SIGNAL] Generated!")
                            logger.info(f"   Fast MA ({fast_ma}): {current_fast_ma:.5f}")
                            logger.info(f"   Slow MA ({slow_ma}): {current_slow_ma:.5f}")
                            logger.info(f"   Current Price: {current_price}")
                        else:
                            logger.info(f"[NO SIGNAL] Fast MA: {current_fast_ma:.5f}, Slow MA: {current_slow_ma:.5f}")
                        
                        # Calculate RSI for additional confirmation
                        if 'rsi' in latest_data.columns:
                            current_rsi = latest_data['rsi'].iloc[-1]
                            logger.info(f"   RSI: {current_rsi:.2f}")
                            
                            # RSI confirmation
                            if signal == "BUY" and current_rsi < 70:
                                logger.info(f"   [RSI CONFIRM] RSI confirms BUY signal (RSI < 70)")
                            elif signal == "SELL" and current_rsi > 30:
                                logger.info(f"   [RSI CONFIRM] RSI confirms SELL signal (RSI > 30)")
                            elif signal:
                                logger.info(f"   [RSI WARNING] RSI does not confirm signal")
                        
                        # Risk management check
                        if signal:
                            position_size = risk_manager.calculate_position_size(
                                current_price,
                                strategy_params.get('stop_loss_percent', 0.01)
                            )
                            logger.info(f"   [POSITION] Calculated position size: {position_size}")
                            
                            # In a real implementation, you would place the order here:
                            # order_manager.place_order(signal, forex_symbol, position_size, current_price)
                            logger.info(f"   [ORDER] Would place {signal} order for {position_size} units at {current_price}")
                    
                else:
                    logger.warning("Insufficient historical data for signal generation")
                
                # Get current account balance
                balance_info = broker_connector.get_balance()
                if balance_info:
                    current_balance = balance_info.get('total', 0.0)
                    logger.info(f"[BALANCE] Current account balance: ${current_balance:,.2f}")
                
                # Wait before next iteration
                if iteration < max_iterations:
                    logger.info(f"[WAIT] Waiting 30 seconds before next iteration...")
                    time.sleep(30)
                    
            except Exception as e:
                logger.error(f"Error in live trading iteration {iteration}: {e}")
                time.sleep(30)
                continue
        
        logger.info("=== LIVE TRADING LOOP COMPLETED ===")
        logger.info("In a real implementation, this would run continuously until stopped.")
        
    except Exception as e:
        logger.critical(f"An error occurred during live trading: {e}")
    finally:
        if broker_connector:
            broker_connector.disconnect()
            logger.info("Disconnected from broker.")

def run_optimization_mode(config):
    """Runs the bot in strategy optimization mode using genetic algorithm."""
    logger.info("Starting trading bot in OPTIMIZATION mode.")
    
    # Use our genetic algorithm optimization instead of the old optimizer
    try:
        # Import our genetic optimizer
        from optimization.genetic_optimizer import GeneticOptimizer
        
        # Create a temporary config file for the genetic optimizer
        import tempfile
        import os
        
        # Create temporary config file
        temp_config_fd, temp_config_path = tempfile.mkstemp(suffix='.yaml', text=True)
        
        try:
            with os.fdopen(temp_config_fd, 'w') as temp_file:
                yaml.dump(config, temp_file, default_flow_style=False, indent=2)
            
            # Initialize genetic optimizer with config file path
            genetic_optimizer = GeneticOptimizer(temp_config_path)
            
            logger.info("Starting genetic algorithm optimization...")
            logger.info(f"Population size: {config.get('optimization', {}).get('population_size', 20)}")
            logger.info(f"Generations: {config.get('optimization', {}).get('generations', 30)}")
            
            # Run optimization
            results = genetic_optimizer.optimize(
                num_generations=config.get('optimization', {}).get('generations', 30),
                sol_per_pop=config.get('optimization', {}).get('population_size', 20),
                mutation_probability=config.get('optimization', {}).get('mutation_probability', 0.15)
            )
            
            best_params = results['best_params']  # Complete parameters
            best_optimized_params = results['best_optimized_params']  # Just optimized ones
            best_fitness = results['best_fitness']
            
            logger.info("=== OPTIMIZATION RESULTS ===")
            logger.info(f"Best fitness score: {best_fitness:.4f}")
            logger.info("Best optimized parameters:")
            for param, value in best_optimized_params.items():
                logger.info(f"  {param}: {value}")
            
            # Export optimization results to CSV
            logger.info("Exporting optimization results to CSV...")
            csv_path = genetic_optimizer.export_results_to_csv("output")
            logger.info(f"Optimization results CSV saved to: {csv_path}")
            
            # Save optimized config
            optimized_config_path = "config/optimized_config.yaml"
            genetic_optimizer.save_optimized_config(best_optimized_params, optimized_config_path)
            logger.info(f"Optimized configuration saved to: {optimized_config_path}")
            
            # Test the optimized parameters
            logger.info("Testing optimized parameters...")
            
            # Initialize components for testing
            data_feed = OANDADataFeed(config)
            preprocessor = DataPreprocessor()
            risk_manager = RiskManager(config)
            
            engine = BacktestEngine(
                data_feed=data_feed,
                preprocessor=preprocessor,
                risk_manager=risk_manager,
                config=config
            )
            
            # Get symbol info
            if 'data' in config and 'symbols' in config['data']:
                symbol_info = config['data']['symbols'][0]
                forex_symbol = symbol_info['name']
                forex_timeframe = symbol_info['timeframe']
                asset_type = symbol_info['type']
            else:
                forex_symbol = config['trading']['forex_pairs'][0]
                forex_timeframe = config['trading']['data_timeframe']
                asset_type = 'forex'
            
            # Load data and test optimized strategy
            forex_data = engine.load_data(forex_symbol, asset_type, forex_timeframe)
            if forex_data is not None:
                # Use the complete parameters (already includes base + optimized)
                test_params = best_params.copy()
                test_params['printlog'] = False  # Disable logging for optimization test
                
                # Add optimized strategy
                engine.add_strategy('ForexStrategy', **test_params)
                test_results = engine.run()
                
                if test_results:
                    logger.info("=== OPTIMIZED STRATEGY RESULTS ===")
                    logger.info(f"Final Portfolio Value: {test_results['final_value']:.2f}")
                    logger.info(f"Total Return: {test_results['total_return']:.2f}%")
                    logger.info(f"Sharpe Ratio: {test_results['sharpe_ratio']:.2f}")
                    logger.info(f"Max Drawdown: {test_results['max_drawdown']:.2f}%")
                    logger.info(f"Total Trades: {test_results['total_trades']}")
                    logger.info(f"Win Rate: {test_results['win_rate']:.2f}%")
                    logger.info(f"Average Win: {test_results['avg_win']:.4f}")
                    logger.info(f"Average Loss: {test_results['avg_loss']:.4f}")
            
        finally:
            # Clean up temporary config file
            if os.path.exists(temp_config_path):
                os.unlink(temp_config_path)
                
    except ImportError as e:
        logger.error(f"Could not import genetic optimizer: {e}")
        logger.error("Please ensure the genetic optimizer is properly installed.")
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