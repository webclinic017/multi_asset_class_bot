"""
Broker Connection Module for Trading Bot

This module handles API connections to various brokers/exchanges
like OANDA, CCXT (for crypto), and Interactive Brokers.
"""

import logging
import yaml
import ccxt
import oandapyV20
from oandapyV20.exceptions import V20Error
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
import threading
import time

class BrokerConnector:
    """Base class for broker connection functionality"""

    def __init__(self, config: dict):
        """
        Initialize broker connector with configuration.

        Args:
            config (dict): Configuration dictionary.
        """
        self.config = config
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing BrokerConnector")

    def connect(self):
        """Establishes connection to the broker."""
        raise NotImplementedError("Subclasses must implement connect")

    def disconnect(self):
        """Closes connection to the broker."""
        raise NotImplementedError("Subclasses must implement disconnect")

    def get_balance(self, currency: str = None):
        """
        Retrieves account balance.

        Args:
            currency (str, optional): Specific currency to get balance for.

        Returns:
            dict: Dictionary of balances or specific currency balance.
        """
        raise NotImplementedError("Subclasses must implement get_balance")

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, **kwargs):
        """
        Creates and places an order.

        Args:
            symbol (str): The trading pair or instrument.
            order_type (str): Type of order ('market', 'limit', 'stop', etc.).
            side (str): 'buy' or 'sell'.
            amount (float): The quantity to trade.
            price (float, optional): Price for limit/stop orders.

        Returns:
            dict: Order details.
        """
        raise NotImplementedError("Subclasses must implement create_order")

    def cancel_order(self, order_id: str, symbol: str = None):
        """
        Cancels an open order.

        Args:
            order_id (str): The ID of the order to cancel.
            symbol (str, optional): The trading pair or instrument.

        Returns:
            bool: True if cancellation was successful, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement cancel_order")

    def fetch_order_status(self, order_id: str, symbol: str = None):
        """
        Fetches the current status of an order.

        Args:
            order_id (str): The ID of the order.
            symbol (str, optional): The trading pair or instrument.

        Returns:
            dict: Current status of the order.
        """
        raise NotImplementedError("Subclasses must implement fetch_order_status")

    def fetch_open_orders(self, symbol: str = None):
        """
        Fetches all currently open orders.

        Args:
            symbol (str, optional): Filter open orders by a specific symbol.

        Returns:
            list: A list of open order dictionaries.
        """
        raise NotImplementedError("Subclasses must implement fetch_open_orders")

    def get_current_price(self, symbol: str):
        """
        Retrieves the current market price for a symbol.

        Args:
            symbol (str): The trading pair or instrument.

        Returns:
            float: Current market price.
        """
        raise NotImplementedError("Subclasses must implement get_current_price")


class OANDABrokerConnector(BrokerConnector):
    """OANDA broker connection implementation"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.account_id = self.config['oanda']['account_id']
        self.access_token = self.config['oanda']['access_token']
        self.practice = self.config['oanda']['practice']
        
        self.client = oandapyV20.API(
            access_token=self.access_token,
            environment='practice' if self.practice else 'live'
        )
        self.logger.info("OANDABrokerConnector initialized")

    def connect(self):
        self.logger.info("OANDA connection is stateless, no explicit 'connect' needed.")
        pass

    def disconnect(self):
        self.logger.info("OANDA connection is stateless, no explicit 'disconnect' needed.")
        pass

    def get_balance(self, currency: str = None):
        try:
            import oandapyV20.endpoints.accounts as accounts
            r = accounts.AccountSummary(self.account_id)
            self.client.request(r)
            summary = r.response['account']
            balance = float(summary['balance'])
            self.logger.info(f"OANDA Account Balance: {balance}")
            return {'total': balance, 'currency': summary['currency']}
        except V20Error as e:
            self.logger.error(f"OANDA API Error getting balance: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting OANDA balance: {str(e)}")
            return None

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, **kwargs):
        import oandapyV20.endpoints.orders as orders
        
        instrument = symbol
        units = str(int(amount) if side == 'buy' else int(-amount)) # OANDA uses negative units for sell
        
        order_body = {
            "order": {
                "units": units,
                "instrument": instrument,
                "type": order_type,
                "timeInForce": "FOK" if order_type == "market" else "GTC", # Fill or Kill for market, Good Till Cancel for others
                "positionFill": "DEFAULT"
            }
        }
        
        if order_type == "limit" and price is not None:
            order_body["order"]["price"] = str(price)
        elif order_type == "stop" and price is not None:
            order_body["order"]["price"] = str(price)
            order_body["order"]["triggerCondition"] = "DEFAULT" # Or other conditions like "BID", "ASK"
        
        # Add stop loss and take profit if provided in kwargs
        if 'stop_loss_price' in kwargs:
            order_body["order"]["stopLossOnFill"] = {"price": str(kwargs['stop_loss_price'])}
        if 'take_profit_price' in kwargs:
            order_body["order"]["takeProfitOnFill"] = {"price": str(kwargs['take_profit_price'])}

        try:
            r = orders.OrderCreate(self.account_id, data=order_body)
            self.client.request(r)
            trade_id = r.response['orderFillTransaction']['tradeID']
            order_id = r.response['orderFillTransaction']['orderID']
            self.logger.info(f"OANDA Order created: {r.response}")
            return {
                'id': order_id,
                'trade_id': trade_id,
                'symbol': instrument,
                'type': order_type,
                'side': side,
                'amount': amount,
                'price': price,
                'status': 'filled' if order_type == 'market' else 'open', # Market orders are usually filled immediately
                'info': r.response
            }
        except V20Error as e:
            self.logger.error(f"OANDA API Error creating order: {e.msg} ({e.code})")
            return None
        except Exception as e:
            self.logger.error(f"Error creating OANDA order: {str(e)}")
            return None

    def cancel_order(self, order_id: str, symbol: str = None):
        import oandapyV20.endpoints.orders as orders
        try:
            r = orders.OrderCancel(self.account_id, orderID=order_id)
            self.client.request(r)
            self.logger.info(f"OANDA Order {order_id} cancelled: {r.response}")
            return True
        except V20Error as e:
            self.logger.error(f"OANDA API Error cancelling order {order_id}: {e.msg} ({e.code})")
            return False
        except Exception as e:
            self.logger.error(f"Error cancelling OANDA order {order_id}: {str(e)}")
            return False

    def fetch_order_status(self, order_id: str, symbol: str = None):
        import oandapyV20.endpoints.orders as orders
        try:
            r = orders.OrderDetails(self.account_id, orderID=order_id)
            self.client.request(r)
            order_info = r.response['order']
            status = 'open'
            if 'state' in order_info:
                if order_info['state'] == 'FILLED':
                    status = 'filled'
                elif order_info['state'] == 'CANCELLED':
                    status = 'canceled'
                elif order_info['state'] == 'PENDING':
                    status = 'open'
            
            return {
                'id': order_info['id'],
                'symbol': order_info['instrument'],
                'type': order_info['type'],
                'side': 'buy' if float(order_info['units']) > 0 else 'sell',
                'amount': abs(float(order_info['units'])),
                'price': float(order_info.get('price', 0)),
                'status': status,
                'info': order_info
            }
        except V20Error as e:
            self.logger.error(f"OANDA API Error fetching order status {order_id}: {e.msg} ({e.code})")
            return None
        except Exception as e:
            self.logger.error(f"Error fetching OANDA order status {order_id}: {str(e)}")
            return None

    def fetch_open_orders(self, symbol: str = None):
        import oandapyV20.endpoints.orders as orders
        try:
            r = orders.OrdersPending(self.account_id)
            self.client.request(r)
            open_orders = []
            for order_info in r.response['orders']:
                if symbol is None or order_info['instrument'] == symbol:
                    open_orders.append({
                        'id': order_info['id'],
                        'symbol': order_info['instrument'],
                        'type': order_info['type'],
                        'side': 'buy' if float(order_info['units']) > 0 else 'sell',
                        'amount': abs(float(order_info['units'])),
                        'price': float(order_info.get('price', 0)),
                        'status': 'open',
                        'info': order_info
                    })
            self.logger.info(f"Fetched {len(open_orders)} open OANDA orders.")
            return open_orders
        except V20Error as e:
            self.logger.error(f"OANDA API Error fetching open orders: {e.msg} ({e.code})")
            return []
        except Exception as e:
            self.logger.error(f"Error fetching open OANDA orders: {str(e)}")
            return []

    def get_current_price(self, symbol: str):
        import oandapyV20.endpoints.pricing as pricing
        try:
            params = {"instruments": symbol}
            r = pricing.PricingInfo(accountID=self.account_id, params=params)
            self.client.request(r)
            price_info = r.response['prices'][0]
            bid = float(price_info['bids'][0]['price'])
            ask = float(price_info['asks'][0]['price'])
            mid = (bid + ask) / 2
            self.logger.info(f"Current OANDA price for {symbol}: Bid={bid}, Ask={ask}, Mid={mid}")
            return mid
        except V20Error as e:
            self.logger.error(f"OANDA API Error getting current price for {symbol}: {e.msg} ({e.code})")
            return None
        except Exception as e:
            self.logger.error(f"Error getting current OANDA price for {symbol}: {str(e)}")
            return None


