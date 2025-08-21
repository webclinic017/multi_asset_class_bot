"""
Risk Manager Module for Trading Bot

This module handles risk management aspects such as position sizing,
drawdown limits, and overall portfolio risk.
"""

import logging
import yaml
import os

class RiskManager:
    """
    Manages trading risk, including position sizing, drawdown limits,
    and overall portfolio exposure.
    """

    def __init__(self, config: dict):
        """
        Initialize RiskManager.
 
        Args:
            config (dict): Configuration dictionary.
        """
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("RiskManager initialized")
        
        # Support both old and new config structures
        if 'trading' in self.config:
            trading_config = self.config['trading']
        elif 'risk' in self.config:
            trading_config = self.config['risk']
        else:
            # Use defaults if no trading/risk config found
            trading_config = {
                'risk_per_trade': 0.01,
                'max_drawdown_limit': 0.20,
                'max_concurrent_positions': 5,
                'position_sizing_method': 'fixed_fraction',
                'fixed_fraction': 0.02
            }
            self.logger.warning("No trading/risk config found, using defaults")
            
        self.risk_per_trade = trading_config.get('risk_per_trade', 0.01)
        self.max_drawdown_limit = trading_config.get('max_drawdown_limit', 0.20)
        self.max_concurrent_positions = trading_config.get('max_concurrent_positions', 5)
        self.position_sizing_method = trading_config.get('position_sizing_method', 'fixed_fraction')
        self.fixed_fraction = trading_config.get('fixed_fraction', 0.02)

        self.initial_capital = None # Will be set by backtesting engine or live trading
        self.current_capital = None
        self.peak_capital = None

    def set_initial_capital(self, capital: float):
        """Sets the initial capital for risk management calculations."""
        self.initial_capital = capital
        self.current_capital = capital
        self.peak_capital = capital
        self.logger.info(f"Initial capital set to: {self.initial_capital}")

    def update_capital(self, new_capital: float):
        """Updates the current capital and peak capital."""
        self.current_capital = new_capital
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        self.logger.debug(f"Capital updated to: {self.current_capital}, Peak capital: {self.peak_capital}")

    def calculate_position_size(self, current_price: float, stop_loss_price: float, account_balance: float) -> float:
        """
        Calculates the appropriate position size based on the configured method.

        Args:
            current_price (float): Current market price of the instrument.
            stop_loss_price (float): The price at which the stop loss would be triggered.
            account_balance (float): Current total account balance.

        Returns:
            float: The calculated quantity (number of units) for the position.
        """
        if self.position_sizing_method == "fixed_fraction":
            return self._fixed_fraction_sizing(current_price, stop_loss_price, account_balance)
        elif self.position_sizing_method == "kelly_criterion":
            self.logger.warning("Kelly Criterion not implemented. Falling back to fixed_fraction.")
            return self._fixed_fraction_sizing(current_price, stop_loss_price, account_balance)
        elif self.position_sizing_method == "volatility_adjusted":
            self.logger.warning("Volatility Adjusted sizing not implemented. Falling back to fixed_fraction.")
            return self._fixed_fraction_sizing(current_price, stop_loss_price, account_balance)
        else:
            self.logger.warning(f"Unknown position sizing method: {self.position_sizing_method}. Falling back to fixed_fraction.")
            return self._fixed_fraction_sizing(current_price, stop_loss_price, account_balance)

    def _fixed_fraction_sizing(self, current_price: float, stop_loss_price: float, account_balance: float) -> float:
        """
        Calculates position size using the fixed fraction method.
        
        Risk per trade = Account Balance * Risk Percentage
        Loss per share/unit = abs(Entry Price - Stop Loss Price)
        Position Size (units) = Risk per trade / Loss per share/unit
        """
        if stop_loss_price == current_price:
            self.logger.warning("Stop loss price is equal to current price. Cannot calculate position size.")
            return 0.0

        risk_amount = account_balance * self.risk_per_trade
        loss_per_unit = abs(current_price - stop_loss_price)
        
        if loss_per_unit == 0:
            self.logger.warning("Loss per unit is zero. Cannot calculate position size.")
            return 0.0

        position_size_units = risk_amount / loss_per_unit
        
        self.logger.info(f"Calculated position size (fixed fraction): {position_size_units:.2f} units")
        return position_size_units

    def check_drawdown(self) -> bool:
        """
        Checks if the current drawdown exceeds the maximum allowed limit.

        Returns:
            bool: True if drawdown limit is exceeded, False otherwise.
        """
        if self.initial_capital is None or self.current_capital is None or self.peak_capital is None:
            self.logger.warning("Capital not set, cannot check drawdown.")
            return False

        if self.peak_capital > 0:
            drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
            self.logger.debug(f"Current Drawdown: {drawdown:.2%}, Max Drawdown Limit: {self.max_drawdown_limit:.2%}")
            if drawdown >= self.max_drawdown_limit:
                self.logger.critical(f"MAX DRAWDOWN LIMIT EXCEEDED! Current Drawdown: {drawdown:.2%}")
                return True
        return False

    def check_max_concurrent_positions(self, current_open_positions: int) -> bool:
        """
        Checks if adding a new position would exceed the maximum allowed concurrent positions.

        Args:
            current_open_positions (int): The number of currently open positions.

        Returns:
            bool: True if adding a new position would exceed the limit, False otherwise.
        """
        if current_open_positions >= self.max_concurrent_positions:
            self.logger.warning(f"Max concurrent positions ({self.max_concurrent_positions}) reached. Cannot open new position.")
            return True
        return False

    def evaluate_trade(self, current_price: float, stop_loss_price: float, account_balance: float, current_open_positions: int) -> (bool, float):
        """
        Evaluates a potential trade based on risk management rules.

        Args:
            current_price (float): Current market price.
            stop_loss_price (float): Proposed stop loss price.
            account_balance (float): Current account balance.
            current_open_positions (int): Number of currently open positions.

        Returns:
            tuple: (can_trade: bool, position_size: float)
                   can_trade is True if the trade is allowed, False otherwise.
                   position_size is the calculated size if allowed, 0 otherwise.
        """
        self.logger.info("Evaluating potential trade...")

        if self.check_drawdown():
            self.logger.warning("Trade rejected: Max drawdown limit exceeded.")
            return False, 0.0

        if self.check_max_concurrent_positions(current_open_positions):
            self.logger.warning("Trade rejected: Max concurrent positions reached.")
            return False, 0.0
        
        if stop_loss_price is None:
            self.logger.warning("Trade rejected: Stop loss price not provided for position sizing.")
            return False, 0.0

        position_size = self.calculate_position_size(current_price, stop_loss_price, account_balance)
        
        if position_size <= 0:
            self.logger.warning("Trade rejected: Calculated position size is zero or negative.")
            return False, 0.0
        
        # Ensure the calculated position size doesn't exceed available capital
        if (position_size * current_price) > account_balance:
            self.logger.warning(f"Trade rejected: Position value ({position_size * current_price:.2f}) exceeds account balance ({account_balance:.2f}).")
            return False, 0.0

        self.logger.info(f"Trade approved. Calculated position size: {position_size:.2f} units.")
        return True, position_size

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {
        'trading': {
            'risk_per_trade': 0.01,
            'max_drawdown_limit': 0.10,
            'max_concurrent_positions': 2,
            'position_sizing_method': "fixed_fraction",
            'fixed_fraction': 0.02
        }
    }
    risk_manager = RiskManager(config=dummy_config)
    risk_manager.set_initial_capital(10000.0)

    print("\n--- Testing Position Sizing ---")
    current_price = 100.0
    stop_loss_price = 99.0 # 1% risk
    account_balance = 10000.0
    
    can_trade, size = risk_manager.evaluate_trade(current_price, stop_loss_price, account_balance, 0)
    print(f"Can trade: {can_trade}, Position Size: {size:.2f}")

    current_price = 100.0
    stop_loss_price = 99.5 # 0.5% risk
    can_trade, size = risk_manager.evaluate_trade(current_price, stop_loss_price, account_balance, 0)
    print(f"Can trade: {can_trade}, Position Size: {size:.2f}")

    print("\n--- Testing Drawdown Limit ---")
    risk_manager.update_capital(9500.0) # 5% drawdown
    print(f"Drawdown check (5%): {risk_manager.check_drawdown()}")
    risk_manager.update_capital(8900.0) # 11% drawdown (exceeds 10%)
    print(f"Drawdown check (11%): {risk_manager.check_drawdown()}")

    print("\n--- Testing Max Concurrent Positions ---")
    risk_manager.set_initial_capital(10000.0) # Reset capital for this test
    risk_manager.update_capital(10000.0)
    
    print(f"Check positions (0 open): {risk_manager.check_max_concurrent_positions(0)}")
    print(f"Check positions (1 open): {risk_manager.check_max_concurrent_positions(1)}")
    print(f"Check positions (2 open): {risk_manager.check_max_concurrent_positions(2)}") # Should be True

    print("\n--- Testing Full Trade Evaluation ---")
    risk_manager.set_initial_capital(10000.0)
    risk_manager.update_capital(10000.0)

    # Scenario 1: Allowed trade
    can_trade, size = risk_manager.evaluate_trade(100.0, 99.0, 10000.0, 0)
    print(f"Scenario 1 (Allowed): Can trade: {can_trade}, Size: {size:.2f}")

    # Scenario 2: Max drawdown exceeded
    risk_manager.update_capital(8000.0) # 20% drawdown
    can_trade, size = risk_manager.evaluate_trade(100.0, 99.0, 8000.0, 0)
    print(f"Scenario 2 (Drawdown Exceeded): Can trade: {can_trade}, Size: {size:.2f}")

    # Scenario 3: Max concurrent positions reached
    risk_manager.set_initial_capital(10000.0) # Reset
    risk_manager.update_capital(10000.0)
    can_trade, size = risk_manager.evaluate_trade(100.0, 99.0, 10000.0, 2) # 2 open positions
    print(f"Scenario 3 (Max Positions): Can trade: {can_trade}, Size: {size:.2f}")

    # No need to clean up dummy config file as it's not created