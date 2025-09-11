"""
Real-time Signal Logging System
Comprehensive logging and tracking of trading signals with real-time updates
"""

import logging
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import threading
from queue import Queue, Empty

class SignalSource(Enum):
    STRATEGY = "strategy"
    INDICATOR = "indicator"
    MANUAL = "manual"
    SYSTEM = "system"

class SignalPriority(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class RealTimeSignal:
    """Enhanced real-time signal with comprehensive metadata"""
    timestamp: datetime
    signal_id: str
    session_id: int
    symbol: str
    timeframe: str
    signal_type: str  # BUY, SELL, HOLD
    signal_strength: float
    confidence: float
    price: float
    source: SignalSource
    priority: SignalPriority
    strategy_name: str
    indicators: Dict[str, Any]
    market_conditions: Dict[str, Any]
    risk_metrics: Dict[str, Any]
    execution_context: Dict[str, Any]
    executed: bool = False
    execution_time: Optional[datetime] = None
    execution_price: Optional[float] = None
    trade_id: Optional[int] = None
    pnl: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        data['source'] = self.source.value
        data['priority'] = self.priority.value
        if self.execution_time:
            data['execution_time'] = self.execution_time.isoformat()
        return data
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

class RealTimeSignalLogger:
    """
    Real-time signal logging system with WebSocket broadcasting and database persistence
    """
    
    def __init__(self, websocket_manager=None, db_manager=None):
        self.logger = logging.getLogger(__name__)
        self.websocket_manager = websocket_manager
        self.db_manager = db_manager
        
        # Signal storage
        self.signals: List[RealTimeSignal] = []
        self.signal_queue = Queue()
        self.signal_counter = 0
        
        # Processing thread
        self.processing_thread = None
        self.is_running = False
        
        # Callbacks
        self.signal_callbacks: List[Callable[[RealTimeSignal], None]] = []
        
        # Statistics
        self.stats = {
            'total_signals': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'hold_signals': 0,
            'executed_signals': 0,
            'high_priority_signals': 0,
            'avg_signal_strength': 0.0,
            'avg_confidence': 0.0
        }
        
        self.logger.info("RealTimeSignalLogger initialized")
    
    def start(self):
        """Start the signal processing thread"""
        if not self.is_running:
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._process_signals, daemon=True)
            self.processing_thread.start()
            self.logger.info("Signal processing thread started")
    
    def stop(self):
        """Stop the signal processing thread"""
        self.is_running = False
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=5)
        self.logger.info("Signal processing thread stopped")
    
    def log_signal(self, session_id: int, symbol: str, timeframe: str, signal_type: str,
                   signal_strength: float, confidence: float, price: float,
                   strategy_name: str, indicators: Dict[str, Any],
                   market_conditions: Dict[str, Any] = None,
                   risk_metrics: Dict[str, Any] = None,
                   execution_context: Dict[str, Any] = None,
                   source: SignalSource = SignalSource.STRATEGY,
                   priority: SignalPriority = SignalPriority.MEDIUM) -> str:
        """
        Log a new trading signal
        
        Returns:
            signal_id: Unique identifier for the signal
        """
        self.signal_counter += 1
        signal_id = f"{session_id}_{symbol}_{self.signal_counter}_{int(datetime.utcnow().timestamp())}"
        
        signal = RealTimeSignal(
            timestamp=datetime.utcnow(),
            signal_id=signal_id,
            session_id=session_id,
            symbol=symbol,
            timeframe=timeframe,
            signal_type=signal_type.upper(),
            signal_strength=signal_strength,
            confidence=confidence,
            price=price,
            source=source,
            priority=priority,
            strategy_name=strategy_name,
            indicators=indicators or {},
            market_conditions=market_conditions or {},
            risk_metrics=risk_metrics or {},
            execution_context=execution_context or {}
        )
        
        # Add to queue for processing
        self.signal_queue.put(signal)
        
        # Log immediately for critical signals
        if priority == SignalPriority.CRITICAL:
            self._log_signal_immediately(signal)
        
        return signal_id
    
    def _process_signals(self):
        """Process signals from the queue"""
        while self.is_running:
            try:
                # Get signal from queue with timeout
                signal = self.signal_queue.get(timeout=1.0)
                self._process_single_signal(signal)
                self.signal_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"Error processing signal: {e}")
    
    def _process_single_signal(self, signal: RealTimeSignal):
        """Process a single signal"""
        try:
            # Add to storage
            self.signals.append(signal)
            
            # Update statistics
            self._update_stats(signal)
            
            # Log to console
            self._log_signal_to_console(signal)
            
            # Store in database
            self._store_signal_in_database(signal)
            
            # Broadcast via WebSocket
            self._broadcast_signal(signal)
            
            # Execute callbacks
            self._execute_callbacks(signal)
            
        except Exception as e:
            self.logger.error(f"Error processing signal {signal.signal_id}: {e}")
    
    def _log_signal_immediately(self, signal: RealTimeSignal):
        """Log critical signals immediately"""
        self.logger.critical(f"CRITICAL SIGNAL: {signal.signal_type} {signal.symbol} @ {signal.price:.5f}")
        self.logger.critical(f"Strength: {signal.signal_strength:.4f}, Confidence: {signal.confidence:.4f}")
    
    def _log_signal_to_console(self, signal: RealTimeSignal):
        """Log signal to console with detailed information"""
        priority_symbol = "🔴" if signal.priority == SignalPriority.CRITICAL else \
                         "🟡" if signal.priority == SignalPriority.HIGH else \
                         "🟢" if signal.priority == SignalPriority.MEDIUM else "⚪"
        
        self.logger.info(f"=== {priority_symbol} REAL-TIME SIGNAL {signal.signal_id} ===")
        self.logger.info(f"Time: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        self.logger.info(f"Symbol: {signal.symbol} ({signal.timeframe})")
        self.logger.info(f"Type: {signal.signal_type}")
        self.logger.info(f"Strength: {signal.signal_strength:.4f}")
        self.logger.info(f"Confidence: {signal.confidence:.4f}")
        self.logger.info(f"Price: {signal.price:.5f}")
        self.logger.info(f"Strategy: {signal.strategy_name}")
        self.logger.info(f"Source: {signal.source.value}")
        self.logger.info(f"Priority: {signal.priority.value}")
        
        # Log indicators
        if signal.indicators:
            self.logger.info("Indicators:")
            for key, value in signal.indicators.items():
                if isinstance(value, float):
                    self.logger.info(f"  {key}: {value:.6f}")
                else:
                    self.logger.info(f"  {key}: {value}")
        
        # Log market conditions
        if signal.market_conditions:
            self.logger.info("Market Conditions:")
            for key, value in signal.market_conditions.items():
                self.logger.info(f"  {key}: {value}")
        
        # Log risk metrics
        if signal.risk_metrics:
            self.logger.info("Risk Metrics:")
            for key, value in signal.risk_metrics.items():
                if isinstance(value, float):
                    self.logger.info(f"  {key}: {value:.6f}")
                else:
                    self.logger.info(f"  {key}: {value}")
    
    def _store_signal_in_database(self, signal: RealTimeSignal):
        """Store signal in database"""
        if not self.db_manager:
            return
        
        try:
            # Combine all metadata
            indicators_data = {
                **signal.indicators,
                'market_conditions': signal.market_conditions,
                'risk_metrics': signal.risk_metrics,
                'execution_context': signal.execution_context,
                'source': signal.source.value,
                'priority': signal.priority.value
            }
            
            self.db_manager.store_trading_signal(
                session_id=signal.session_id,
                symbol=signal.symbol,
                timestamp=signal.timestamp,
                signal_type=signal.signal_type,
                signal_strength=signal.signal_strength,
                confidence=signal.confidence,
                price=signal.price,
                indicators=indicators_data
            )
            
        except Exception as e:
            self.logger.error(f"Failed to store signal in database: {e}")
    
    def _broadcast_signal(self, signal: RealTimeSignal):
        """Broadcast signal via WebSocket"""
        if not self.websocket_manager:
            return
        
        try:
            message = {
                "type": "realtime_signal",
                "timestamp": datetime.utcnow().isoformat(),
                "data": signal.to_dict()
            }
            
            # Create async task for broadcasting
            asyncio.create_task(self.websocket_manager.broadcast(json.dumps(message)))
            
        except Exception as e:
            self.logger.error(f"Failed to broadcast signal: {e}")
    
    def _execute_callbacks(self, signal: RealTimeSignal):
        """Execute registered callbacks"""
        for callback in self.signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                self.logger.error(f"Error in signal callback: {e}")
    
    def _update_stats(self, signal: RealTimeSignal):
        """Update signal statistics"""
        self.stats['total_signals'] += 1
        
        if signal.signal_type == 'BUY':
            self.stats['buy_signals'] += 1
        elif signal.signal_type == 'SELL':
            self.stats['sell_signals'] += 1
        else:
            self.stats['hold_signals'] += 1
        
        if signal.executed:
            self.stats['executed_signals'] += 1
        
        if signal.priority == SignalPriority.HIGH or signal.priority == SignalPriority.CRITICAL:
            self.stats['high_priority_signals'] += 1
        
        # Update averages
        total = self.stats['total_signals']
        self.stats['avg_signal_strength'] = (
            (self.stats['avg_signal_strength'] * (total - 1) + signal.signal_strength) / total
        )
        self.stats['avg_confidence'] = (
            (self.stats['avg_confidence'] * (total - 1) + signal.confidence) / total
        )
    
    def mark_signal_executed(self, signal_id: str, execution_time: datetime,
                           execution_price: float, trade_id: int):
        """Mark a signal as executed"""
        for signal in self.signals:
            if signal.signal_id == signal_id:
                signal.executed = True
                signal.execution_time = execution_time
                signal.execution_price = execution_price
                signal.trade_id = trade_id
                
                self.logger.info(f"Signal {signal_id} marked as executed at {execution_price:.5f}")
                
                # Broadcast execution update
                if self.websocket_manager:
                    try:
                        message = {
                            "type": "signal_executed",
                            "timestamp": datetime.utcnow().isoformat(),
                            "signal_id": signal_id,
                            "execution_price": execution_price,
                            "trade_id": trade_id
                        }
                        asyncio.create_task(self.websocket_manager.broadcast(json.dumps(message)))
                    except Exception as e:
                        self.logger.error(f"Failed to broadcast signal execution: {e}")
                
                break
    
    def add_callback(self, callback: Callable[[RealTimeSignal], None]):
        """Add a callback function to be executed for each signal"""
        self.signal_callbacks.append(callback)
    
    def get_signals(self, session_id: int = None, limit: int = 100,
                   signal_type: str = None, priority: SignalPriority = None) -> List[Dict[str, Any]]:
        """Get signals with optional filtering"""
        filtered_signals = self.signals
        
        if session_id:
            filtered_signals = [s for s in filtered_signals if s.session_id == session_id]
        
        if signal_type:
            filtered_signals = [s for s in filtered_signals if s.signal_type == signal_type.upper()]
        
        if priority:
            filtered_signals = [s for s in filtered_signals if s.priority == priority]
        
        # Sort by timestamp (most recent first) and limit
        filtered_signals = sorted(filtered_signals, key=lambda x: x.timestamp, reverse=True)
        if limit:
            filtered_signals = filtered_signals[:limit]
        
        return [signal.to_dict() for signal in filtered_signals]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get signal statistics"""
        return {
            **self.stats,
            'signals_in_queue': self.signal_queue.qsize(),
            'total_stored_signals': len(self.signals),
            'processing_thread_active': self.is_running and self.processing_thread and self.processing_thread.is_alive()
        }
    
    def clear_old_signals(self, max_age_hours: int = 24):
        """Clear old signals to prevent memory buildup"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        initial_count = len(self.signals)
        
        self.signals = [s for s in self.signals if s.timestamp > cutoff_time]
        
        cleared_count = initial_count - len(self.signals)
        if cleared_count > 0:
            self.logger.info(f"Cleared {cleared_count} old signals (older than {max_age_hours} hours)")

# Global signal logger instance
_signal_logger_instance = None

def get_signal_logger(websocket_manager=None, db_manager=None) -> RealTimeSignalLogger:
    """Get or create the global signal logger instance"""
    global _signal_logger_instance
    
    if _signal_logger_instance is None:
        _signal_logger_instance = RealTimeSignalLogger(websocket_manager, db_manager)
        _signal_logger_instance.start()
    
    return _signal_logger_instance

if __name__ == "__main__":
    # Test the signal logger
    logging.basicConfig(level=logging.INFO)
    
    logger = RealTimeSignalLogger()
    logger.start()
    
    # Test signal logging
    signal_id = logger.log_signal(
        session_id=1,
        symbol="EUR_USD",
        timeframe="1m",
        signal_type="BUY",
        signal_strength=0.75,
        confidence=0.85,
        price=1.1234,
        strategy_name="RealtimeScalping1MStrategy",
        indicators={
            "ema_fast": 1.1230,
            "ema_slow": 1.1220,
            "rsi": 35.5,
            "macd": 0.0012
        },
        market_conditions={
            "volatility": 0.0015,
            "trend": "bullish",
            "volume_ratio": 1.2
        },
        risk_metrics={
            "position_size": 0.02,
            "risk_reward_ratio": 2.5,
            "max_drawdown": 0.05
        },
        priority=SignalPriority.HIGH
    )
    
    print(f"Logged signal: {signal_id}")
    print(f"Stats: {logger.get_stats()}")
    
    # Wait a bit for processing
    import time
    time.sleep(2)
    
    logger.stop()