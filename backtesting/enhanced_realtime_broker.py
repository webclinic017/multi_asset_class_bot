"""
Enhanced Real-time Broker with Comprehensive Logging
Provides detailed buy/sell signal logs and order lifecycle tracking for scalping strategies
"""

import backtrader as bt
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

class OrderStatus(Enum):
    CREATED = "created"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    PARTIAL = "partial"
    COMPLETED = "completed"
    CANCELED = "canceled"
    REJECTED = "rejected"
    MARGIN = "margin"

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

@dataclass
class TradingSignal:
    """Trading signal data structure"""
    timestamp: datetime
    symbol: str
    signal_type: SignalType
    signal_strength: float
    confidence: float
    price: float
    indicators: Dict[str, Any]
    strategy_name: str
    timeframe: str
    executed: bool = False
    trade_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['signal_type'] = self.signal_type.value
        return data

@dataclass
class OrderActivity:
    """Order activity tracking data structure"""
    timestamp: datetime
    order_id: int
    symbol: str
    order_type: str
    side: str
    size: float
    price: Optional[float]
    status: OrderStatus
    message: str
    execution_price: Optional[float] = None
    execution_size: Optional[float] = None
    commission: Optional[float] = None
    strategy_name: str = ""
    signal_id: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['status'] = self.status.value
        return data

