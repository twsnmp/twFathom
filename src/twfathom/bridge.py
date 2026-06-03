import os
import webview
from . import db
from . import collectors

class Bridge:
    def __init__(self, main_window=None):
        self._main_window = main_window
        self._dashboard_windows = {}

    def get_sources(self):
        return db.get_sources()

    def get_source(self, source_id):
        return db.get_source(source_id)

    def add_source(self, name, type_, config_dict, interval):
        try:
            source_id = db.add_source(name, type_, config_dict, interval)
            collectors.start_collector(source_id)
            return source_id
        except Exception as e:
            import traceback
            print(f"Error in add_source: {e}")
            traceback.print_exc()
            raise e

    def update_source(self, source_id, name, type_, config_dict, interval, data_type, active):
        try:
            db.update_source(source_id, name, type_, config_dict, interval, data_type, active)
            if active:
                collectors.start_collector(source_id)
            else:
                collectors.stop_collector(source_id)
        except Exception as e:
            import traceback
            print(f"Error in update_source: {e}")
            traceback.print_exc()
            raise e

    def delete_source(self, source_id):
        try:
            collectors.stop_collector(source_id)
            db.delete_source(source_id)
            if source_id in self._dashboard_windows:
                try:
                    self._dashboard_windows[source_id].destroy()
                except Exception:
                    pass
                del self._dashboard_windows[source_id]
        except Exception as e:
            import traceback
            print(f"Error in delete_source: {e}")
            traceback.print_exc()
            raise e

    def toggle_source_active(self, source_id):
        source = db.get_source(source_id)
        if source:
            new_active = 0 if source['active'] else 1
            db.update_source(
                source_id, source['name'], source['type'],
                source['config'], source['interval'], source['data_type'], new_active
            )
            if new_active:
                collectors.start_collector(source_id)
            else:
                collectors.stop_collector(source_id)
            return new_active
        return None

    def get_environment_history(self, source_id, limit=-1):
        return db.get_environment_history(source_id, limit)

    def get_traffic_history(self, source_id, limit=-1):
        return db.get_traffic_history(source_id, limit)

    def open_dashboard(self, source_id):
        if source_id in self._dashboard_windows:
            try:
                self._dashboard_windows[source_id].focus()
                return
            except Exception:
                pass
                
        source = db.get_source(source_id)
        if not source:
            return
            
        base_dir = os.path.dirname(os.path.abspath(__file__))
        url = f"file://{os.path.join(base_dir, 'gui', 'dashboard', 'index.html')}?id={source_id}"
        
        sub_window = webview.create_window(
            title=f"twFathom - {source['name']} Dashboard",
            url=url,
            width=640,
            height=480,
            resizable=True,
            js_api=self
        )
        self._dashboard_windows[source_id] = sub_window

    def clear_source_data(self, source_id):
        try:
            db.clear_source_data(source_id)
        except Exception as e:
            import traceback
            print(f"Error in clear_source_data: {e}")
            traceback.print_exc()
            raise e
