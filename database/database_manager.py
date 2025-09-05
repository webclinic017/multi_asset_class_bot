"""
Database Manager for Trading Bot Dashboard
Handles SQLite database operations and data persistence
"""

import sqlite3
import json
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
import os

class DatabaseManager:
    """Manages SQLite database operations for the trading bot"""
    
    def __init__(self, db_path: str = "database/trading_bot.db"):
        """
        Initialize database manager
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure database directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._initialize_database()
        
    def _initialize_database(self):
        """Initialize database with schema"""
        try:
            # Read and execute schema
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with self.get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()
                
            self.logger.info("Database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get database connection with context manager"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    # Strategy Management
    def create_strategy(self, name: str, description: str, strategy_type: str, 
                       asset_class: str, timeframe: str, parameters: Dict) -> int:
        """Create a new strategy"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO strategies (name, description, strategy_type, asset_class, timeframe, parameters)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, description, strategy_type, asset_class, timeframe, json.dumps(parameters)))
            conn.commit()
            return cursor.lastrowid
    
    def get_strategies(self) -> List[Dict]:
        """Get all strategies"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM strategies
                WHERE is_active = 1
                ORDER BY name, created_at DESC
            """)
            rows = cursor.fetchall()
            
            strategies = []
            seen_names = set()
            for row in rows:
                strategy = dict(row)
                strategy['parameters'] = json.loads(strategy['parameters']) if strategy['parameters'] else {}
                
                # Avoid duplicates by name
                if strategy['name'] not in seen_names:
                    strategies.append(strategy)
                    seen_names.add(strategy['name'])
            
            return strategies
    
    def get_strategy(self, strategy_id: int) -> Optional[Dict]:
        """Get strategy by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
            row = cursor.fetchone()
            
            if row:
                strategy = dict(row)
                strategy['parameters'] = json.loads(strategy['parameters']) if strategy['parameters'] else {}
                return strategy
            return None
    
    # Trading Session Management
    def create_trading_session(self, session_type: str, strategy_id: int, symbol: str,
                              initial_capital: float, start_time: datetime = None) -> int:
        """Create a new trading session"""
        if start_time is None:
            start_time = datetime.utcnow()
            
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_sessions (session_type, strategy_id, symbol, start_time, initial_capital)
                VALUES (?, ?, ?, ?, ?)
            """, (session_type, strategy_id, symbol, start_time, initial_capital))
            conn.commit()
            return cursor.lastrowid
    
    def update_trading_session(self, session_id: int, **kwargs):
        """Update trading session"""
        if not kwargs:
            return
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [session_id]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE trading_sessions
                SET {set_clause}
                WHERE id = ?
            """, values)
            conn.commit()
    
    def get_trading_sessions(self, limit: int = 100) -> List[Dict]:
        """Get trading sessions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ts.*, s.name as strategy_name, s.strategy_type, s.asset_class, s.timeframe
                FROM trading_sessions ts
                JOIN strategies s ON ts.strategy_id = s.id
                ORDER BY ts.created_at DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_sessions(self) -> List[Dict]:
        """Get active trading sessions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ts.*, s.name as strategy_name, s.strategy_type, s.asset_class, s.timeframe
                FROM trading_sessions ts
                JOIN strategies s ON ts.strategy_id = s.id
                WHERE ts.status = 'active'
                ORDER BY ts.created_at DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Trade Management
    def create_trade(self, session_id: int, symbol: str, side: str, entry_time: datetime,
                    entry_price: float, quantity: float, **kwargs) -> int:
        """Create a new trade"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build dynamic insert query
            columns = ['session_id', 'symbol', 'side', 'entry_time', 'entry_price', 'quantity']
            values = [session_id, symbol, side, entry_time, entry_price, quantity]
            
            for key, value in kwargs.items():
                if key in ['trade_id', 'stop_loss', 'take_profit', 'signal_strength', 'confidence']:
                    columns.append(key)
                    values.append(value)
            
            placeholders = ', '.join(['?' for _ in values])
            columns_str = ', '.join(columns)
            
            cursor.execute(f"""
                INSERT INTO trades ({columns_str})
                VALUES ({placeholders})
            """, values)
            conn.commit()
            return cursor.lastrowid
    
    def update_trade(self, trade_id: int, **kwargs):
        """Update trade"""
        if not kwargs:
            return
        
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [trade_id]
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE trades 
                SET {set_clause}
                WHERE id = ?
            """, values)
            conn.commit()
    
    def close_trade(self, trade_id: int, exit_time: datetime, exit_price: float,
                   exit_reason: str, pnl: float, pnl_pips: float = None):
        """Close a trade"""
        self.update_trade(
            trade_id,
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl=pnl,
            pnl_pips=pnl_pips,
            status='closed',
            duration_seconds=int((exit_time - datetime.utcnow()).total_seconds())
        )
    
    def get_trades(self, session_id: int = None, limit: int = 1000) -> List[Dict]:
        """Get trades"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE session_id = ?
                    ORDER BY entry_time DESC
                    LIMIT ?
                """, (session_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM trades 
                    ORDER BY entry_time DESC
                    LIMIT ?
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_open_trades(self, session_id: int = None) -> List[Dict]:
        """Get open trades"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if session_id:
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE session_id = ? AND status = 'open'
                    ORDER BY entry_time DESC
                """, (session_id,))
            else:
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE status = 'open'
                    ORDER BY entry_time DESC
                """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    # Market Data Management
    def store_market_data(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """Store market data"""
        with self.get_connection() as conn:
            for index, row in data.iterrows():
                try:
                    # Convert timestamp to string if it's a datetime object
                    timestamp_str = index.strftime('%Y-%m-%d %H:%M:%S') if hasattr(index, 'strftime') else str(index)
                    
                    # Ensure all values are proper Python types (not numpy types)
                    open_price = float(row['open']) if pd.notna(row['open']) else 0.0
                    high_price = float(row['high']) if pd.notna(row['high']) else 0.0
                    low_price = float(row['low']) if pd.notna(row['low']) else 0.0
                    close_price = float(row['close']) if pd.notna(row['close']) else 0.0
                    volume = float(row.get('volume', 0)) if pd.notna(row.get('volume', 0)) else 0.0
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO market_data
                        (symbol, timeframe, timestamp, open_price, high_price, low_price, close_price, volume)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (symbol, timeframe, timestamp_str, open_price, high_price, low_price, close_price, volume))
                except Exception as e:
                    self.logger.error(f"Error storing row for {symbol} at {index}: {e}")
                    continue
            conn.commit()
    
    def get_market_data(self, symbol: str, timeframe: str, start_time: datetime = None,
                       end_time: datetime = None, limit: int = 1000) -> pd.DataFrame:
        """Get market data"""
        with self.get_connection() as conn:
            query = """
                SELECT timestamp, open_price, high_price, low_price, close_price, volume
                FROM market_data
                WHERE symbol = ? AND timeframe = ?
            """
            params = [symbol, timeframe]
            
            if start_time:
                query += " AND timestamp >= ?"
                # Convert datetime to string for SQLite compatibility
                start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(start_time, 'strftime') else str(start_time)
                params.append(start_time_str)
            
            if end_time:
                query += " AND timestamp <= ?"
                # Convert datetime to string for SQLite compatibility
                end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S') if hasattr(end_time, 'strftime') else str(end_time)
                params.append(end_time_str)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            df = pd.read_sql_query(query, conn, params=params)
            
            if not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                df.columns = ['open', 'high', 'low', 'close', 'volume']
            
            return df
    
    # Portfolio Snapshots
    def store_portfolio_snapshot(self, session_id: int, timestamp: datetime,
                               total_value: float, cash_balance: float, **kwargs):
        """Store portfolio snapshot"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            columns = ['session_id', 'timestamp', 'total_value', 'cash_balance']
            values = [session_id, timestamp, total_value, cash_balance]
            
            for key, value in kwargs.items():
                if key in ['unrealized_pnl', 'realized_pnl', 'open_positions', 'daily_pnl', 'drawdown']:
                    columns.append(key)
                    values.append(value)
            
            placeholders = ', '.join(['?' for _ in values])
            columns_str = ', '.join(columns)
            
            cursor.execute(f"""
                INSERT INTO portfolio_snapshots ({columns_str})
                VALUES ({placeholders})
            """, values)
            conn.commit()
    
    def get_portfolio_snapshots(self, session_id: int, start_time: datetime = None,
                              end_time: datetime = None) -> List[Dict]:
        """Get portfolio snapshots"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM portfolio_snapshots WHERE session_id = ?"
            params = [session_id]
            
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            
            query += " ORDER BY timestamp ASC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # Trading Signals
    def store_trading_signal(self, session_id: int, symbol: str, timestamp: datetime,
                           signal_type: str, signal_strength: float, confidence: float,
                           price: float, indicators: Dict = None):
        """Store trading signal"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trading_signals 
                (session_id, symbol, timestamp, signal_type, signal_strength, confidence, price, indicators)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, symbol, timestamp, signal_type, signal_strength, confidence, price,
                  json.dumps(indicators) if indicators else None))
            conn.commit()
            return cursor.lastrowid
    
    def get_trading_signals(self, session_id: int, limit: int = 1000) -> List[Dict]:
        """Get trading signals"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trading_signals 
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, limit))
            
            signals = []
            for row in cursor.fetchall():
                signal = dict(row)
                signal['indicators'] = json.loads(signal['indicators']) if signal['indicators'] else {}
                signals.append(signal)
            
            return signals
    
    # Performance Analytics
    def calculate_session_performance(self, session_id: int) -> Dict:
        """Calculate performance metrics for a session"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get session info
            cursor.execute("SELECT * FROM trading_sessions WHERE id = ?", (session_id,))
            session = dict(cursor.fetchone())
            
            # Get trades
            cursor.execute("SELECT * FROM trades WHERE session_id = ? AND status = 'closed'", (session_id,))
            trades = [dict(row) for row in cursor.fetchall()]
            
            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0.0,
                    'total_pnl': 0.0,
                    'avg_win': 0.0,
                    'avg_loss': 0.0,
                    'profit_factor': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0
                }
            
            # Calculate metrics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            total_pnl = sum(t['pnl'] for t in trades)
            wins = [t['pnl'] for t in trades if t['pnl'] > 0]
            losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
            
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            profit_factor = avg_win / avg_loss if avg_loss > 0 else 0
            
            # Get portfolio snapshots for drawdown calculation
            cursor.execute("""
                SELECT total_value FROM portfolio_snapshots 
                WHERE session_id = ? 
                ORDER BY timestamp ASC
            """, (session_id,))
            
            portfolio_values = [row[0] for row in cursor.fetchall()]
            max_drawdown = 0.0
            
            if portfolio_values:
                peak = portfolio_values[0]
                for value in portfolio_values:
                    if value > peak:
                        peak = value
                    drawdown = (peak - value) / peak
                    max_drawdown = max(max_drawdown, drawdown)
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': 0.0  # Would need returns data to calculate properly
            }
    
    # System Logs
    def log_system_event(self, log_level: str, component: str, message: str,
                        session_id: int = None, trade_id: int = None):
        """Log system event"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_logs (timestamp, log_level, component, message, session_id, trade_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.utcnow(), log_level, component, message, session_id, trade_id))
            conn.commit()
    
    def get_system_logs(self, limit: int = 1000, log_level: str = None) -> List[Dict]:
        """Get system logs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM system_logs"
            params = []
            
            if log_level:
                query += " WHERE log_level = ?"
                params.append(log_level)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # User Settings
    def get_setting(self, key: str) -> Any:
        """Get user setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value, setting_type FROM user_settings WHERE setting_key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                value, setting_type = row
                if setting_type == 'number':
                    return float(value)
                elif setting_type == 'boolean':
                    return value.lower() == 'true'
                elif setting_type == 'json':
                    return json.loads(value)
                else:
                    return value
            return None
    
    def set_setting(self, key: str, value: Any, setting_type: str = 'string'):
        """Set user setting"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if setting_type == 'json':
                value = json.dumps(value)
            elif setting_type == 'boolean':
                value = str(value).lower()
            else:
                value = str(value)
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_settings (setting_key, setting_value, setting_type, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, value, setting_type))
            conn.commit()
    
    # Cleanup methods
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data"""
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Clean up old market data
            cursor.execute("DELETE FROM market_data WHERE created_at < ?", (cutoff_date,))
            
            # Clean up old system logs
            cursor.execute("DELETE FROM system_logs WHERE timestamp < ?", (cutoff_date,))
            
            # Clean up old portfolio snapshots (keep only for active sessions)
            cursor.execute("""
                DELETE FROM portfolio_snapshots 
                WHERE created_at < ? AND session_id NOT IN (
                    SELECT id FROM trading_sessions WHERE status = 'active'
                )
            """, (cutoff_date,))
            
            conn.commit()
            
            self.logger.info(f"Cleaned up data older than {days_to_keep} days")

if __name__ == "__main__":
    # Test database manager
    logging.basicConfig(level=logging.INFO)
    
    db = DatabaseManager("test_trading_bot.db")
    
    # Test strategy creation
    strategy_id = db.create_strategy(
        "Test Scalping Strategy",
        "Test strategy for EUR_USD scalping",
        "scalping",
        "forex",
        "1m",
        {"fast_ema": 5, "slow_ema": 13}
    )
    
    print(f"Created strategy with ID: {strategy_id}")
    
    # Test session creation
    session_id = db.create_trading_session("backtest", strategy_id, "EUR_USD", 10000.0)
    print(f"Created session with ID: {session_id}")
    
    # Test trade creation
    trade_id = db.create_trade(
        session_id, "EUR_USD", "BUY", datetime.utcnow(),
        1.1234, 10000, stop_loss=1.1200, take_profit=1.1280
    )
    print(f"Created trade with ID: {trade_id}")
    
    print("Database manager test completed successfully!")