class CCXTBrokerConnector(BrokerConnector):
    """CCXT broker connection implementation for crypto exchanges"""

    def __init__(self, config: dict, exchange_id='binance'):
        super().__init__(config)
        self.exchange_id = exchange_id
        self.exchange = None
        self.logger.info(f"CCXTBrokerConnector initialized for {exchange_id}")

    def connect(self):
        try:
            exchange_config = self.config['ccxt']
            exchange_class = getattr(ccxt, self.exchange_id)
            self.exchange = exchange_class({
                'apiKey': exchange_config['api_key'],
                'secret': exchange_config['secret'],
                'password': exchange_config.get('password'),
                'enableRateLimit': True,
            })
            self.exchange.load_markets()
            self.logger.info(f"Connected to CCXT exchange: {self.exchange_id}")
        except Exception as e:
            self.logger.error(f"Error connecting to CCXT exchange {self.exchange_id}: {str(e)}")
            self.exchange = None
            raise

    def disconnect(self):
        self.logger.info(f"CCXT exchange {self.exchange_id} connection is stateless, no explicit 'disconnect' needed.")
        pass

    def get_balance(self, currency: str = None):
        if not self.exchange:
            self.logger.error("CCXT exchange not connected.")
            return None
        try:
            balance = self.exchange.fetch_balance()
            if currency:
                return balance['free'].get(currency)
            return balance
        except Exception as e:
            self.logger.error(f"Error getting CCXT balance: {str(e)}")
            return None

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, **kwargs):
        if not self.exchange:
            self.logger.error("CCXT exchange not connected.")
            return None
        try:
            order = self.exchange.create_order(symbol, order_type, side, amount, price, params=kwargs)
            self.logger.info(f"CCXT Order created: {order}")
            return order
        except Exception as e:
            self.logger.error(f"Error creating CCXT order: {str(e)}")
            return None

    def cancel_order(self, order_id: str, symbol: str = None):
        if not self.exchange:
            self.logger.error("CCXT exchange not connected.")
            return False
        try:
            response = self.exchange.cancel_order(order_id, symbol)
            self.logger.info(f"CCXT Order {order_id} cancelled: {response}")
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling CCXT order {order_id}: {str(e)}")
            return False

    def fetch_order_status(self, order_id: str, symbol: str = None):
        if not self.exchange:
            self.logger.error("CCXT exchange not connected.")
            return None
        try:
            order = self.exchange.fetch_order(order_id, symbol)
            self.logger.info(f"CCXT Order status for {order_id}: {order['status']}")
            return order
        except Exception as e:
            self.logger.error(f"Error fetching CCXT order status {order_id}: {str(e)}")
            return None

    def fetch_open_orders(self, symbol: str = None):
        if not self.exchange:
            self.logger.error("CCXT exchange not connected.")
            return []
        try:
            open_orders = self.exchange.fetch_open_orders(symbol)
            self.logger.info(f"Fetched {len(open_orders)} open CCXT orders.")
            return open_orders
        except Exception as e:
            self.logger.error(f"Error fetching open CCXT orders: {str(e)}")
            return []

    def get_current_price(self, symbol: str):
        if not self.exchange:
            self.logger.error("CCXT exchange not connected.")
            return None
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            self.logger.info(f"Current CCXT price for {symbol}: {price}")
            return price
        except Exception as e:
            self.logger.error(f"Error getting current CCXT price for {symbol}: {str(e)}")
            return None


