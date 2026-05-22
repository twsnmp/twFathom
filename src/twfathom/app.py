import os
import webview
from . import db
from . import collectors
from .bridge import Bridge

def main():
    # Initialize SQLite database
    db.init_db()
    
    # Start background collectors for active sources
    collectors.start_all_collectors()
    
    # Define main console HTML URL
    base_dir = os.path.dirname(os.path.abspath(__file__))
    url = f"file://{os.path.join(base_dir, 'gui', 'main', 'index.html')}"
    
    # Initialize the Javascript API bridge
    api_bridge = Bridge()
    
    main_window = webview.create_window(
        title="twFathom - Main Console",
        url=url,
        width=1100,
        height=800,
        resizable=True,
        js_api=api_bridge
    )
    api_bridge._main_window = main_window
    
    # Shut down collectors gracefully when closing the main window
    def on_closed():
        collectors.stop_all_collectors()
        
    main_window.events.closed += on_closed
    
    # Start pywebview with devtools enabled
    webview.start(debug=True)

if __name__ == '__main__':
    main()
