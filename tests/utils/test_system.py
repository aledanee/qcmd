#!/usr/bin/env python3
"""
Tests for the system utility functions.
"""
import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open, call
from datetime import datetime
import requests
from qcmd_cli.ui.display import Colors

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.utils.system import (
    get_system_status, check_ollama_status, display_system_status, 
    check_for_updates, __version__, OLLAMA_API
)


class TestSystemUtils(unittest.TestCase):
    """Test the system utility functions."""
    
    def setUp(self):
        """Set up temporary files and directories for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_dir = os.path.join(self.temp_dir.name, 'config')
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Create a patcher for CONFIG_DIR
        self.config_dir_patcher = patch('qcmd_cli.utils.system.CONFIG_DIR', self.config_dir)
        self.config_dir_patcher.start()
        
    def tearDown(self):
        """Clean up temporary files and stop patchers."""
        self.config_dir_patcher.stop()
        self.temp_dir.cleanup()

    @patch('qcmd_cli.utils.system.requests.get')
    @patch('qcmd_cli.utils.system.cleanup_stale_monitors')
    @patch('qcmd_cli.utils.system.cleanup_stale_sessions')
    @patch('qcmd_cli.utils.system.shutil.disk_usage')
    def test_get_system_status(self, mock_disk_usage, mock_cleanup_sessions, 
                              mock_cleanup_monitors, mock_requests_get):
        """Test getting system status information."""
        # Setup mocks
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest"},
                {"name": "qwen2:latest"}
            ]
        }
        mock_requests_get.return_value = mock_response
        
        mock_cleanup_monitors.return_value = {
            "monitor1": {"log_file": "/var/log/test.log", "pid": 12345, "analyze": True},
            "monitor2": {"log_file": "/var/log/app.log", "pid": 67890, "analyze": False}
        }
        
        mock_cleanup_sessions.return_value = {
            "session1": {"type": "shell", "start_time": 1614556800, "pid": 12345},
            "session2": {"type": "log_analysis", "start_time": 1614556900, "pid": 67890}
        }
        
        mock_disk_usage.return_value = (1000000000000, 300000000000, 700000000000)  # 1TB total, 300GB used, 700GB free
        
        # Call the function
        status = get_system_status()
        
        # Verify the response
        self.assertIsInstance(status, dict)
        self.assertEqual(status["os"], os.name)
        self.assertEqual(status["qcmd_version"], __version__)
        
        # Verify Ollama status
        self.assertEqual(status["ollama"]["status"], "running")
        self.assertEqual(status["ollama"]["api_url"], OLLAMA_API)
        self.assertEqual(status["ollama"]["models"], ["llama3:latest", "qwen2:latest"])
        
        # Verify active monitors and sessions
        self.assertEqual(status["active_monitors"], ["monitor1", "monitor2"])
        self.assertEqual(status["active_sessions"], ["session1", "session2"])
        self.assertEqual(status["sessions_info"], mock_cleanup_sessions.return_value)
        
        # Verify disk space info
        if "disk" in status:
            self.assertAlmostEqual(status["disk"]["total_gb"], 931.32, places=1)  # 1TB in GB, rounded
            self.assertAlmostEqual(status["disk"]["used_gb"], 279.4, places=1)   # 300GB in GB, rounded
            self.assertAlmostEqual(status["disk"]["free_gb"], 651.93, places=1)  # 700GB in GB, rounded
            self.assertAlmostEqual(status["disk"]["percent_used"], 30.0, places=1)  # 30% used

    @patch('qcmd_cli.utils.system.requests.get')
    @patch('qcmd_cli.utils.system.cleanup_stale_monitors')
    @patch('qcmd_cli.utils.system.cleanup_stale_sessions')
    def test_get_system_status_ollama_not_running(self, mock_cleanup_sessions, 
                                              mock_cleanup_monitors, mock_requests_get):
        """Test getting system status when Ollama is not running."""
        # Setup mocks for a request exception
        mock_requests_get.side_effect = requests.exceptions.RequestException("Connection refused")
        
        mock_cleanup_monitors.return_value = {}
        mock_cleanup_sessions.return_value = {}
        
        # Call the function
        status = get_system_status()
        
        # Verify the response
        self.assertIsInstance(status, dict)
        self.assertEqual(status["ollama"]["status"], "not running")
        self.assertEqual(status["active_monitors"], [])
        self.assertEqual(status["active_sessions"], [])

    @patch('qcmd_cli.utils.system.requests.get')
    def test_check_ollama_status_running(self, mock_requests_get):
        """Test checking Ollama status when it's running."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest"},
                {"name": "qwen2:latest"}
            ]
        }
        mock_requests_get.return_value = mock_response
        
        # Call the function
        status, api_url, models = check_ollama_status()
        
        # Verify the results
        self.assertEqual(status, "Running")
        self.assertEqual(api_url, OLLAMA_API)
        self.assertEqual(models, ["llama3:latest", "qwen2:latest"])
        mock_requests_get.assert_called_once_with(f"{OLLAMA_API}/tags", timeout=2)

    @patch('qcmd_cli.utils.system.requests.get')
    def test_check_ollama_status_not_running(self, mock_requests_get):
        """Test checking Ollama status when it's not running."""
        # Setup mock
        mock_requests_get.side_effect = requests.exceptions.RequestException("Connection refused")
        
        # Call the function
        status, api_url, models = check_ollama_status()
        
        # Verify the results
        self.assertEqual(status, "Not running")
        self.assertEqual(api_url, OLLAMA_API)
        self.assertEqual(models, [])

    @patch('qcmd_cli.utils.system.requests.get')
    def test_check_ollama_status_bad_response(self, mock_requests_get):
        """Test checking Ollama status when it returns a bad response."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_requests_get.return_value = mock_response
        
        # Call the function
        status, api_url, models = check_ollama_status()
        
        # Verify the results
        self.assertEqual(status, "Not running")
        self.assertEqual(api_url, OLLAMA_API)
        self.assertEqual(models, [])

    @patch('qcmd_cli.utils.system.requests.get')
    def test_check_ollama_status_malformed_json(self, mock_requests_get):
        """Test checking Ollama status when it returns malformed JSON."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Expecting value", "", 0)
        mock_requests_get.return_value = mock_response
        
        # Call the function
        status, api_url, models = check_ollama_status()
        
        # Verify the results
        self.assertEqual(status, "Running")
        self.assertEqual(api_url, OLLAMA_API)
        self.assertEqual(models, [])

    @patch('builtins.print')
    @patch('qcmd_cli.utils.system.check_ollama_status')
    @patch('qcmd_cli.utils.system.cleanup_stale_monitors')
    @patch('qcmd_cli.utils.system.cleanup_stale_sessions')
    @patch('qcmd_cli.utils.system.shutil.disk_usage')
    @patch('qcmd_cli.utils.system.load_config')
    def test_display_system_status(self, mock_load_config, mock_disk_usage, 
                                 mock_cleanup_sessions, mock_cleanup_monitors, 
                                 mock_check_ollama_status, mock_print):
        """Test displaying system status information."""
        # Setup mocks
        mock_load_config.return_value = {
            'model': 'llama3:latest',
            'temperature': 0.7,
            'max_attempts': 3,
            'ui': {
                'show_iraq_banner': True,
                'show_progress_bar': True
            }
        }
        
        mock_check_ollama_status.return_value = ("Running", OLLAMA_API, ["llama3:latest", "qwen2:latest"])
        
        mock_cleanup_monitors.return_value = {
            "monitor1": {"log_file": "/var/log/test.log", "pid": 12345, "analyze": True},
            "monitor2": {"log_file": "/var/log/app.log", "pid": 67890, "analyze": False}
        }
        
        mock_cleanup_sessions.return_value = {
            "session1": {"type": "shell", "start_time": 1614556800, "pid": 12345},
            "session2": {"type": "log_analysis", "start_time": 1614556900, "pid": 67890}
        }
        
        mock_disk_usage.return_value = (1000000000000, 300000000000, 700000000000)  # 1TB total, 300GB used, 700GB free
        
        # Call the function
        display_system_status()
        
        # Verify that print was called multiple times (specific content checking is too brittle)
        self.assertTrue(mock_print.call_count > 20)
        
        # Check for specific section headers
        header_texts = [
            "SYSTEM INFORMATION",
            "OLLAMA STATUS",
            "ACTIVE LOG MONITORS",
            "ACTIVE SESSIONS",
            "DISK SPACE",
            "CONFIGURATION"
        ]
        
        for text in header_texts:
            header_found = False
            for call_args in mock_print.call_args_list:
                if len(call_args[0]) > 0 and text in str(call_args[0][0]):
                    header_found = True
                    break
            self.assertTrue(header_found, f"Header '{text}' was not found in output")

    @patch('builtins.print')
    @patch('qcmd_cli.utils.system.check_ollama_status')
    @patch('qcmd_cli.utils.system.cleanup_stale_monitors')
    @patch('qcmd_cli.utils.system.cleanup_stale_sessions')
    @patch('qcmd_cli.utils.system.shutil.disk_usage')
    @patch('qcmd_cli.utils.system.load_config')
    def test_display_system_status_no_active_items(self, mock_load_config, mock_disk_usage, 
                                              mock_cleanup_sessions, mock_cleanup_monitors, 
                                              mock_check_ollama_status, mock_print):
        """Test displaying system status with no active monitors or sessions."""
        # Setup mocks
        mock_load_config.return_value = {
            'model': 'llama3:latest',
            'temperature': 0.7,
            'max_attempts': 3,
            'ui': {
                'show_iraq_banner': True,
                'show_progress_bar': True
            }
        }
        
        mock_check_ollama_status.return_value = ("Not running", OLLAMA_API, [])
        
        mock_cleanup_monitors.return_value = {}
        mock_cleanup_sessions.return_value = {}
        
        mock_disk_usage.return_value = (1000000000000, 300000000000, 700000000000)
        
        # Call the function
        display_system_status()
        
        # Check for 'No active' messages
        no_active_monitors_found = False
        no_active_sessions_found = False
        
        for call_args in mock_print.call_args_list:
            if len(call_args[0]) > 0:
                call_str = str(call_args[0][0])
                if "No active log monitors" in call_str:
                    no_active_monitors_found = True
                if "No active sessions" in call_str:
                    no_active_sessions_found = True
        
        self.assertTrue(no_active_monitors_found, "No active monitors message not found")
        self.assertTrue(no_active_sessions_found, "No active sessions message not found")

    @patch('qcmd_cli.utils.system.requests.get')
    @patch('builtins.print')
    def test_check_for_updates_newer_version(self, mock_print, mock_requests_get):
        """Test checking for updates when a newer version is available."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "version": "999.0.0"  # A version that is definitely newer
            }
        }
        mock_requests_get.return_value = mock_response
        
        # Call the function
        check_for_updates()
        
        # Verify the output with exact string matching
        new_version_msg = f"\n{Colors.YELLOW}New version available: {Colors.BOLD}999.0.0{Colors.END}"
        mock_print.assert_any_call(new_version_msg)
        
        # Test with force_display
        mock_print.reset_mock()
        check_for_updates(force_display=True)
        mock_print.assert_any_call(new_version_msg)

    @patch('qcmd_cli.utils.system.requests.get')
    @patch('builtins.print')
    def test_check_for_updates_same_version(self, mock_print, mock_requests_get):
        """Test checking for updates when the current version is the latest."""
        # Setup mock response with current version
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "info": {
                "version": __version__  # Same as current version
            }
        }
        mock_requests_get.return_value = mock_response
        
        # Call the function without force_display
        check_for_updates()
        
        # Verify no output was printed
        mock_print.assert_not_called()
        
        # Test with force_display=True
        mock_print.reset_mock()
        check_for_updates(force_display=True)
        
        # Verify output was printed
        latest_version_msg = f"{Colors.GREEN}You have the latest version: {Colors.BOLD}{__version__}{Colors.END}"
        mock_print.assert_called_once_with(latest_version_msg)

    @patch('qcmd_cli.utils.system.requests.get')
    @patch('builtins.print')
    def test_check_for_updates_error(self, mock_print, mock_requests_get):
        """Test checking for updates when an error occurs."""
        # Setup mock to raise an exception
        error_msg = "Network error"
        mock_requests_get.side_effect = Exception(error_msg)
        
        # Call the function without force_display
        check_for_updates()
        
        # Verify no output was printed
        mock_print.assert_not_called()
        
        # Test with force_display=True
        mock_print.reset_mock()
        check_for_updates(force_display=True)
        
        # Verify error message was printed
        expected_msg = f"{Colors.YELLOW}Could not check for updates: {error_msg}{Colors.END}"
        mock_print.assert_called_once_with(expected_msg)


if __name__ == "__main__":
    unittest.main() 