"""
Order Manager Module for Trading Bot

This module handles order placement, modification, and cancellation,
interacting with the broker connection.
"""

import logging
import yaml
import os
from datetime import datetime

class OrderManager:
    """
    Manages trading orders, including placement, modification, and cancellation.
    Interacts with the BrokerConnector to send orders to exchanges.
    """

    def __init__(self, broker_connector, config: dict):
        """
        Initialize OrderManager.
 
        Args:
            broker_connector: An instance of BrokerConnector for sending orders.
            config (dict): Configuration dictionary.
        """
        self.broker_connector = broker_connector
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("OrderManager initialized")
        
        self.open_orders = {} # Track open orders: {order_id: order_details}

    def place_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, **kwargs):
        """
        Places a new order.

        Args:
            symbol (str): The trading pair or instrument (e.g., 'EUR_USD', 'BTC/USDT').
            order_type (str): Type of order ('market', 'limit', 'stop', etc.).
            side (str): 'buy' or 'sell'.
            amount (float): The quantity to trade.
            price (float, optional): Price for limit/stop orders. Required for non-market orders.
            **kwargs: Additional parameters for specific order types or brokers.

        Returns:
            dict: Order details from the broker, or None if placement fails.
        """
        self.logger.info(f"Attempting to place {side} {order_type} order for {amount} of {symbol} at price {price}")
        try:
            order_details = self.broker_connector.create_order(
                symbol=symbol,
                order_type=order_type,
                side=side,
                amount=amount,
                price=price,
                **kwargs
            )
            if order_details and 'id' in order_details:
                self.open_orders[order_details['id']] = order_details
                self.logger.info(f"Order placed successfully: {order_details}")
            else:
                self.logger.error(f"Failed to place order for {symbol}. Details: {order_details}")
            return order_details
        except Exception as e:
            self.logger.error(f"Error placing order for {symbol}: {str(e)}")
            return None

    def cancel_order(self, order_id: str, symbol: str = None):
        """
        Cancels an open order.

        Args:
            order_id (str): The ID of the order to cancel.
            symbol (str, optional): The trading pair or instrument. Some brokers require this for cancellation.

        Returns:
            bool: True if cancellation was successful, False otherwise.
        """
        self.logger.info(f"Attempting to cancel order {order_id}")
        if order_id not in self.open_orders:
            self.logger.warning(f"Order {order_id} not found in open orders.")
            return False

        try:
            success = self.broker_connector.cancel_order(order_id, symbol)
            if success:
                del self.open_orders[order_id]
                self.logger.info(f"Order {order_id} cancelled successfully.")
            else:
                self.logger.warning(f"Failed to cancel order {order_id}.")
            return success
        except Exception as e:
            self.logger.error(f"Error cancelling order {order_id}: {str(e)}")
            return False

    def get_order_status(self, order_id: str, symbol: str = None):
        """
        Retrieves the current status of an order.

        Args:
            order_id (str): The ID of the order.
            symbol (str, optional): The trading pair or instrument.

        Returns:
            dict: Current status of the order, or None if not found/error.
        """
        self.logger.info(f"Retrieving status for order {order_id}")
        try:
            status = self.broker_connector.fetch_order_status(order_id, symbol)
            if status:
                self.logger.info(f"Status for order {order_id}: {status['status']}")
                # Update internal tracking if status changed (e.g., filled, canceled)
                if status['status'] in ['closed', 'canceled', 'rejected']:
                    if order_id in self.open_orders:
                        del self.open_orders[order_id]
                else:
                    self.open_orders[order_id] = status # Update with latest status
            else:
                self.logger.warning(f"Could not retrieve status for order {order_id}.")
            return status
        except Exception as e:
            self.logger.error(f"Error fetching order status for {order_id}: {str(e)}")
            return None

    def get_open_orders(self, symbol: str = None):
        """
        Retrieves all currently open orders.

        Args:
            symbol (str, optional): Filter open orders by a specific symbol.

        Returns:
            list: A list of open order dictionaries.
        """
        self.logger.info(f"Fetching open orders for symbol: {symbol if symbol else 'all'}")
        try:
            # It's better to fetch from broker directly to ensure up-to-date status
            # and then update internal open_orders cache.
            broker_open_orders = self.broker_connector.fetch_open_orders(symbol)
            
            # Clear and repopulate internal cache to ensure it's in sync
            self.open_orders = {order['id']: order for order in broker_open_orders}
            
            self.logger.info(f"Retrieved {len(self.open_orders)} open orders.")
            return list(self.open_orders.values())
        except Exception as e:
            self.logger.error(f"Error fetching open orders: {str(e)}")
            return []

if __name__ == "__main__":
    # Example Usage (requires a mock BrokerConnector for testing)
    logging.basicConfig(level=logging.INFO)

    class MockBrokerConnector:
        def __init__(self):
            self.orders = {}
            self.order_id_counter = 1
            self.logger = logging.getLogger("MockBrokerConnector")

        def create_order(self, symbol, order_type, side, amount, price=None, **kwargs):
            order_id = f"mock_order_{self.order_id_counter}"
            self.order_id_counter += 1
            order = {
                'id': order_id,
                'symbol': symbol,
                'type': order_type,
                'side': side,
                'amount': amount,
                'price': price,
                'status': 'open',
                'timestamp': datetime.now().isoformat(),
                **kwargs
            }
            self.orders[order_id] = order
            self.logger.info(f"Mock order created: {order}")
            return order

        def cancel_order(self, order_id, symbol=None):
            if order_id in self.orders:
                self.orders[order_id]['status'] = 'canceled'
                self.logger.info(f"Mock order {order_id} cancelled.")
                return True
            self.logger.warning(f"Mock order {order_id} not found for cancellation.")
            return False

        def fetch_order_status(self, order_id, symbol=None):
            return self.orders.get(order_id)

        def fetch_open_orders(self, symbol=None):
            return [order for order in self.orders.values() if order['status'] == 'open' and (symbol is None or order['symbol'] == symbol)]

    mock_broker = MockBrokerConnector()
    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {} # OrderManager doesn't directly use config for its logic, but needs it for init
    order_manager = OrderManager(mock_broker, config=dummy_config)

    # Test placing a market buy order
    order1 = order_manager.place_order("BTC/USDT", "market", "buy", 0.01)
    if order1:
        print(f"Placed Order 1: {order1}")
        print(f"Open Orders: {order_manager.get_open_orders()}")

    # Test placing a limit sell order
    order2 = order_manager.place_order("EUR_USD", "limit", "sell", 1000, price=1.0850)
    if order2:
        print(f"Placed Order 2: {order2}")
        print(f"Open Orders: {order_manager.get_open_orders()}")

    # Test getting order status
    if order1:
        status1 = order_manager.get_order_status(order1['id'])
        print(f"Status of Order 1: {status1}")

    # Test cancelling an order
    if order2:
        cancel_success = order_manager.cancel_order(order2['id'])
        print(f"Order 2 cancelled: {cancel_success}")
        print(f"Open Orders after cancellation: {order_manager.get_open_orders()}")

    # Simulate filling an order (manual update for mock)
    if order1:
        mock_broker.orders[order1['id']]['status'] = 'filled'
        mock_broker.orders[order1['id']]['filled'] = order1['amount']
        mock_broker.orders[order1['id']]['remaining'] = 0
        status1_after_fill = order_manager.get_order_status(order1['id'])
        print(f"Status of Order 1 after fill: {status1_after_fill}")
        print(f"Open Orders after fill: {order_manager.get_open_orders()}")