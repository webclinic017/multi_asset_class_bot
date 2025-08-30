"""
VS Code Plotly Visualization Fix
Ensures Plotly charts display properly in VS Code interactive window
"""

import os
import sys
from typing import Optional, Any

def setup_plotly_for_vscode():
    """
    Configure Plotly to work properly in VS Code interactive window
    """
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
        
        # Check if running in VS Code
        if is_vscode_environment():
            print("Configuring Plotly for VS Code interactive window...")
            
            # Set the default renderer for VS Code
            pio.renderers.default = "vscode"
            
            # Also try notebook renderer as fallback
            if "vscode" not in pio.renderers:
                pio.renderers.default = "notebook"
                
            # Enable widget support
            try:
                import plotly.offline as pyo
                pyo.init_notebook_mode(connected=True)
            except:
                pass
                
            print("Plotly configured for VS Code")
            return True
        else:
            # Use browser renderer for non-VS Code environments
            pio.renderers.default = "browser"
            return True
            
    except ImportError:
        print("Plotly not available - visualization disabled")
        return False
    except Exception as e:
        print(f"Error configuring Plotly: {e}")
        return False

def is_vscode_environment() -> bool:
    """
    Detect if running in VS Code environment
    """
    # Check for VS Code specific environment variables
    vscode_indicators = [
        'VSCODE_PID',
        'VSCODE_IPC_HOOK',
        'VSCODE_IPC_HOOK_CLI',
        'TERM_PROGRAM'
    ]
    
    for indicator in vscode_indicators:
        if indicator in os.environ:
            if indicator == 'TERM_PROGRAM' and os.environ[indicator] == 'vscode':
                return True
            elif indicator != 'TERM_PROGRAM':
                return True
    
    # Check if running in Jupyter-like environment (VS Code interactive)
    try:
        from IPython import get_ipython
        if get_ipython() is not None:
            return True
    except ImportError:
        pass
    
    return False

def create_vscode_compatible_plot(fig, title: str = "Trading Bot Visualization", 
                                 filename: Optional[str] = None, 
                                 show_in_browser: bool = False):
    """
    Create a plot that works in VS Code interactive window
    """
    try:
        import plotly.graph_objects as go
        import plotly.io as pio
        
        # Ensure Plotly is configured
        setup_plotly_for_vscode()
        
        if is_vscode_environment():
            # For VS Code, use show() which should display inline
            print(f"Displaying {title} in VS Code interactive window...")
            fig.show()
            
            # Also save as HTML file as backup
            if filename:
                html_file = f"{filename}.html"
                fig.write_html(html_file)
                print(f"Chart also saved as: {html_file}")
                
                if show_in_browser:
                    import webbrowser
                    webbrowser.open(f"file://{os.path.abspath(html_file)}")
        else:
            # For non-VS Code environments, save as HTML and optionally open in browser
            if not filename:
                filename = "trading_visualization"
            
            html_file = f"{filename}.html"
            fig.write_html(html_file)
            print(f"Chart saved as: {html_file}")
            
            if show_in_browser:
                import webbrowser
                webbrowser.open(f"file://{os.path.abspath(html_file)}")
                
        return True
        
    except Exception as e:
        print(f"Error creating plot: {e}")
        return False

def test_plotly_in_vscode():
    """
    Test Plotly functionality in VS Code
    """
    try:
        import plotly.graph_objects as go
        import numpy as np
        
        # Setup Plotly for VS Code
        setup_plotly_for_vscode()
        
        # Create a simple test plot
        x = np.linspace(0, 10, 100)
        y = np.sin(x)
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=x, y=y, mode='lines', name='Test Line'))
        fig.update_layout(
            title="Plotly Test in VS Code",
            xaxis_title="X Axis",
            yaxis_title="Y Axis"
        )
        
        # Display the plot
        success = create_vscode_compatible_plot(
            fig, 
            title="Plotly Test", 
            filename="plotly_test",
            show_in_browser=False
        )
        
        if success:
            print("Plotly test successful!")
        else:
            print("Plotly test failed")
            
        return success
        
    except Exception as e:
        print(f"Error in Plotly test: {e}")
        return False

# Auto-configure when module is imported
if __name__ != "__main__":
    setup_plotly_for_vscode()

if __name__ == "__main__":
    print("Testing Plotly in VS Code...")
    test_plotly_in_vscode()