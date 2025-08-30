"""
Startup patch to ensure TA-Lib compatibility
This should be imported before any Backtrader imports
"""

def apply_startup_patches():
    """Apply all necessary patches for compatibility"""
    try:
        # Apply TA-Lib compatibility patch
        from utils.talib_compatibility_patch import patch_talib_for_backtrader
        patch_talib_for_backtrader()
        return True
    except Exception as e:
        print(f"Warning: Could not apply startup patches: {e}")
        return False

# Auto-apply patches when this module is imported
if __name__ != "__main__":
    apply_startup_patches()