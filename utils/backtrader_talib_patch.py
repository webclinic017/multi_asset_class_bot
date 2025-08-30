"""
Direct patch for Backtrader's TA-Lib integration
Fixes compatibility issues with newer TA-Lib versions
"""

def patch_backtrader_talib():
    """
    Patch Backtrader's TA-Lib module to handle newer TA-Lib versions
    """
    try:
        import talib.abstract
        
        # First apply the basic TA-Lib patches
        if not hasattr(talib.abstract, 'TA_FUNC_FLAGS'):
            talib.abstract.TA_FUNC_FLAGS = {
                16777216: 'Output scale same as input',
                67108864: 'Output is over volume', 
                134217728: 'Function has an unstable period',
                268435456: 'Output is a candlestick'
            }
            
        if not hasattr(talib.abstract, 'TA_OUTPUT_FLAGS'):
            talib.abstract.TA_OUTPUT_FLAGS = {
                'Line': 1,
                'Dotted Line': 2, 
                'Dashed Line': 4,
                'Histogram': 16,
                'Upper Limit': 2048,
                'Lower Limit': 4096,
                'Values represent an upper limit': 2048,
                'Values represent a lower limit': 4096,
                1: 'Line',
                2: 'Dotted Line',
                4: 'Dashed Line', 
                16: 'Histogram',
                2048: 'Upper Limit',
                4096: 'Lower Limit'
            }
            
        if not hasattr(talib.abstract, 'TA_INPUT_FLAGS'):
            talib.abstract.TA_INPUT_FLAGS = {
                1: 'Open',
                2: 'High', 
                4: 'Low',
                8: 'Close',
                16: 'Volume',
                32: 'Open Interest',
                64: 'Timestamp'
            }
        
        # Now patch the Backtrader TA-Lib file directly
        import backtrader.talib as bt_talib
        
        # Check if the problematic reverse mapping exists
        if hasattr(bt_talib, 'R_TA_OUTPUT_FLAGS'):
            # Add missing mappings to the reverse dictionary
            additional_mappings = {
                'Values represent an upper limit': 2048,
                'Values represent a lower limit': 4096,
                'Line': 1,
                'Dotted Line': 2,
                'Dashed Line': 4,
                'Histogram': 16,
                'Upper Limit': 2048,
                'Lower Limit': 4096
            }
            
            for key, value in additional_mappings.items():
                if key not in bt_talib.R_TA_OUTPUT_FLAGS:
                    bt_talib.R_TA_OUTPUT_FLAGS[key] = value
                    
        print("Backtrader TA-Lib compatibility patch applied successfully")
        return True
        
    except Exception as e:
        print(f"Error applying Backtrader TA-Lib patch: {e}")
        return False

def create_safe_backtrader_import():
    """
    Create a safe way to import Backtrader with TA-Lib compatibility
    """
    try:
        # Apply patches first
        patch_backtrader_talib()
        
        # Now try to import Backtrader
        import backtrader as bt
        return bt
        
    except Exception as e:
        print(f"Error importing Backtrader with patches: {e}")
        return None

if __name__ == "__main__":
    print("Testing Backtrader TA-Lib patch...")
    result = patch_backtrader_talib()
    
    if result:
        try:
            import backtrader as bt
            print("Backtrader imported successfully after patching!")
        except Exception as e:
            print(f"Backtrader import still failed: {e}")
    else:
        print("Patch failed")