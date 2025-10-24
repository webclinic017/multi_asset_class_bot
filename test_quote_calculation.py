def calculate_quotes(mid_price, current_inventory, volatility, params):
    """
    Calculate optimal bid/ask quotes based on:
    - Mid-market price
    - Current inventory position
    - Market volatility
    """
    # Base spread adjusted for volatility
    if params['volatility_adjustment'] and volatility > 0:
        base_spread = params['spread_width'] * (1 + volatility * 20)  # Using the multiplier from the strategy
    else:
        base_spread = params['spread_width']
    
    # Ensure spread is within bounds
    base_spread = max(params['min_spread'], min(base_spread, params['max_spread']))
    
    # Inventory skew - widen spread on side with inventory
    inventory_ratio = current_inventory / params['max_inventory'] if params['max_inventory'] > 0 else 0
    
    # Calculate bid and ask skews
    bid_skew = base_spread * (1 + abs(inventory_ratio) * params['inventory_skew_factor'])
    ask_skew = base_spread * (1 + abs(inventory_ratio) * params['inventory_skew_factor'])
    
    # Adjust prices based on inventory direction
    if inventory_ratio > 0:  # Long position, favor selling
        bid_price = mid_price - bid_skew * (1 + inventory_ratio)
        ask_price = mid_price + ask_skew * (1 - inventory_ratio)
    elif inventory_ratio < 0:  # Short position, favor buying
        bid_price = mid_price - bid_skew * (1 + abs(inventory_ratio))
        ask_price = mid_price + ask_skew * (1 - abs(inventory_ratio))
    else:  # Neutral position
        bid_price = mid_price - bid_skew
        ask_price = mid_price + ask_skew
    
    return {
        'bid': round(bid_price, 5),
        'ask': round(ask_price, 5),
        'bid_size': 1,  # Simplified size calculation
        'ask_size': 1
    }

def test_quote_calculation():
    """Test the quote calculation logic of the Market Making HFT strategy"""
    print("Testing Market Making HFT strategy quote calculation...")
    
    # Sample parameters from the database
    params = {
        'spread_width': 0.0005,
        'min_spread': 0.0002,
        'max_spread': 0.002,
        'max_inventory': 5,
        'quote_refresh_time': 3,
        'inventory_skew_factor': 1.0,
        'inventory_rebalance_threshold': 0.6,
        'volatility_lookback': 20,
        'adaptive_spread': True,
        'max_orders_per_side': 2,
        'order_size': 1,
        'max_position_size': 5,
        'max_daily_trades': 1000,
        'circuit_breaker': 0.1,
        'risk_limit': 0.05,
        'target_sharpe': 2.0,
        'target_daily_return': 0.01,
        'volatility_window': 20,
        'volatility_adjustment': True,
        'initial_capital': 100000,
        'printlog': False
    }
    
    print("Strategy parameters:")
    for key, value in params.items():
        print(f"  {key}: {value}")
    
    # Sample data point
    mid_price = 6696.38  # Mid price from our data
    current_inventory = 0  # Start neutral
    volatility = 0.001  # Sample volatility
    
    print(f"\nSample calculation:")
    print(f"  Mid price: {mid_price:.2f}")
    print(f"  Current inventory: {current_inventory}")
    print(f"  Volatility: {volatility:.6f}")
    
    # Calculate quotes
    try:
        quotes = calculate_quotes(mid_price, current_inventory, volatility, params)
        print(f"\nCalculated quotes:")
        print(f"  Bid price: {quotes['bid']:.2f}")
        print(f"  Ask price: {quotes['ask']:.2f}")
        print(f"  Bid size: {quotes['bid_size']}")
        print(f"  Ask size: {quotes['ask_size']}")
        
        # Check if the quotes make sense
        spread = quotes['ask'] - quotes['bid']
        print(f"  Spread: {spread:.2f}")
        print(f"  Mid price: {mid_price:.2f}")
        print(f"  Bid distance from mid: {mid_price - quotes['bid']:.2f}")
        print(f"  Ask distance from mid: {quotes['ask'] - mid_price:.2f}")
        
        # Check if the spread is reasonable for ES futures
        # ES futures typically have point values of $50 per point
        # So a spread of 1 point = $50
        print(f"\nSpread analysis:")
        print(f"  Spread in points: {spread:.2f}")
        print(f"  Spread value: ${spread * 50:.2f}")
        
        # Let's also test with different inventory levels
        print(f"\n=== Testing with different inventory levels ===")
        for inventory in [-2, -1, 0, 1, 2]:
            quotes = calculate_quotes(mid_price, inventory, volatility, params)
            spread = quotes['ask'] - quotes['bid']
            print(f"  Inventory {inventory}: Bid={quotes['bid']:.2f}, Ask={quotes['ask']:.2f}, Spread={spread:.2f}")
        
    except Exception as e:
        print(f"ERROR calculating quotes: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_quote_calculation()