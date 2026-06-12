import os
import webview
from . import db
from . import collectors
from .bridge import Bridge

def main():
    # Force X11 backend on Wayland to allow absolute window positioning (auto-arrange)
    if os.environ.get('XDG_SESSION_TYPE') == 'wayland' or 'WAYLAND_DISPLAY' in os.environ:
        if 'GDK_BACKEND' not in os.environ:
            os.environ['GDK_BACKEND'] = 'x11'

    # If GDK_BACKEND is x11, disable WebKit compositing/DMABUF to prevent black screens
    if os.environ.get('GDK_BACKEND') == 'x11':
        os.environ['WEBKIT_DISABLE_COMPOSITING_MODE'] = '1'
        os.environ['WEBKIT_DISABLE_DMABUF_RENDERER'] = '1'

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
    
    # Set closing flag when main window starts closing
    def on_closing():
        api_bridge._main_window_closing = True

    main_window.events.closing += on_closing

    # Shut down collectors gracefully and close all sub-windows when closing the main window
    def on_closed():
        collectors.stop_all_collectors()
        # Close all active dashboard sub-windows and save their state
        for source_id in list(api_bridge._dashboard_windows.keys()):
            try:
                api_bridge.close_dashboard(source_id, is_app_exiting=True)
            except Exception:
                pass
        
    main_window.events.closed += on_closed

    # Restore dashboards that were open on last main window close
    def on_loaded():
        try:
            sources = db.get_sources()
            for src in sources:
                source_id = src['id']
                state = db.get_window_state(f"dashboard_{source_id}")
                if state and state.get('is_open'):
                    api_bridge.open_dashboard(source_id)
        except Exception as e:
            print(f"Error restoring dashboards: {e}")

    main_window.events.loaded += on_loaded
    
    # Start pywebview
    webview.start(debug=False)

if __name__ == '__main__':
    main()
