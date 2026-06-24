import os
import sys
import time
import threading
import webview
from . import db
from . import collectors
from . import anomaly

class Bridge:
    def __init__(self, main_window=None):
        self._main_window = main_window
        self._dashboard_windows = {}
        self._main_window_closing = False
        self._anomaly_baselines = {}
        self._anomaly_baselines_lock = threading.Lock()

    def get_version_info(self):
        import subprocess
        version = "0.2.0"
        commit = "unknown"
        try:
            from . import __version__
            version = __version__
        except ImportError:
            pass
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=base_dir,
                stderr=subprocess.DEVNULL
            ).decode("utf-8").strip()
        except Exception:
            commit = "unknown"
        return {"version": version, "commit": commit}

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
                state_now = db.get_window_state(f"dashboard_{source_id}")
                if state_now and isinstance(state_now, dict):
                    win_x = state_now.get('x')
                    win_y = state_now.get('y')
                    win_w = state_now.get('width', 640)
                    win_h = state_now.get('height', 480)
                elif state_now is None:
                    # In production, if no state in DB, use default None/640/480
                    win_x = None
                    win_y = None
                    win_w = 640
                    win_h = 480
                else:
                    # Fallback for unit tests where db is mocked
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

        def on_moved(wx, wy):
            try:
                self._update_window_coords(source_id, x=int(wx), y=int(wy))
            except Exception as e:
                print(f"Error in on_moved event: {e}")
                
        def on_resized(ww, wh):
            try:
                self._update_window_coords(source_id, width=int(ww), height=int(wh))
            except Exception as e:
                print(f"Error in on_resized event: {e}")

        sub_window.events.moved += on_moved
        sub_window.events.resized += on_resized

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
                # Save size and position, and update open status from database state
                state = db.get_window_state(f"dashboard_{source_id}")
                if state and isinstance(state, dict):
                    win_x = state.get('x')
                    win_y = state.get('y')
                    win_w = state.get('width', 640)
                    win_h = state.get('height', 480)
                elif state is None:
                    # In production, if no state in DB, use default None/640/480
                    win_x = None
                    win_y = None
                    win_w = 640
                    win_h = 480
                else:
                    # Fallback for tests/environments where db is mocked
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
                # verify window is active/accessible using database state to avoid thread safety issues
                state = db.get_window_state(f"dashboard_{source_id}")
                if state and isinstance(state, dict):
                    wx = state.get('x') or 0
                    wy = state.get('y') or 0
                    ww = state.get('width') or 640
                    wh = state.get('height') or 480
                elif state is None:
                    # In production, if no state in DB, use default 0/640/480
                    wx = 0
                    wy = 0
                    ww = 640
                    wh = 480
                else:
                    # Fallback for unit tests where db is mocked
                    wx = win.x
                    wy = win.y
                    ww = win.width
                    wh = win.height
                open_wins.append((source_id, win, wx, wy, ww, wh))
            except Exception as e:
                print(f"Error checking window state for source_id {source_id}: {e}")
                
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
        # item[3] is wy, item[2] is wx
        open_wins.sort(key=lambda item: (item[3], item[2]))
        
        # Base window is the first in the sorted list (closest to top-left)
        base_id, base_win, base_x, base_y, base_w, base_h = open_wins[0]
        
        gap = 10
        curr_x = base_x
        curr_y = base_y
        
        for i, (source_id, win, wx, wy, ww, wh) in enumerate(open_wins):
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

    def run_anomaly_detection(self, source_id):
        """
        指定されたデータソースの履歴データを取得し、過去すべてのデータをもとに異常検知アルゴリズムを実行します。
        パフォーマンス向上のため、過去すべての統計値はSQLiteで計算されバックグラウンドでキャッシュされます。
        """
        try:
            source = db.get_source(source_id)
            if not source:
                return {"status": "error", "message": "データソースが見つかりません"}
                
            data_type = source.get('data_type')
            limit = -1  # 全期間の履歴を使用 (制限なし)
            
            # キャッシュされた過去すべての基準統計情報を取得
            baseline_stats = self._get_cached_baseline(source_id, data_type)
            
            if data_type == 'environment':
                history = db.get_environment_history(source_id, limit)
            elif data_type == 'traffic':
                history = db.get_traffic_history(source_id, limit)
            elif data_type == 'cpu_mem_disk':
                history = db.get_cpu_mem_disk_history(source_id, limit)
            elif data_type == 'process_load':
                history = db.get_process_load_history(source_id, limit)
            elif data_type == 'network_speed':
                history = db.get_network_speed_history(source_id, limit)
            else:
                return {"status": "error", "message": f"未対応のデータタイプです: {data_type}"}
                
            # 計算の実行（基準統計がある場合はそれを使用、ない場合は直近データから計算）
            result = anomaly.calculate_anomaly(history, data_type, baseline_stats=baseline_stats)
            return result
        except Exception as e:
            import traceback
            print(f"Error in run_anomaly_detection: {e}")
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _get_cached_baseline(self, source_id, data_type):
        key = (source_id, data_type)
        now = time.time()
        
        with self._anomaly_baselines_lock:
            entry = self._anomaly_baselines.get(key)
            if entry:
                stats, last_computed, is_computing = entry
                # 5分以上経過しており、かつ現在計算中でなければバックグラウンドスレッドで更新を開始
                if now - last_computed > 300 and not is_computing:
                    self._anomaly_baselines[key] = (stats, last_computed, True)
                    threading.Thread(
                        target=self._bg_compute_baseline,
                        args=(source_id, data_type),
                        daemon=True
                    ).start()
                return stats
            else:
                # 初回：計算中フラグを立ててバックグラウンドスレッドを起動し、一旦Noneを返す（直近データでの算出にフォールバック）
                self._anomaly_baselines[key] = (None, 0, True)
                threading.Thread(
                    target=self._bg_compute_baseline,
                    args=(source_id, data_type),
                    daemon=True
                ).start()
                return None

    def _bg_compute_baseline(self, source_id, data_type):
        try:
            # SQLiteウィンドウ関数を用いて過去すべての統計情報（平均・不偏分散）を計算
            stats = db.get_baseline_stats(source_id, data_type)
            
            with self._anomaly_baselines_lock:
                self._anomaly_baselines[(source_id, data_type)] = (stats, time.time(), False)
        except Exception as e:
            print(f"Error in _bg_compute_baseline for source_id={source_id}, type={data_type}: {e}")
            with self._anomaly_baselines_lock:
                # エラー時は計算中フラグを下ろす
                entry = self._anomaly_baselines.get((source_id, data_type))
                if entry:
                    stats, last_computed, _ = entry
                    self._anomaly_baselines[(source_id, data_type)] = (stats, last_computed, False)

    def _update_window_coords(self, source_id, x=None, y=None, width=None, height=None):
        state = db.get_window_state(f"dashboard_{source_id}")
        if not state:
            state = {'x': None, 'y': None, 'width': 640, 'height': 480}
        
        new_x = x if x is not None else state.get('x')
        new_y = y if y is not None else state.get('y')
        new_w = width if width is not None else state.get('width', 640)
        new_h = height if height is not None else state.get('height', 480)
        
        db.save_window_state(f"dashboard_{source_id}", new_x, new_y, new_w, new_h, 1)

    def get_window_position_from_db(self, source_id):
        try:
            state = db.get_window_state(f"dashboard_{source_id}")
            if state and isinstance(state, dict):
                return {"x": state.get('x') or 0, "y": state.get('y') or 0}
        except Exception as e:
            print(f"Error in get_window_position_from_db: {e}")
        return {"x": 0, "y": 0}

    def move_dashboard(self, source_id, x, y):
        win = self._dashboard_windows.get(source_id)
        if win:
            try:
                win.move(int(x), int(y))
                # Explicitly update coordinates cache in DB
                self._update_window_coords(source_id, x=int(x), y=int(y))
            except Exception as e:
                print(f"Error moving window: {e}")

    def start_drag(self, source_id, button, screen_x, screen_y, timestamp):
        if not sys.platform.startswith('linux'):
            return
        win = self._dashboard_windows.get(source_id)
        if win:
            try:
                from gi.repository import GLib, Gtk
                def _do_drag():
                    try:
                        gtk_win = getattr(win, 'native', None)
                        if gtk_win:
                            event_time = Gtk.get_current_event_time()
                            if event_time == 0:
                                event_time = int(timestamp) or 0
                            gtk_win.begin_move_drag(
                                int(button) + 1,  # GTK button is 1-based (left=1)
                                int(screen_x),
                                int(screen_y),
                                event_time
                            )
                    except Exception as ex:
                        print(f"Error in GTK begin_move_drag: {ex}")
                GLib.idle_add(_do_drag)
            except Exception as e:
                print(f"Error starting native GTK drag: {e}")
