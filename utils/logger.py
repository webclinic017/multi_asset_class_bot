"""
Logger Module for Trading Bot

This module provides a centralized logging utility for the trading bot,
allowing for easy configuration of log levels, file output, and rotation.
"""

import logging
import logging.handlers
import os
import yaml

def setup_logging(config: dict):
    """
    Sets up the logging configuration for the trading bot.
 
    Args:
        config (dict): Configuration dictionary.
    """
    try:
        log_config = config.get('logging', {})
        log_level_str = log_config.get('level', 'INFO').upper()
        log_file = log_config.get('file', 'logs/trading_bot.log')
        max_file_size_str = log_config.get('max_file_size', '10MB')
        backup_count = log_config.get('backup_count', 5)

        # Convert human-readable size to bytes
        size_multipliers = {'KB': 1024, 'MB': 1024**2, 'GB': 1024**3}
        size_value = float(max_file_size_str[:-2])
        size_unit = max_file_size_str[-2:].upper()
        max_bytes = int(size_value * size_multipliers.get(size_unit, 1))

        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        # Map string log level to logging module constants
        log_level = getattr(logging, log_level_str, logging.INFO)

        # Basic configuration for root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler() # Console output
            ]
        )

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        
        # Add file handler to the root logger
        logging.getLogger().addHandler(file_handler)

        logging.info(f"Logging configured. Level: {log_level_str}, File: {log_file}")

    except FileNotFoundError:
        print(f"Error: Config file not found at {config_path}. Using default logging.")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    except Exception as e:
        print(f"Error setting up logging: {e}. Using default logging.")
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

if __name__ == "__main__":
    # Example Usage
    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {
        'logging': {
            'level': "DEBUG",
            'file': "logs/test_bot.log",
            'max_file_size': "1KB", # Small size for quick rotation test
            'backup_count': 2
        }
    }
    setup_logging(config=dummy_config)

    logger = logging.getLogger("TestLogger")
    logger.debug("This is a debug message.")
    logger.info("This is an info message.")
    logger.warning("This is a warning message.")
    logger.error("This is an error message.")
    logger.critical("This is a critical message.")

    # Simulate writing enough to trigger rotation
    for i in range(50):
        logger.info(f"Writing line {i} to trigger log rotation.")

    print("Check 'logs/' directory for 'test_bot.log' and its backups.")

    # Clean up dummy log files
    # Note: This part assumes the 'logs' directory is created in the current working directory
    # and might need adjustment if the log file path is different.
    log_file_path = dummy_config['logging']['file']
    log_dir = os.path.dirname(log_file_path)
    
    if os.path.exists(log_file_path):
        os.remove(log_file_path)
    for i in range(1, dummy_config['logging']['backup_count'] + 1):
        backup_file = f"{log_file_path}.{i}"
        if os.path.exists(backup_file):
            os.remove(backup_file)
    if log_dir and os.path.exists(log_dir):
        try:
            os.rmdir(log_dir)
        except OSError:
            # Directory might not be empty if other files were created
            pass