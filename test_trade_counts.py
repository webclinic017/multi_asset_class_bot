"""
Test script to verify trade counts are correctly retrieved from the database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database_manager import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_trade_counts():
    """Test that trade counts are correctly retrieved from trades table"""
    db = DatabaseManager()
    
    # Get recent sessions
    sessions = db.get_trading_sessions(limit=10)
    
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing Trade Counts for Recent Sessions")
    logger.info(f"{'='*80}\n")
    
    for session in sessions:
        session_id = session['id']
        session_type = session['session_type']
        strategy_name = session['strategy_name']
        
        # Skip non-backtest sessions
        if session_type != 'backtest':
            continue
        
        logger.info(f"\nSession ID: {session_id}")
        logger.info(f"Strategy: {strategy_name}")
        logger.info(f"Status: {session['status']}")
        
        # Get actual trades from database
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count all trades
            cursor.execute("""
                SELECT COUNT(*) FROM trades WHERE session_id = ?
            """, (session_id,))
            total_trades_db = cursor.fetchone()[0]
            
            # Count closed trades with P&L
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN pnl > 0 THEN 1 END) as winning,
                    COUNT(CASE WHEN pnl < 0 THEN 1 END) as losing,
                    SUM(CASE WHEN pnl IS NOT NULL THEN pnl ELSE 0 END) as total_pnl
                FROM trades
                WHERE session_id = ? AND status = 'closed'
            """, (session_id,))
            
            trade_stats = cursor.fetchone()
            closed_trades = trade_stats[0]
            winning_trades = trade_stats[1] or 0
            losing_trades = trade_stats[2] or 0
            total_pnl = trade_stats[3] or 0.0
            
            # Count portfolio snapshots
            cursor.execute("""
                SELECT COUNT(*) FROM portfolio_snapshots WHERE session_id = ?
            """, (session_id,))
            snapshot_count = cursor.fetchone()[0]
        
        logger.info(f"  Total trades in DB: {total_trades_db}")
        logger.info(f"  Closed trades: {closed_trades}")
        logger.info(f"  Winning trades: {winning_trades}")
        logger.info(f"  Losing trades: {losing_trades}")
        logger.info(f"  Total P&L: ${total_pnl:.2f}")
        logger.info(f"  Portfolio snapshots: {snapshot_count}")
        
        # Compare with session stored values
        logger.info(f"\n  Session stored values:")
        logger.info(f"    Total trades: {session.get('total_trades', 0)}")
        logger.info(f"    Winning trades: {session.get('winning_trades', 0)}")
        logger.info(f"    Losing trades: {session.get('losing_trades', 0)}")
        logger.info(f"    Final capital: ${session.get('final_capital', 0):.2f}")
        logger.info(f"    Initial capital: ${session.get('initial_capital', 0):.2f}")
        
        # Verify the fix
        if closed_trades > 0:
            expected_final = session.get('initial_capital', 100000) + total_pnl
            logger.info(f"\n  Verification:")
            logger.info(f"    Expected final capital: ${expected_final:.2f}")
            logger.info(f"    Actual stored final: ${session.get('final_capital', 0):.2f}")
            
            if abs(expected_final - session.get('final_capital', 0)) < 0.01:
                logger.info(f"    ✓ Final capital matches!")
            else:
                logger.warning(f"    ✗ Final capital mismatch!")
        
        logger.info(f"\n{'-'*80}")

if __name__ == "__main__":
    test_trade_counts()