class IBKRBrokerConnector(BrokerConnector, EWrapper):
    """Interactive Brokers broker connection implementation"""

    def __init__(self, config: dict):
        super().__init__(config)
        EWrapper.__init__(self)
        
        self.host = self.config['ibkr']['host']
        self.port = self.config['ibkr']['port']
        self.client_id = self.config['ibkr']['client_id']
        
        self.client = EClient(self)
        self.next_order_id = -1
        self.data_lock = threading.Lock()
        self.order_status_data = {}
        self.balance_data = {}
        self.open_orders_data = []
        self.price_data = {}

        self.logger.info("IBKRBrokerConnector initialized")

    def connect(self):
        try:
            self.client.connect(self.host, self.port, self.client_id)
            self.logger.info(f"Connected to IBKR at {self.host}:{self.port}")
            
            # Start the socket in a different thread
            thread = threading.Thread(target=self.client.run)
            thread.start()
            setattr(self.client, "thread", thread)
            
            # Request next valid ID
            self.client.reqIds(-1)
            # Wait for next_order_id to be set
            while self.next_order_id == -1:
                time.sleep(0.1)
            self.logger.info(f"Next valid order ID: {self.next_order_id}")

        except Exception as e:
            self.logger.error(f"Error connecting to IBKR: {str(e)}")
            raise

    def disconnect(self):
        self.client.disconnect()
        self.logger.info("Disconnected from IBKR")

    # EWrapper callbacks
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        self.next_order_id = orderId
        self.logger.debug(f"Received next valid ID: {orderId}")

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):
        super().error(reqId, errorCode, errorString, advancedOrderRejectJson)
        self.logger.error(f"IBKR Error. Id: {reqId}, Code: {errorCode}, Msg: {errorString}")
        # Handle specific errors or set flags for requests

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        super().accountSummary(reqId, account, tag, value, currency)
        with self.data_lock:
            if reqId not in self.balance_data:
                self.balance_data[reqId] = {}
            self.balance_data[reqId][tag] = {'value': value, 'currency': currency}

    def accountSummaryEnd(self, reqId: int):
        super().accountSummaryEnd(reqId)
        with self.data_lock:
            self.balance_data[reqId]['complete'] = True
        self.logger.debug(f"Account summary for request {reqId} finished.")

    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float,
                    avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float,
                    clientId: int, whyHeld: str, mktCapPrice: float):
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice, permId, parentId,
                            lastFillPrice, clientId, whyHeld, mktCapPrice)
        with self.data_lock:
            self.order_status_data[orderId] = {
                'status': status,
                'filled': filled,
                'remaining': remaining,
                'avgFillPrice': avgFillPrice,
                'lastFillPrice': lastFillPrice,
                'complete': True # Mark as complete for polling
            }
        self.logger.debug(f"Order Status: OrderId: {orderId}, Status: {status}, Filled: {filled}")

    def openOrder(self, orderId: int, contract: Contract, order: Order, orderState):
        super().openOrder(orderId, contract, order, orderState)
        with self.data_lock:
            self.open_orders_data.append({
                'id': str(orderId),
                'symbol': contract.symbol,
                'secType': contract.secType,
                'exchange': contract.exchange,
                'currency': contract.currency,
                'type': order.orderType,
                'side': 'buy' if order.action == 'BUY' else 'sell',
                'amount': order.totalQuantity,
                'price': order.lmtPrice if order.orderType == 'LMT' else order.auxPrice,
                'status': orderState.status,
                'info': {'contract': contract, 'order': order, 'orderState': orderState}
            })
        self.logger.debug(f"Open Order: OrderId: {orderId}, Symbol: {contract.symbol}, Status: {orderState.status}")

    def openOrderEnd(self):
        super().openOrderEnd()
        with self.data_lock:
            self.open_orders_data.append({'complete': True}) # Signal end of open orders
        self.logger.debug("Open Order End")

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib: dict):
        super().tickPrice(reqId, tickType, price, attrib)
        if tickType == 1: # BID
            self.price_data[reqId] = {'bid': price}
        elif tickType == 2: # ASK
            if reqId in self.price_data:
                self.price_data[reqId]['ask'] = price
            else:
                self.price_data[reqId] = {'ask': price}
        elif tickType == 4: # LAST
            if reqId in self.price_data:
                self.price_data[reqId]['last'] = price
            else:
                self.price_data[reqId] = {'last': price}
        self.logger.debug(f"Tick Price. ReqId: {reqId}, TickType: {tickType}, Price: {price}")

    def tickSize(self, reqId: int, tickType: int, size: int):
        super().tickSize(reqId, tickType, size)
        # Not directly used for price, but can be useful for market depth

    def get_balance(self, currency: str = None):
        self.connect()
        req_id = self.next_order_id # Use next valid ID for request
        self.client.reqAccountSummary(req_id, "All", "$LEDGER")
        
        with self.data_lock:
            self.balance_data[req_id] = {'complete': False}
        
        while not self.balance_data[req_id].get('complete', False):
            time.sleep(0.1)
        
        balance_info = self.balance_data[req_id]
        self.client.cancelAccountSummary(req_id)
        
        if currency:
            for tag, data in balance_info.items():
                if isinstance(data, dict) and data.get('currency') == currency and tag == 'TotalCashValue':
                    return float(data['value'])
            return None
        
        total_cash = float(balance_info.get('TotalCashValue', {}).get('value', 0))
        return {'total': total_cash, 'currency': balance_info.get('TotalCashValue', {}).get('currency', 'USD')}

    def create_order(self, symbol: str, order_type: str, side: str, amount: float, price: float = None, **kwargs):
        self.connect()
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = kwargs.get('secType', "STK") # Default to Stock
        contract.exchange = kwargs.get('exchange', "SMART")
        contract.currency = kwargs.get('currency', "USD")
        
        if contract.secType == "FUT":
            contract.lastTradeDateOrContractMonth = kwargs.get('lastTradeDateOrContractMonth')
            contract.multiplier = kwargs.get('multiplier')

        order = Order()
        order.action = side.upper()
        order.orderType = order_type.upper()
        order.totalQuantity = amount
        
        if order_type.lower() == 'limit' and price is not None:
            order.lmtPrice = price
        elif order_type.lower() == 'stop' and price is not None:
            order.auxPrice = price # Stop price
            order.orderType = "STP" # Ensure order type is STP for stop orders
        
        # Add stop loss and take profit if provided
        if 'stop_loss_price' in kwargs:
            order.ocaType = 1 # One Cancels All
            order.ocaGroup = f"OCA_{self.next_order_id}"
            order.transmit = False # Don't transmit parent order yet
            
            stop_loss_order = Order()
            stop_loss_order.action = "SELL" if side.lower() == "buy" else "BUY"
            stop_loss_order.orderType = "STP"
            stop_loss_order.auxPrice = kwargs['stop_loss_price']
            stop_loss_order.totalQuantity = amount
            stop_loss_order.parentId = self.next_order_id
            stop_loss_order.ocaGroup = order.ocaGroup
            stop_loss_order.transmit = False
            
            self.client.placeOrder(self.next_order_id, contract, order)
            self.next_order_id += 1
            self.client.placeOrder(self.next_order_id, contract, stop_loss_order)
            self.next_order_id += 1
            
            # Transmit the parent order (which will transmit children)
            order.transmit = True
            self.client.placeOrder(order.parentId, contract, order)
            
            self.logger.info(f"IBKR Order with SL created. Parent ID: {order.parentId}")
            return {'id': str(order.parentId), 'status': 'open', 'info': {'contract': contract, 'order': order}}

        elif 'take_profit_price' in kwargs:
            order.ocaType = 1 # One Cancels All
            order.ocaGroup = f"OCA_{self.next_order_id}"
            order.transmit = False # Don't transmit parent order yet
            
            take_profit_order = Order()
            take_profit_order.action = "SELL" if side.lower() == "buy" else "BUY"
            take_profit_order.orderType = "LMT"
            take_profit_order.lmtPrice = kwargs['take_profit_price']
            take_profit_order.totalQuantity = amount
            take_profit_order.parentId = self.next_order_id
            take_profit_order.ocaGroup = order.ocaGroup
            take_profit_order.transmit = False
            
            self.client.placeOrder(self.next_order_id, contract, order)
            self.next_order_id += 1
            self.client.placeOrder(self.next_order_id, contract, take_profit_order)
            self.next_order_id += 1
            
            # Transmit the parent order (which will transmit children)
            order.transmit = True
            self.client.placeOrder(order.parentId, contract, order)
            
            self.logger.info(f"IBKR Order with TP created. Parent ID: {order.parentId}")
            return {'id': str(order.parentId), 'status': 'open', 'info': {'contract': contract, 'order': order}}
        
        else:
            # Simple order
            order_id = self.next_order_id
            self.next_order_id += 1
            self.client.placeOrder(order_id, contract, order)
            self.logger.info(f"IBKR Simple Order created. ID: {order_id}")
            return {'id': str(order_id), 'status': 'open', 'info': {'contract': contract, 'order': order}}

    def cancel_order(self, order_id: str, symbol: str = None):
        self.connect()
        try:
            self.client.cancelOrder(int(order_id))
            self.logger.info(f"IBKR Order {order_id} cancellation requested.")
            # IBKR doesn't immediately confirm cancellation via API,
            # status will be updated via orderStatus callback
            return True
        except Exception as e:
            self.logger.error(f"Error cancelling IBKR order {order_id}: {str(e)}")
            return False

    def fetch_order_status(self, order_id: str, symbol: str = None):
        self.connect()
        with self.data_lock:
            self.order_status_data[int(order_id)] = {'complete': False}
        
        # Request order status (this will trigger orderStatus callback)
        self.client.reqAllOpenOrders() # This is a workaround, ideally reqOpenOrders(orderId) would exist
        self.client.reqAutoOpenOrders(True) # Ensure we get updates
        
        # Wait for the status to be updated by the callback
        start_time = time.time()
        while not self.order_status_data[int(order_id)].get('complete', False) and (time.time() - start_time) < 5: # 5 sec timeout
            time.sleep(0.1)
        
        status_info = self.order_status_data.get(int(order_id))
        if status_info and status_info.get('complete'):
            return {
                'id': str(order_id),
                'status': status_info['status'].lower(),
                'filled': status_info['filled'],
                'remaining': status_info['remaining'],
                'avgFillPrice': status_info['avgFillPrice'],
                'info': status_info
            }
        self.logger.warning(f"Could not fetch IBKR order status for {order_id} within timeout.")
        return None

    def fetch_open_orders(self, symbol: str = None):
        self.connect()
        with self.data_lock:
            self.open_orders_data = [] # Clear previous data
            self.open_orders_data.append({'complete': False}) # Sentinel for completion
        
        self.client.reqAllOpenOrders()
        
        start_time = time.time()
        while not any(d.get('complete') for d in self.open_orders_data) and (time.time() - start_time) < 5:
            time.sleep(0.1)
        
        # Filter out the completion sentinel and apply symbol filter
        filtered_orders = [
            order for order in self.open_orders_data if 'complete' not in order and 
            (symbol is None or order['symbol'] == symbol)
        ]
        self.logger.info(f"Fetched {len(filtered_orders)} open IBKR orders.")
        return filtered_orders

    def get_current_price(self, symbol: str, secType: str = "STK", exchange: str = "SMART", currency: str = "USD", **kwargs):
        self.connect()
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
        contract.currency = currency
        
        if secType == "FUT":
            contract.lastTradeDateOrContractMonth = kwargs.get('lastTradeDateOrContractMonth')
            contract.multiplier = kwargs.get('multiplier')

        req_id = self.next_order_id
        self.next_order_id += 1
        
        with self.data_lock:
            self.price_data[req_id] = {'complete': False}
        
        self.client.reqMktData(req_id, contract, "", False, False, [])
        
        start_time = time.time()
        while not self.price_data[req_id].get('complete', False) and (time.time() - start_time) < 5:
            time.sleep(0.1)
            if 'bid' in self.price_data[req_id] and 'ask' in self.price_data[req_id]:
                self.price_data[req_id]['complete'] = True # Mark complete if we have bid/ask
        
        price_info = self.price_data.get(req_id)
        self.client.cancelMktData(req_id)
        
        if price_info and price_info.get('complete'):
            bid = price_info.get('bid')
            ask = price_info.get('ask')
            last = price_info.get('last')
            
            if bid is not None and ask is not None:
                mid = (bid + ask) / 2
                self.logger.info(f"Current IBKR price for {symbol}: Bid={bid}, Ask={ask}, Mid={mid}")
                return mid
            elif last is not None:
                self.logger.info(f"Current IBKR price for {symbol}: Last={last}")
                return last
        
        self.logger.warning(f"Could not get current IBKR price for {symbol} within timeout.")
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Example Usage for OANDA
    print("\n--- Testing OANDA Broker Connector ---")
    # To run this example, you would need a dummy config dictionary
    # or load it from a file as main.py does.
    dummy_config = {
        'oanda': {
            'account_id': 'YOUR_OANDA_ACCOUNT_ID',
            'access_token': 'YOUR_OANDA_ACCESS_TOKEN',
            'practice': True
        },
        'ccxt': {
            'api_key': 'YOUR_CCXT_API_KEY',
            'secret': 'YOUR_CCXT_SECRET',
            'password': 'YOUR_CCXT_PASSWORD'
        },
        'ibkr': {
            'host': '127.0.0.1',
            'port': 7497,
            'client_id': 1
        }
    }
    oanda_connector = OANDABrokerConnector(config=dummy_config)
    try:
        oanda_connector.connect()
        balance = oanda_connector.get_balance()
        print(f"OANDA Balance: {balance}")

        # Example: Place a dummy market order (will likely fail without real credentials)
        # order_details = oanda_connector.create_order("EUR_USD", "market", "buy", 1000)
        # print(f"OANDA Order Details: {order_details}")

    except Exception as e:
        print(f"OANDA Test Error: {e}")

    # Example Usage for CCXT (Binance)
    print("\n--- Testing CCXT Broker Connector (Binance) ---")
    ccxt_connector = CCXTBrokerConnector(config=dummy_config, exchange_id='binance')
    try:
        ccxt_connector.connect()
        balance = ccxt_connector.get_balance('USDT')
        print(f"CCXT USDT Balance: {balance}")
        
        price = ccxt_connector.get_current_price("BTC/USDT")
        print(f"Current BTC/USDT price: {price}")

        # Example: Place a dummy market order (will likely fail without real credentials)
        # order_details = ccxt_connector.create_order("BTC/USDT", "market", "buy", 0.0001)
        # print(f"CCXT Order Details: {order_details}")

    except Exception as e:
        print(f"CCXT Test Error: {e}")

    # Example Usage for IBKR (Requires TWS/Gateway running and connected)
    print("\n--- Testing IBKR Broker Connector ---")
    ibkr_connector = IBKRBrokerConnector(config=dummy_config)
    try:
        ibkr_connector.connect()
        
        # Give some time for nextValidId to be received
        time.sleep(2)
        
        balance = ibkr_connector.get_balance()
        print(f"IBKR Balance: {balance}")

        # Example: Get current price for a stock (e.g., AAPL)
        # price = ibkr_connector.get_current_price("AAPL", secType="STK", exchange="SMART", currency="USD")
        # print(f"Current AAPL price: {price}")

        # Example: Place a dummy market order (will likely fail without real TWS connection)
        # order_details = ibkr_connector.create_order("AAPL", "market", "buy", 1, secType="STK", exchange="SMART", currency="USD")
        # print(f"IBKR Order Details: {order_details}")

        ibkr_connector.disconnect()
    except Exception as e:
        print(f"IBKR Test Error: {e}")