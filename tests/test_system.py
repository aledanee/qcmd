#!/usr/bin/env python3
"""
Tests for system utilities module.
"""

import unittest
import os
import sys
import json
import tempfile
import re
from unittest.mock import patch, MagicMock
from io import StringIO

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions to test
from qcmd_cli.utils.system import (
    check_for_updates, display_update_status, 
    execute_command, format_bytes, display_system_status
)
from qcmd_cli.log_analysis.monitor_state import active_log_monitors


def strip_ansi_escape_codes(text):
    """Remove ANSI escape codes from the given text."""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


class TestSystemUtilities(unittest.TestCase):
    """Test the system utilities functionality."""

    def test_format_bytes(self):
        """Test the format_bytes function."""
        # Test different byte sizes
        self.assertEqual(format_bytes(500), "500.00 B")
        self.assertEqual(format_bytes(1024), "1.00 KB")
        self.assertEqual(format_bytes(1024 * 1024), "1.00 MB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024), "1.00 GB")
        self.assertEqual(format_bytes(1024 * 1024 * 1024 * 1024), "1.00 TB")
        
    def test_execute_command(self):
        """Test the execute_command function."""
        # Test a simple command
        exit_code, output = execute_command("echo 'test command'")
        self.assertEqual(exit_code, 0)
        self.assertIn("test command", output)
        
        # Test a failing command
        exit_code, output = execute_command("command_that_does_not_exist")
        self.assertNotEqual(exit_code, 0)
        
    @patch('requests.get')
    def test_check_for_updates_newer_version(self, mock_get):
        """Test check_for_updates when a newer version is available."""
        # Mock the response from PyPI
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'info': {
                'version': '1.1.0'  # Newer version than current
            }
        }
        mock_get.return_value = mock_response
        
        # Patch the current version
        with patch('qcmd_cli.utils.system.__version__', '1.0.0'):
            # Call the function
            result = check_for_updates(force_display=False)
            
            # Verify result
            self.assertTrue(result['update_available'])
            self.assertEqual(result['current_version'], '1.0.0')
            self.assertEqual(result['latest_version'], '1.1.0')
            
    @patch('requests.get')
    def test_check_for_updates_same_version(self, mock_get):
        """Test check_for_updates when the current version is the latest."""
        # Mock the response from PyPI
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'info': {
                'version': '1.0.0'  # Same as current
            }
        }
        mock_get.return_value = mock_response
        
        # Patch the current version
        with patch('qcmd_cli.utils.system.__version__', '1.0.0'):
            # Call the function
            result = check_for_updates(force_display=False)
            
            # Verify result
            self.assertFalse(result['update_available'])
            self.assertEqual(result['current_version'], '1.0.0')
            self.assertEqual(result['latest_version'], '1.0.0')
            
    @patch('requests.get')
    def test_check_for_updates_connection_error(self, mock_get):
        """Test check_for_updates when a connection error occurs."""
        # Mock a connection error
        mock_get.side_effect = Exception("Connection error")
        
        # Call the function
        result = check_for_updates(force_display=False)
        
        # Verify result
        self.assertIsNone(result)
        
    @patch('qcmd_cli.utils.system.check_for_updates')
    @patch('qcmd_cli.utils.system.print')
    def test_display_update_status_with_update(self, mock_print, mock_check):
        """Test display_update_status when an update is available."""
        # Mock the update check to return an update is available
        mock_check.return_value = {
            'update_available': True,
            'current_version': '1.0.0',
            'latest_version': '1.1.0'
        }
        
        # Call the function
        display_update_status()
        
        # Verify display was called
        mock_print.assert_called()  # At least one call to print
        
    @patch('qcmd_cli.utils.system.check_for_updates')
    @patch('qcmd_cli.utils.system.print')
    def test_display_update_status_no_update(self, mock_print, mock_check):
        """Test display_update_status when no update is available."""
        # Mock the update check to return no update is available
        mock_check.return_value = {
            'update_available': False,
            'current_version': '1.0.0',
            'latest_version': '1.0.0'
        }
        
        # Call the function
        display_update_status()
        
        # Verify display was not called (no message needed)
        self.assertEqual(mock_print.call_count, 0)
        
    @patch('qcmd_cli.utils.system.load_config')
    def test_display_update_status_disabled(self, mock_load_config):
        """Test display_update_status when updates are disabled in config."""
        # Mock the config to disable update checks
        mock_load_config.return_value = {
            'disable_update_check': True
        }
        
        # Call the function
        with patch('qcmd_cli.utils.system.check_for_updates') as mock_check:
            display_update_status()
            
            # Verify check_for_updates was not called
            mock_check.assert_not_called()


class TestDisplaySystemStatus(unittest.TestCase):
    """Test cases for the display_system_status function."""

    def setUp(self):
        """Set up test environment."""
        active_log_monitors.clear()
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_display_system_status_with_active_monitors(self, mock_stdout):
        """Test display_system_status when active log monitors exist."""
        active_log_monitors[12345] = '/var/log/test1.log'
        active_log_monitors[67890] = '/var/log/test2.log'
        
        display_system_status()
        
        output = strip_ansi_escape_codes(mock_stdout.getvalue())
        self.assertIn("► ACTIVE LOG MONITORS", output)
        self.assertIn("• Monitor 12345: /var/log/test1.log", output)  # Updated assertion
        
        # Clean up
        active_log_monitors.clear()

    @patch('sys.stdout', new_callable=StringIO)
    def test_display_system_status_no_active_monitors(self, mock_stdout):
        """Test display_system_status when no active log monitors exist."""
        # Ensure no active log monitors
        active_log_monitors.clear()

        # Call the function
        display_system_status()

        # Verify output
        output = strip_ansi_escape_codes(mock_stdout.getvalue())
        self.assertIn("► ACTIVE LOG MONITORS", output)
        self.assertIn("No active log monitors.", output)


if __name__ == '__main__':
    unittest.main()