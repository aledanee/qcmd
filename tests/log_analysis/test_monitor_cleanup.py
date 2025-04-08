#!/usr/bin/env python3
"""
Tests for the cleanup functionality in the monitor module.
"""
import unittest
import os
import sys
import json
import tempfile
import signal
import time
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.monitor import save_monitors, load_monitors, cleanup_stale_monitors


class TestMonitorCleanup(unittest.TestCase):
    """Test the cleanup functionality in the monitor module."""
    
    def setUp(self):
        """Set up the test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.monitor_file_path = os.path.join(self.temp_dir.name, 'monitors.json')
        self.test_log_file = os.path.join(self.temp_dir.name, 'test.log')
        
        # Create a test log file
        with open(self.test_log_file, 'w') as f:
            f.write("Test log line 1\nTest log line 2\n")
    
    def tearDown(self):
        """Clean up the test environment."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.log_analysis.monitor.os.path.join')
    @patch('qcmd_cli.log_analysis.monitor.os.kill')
    def test_cleanup_stale_monitors(self, mock_kill, mock_join):
        """Test that stale monitors are cleaned up properly."""
        # Mock os.path.join to return our test file path
        mock_join.return_value = self.monitor_file_path
        
        # Mock kill to simulate process status
        def mock_kill_side_effect(pid, sig):
            # pid 12345 is running, 67890 is not
            if pid == 67890:
                raise OSError("No such process")
            return None
        
        mock_kill.side_effect = mock_kill_side_effect
        
        # Create test monitors
        current_time = int(time.time())
        test_monitors = {
            'monitor1': {
                'pid': 12345, 
                'log_file': self.test_log_file,
                'started_at': datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
            },
            'monitor2': {
                'pid': 67890, 
                'log_file': '/var/log/other.log',
                'started_at': datetime.fromtimestamp(current_time - 86400).strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        # Save test monitors to file
        os.makedirs(os.path.dirname(self.monitor_file_path), exist_ok=True)
        with open(self.monitor_file_path, 'w') as f:
            json.dump(test_monitors, f)
        
        # Call the cleanup function
        active_monitors = cleanup_stale_monitors()
        
        # Verify stale monitor was removed
        self.assertEqual(len(active_monitors), 1)
        self.assertIn('monitor1', active_monitors)
        self.assertNotIn('monitor2', active_monitors)
        
        # Verify monitor file was updated
        with open(self.monitor_file_path, 'r') as f:
            saved_monitors = json.load(f)
            self.assertEqual(len(saved_monitors), 1)
            self.assertIn('monitor1', saved_monitors)
            self.assertNotIn('monitor2', saved_monitors)
    
    @patch('qcmd_cli.log_analysis.monitor.os.path.join')
    def test_save_and_load_monitors(self, mock_join):
        """Test saving and loading monitors."""
        # Mock os.path.join to return our test file path
        mock_join.return_value = self.monitor_file_path
        
        # Create test monitors
        test_monitors = {
            'monitor1': {'pid': 12345, 'log_file': self.test_log_file},
            'monitor2': {'pid': 67890, 'log_file': '/var/log/other.log'}
        }
        
        # Test saving monitors
        save_monitors(test_monitors)
        
        # Verify file was created
        self.assertTrue(os.path.exists(self.monitor_file_path))
        
        # Test loading monitors
        loaded_monitors = load_monitors()
        
        # Verify loaded data matches the original
        self.assertEqual(loaded_monitors, test_monitors)
    
    @patch('qcmd_cli.log_analysis.monitor.os.path.join')
    def test_load_monitors_nonexistent(self, mock_join):
        """Test loading monitors when file doesn't exist."""
        # Setup patching for the monitor file with a file that doesn't exist
        nonexistent_file = os.path.join(self.temp_dir.name, 'nonexistent.json')
        mock_join.return_value = nonexistent_file
        
        # No need to remove a file that doesn't exist
        # Simply patch os.path.exists to return False for this file
        with patch('qcmd_cli.log_analysis.monitor.os.path.exists', return_value=False):
            # Call load_monitors function
            monitors = load_monitors()
            # Should return an empty dictionary
            self.assertEqual({}, monitors)


if __name__ == '__main__':
    unittest.main() 