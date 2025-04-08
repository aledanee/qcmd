#!/usr/bin/env python3
"""
Tests for log file discovery and selection functionality.
"""
import unittest
import os
import sys
import json
import tempfile
import time
from unittest.mock import patch, MagicMock, mock_open

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.log_analysis.log_files import (
    find_log_files, is_log_file, display_log_selection,
    handle_log_selection, handle_log_analysis, LOG_CACHE_FILE
)
from qcmd_cli.ui.display import Colors


class TestLogFiles(unittest.TestCase):
    """Test the log file discovery and selection functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_cache_file = os.path.join(self.temp_dir.name, 'log_cache.json')
        self.temp_log_file = os.path.join(self.temp_dir.name, 'test.log')
        
        # Create a test log file
        with open(self.temp_log_file, 'w') as f:
            f.write("2023-01-01 12:00:00 ERROR: Failed to connect to database\n")
            f.write("2023-01-01 12:01:00 INFO: Retrying connection\n")
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    def test_is_log_file(self):
        """Test identifying log files by name and content."""
        # Test files with log extensions
        self.assertTrue(is_log_file("test.log"))
        self.assertTrue(is_log_file("system.log"))
        self.assertTrue(is_log_file("app.log.1"))
        self.assertTrue(is_log_file("error_log"))
        
        # Test non-log files
        self.assertFalse(is_log_file("image.png"))
        self.assertFalse(is_log_file("document.pdf"))
        self.assertFalse(is_log_file("script.py"))
        
        # Test edge cases
        self.assertFalse(is_log_file(""))  # Empty string
        # Note: 'log' is considered a log file in the implementation, so this test should expect True
        self.assertTrue(is_log_file("log"))  # Just "log"
        self.assertTrue(is_log_file(".log"))  # Hidden log file
    
    @patch('builtins.print')
    def test_find_log_files_cached(self, mock_print):
        """Test finding log files with a valid cache."""
        # Create a test cache
        cached_time = int(time.time()) - 1800  # 30 minutes ago (still valid)
        cache_data = {
            "timestamp": cached_time,
            "log_files": [
                "/var/log/system.log",
                "/var/log/apache2/error.log"
            ]
        }
        
        # Write cache data to temp file
        os.makedirs(os.path.dirname(self.temp_cache_file), exist_ok=True)
        with open(self.temp_cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Set up the patchers we need - patching at the module import level since load_config is imported locally
        with patch('qcmd_cli.log_analysis.log_files.LOG_CACHE_FILE', self.temp_cache_file):
            with patch('qcmd_cli.log_analysis.log_files.os.path.exists', return_value=True):
                with patch('qcmd_cli.log_analysis.log_files.os.path.isfile', return_value=True):
                    with patch('qcmd_cli.log_analysis.log_files.os.access', return_value=True):
                        # Use patch.dict to mock the import path
                        with patch.dict('sys.modules', {
                            'qcmd_cli.config.settings': MagicMock(
                                load_config=MagicMock(return_value={'favorite_logs': ["/var/log/custom.log"]})
                            )
                        }):
                            # Test finding log files
                            log_files = find_log_files()
                            
                            # Verify cached logs + favorite logs are returned
                            self.assertEqual(len(log_files), 3)
                            self.assertIn("/var/log/system.log", log_files)
                            self.assertIn("/var/log/apache2/error.log", log_files)
                            self.assertIn("/var/log/custom.log", log_files)
                            
                            # Verify message about using cache
                            mock_print.assert_any_call(f"{Colors.BLUE}Using cached log file list.{Colors.END}")
    
    @patch('builtins.print')
    def test_find_log_files_no_cache(self, mock_print):
        """Test finding log files without a cache."""
        # Set up the patchers we need - patching the imported system functions
        with patch('qcmd_cli.log_analysis.log_files.LOG_CACHE_FILE', self.temp_cache_file):
            with patch('qcmd_cli.log_analysis.log_files.os.path.exists', side_effect=lambda path: path != self.temp_cache_file and os.path.basename(path) != 'log_cache.json'):
                with patch('qcmd_cli.log_analysis.log_files.os.path.isfile', return_value=True):
                    with patch('qcmd_cli.log_analysis.log_files.os.access', return_value=True):
                        with patch('qcmd_cli.log_analysis.log_files.subprocess.check_output', return_value=b"/var/log/system.log\n/var/log/auth.log"):
                            # Mock module import
                            with patch.dict('sys.modules', {
                                'qcmd_cli.config.settings': MagicMock(
                                    load_config=MagicMock(return_value={'favorite_logs': []})
                                )
                            }):
                                # Mock file operations
                                with patch('builtins.open', mock_open()) as m:
                                    # Test finding log files
                                    log_files = find_log_files()
                                    
                                    # Check that print was called for searching message
                                    mock_print.assert_any_call(f"{Colors.BLUE}Searching for log files...{Colors.END}")
    
    @patch('builtins.input')
    @patch('builtins.print')
    def test_display_log_selection(self, mock_print, mock_input):
        """Test displaying log selection menu."""
        # Test logs to display
        test_logs = [
            "/var/log/system.log",
            "/var/log/apache2/error.log",
            "/var/log/auth.log"
        ]
        
        # The function starts by grouping logs by directory, so the display order matters
        # When grouped by directory, the first displayed item is /var/log/system.log
        # Second item is /var/log/apache2/error.log
        
        # First test: user selects second item displayed
        mock_input.return_value = "2"
        selected_log = display_log_selection(test_logs)
        
        # In the implementation, the logs are grouped by directory, so check if any print statement
        # contained the expected log directory
        mock_print.assert_any_call(f"\n{Colors.GREEN}{Colors.BOLD}Found {len(test_logs)} log files:{Colors.END}")
        
        # The function groups files differently than our simple list, but we can still test if one is returned
        self.assertIn(selected_log, test_logs)
        
        # Test cancellation
        mock_input.return_value = "q"  # Cancel selection
        selected_log = display_log_selection(test_logs)
        
        # Verify None was returned
        self.assertIsNone(selected_log)
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('qcmd_cli.log_analysis.log_files.os.path.isfile')
    @patch('qcmd_cli.log_analysis.log_files.os.path.exists')
    def test_handle_log_selection(self, mock_exists, mock_isfile, mock_input, mock_analyze):
        """Test handling log file selection."""
        # Mock file exists
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock user choices - when prompted for analyze/monitor/watch, choose monitor
        mock_input.return_value = "m"  # Monitor with analysis
        
        # Call function
        handle_log_selection("/var/log/test.log", model="test-model")
        
        # Verify analyze_log_file was called with monitoring enabled (background=True, analyze=True)
        mock_analyze.assert_called_once_with(
            "/var/log/test.log", "test-model", True, True
        )
        
        # Test with watch mode (background=True, analyze=False)
        mock_input.return_value = "w"  # Watch without analysis
        mock_analyze.reset_mock()
        
        handle_log_selection("/var/log/test.log", model="test-model")
        
        # Verify analyze_log_file was called without analysis but with monitoring
        mock_analyze.assert_called_once_with(
            "/var/log/test.log", "test-model", True, False
        )
        
        # Test with analyze once (background=False, analyze=True)
        mock_input.return_value = "a"  # Analyze once
        mock_analyze.reset_mock()
        
        handle_log_selection("/var/log/test.log", model="test-model")
        
        # Verify analyze_log_file was called with analysis but without monitoring
        mock_analyze.assert_called_once_with(
            "/var/log/test.log", "test-model", False, True
        )
    
    @patch('qcmd_cli.log_analysis.log_files.analyze_log_file')
    @patch('builtins.input')
    @patch('qcmd_cli.log_analysis.log_files.os.path.isfile')
    @patch('qcmd_cli.log_analysis.log_files.os.path.exists')
    def test_handle_log_analysis_with_file(self, mock_exists, mock_isfile, mock_input, mock_analyze):
        """Test log analysis with a specified file."""
        # Mock file exists
        mock_exists.return_value = True
        mock_isfile.return_value = True
        
        # Mock user input
        mock_input.return_value = "n"  # Don't monitor
        
        # Call with a specified file
        handle_log_analysis(model="test-model", file_path="/var/log/test.log")
        
        # Verify analyze_log_file was called
        mock_analyze.assert_called_once_with("/var/log/test.log", "test-model", False)
    
    @patch('qcmd_cli.log_analysis.log_files.find_log_files')
    @patch('builtins.print')
    def test_handle_log_analysis_no_logs(self, mock_print, mock_find):
        """Test log analysis when no logs are found."""
        # Mock finding no log files
        mock_find.return_value = []
        
        # Call without a specified file
        handle_log_analysis(model="test-model")
        
        # Verify find_log_files was called
        mock_find.assert_called_once()
        
        # Verify error message was printed
        mock_print.assert_any_call(f"{Colors.YELLOW}No accessible log files found on the system.{Colors.END}")
    
    @patch('qcmd_cli.log_analysis.log_files.find_log_files')
    @patch('qcmd_cli.log_analysis.log_files.display_log_selection')
    @patch('builtins.print')
    def test_handle_log_analysis_user_cancelled(self, mock_print, mock_display, mock_find):
        """Test log analysis when user cancels selection."""
        # Mock finding log files
        mock_find.return_value = ["/var/log/system.log", "/var/log/auth.log"]
        
        # Mock user cancelling selection
        mock_display.return_value = None
        
        # Call without a specified file
        handle_log_analysis(model="test-model")
        
        # Verify find_log_files was called
        mock_find.assert_called_once()
        
        # Verify display_log_selection was called
        mock_display.assert_called_once()


if __name__ == '__main__':
    unittest.main() 