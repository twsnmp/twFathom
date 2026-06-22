import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Append the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from twfathom.bridge import Bridge

class TestBridge(unittest.TestCase):
    def test_get_version_info(self):
        bridge = Bridge()
        info = bridge.get_version_info()
        self.assertIn("version", info)
        self.assertIn("commit", info)
        self.assertIsInstance(info["version"], str)
        self.assertIsInstance(info["commit"], str)

    @patch('subprocess.check_output')
    def test_get_version_info_git_error(self, mock_check_output):
        mock_check_output.side_effect = Exception("git command not found")
        bridge = Bridge()
        info = bridge.get_version_info()
        self.assertEqual(info["commit"], "unknown")

if __name__ == '__main__':
    unittest.main()
