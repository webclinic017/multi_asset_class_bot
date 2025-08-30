"""
TA-Lib Compatibility Patch for Backtrader
Adds missing attributes for newer TA-Lib versions
"""

def patch_talib_for_backtrader():
    """
    Patch TA-Lib to add missing attributes required by Backtrader
    """
    try:
        import talib.abstract
        
        # Check if TA_FUNC_FLAGS is missing (newer versions)
        if not hasattr(talib.abstract, 'TA_FUNC_FLAGS'):
            print("Patching TA-Lib: Adding missing TA_FUNC_FLAGS attribute")
            
            # Define the missing TA_FUNC_FLAGS dictionary
            # These are the standard TA-Lib function flags
            talib.abstract.TA_FUNC_FLAGS = {
                16777216: 'Output scale same as input',
                67108864: 'Output is over volume', 
                134217728: 'Function has an unstable period',
                268435456: 'Output is a candlestick'
            }
            
        # Check if TA_OUTPUT_FLAGS is missing
        if not hasattr(talib.abstract, 'TA_OUTPUT_FLAGS'):
            print("Patching TA-Lib: Adding missing TA_OUTPUT_FLAGS attribute")
            
            # Define the missing TA_OUTPUT_FLAGS dictionary
            # Map string descriptions to numeric flags for backward compatibility
            talib.abstract.TA_OUTPUT_FLAGS = {
                'Line': 1,
                'Dotted Line': 2,
                'Dashed Line': 4,
                'Histogram': 16,
                'Upper Limit': 2048,
                'Lower Limit': 4096,
                'Values represent an upper limit': 2048,
                'Values represent a lower limit': 4096,
                # Additional mappings for newer TA-Lib versions
                1: 'Line',
                2: 'Dotted Line',
                4: 'Dashed Line',
                16: 'Histogram',
                2048: 'Upper Limit',
                4096: 'Lower Limit'
            }
            
        # Check if TA_INPUT_FLAGS is missing
        if not hasattr(talib.abstract, 'TA_INPUT_FLAGS'):
            print("Patching TA-Lib: Adding missing TA_INPUT_FLAGS attribute")
            
            talib.abstract.TA_INPUT_FLAGS = {
                1: 'Open',
                2: 'High', 
                4: 'Low',
                8: 'Close',
                16: 'Volume',
                32: 'Open Interest',
                64: 'Timestamp'
            }
            
        print("TA-Lib compatibility patch applied successfully")
        return True
        
    except ImportError:
        print("TA-Lib not available - patch not needed")
        return False
    except Exception as e:
        print(f"Error applying TA-Lib compatibility patch: {e}")
        return False

def verify_patch():
    """
    Verify that the patch was applied correctly
    """
    try:
        import talib.abstract
        
        required_attrs = ['TA_FUNC_FLAGS', 'TA_OUTPUT_FLAGS', 'TA_INPUT_FLAGS']
        missing_attrs = []
        
        for attr in required_attrs:
            if not hasattr(talib.abstract, attr):
                missing_attrs.append(attr)
                
        if missing_attrs:
            print(f"Patch verification failed - missing attributes: {missing_attrs}")
            return False
        else:
            print("Patch verification successful - all required attributes present")
            return True
            
    except ImportError:
        print("TA-Lib not available for verification")
        return False
    except Exception as e:
        print(f"Error verifying patch: {e}")
        return False

if __name__ == "__main__":
    print("TA-Lib Compatibility Patch")
    print("=" * 30)
    
    # Apply the patch
    success = patch_talib_for_backtrader()
    
    if success:
        # Verify the patch
        verify_patch()
        
        # Test Backtrader import
        try:
            print("\nTesting Backtrader import...")
            import backtrader as bt
            print("Backtrader imported successfully!")
            
            # Test TA-Lib integration
            print("Testing TA-Lib integration with Backtrader...")
            import backtrader.talib
            print("TA-Lib integration with Backtrader successful!")
            
        except Exception as e:
            print(f"Error testing Backtrader integration: {e}")
    else:
        print("Patch application failed")