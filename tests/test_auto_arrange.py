import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Append the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from twfathom.bridge import Bridge

class MockWindow:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    def move(self, x, y):
        self.x = x
        self.y = y
        
    def resize(self, w, h):
        self.width = w
        self.height = h

class MockScreen:
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

class TestAutoArrange(unittest.TestCase):
    @patch('twfathom.bridge.db')
    @patch('twfathom.bridge.webview')
    def test_auto_arrange_dashboards_with_windows(self, mock_webview, mock_db):
        # Setup screens mock
        mock_webview.screens = [MockScreen(0, 0, 1920, 1080)]
        
        # Setup main window mock (located in center of screen)
        main_win = MockWindow(100, 100, 1100, 800)
        bridge = Bridge(main_window=main_win)
        
        # Open 3 dashboard windows
        # win1 is closest to top-left
        win1 = MockWindow(200, 150, 500, 400)
        win2 = MockWindow(800, 150, 400, 300)
        win3 = MockWindow(200, 600, 400, 300)
        
        bridge._dashboard_windows = {
            1: win1,
            2: win2,
            3: win3
        }
        
        # Call auto_arrange_dashboards
        bridge.auto_arrange_dashboards()
        
        # Base window is win1
        self.assertEqual(win1.width, 500)
        self.assertEqual(win1.height, 400)
        self.assertEqual(win1.x, 200)
        self.assertEqual(win1.y, 150)
        
        # Next window should be win2.
        self.assertEqual(win2.width, 500)
        self.assertEqual(win2.height, 400)
        self.assertEqual(win2.x, 710)
        self.assertEqual(win2.y, 150)
        
        # Next window is win3.
        self.assertEqual(win3.width, 500)
        self.assertEqual(win3.height, 400)
        self.assertEqual(win3.x, 1220)
        self.assertEqual(win3.y, 150)

    @patch('twfathom.bridge.db')
    @patch('twfathom.bridge.webview')
    def test_auto_arrange_dashboards_with_wrapping(self, mock_webview, mock_db):
        mock_webview.screens = [MockScreen(0, 0, 1280, 1024)]
        main_win = MockWindow(100, 100, 500, 400)
        bridge = Bridge(main_window=main_win)
        
        # 3 windows
        # Base window is win1: (x=100, y=100, w=600, h=400)
        win1 = MockWindow(100, 100, 600, 400)
        win2 = MockWindow(800, 100, 400, 300)
        win3 = MockWindow(200, 600, 400, 300)
        
        bridge._dashboard_windows = {
            1: win1,
            2: win2,
            3: win3
        }
        
        bridge.auto_arrange_dashboards()
        
        # Win1 is base
        self.assertEqual(win1.x, 100)
        self.assertEqual(win1.y, 100)
        
        # Win2 tries to go to x = 100 + 600 + 10 = 710.
        # Check right edge: 710 + 600 = 1310 > 1260 (avail_x + avail_w).
        # It overflows, so it must wrap!
        # Wrap: x = base_x = 100, y = base_y + base_h + gap = 100 + 400 + 10 = 510.
        self.assertEqual(win2.x, 100)
        self.assertEqual(win2.y, 510)
        
        # Win3 goes to x = 100 + 600 + 10 = 710.
        # Right edge: 710 + 600 = 1310 > 1260.
        # It overflows again, wraps!
        # Wrap: x = base_x = 100, y = 510 + 400 + 10 = 920.
        self.assertEqual(win3.x, 100)
        self.assertEqual(win3.y, 920)

    @patch('twfathom.bridge.db')
    @patch('twfathom.bridge.webview')
    def test_auto_arrange_dashboards_empty(self, mock_webview, mock_db):
        mock_webview.screens = [MockScreen(0, 0, 1920, 1080)]
        main_win = MockWindow(100, 100, 800, 600)
        bridge = Bridge(main_window=main_win)
        
        # Mock database sources
        mock_db.get_sources.return_value = [{'id': 42, 'name': 'First Source'}]
        
        # Spy on open_dashboard
        bridge.open_dashboard = MagicMock()
        
        bridge.auto_arrange_dashboards()
        
        # Verify first source state is saved and opened
        mock_db.save_window_state.assert_called_once_with(
            "dashboard_42",
            10 + 50, # avail_x + 50
            50 + 50, # avail_y + 50
            640,
            480,
            1
        )
        bridge.open_dashboard.assert_called_once_with(42)

if __name__ == '__main__':
    unittest.main()