class EnhancedRealTimeBroker(bt.brokers.BackBroker):
    """
    Enhanced real-time broker with comprehensive logging and activity tracking
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = logging.getLogger(__name__)
        self.logger.info("EnhancedRealTimeBroker initialized with comprehensive logging")
        
        # Initialize cash and value
        self.cash = 100000.0
        self.value = 100000.0
        
        # Tracking collections
        self.trading_signals: List[TradingSignal] = []
        self.order_activities: List[OrderActivity] = []
        self.execution_count = 0
        self.signal_count = 0
        
        # WebSocket manager for real-time updates (will be set externally)
        self.websocket_manager = None
        self.session_id = None
        
        # Database manager for persistence (will be set externally)
        self.db_manager = None
        
        # Strategy reference for logging
        self.current_strategy = None
        
    def set_websocket_manager(self, manager):
        """Set WebSocket manager for real-time updates"""
        self.websocket_manager = manager
        
    def set_database_manager(self, db_manager):
        """Set database manager for persistence"""
        self.db_manager = db_manager
        
    def set_session_id(self, session_id: int):
        """Set trading session ID"""
        self.session_id = session_id
        
    def set_current_strategy(self, strategy):
        """Set current strategy reference"""
        self.current_strategy = strategy
        
    def log_trading_signal(self, signal_type: SignalType, signal_strength: float, 
                          confidence: float, price: float, indicators: Dict[str, Any],
                          symbol: str = "EUR_USD", timeframe: str = "1m") -> int:
        """
        Log a trading signal with comprehensive details
        
        Returns:
            signal_id: Unique identifier for the signal
        """
        self.signal_count += 1
        
        strategy_name = ""
        if self.current_strategy:
            strategy_name = self.current_strategy.__class__.__name__
            
        signal = TradingSignal(
            timestamp=datetime.utcnow(),
            symbol=symbol,
            signal_type=signal_type,
            signal_strength=signal_strength,
            confidence=confidence,
            price=price,
            indicators=indicators,
            strategy_name=strategy_name,
            timeframe=timeframe
        )
        
        self.trading_signals.append(signal)
        signal_id = len(self.trading_signals)
        
        # Log to console
        self.logger.info(f"=== TRADING SIGNAL #{signal_id} ===")
        self.logger.info(f"Type: {signal_type.value}")
        self.logger.info(f"Strength: {signal_strength:.4f}")
        self.logger.info(f"Confidence: {confidence:.4f}")
        self.logger.info(f"Price: {price:.5f}")
        self.logger.info(f"Strategy: {strategy_name}")
        self.logger.info(f"Indicators: {json.dumps(indicators, indent=2)}")
        
        # Store in database if available
        if self.db_manager and self.session_id:
            try:
                self.db_manager.store_trading_signal(
                    session_id=self.session_id,
                    symbol=symbol,
                    timestamp=signal.timestamp,
                    signal_type=signal_type.value,
                    signal_strength=signal_strength,
                    confidence=confidence,
                    price=price,
                    indicators=indicators
                )
            except Exception as e:
                self.logger.error(f"Failed to store signal in database: {e}")
        
        # Broadcast via WebSocket if available
        if self.websocket_manager:
            try:
                import asyncio
                asyncio.create_task(self.websocket_manager.broadcast(json.dumps({
                    "type": "trading_signal",
                    "session_id": self.session_id,
                    "signal_id": signal_id,
                    "data": signal.to_dict()
                })))
            except Exception as e:
                self.logger.error(f"Failed to broadcast signal: {e}")
        
        return signal_id
    
    def log_order_activity(self, order, status: OrderStatus, message: str, 
                          signal_id: Optional[int] = None):
        """Log order activity with detailed tracking"""
        strategy_name = ""
        if self.current_strategy:
            strategy_name = self.current_strategy.__class__.__name__
            
        activity = OrderActivity(
            timestamp=datetime.utcnow(),
            order_id=order.ref,
            symbol=getattr(order.data, '_name', 'EUR_USD'),
            order_type=self._get_order_type_name(order.ordtype),
            side="BUY" if order.isbuy() else "SELL",
            size=order.size,
            price=order.price,
            status=status,
            message=message,
            execution_price=getattr(order.executed, 'price', None) if hasattr(order, 'executed') else None,
            execution_size=getattr(order.executed, 'size', None) if hasattr(order, 'executed') else None,
            commission=getattr(order.executed, 'comm', None) if hasattr(order, 'executed') else None,
            strategy_name=strategy_name,
            signal_id=signal_id
        )
        
        self.order_activities.append(activity)
        
        # Log to console
        self.logger.info(f"=== ORDER ACTIVITY #{len(self.order_activities)} ===")
        self.logger.info(f"Order ID: {order.ref}")
        self.logger.info(f"Status: {status.value}")
        self.logger.info(f"Side: {activity.side}")
        self.logger.info(f"Size: {activity.size}")
        self.logger.info(f"Price: {activity.price}")
        self.logger.info(f"Message: {message}")
        if activity.execution_price:
            self.logger.info(f"Execution Price: {activity.execution_price:.5f}")
        if activity.execution_size:
            self.logger.info(f"Execution Size: {activity.execution_size}")
        if activity.commission:
            self.logger.info(f"Commission: {activity.commission:.4f}")
        
        # Store in database if available
        if self.db_manager and self.session_id:
            try:
                self.db_manager.log_system_event(
                    log_level="INFO",
                    component="broker",
                    message=f"Order {order.ref} {status.value}: {message}",
                    session_id=self.session_id
                )
            except Exception as e:
                self.logger.error(f"Failed to store order activity in database: {e}")
        
        # Broadcast via WebSocket if available
        if self.websocket_manager:
            try:
                import asyncio
                asyncio.create_task(self.websocket_manager.broadcast(json.dumps({
                    "type": "order_activity",
                    "session_id": self.session_id,
                    "data": activity.to_dict()
                })))
            except Exception as e:
                self.logger.error(f"Failed to broadcast order activity: {e}")
    
    def _get_order_type_name(self, ordtype) -> str:
        """Get human-readable order type name"""
        type_map = {
            bt.Order.Market: "Market",
            bt.Order.Limit: "Limit",
            bt.Order.Stop: "Stop",
            bt.Order.StopLimit: "StopLimit"
        }
        return type_map.get(ordtype, "Unknown")
    
    def submit(self, order, check=True):
        """Override submit to log order creation and submission"""
        self.logger.info(f"=== BROKER SUBMIT CALLED ===")
        
        # Log order creation
        self.log_order_activity(order, OrderStatus.CREATED, "Order created by strategy")
        
        # Call parent submit
        result = super().submit(order)
        
        # Log order submission
        self.log_order_activity(order, OrderStatus.SUBMITTED, "Order submitted to broker")
        
        # Force immediate execution for ALL order types to ensure both BUY and SELL execute
        if order.alive():
            order_type_name = "MARKET" if order.ordtype == bt.Order.Market else "LIMIT/STOP"
            self.logger.info(f"*** FORCING IMMEDIATE {order_type_name} ORDER EXECUTION ***")
            
            try:
                self._execute_order_immediately(order)
            except Exception as e:
                self.logger.error(f"Failed to force immediate execution: {e}")
                self.log_order_activity(order, OrderStatus.REJECTED, f"Execution failed: {e}")
        
        return result
    
    def _execute_order_immediately(self, order):
        """Force immediate execution of any order (market, limit, stop) with detailed logging"""
        try:
            # Get current price from the data feed
            data = order.data
            if not data:
                raise Exception("No data available for order execution")
            
            current_price = data.close[0]
            if current_price <= 0:
                raise Exception(f"Invalid current price: {current_price}")
            
            self.logger.info(f"Executing market order at price: {current_price:.5f}")
            
            # Calculate execution details
            size = order.size
            value = size * current_price
            
            # Check if we have enough cash for buy orders
            if order.isbuy() and value > self.get_cash():
                raise Exception(f"Insufficient cash: {value:.2f} > {self.get_cash():.2f}")
            
            # Set execution details
            order.executed.price = current_price
            order.executed.size = size
            order.executed.value = value
            order.executed.comm = self.getcommissioninfo(data).getcommission(size, current_price)
            order.executed.dt = data.datetime.datetime(0)
            
            # Log order acceptance
            self.log_order_activity(order, OrderStatus.ACCEPTED, "Order accepted for execution")
            
            # Update order status to completed
            order.completed()
            
            # Update broker state
            if order.isbuy():
                if self.cash >= (value + order.executed.comm):
                    self.cash -= (value + order.executed.comm)
                    self.logger.info(f"Buy execution: Cash reduced by {value + order.executed.comm:.2f}")
                else:
                    order.reject()
                    self.log_order_activity(order, OrderStatus.REJECTED, "Insufficient cash")
                    return
            else:
                # Sell order: increase cash (value is negative for sell orders)
                cash_change = abs(value) - order.executed.comm
                self.cash += cash_change
                self.logger.info(f"Sell execution: Cash increased by {cash_change:.2f}")
            
            # Update portfolio value
            self._update_value()
            
            self.execution_count += 1
            
            # Log successful execution
            self.log_order_activity(
                order, 
                OrderStatus.COMPLETED, 
                f"Order executed at {current_price:.5f}, value: {value:.2f}, commission: {order.executed.comm:.4f}"
            )
            
            self.logger.info(f"*** IMMEDIATE EXECUTION #{self.execution_count} COMPLETED ***")
            
        except Exception as e:
            self.logger.error(f"Error in immediate execution: {e}")
            self.log_order_activity(order, OrderStatus.REJECTED, f"Execution error: {e}")
            raise
    
    def next(self):
        """Override next to ensure all pending orders are processed"""
        result = super().next()
        
        # Force processing of any stuck orders
        if hasattr(self, '_orders'):
            stuck_orders = [o for o in self._orders if o.alive() and o.status == bt.Order.Submitted]
            if stuck_orders:
                self.logger.warning(f"Found {len(stuck_orders)} stuck orders - forcing execution")
                for order in stuck_orders:
                    # Execute ALL stuck orders, not just market orders
                    try:
                        self._execute_order_immediately(order)
                    except Exception as e:
                        self.logger.error(f"Failed to execute stuck order {order.ref}: {e}")
        
        return result
    
    def _update_value(self):
        """Update the total portfolio value"""
        try:
            positions_value = 0
            if hasattr(self, 'cerebro') and self.cerebro:
                for data in self.cerebro.datas:
                    position = self.getposition(data)
                    if position.size != 0:
                        current_price = data.close[0]
                        positions_value += position.size * current_price
            
            self.value = self.cash + positions_value
            
        except Exception as e:
            self.logger.error(f"Error updating portfolio value: {e}")
    
    def get_cash(self):
        """Return current cash"""
        return self.cash
    
    def get_value(self, datas=None, mkt=False, lever=False):
        """Return current portfolio value"""
        try:
            self._update_value()
            return self.value
        except Exception as e:
            self.logger.error(f"Error getting portfolio value: {e}")
            return self.value
    
    def set_cash(self, cash):
        """Set cash amount"""
        self.cash = float(cash)
        self.value = self.cash
        self.logger.info(f"Cash set to: ${self.cash:.2f}")
    
    def get_trading_signals(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent trading signals"""
        signals = self.trading_signals[-limit:] if limit else self.trading_signals
        return [signal.to_dict() for signal in signals]
    
    def get_order_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent order activities"""
        activities = self.order_activities[-limit:] if limit else self.order_activities
        return [activity.to_dict() for activity in activities]
    
    def get_broker_stats(self) -> Dict[str, Any]:
        """Get comprehensive broker statistics"""
        return {
            "cash": self.cash,
            "value": self.value,
            "total_signals": len(self.trading_signals),
            "total_orders": len(self.order_activities),
            "executions": self.execution_count,
            "buy_signals": len([s for s in self.trading_signals if s.signal_type == SignalType.BUY]),
            "sell_signals": len([s for s in self.trading_signals if s.signal_type == SignalType.SELL]),
            "completed_orders": len([a for a in self.order_activities if a.status == OrderStatus.COMPLETED]),
            "rejected_orders": len([a for a in self.order_activities if a.status == OrderStatus.REJECTED])
        }

def create_enhanced_realtime_broker(initial_cash=100000.0, commission=0.001):
    """
    Factory function to create an enhanced real-time broker
    
    Args:
        initial_cash: Initial cash amount
        commission: Commission rate
        
    Returns:
        EnhancedRealTimeBroker: Configured broker instance
    """
    broker = EnhancedRealTimeBroker()
    broker.set_cash(initial_cash)
    broker.setcommission(commission=commission)
    
    logger = logging.getLogger(__name__)
    logger.info(f"EnhancedRealTimeBroker created with ${initial_cash:,.2f} initial cash")
    
    return broker

if __name__ == "__main__":
    # Test the enhanced real-time broker
    logging.basicConfig(level=logging.INFO)
    
    broker = create_enhanced_realtime_broker(100000.0, 0.001)
    
    # Test signal logging
    signal_id = broker.log_trading_signal(
        SignalType.BUY,
        0.75,
        0.85,
        1.1234,
        {
            "ema_fast": 1.1230,
            "ema_slow": 1.1220,
            "rsi": 35.5,
            "macd": 0.0012
        }
    )
    
    print(f"Logged signal with ID: {signal_id}")
    print(f"Broker stats: {broker.get_broker_stats()}")