#!/usr/bin/env python3
"""
Tests for the command history functionality.
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, mock_open, MagicMock
from datetime import datetime

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.utils.history import (
    save_to_history, load_history, show_history, HISTORY_FILE
)
from qcmd_cli.ui.display import Colors


class TestHistory(unittest.TestCase):
    """Test the history management functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_history_file = os.path.join(self.temp_dir.name, 'history.txt')
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.utils.history.os.makedirs')
    def test_save_to_history(self, mock_makedirs):
        """Test saving command to history."""
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.datetime') as mock_datetime:
                # Mock the datetime.now() function
                mock_now = MagicMock()
                mock_now.strftime.return_value = "2023-01-01 12:00:00"
                mock_datetime.now.return_value = mock_now
                
                # Call the function to save a command
                save_to_history("test command")
                
                # Verify the directory was created
                mock_makedirs.assert_called_once_with(os.path.dirname(self.temp_history_file), exist_ok=True)
                
                # Verify the file was written with correct content
                with open(self.temp_history_file, 'r') as f:
                    content = f.read()
                    self.assertIn("2023-01-01 12:00:00 | test command", content)
    
    def test_load_history_empty(self):
        """Test loading history when file doesn't exist."""
        # Patch the HISTORY_FILE constant with a non-existent file
        non_existent_file = os.path.join(self.temp_dir.name, 'nonexistent.txt')
        with patch('qcmd_cli.utils.history.HISTORY_FILE', non_existent_file):
            # Test loading history from non-existent file
            history = load_history()
            
            # Verify empty list is returned
            self.assertEqual(history, [])
    
    def test_load_history(self):
        """Test loading history from file."""
        # Create a test history file
        test_history = [
            "2023-01-01 12:00:00 | first command",
            "2023-01-01 12:30:00 | second command",
            "2023-01-01 13:00:00 | third command"
        ]
        
        # Create parent directory
        os.makedirs(os.path.dirname(self.temp_history_file), exist_ok=True)
        
        # Write test history to the temporary file
        with open(self.temp_history_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_history))
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            # Test loading history (default count=10)
            history = load_history()
            
            # Verify the loaded history
            self.assertEqual(len(history), 3)
            self.assertEqual(history[0], "third command")  # Most recent first
            self.assertEqual(history[1], "second command")
            self.assertEqual(history[2], "first command")
            
            # Test loading history with count=2
            history = load_history(count=2)
            
            # Verify only the most recent 2 entries are loaded
            self.assertEqual(len(history), 2)
            self.assertEqual(history[0], "third command")
            self.assertEqual(history[1], "second command")
    
    @patch('builtins.print')
    def test_show_history(self, mock_print):
        """Test displaying history."""
        # Create a test history file
        test_history = [
            "2023-01-01 12:00:00 | first command",
            "2023-01-01 12:30:00 | second command",
            "2023-01-01 13:00:00 | search term command"
        ]
        
        # Create parent directory
        os.makedirs(os.path.dirname(self.temp_history_file), exist_ok=True)
        
        # Write test history to the temporary file
        with open(self.temp_history_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(test_history))
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            # Test showing history
            show_history()
            
            # Verify print was called appropriately
            mock_print.assert_any_call(f"\n{Colors.GREEN}{Colors.BOLD}Command History:{Colors.END}")
            mock_print.assert_any_call(f"{Colors.CYAN}{'#':<4} {'Timestamp':<20} {'Command'}{Colors.END}")
            
            # Test showing history with search term
            mock_print.reset_mock()
            show_history(search_term="search")
            
            # Verify search results were filtered
            mock_print.assert_any_call(f"\n{Colors.GREEN}{Colors.BOLD}Command History matching 'search':{Colors.END}")
    
    def test_history_limit(self):
        """Test that history is limited to MAX_HISTORY entries."""
        # Create parent directory for history file
        os.makedirs(os.path.dirname(self.temp_history_file), exist_ok=True)
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            # Create a large number of history entries
            import qcmd_cli.utils.history as history_module
            original_max = history_module.MAX_HISTORY
            
            try:
                # Set a smaller MAX_HISTORY for testing
                history_module.MAX_HISTORY = 5
                
                # Create test entries
                for i in range(10):  # More than MAX_HISTORY
                    with patch('qcmd_cli.utils.history.datetime') as mock_datetime:
                        # Mock the datetime.now() function
                        mock_now = MagicMock()
                        mock_now.strftime.return_value = f"2023-01-01 {i:02d}:00:00"
                        mock_datetime.now.return_value = mock_now
                        
                        save_to_history(f"command {i}")
                
                # Read the history file directly
                with open(self.temp_history_file, 'r') as f:
                    lines = f.readlines()
                
                # Verify only MAX_HISTORY entries are kept
                self.assertEqual(len(lines), 5)  # Our modified MAX_HISTORY
                
                # Verify the most recent entries are kept
                self.assertIn("command 9", lines[-1])  # Last command should be retained
                self.assertIn("command 8", lines[-2])  # Second-to-last should be retained
                
            finally:
                # Restore original MAX_HISTORY
                history_module.MAX_HISTORY = original_max


if __name__ == '__main__':
    unittest.main() 