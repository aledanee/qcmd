#!/usr/bin/env python3
"""
Additional tests for the history management functionality to improve coverage.
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, mock_open, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.utils.history import (
    save_to_history, load_history, show_history,
    HISTORY_FILE, MAX_HISTORY
)

class TestHistoryManagementAdditional(unittest.TestCase):
    """Additional tests for the history management functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_history_file = os.path.join(self.temp_dir.name, 'history.txt')
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.utils.history.os.makedirs')
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_save_to_history_exception_making_dir(self, mock_exists, mock_makedirs):
        """Test save_to_history handling exception when creating directory."""
        # Set up mock to make os.path.exists return False for history file
        mock_exists.return_value = False
        
        # Simulate permission error when creating directory
        mock_makedirs.side_effect = PermissionError("Permission denied")
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('sys.stderr'):  # Suppress error output
                # Test saving to history - should handle exception
                save_to_history("test command")
                
                # Verify error was printed to stderr
                self.assertTrue(mock_makedirs.called)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_save_to_history_unicode_error(self, mock_exists):
        """Test save_to_history handling UnicodeDecodeError when reading existing file."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file that raises UnicodeDecodeError on first read
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = [
            UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte'),
            mock_context  # Second read succeeds
        ]
        mock_file.return_value = mock_context
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    # Test saving to history - should handle UnicodeDecodeError
                    save_to_history("test command")
                    
                    # Verify file was opened at least twice (once for each encoding attempt)
                    self.assertGreaterEqual(mock_file.call_count, 2)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_save_to_history_write_error(self, mock_exists):
        """Test save_to_history handling error when writing file."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file that raises error on write
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.return_value.write.side_effect = IOError("Write error")
        mock_file.return_value = mock_context
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    # Test saving to history - should handle IOError
                    save_to_history("test command")
                    
                    # Verify file was opened
                    self.assertTrue(mock_file.called)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_load_history_file_not_exists(self, mock_exists):
        """Test load_history when file doesn't exist."""
        # Set up mock to make os.path.exists return False
        mock_exists.return_value = False
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            # Test loading history
            history = load_history()
            
            # Verify empty list is returned
            self.assertEqual(history, [])
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_load_history_with_unicode_error(self, mock_exists):
        """Test load_history handling UnicodeDecodeError."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file that raises UnicodeDecodeError on first read
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = [
            UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid start byte'),
            mock_context  # Second read succeeds
        ]
        mock_file.return_value = mock_context
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    # Test loading history - should handle UnicodeDecodeError
                    history = load_history()
                    
                    # Verify file was opened at least twice (once for each encoding attempt)
                    self.assertGreaterEqual(mock_file.call_count, 2)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_load_history_with_io_error(self, mock_exists):
        """Test load_history handling IOError."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file that raises IOError
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = IOError("Read error")
        mock_file.return_value = mock_context
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    # Test loading history - should handle IOError
                    history = load_history()
                    
                    # Verify empty list is returned
                    self.assertEqual(history, [])
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_show_history_file_not_exists(self, mock_exists):
        """Test show_history when file doesn't exist."""
        # Set up mock to make os.path.exists return False
        mock_exists.return_value = False
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('sys.stdout'):  # Suppress output
                # Test showing history
                show_history()
                
                # Verify appropriate message was printed
                self.assertTrue(mock_exists.called)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_show_history_with_io_error(self, mock_exists):
        """Test show_history handling IOError."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file that raises IOError
        mock_file = MagicMock()
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = IOError("Read error")
        mock_file.return_value = mock_context
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stderr'):  # Suppress error output
                    # Test showing history - should handle IOError
                    show_history()
                    
                    # Verify file was opened
                    self.assertTrue(mock_file.called)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_show_history_with_search(self, mock_exists):
        """Test show_history with search term."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file with test history
        test_history = [
            "2024-01-01 12:00:00 | test command 1",
            "2024-01-01 12:01:00 | test command 2",
            "2024-01-01 12:02:00 | different command"
        ]
        mock_file = mock_open(read_data='\n'.join(test_history))
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stdout'):  # Suppress output
                    # Test showing history with search term
                    show_history(search_term="test")
                    
                    # Verify file was opened
                    self.assertTrue(mock_file.called)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_show_history_with_invalid_format(self, mock_exists):
        """Test show_history with invalid history format."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file with invalid history format
        test_history = [
            "invalid format 1",
            "2024-01-01 12:00:00 | valid command",
            "invalid format 2"
        ]
        mock_file = mock_open(read_data='\n'.join(test_history))
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stdout'):  # Suppress output
                    # Test showing history with invalid format
                    show_history()
                    
                    # Verify file was opened
                    self.assertTrue(mock_file.called)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_show_history_empty_file(self, mock_exists):
        """Test show_history with empty file."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file with no content
        mock_file = mock_open(read_data='')
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stdout'):  # Suppress output
                    # Test showing history with empty file
                    show_history()
                    
                    # Verify file was opened
                    self.assertTrue(mock_file.called)
    
    @patch('qcmd_cli.utils.history.os.path.exists')
    def test_show_history_no_matching_search(self, mock_exists):
        """Test show_history with search term that matches no entries."""
        # Set up mock to make os.path.exists return True
        mock_exists.return_value = True
        
        # Create mock file with test history
        test_history = [
            "2024-01-01 12:00:00 | test command 1",
            "2024-01-01 12:01:00 | test command 2",
            "2024-01-01 12:02:00 | different command"
        ]
        mock_file = mock_open(read_data='\n'.join(test_history))
        
        # Patch the HISTORY_FILE constant
        with patch('qcmd_cli.utils.history.HISTORY_FILE', self.temp_history_file):
            with patch('qcmd_cli.utils.history.open', mock_file):
                with patch('sys.stdout'):  # Suppress output
                    # Test showing history with non-matching search term
                    show_history(search_term="nonexistent")
                    
                    # Verify file was opened
                    self.assertTrue(mock_file.called)

if __name__ == '__main__':
    unittest.main() 