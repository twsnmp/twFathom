import os
import webview
from . import db
from . import collectors

class Bridge:
    def __init__(self, main_window=None):
        self._main_window = main_window
        self._dashboard_windows = {}
        self._main_window_closing = False

    def get_sources(self):
        return db.get_sources()

    def get_source(self, source_id):
        return db.get_source(source_id)

    def add_source(self, name, type_, config_dict, interval, data_type='unknown'):
        try:
            source_id = db.add_source(name, type_, config_dict, interval, data_type)
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

    def get_cpu_mem_disk_history(self, source_id, limit=-1):
        return db.get_cpu_mem_disk_history(source_id, limit)

    def get_process_load_history(self, source_id, limit=-1):
        return db.get_process_load_history(source_id, limit)

    def get_network_speed_history(self, source_id, limit=-1):
        return db.get_network_speed_history(source_id, limit)

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
        
        # Load saved window state from DB
        state = db.get_window_state(f"dashboard_{source_id}")
        if state:
            x = state.get('x')
            y = state.get('y')
            width = state.get('width', 640)
            height = state.get('height', 480)
        else:
            x = None
            y = None
            width = 640
            height = 480

        # Save active/open state as 1 in DB immediately
        db.save_window_state(f"dashboard_{source_id}", x, y, width, height, 1)
        
        sub_window = webview.create_window(
            title="", # Empty title ensures macOS frameless mode works correctly
            url=url,
            width=width,
            height=height,
            x=x,
            y=y,
            resizable=True,
            frameless=True,
            easy_drag=False,
            js_api=self
        )
        self._dashboard_windows[source_id] = sub_window

        def on_closing():
            # Fallback for native closes (like keyboard shortcut Cmd+W)
            if source_id not in self._dashboard_windows:
                return
            try:
                win_x = sub_window.x
                win_y = sub_window.y
                win_w = sub_window.width
                win_h = sub_window.height
                is_open = 1 if self._main_window_closing else 0
                db.save_window_state(f"dashboard_{source_id}", win_x, win_y, win_w, win_h, is_open)
            except Exception as e:
                print(f"Error saving dashboard state on closing fallback: {e}")
            
            if source_id in self._dashboard_windows:
                del self._dashboard_windows[source_id]

        sub_window.events.closing += on_closing

    def toggle_dashboard(self, source_id):
        if source_id in self._dashboard_windows:
            self.close_dashboard(source_id)
            return
        self.open_dashboard(source_id)

    def get_open_dashboards(self):
        return list(self._dashboard_windows.keys())

    def resize_dashboard(self, source_id, width, height):
        win = self._dashboard_windows.get(source_id)
        if win:
            try:
                win.resize(width, height)
            except Exception as e:
                print(f"Error resizing window: {e}")

    def minimize_dashboard(self, source_id):
        win = self._dashboard_windows.get(source_id)
        if win:
            try:
                win.minimize()
            except Exception as e:
                print(f"Error minimizing window: {e}")

    def close_dashboard(self, source_id, is_app_exiting=False):
        win = self._dashboard_windows.get(source_id)
        if win:
            try:
                # Save size and position, and update open status synchronously
                win_x = win.x
                win_y = win.y
                win_w = win.width
                win_h = win.height
                is_open = 1 if is_app_exiting else 0
                db.save_window_state(f"dashboard_{source_id}", win_x, win_y, win_w, win_h, is_open)
            except Exception as e:
                print(f"Error saving dashboard state in close_dashboard: {e}")
            
            try:
                win.destroy()
            except Exception as e:
                print(f"Error destroying window: {e}")
            
            # Remove from dict synchronously
            if source_id in self._dashboard_windows:
                del self._dashboard_windows[source_id]

    def clear_source_data(self, source_id):
        try:
            db.clear_source_data(source_id)
        except Exception as e:
            import traceback
            print(f"Error in clear_source_data: {e}")
            traceback.print_exc()
            raise e

    def auto_arrange_dashboards(self):
        if not self._main_window:
            return
            
        # Find active dashboard windows
        open_wins = []
        for source_id, win in list(self._dashboard_windows.items()):
            try:
                # verify window is active/accessible
                wx, wy = win.x, win.y
                open_wins.append((source_id, win, wx, wy))
            except Exception:
                pass
                
        target_screen = self._get_target_screen()
        sx, sy, sw, sh = self._get_screen_geometry(target_screen)
        
        margin_left = 10
        margin_right = 10
        margin_top = 50
        margin_bottom = 60
        
        avail_x = sx + margin_left
        avail_y = sy + margin_top
        avail_w = sw - margin_left - margin_right
        
        if len(open_wins) == 0:
            sources = db.get_sources()
            if not sources:
                return
            first_source_id = sources[0]['id']
            default_x = avail_x + 50
            default_y = avail_y + 50
            default_w = 640
            default_h = 480
            db.save_window_state(f"dashboard_{first_source_id}", default_x, default_y, default_w, default_h, 1)
            self.open_dashboard(first_source_id)
            return

        # Sort by y first, then x to find top-left closest window
        open_wins.sort(key=lambda item: (item[3], item[2]))
        
        # Base window is the first in the sorted list (closest to top-left)
        base_id, base_win, base_x, base_y = open_wins[0]
        base_w = base_win.width
        base_h = base_win.height
        
        gap = 10
        curr_x = base_x
        curr_y = base_y
        
        for i, (source_id, win, wx, wy) in enumerate(open_wins):
            if i == 0:
                # Base window stays at its current position
                self._apply_and_save_layout(win, source_id, base_x, base_y, base_w, base_h)
            else:
                next_x = curr_x + base_w + gap
                if next_x + base_w > avail_x + avail_w:
                    # Wrap to the next row, aligning left edge with the base window's left edge
                    curr_x = base_x
                    curr_y = curr_y + base_h + gap
                    x = curr_x
                    y = curr_y
                else:
                    curr_x = next_x
                    x = curr_x
                    y = curr_y
                self._apply_and_save_layout(win, source_id, x, y, base_w, base_h)

    def _get_screen_geometry(self, screen):
        x = 0
        y = 0
        w = screen.width
        h = screen.height
        
        if hasattr(screen, 'frame') and screen.frame is not None:
            frame = screen.frame
            if hasattr(frame, 'origin') and hasattr(frame.origin, 'x') and hasattr(frame.origin, 'y'):
                x = int(frame.origin.x)
                y = int(frame.origin.y)
            elif isinstance(frame, (tuple, list)) and len(frame) >= 4:
                x = int(frame[0])
                y = int(frame[1])
                w = int(frame[2])
                h = int(frame[3])
            elif isinstance(frame, dict):
                x = int(frame.get('x', 0))
                y = int(frame.get('y', 0))
                w = int(frame.get('width', w))
                h = int(frame.get('height', h))
                
        if hasattr(screen, 'x'):
            x = int(screen.x)
        if hasattr(screen, 'y'):
            y = int(screen.y)
            
        return x, y, w, h

    def _get_target_screen(self):
        try:
            main_center_x = self._main_window.x + self._main_window.width // 2
            main_center_y = self._main_window.y + self._main_window.height // 2
        except Exception:
            main_center_x = 0
            main_center_y = 0
            
        target_screen = None
        try:
            screens = webview.screens
            if screens:
                target_screen = screens[0]
                for screen in screens:
                    sx, sy, sw, sh = self._get_screen_geometry(screen)
                    if (sx <= main_center_x < sx + sw and
                        sy <= main_center_y < sy + sh):
                        target_screen = screen
                        break
        except Exception as e:
            print(f"Error obtaining screens: {e}")
            
        if not target_screen:
            # Fallback values
            class FallbackScreen:
                width = 1920
                height = 1080
                frame = None
            target_screen = FallbackScreen()
        return target_screen

    def _apply_and_save_layout(self, win, source_id, x, y, w, h):
        try:
            ix, iy, iw, ih = int(x), int(y), int(w), int(h)
            win.resize(iw, ih)
            win.move(ix, iy)
            db.save_window_state(f"dashboard_{source_id}", ix, iy, iw, ih, 1)
        except Exception as e:
            print(f"Error applying layout for window {source_id}: {e}")
