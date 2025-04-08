#!/usr/bin/env python3
"""
Tests for UI display functionality.
"""
import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.ui.display import (
    Colors, print_cool_header, print_examples, print_iraq_banner,
    show_download_progress, display_help_command
)


class TestUIDisplay(unittest.TestCase):
    """Test the UI display functions."""
    
    def setUp(self):
        """Set up test environment."""
        # Save original color values
        self.original_colors = Colors.get_all_colors()
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore original color values
        for color_name, color_value in self.original_colors.items():
            setattr(Colors, color_name, color_value)
    
    def test_colors_load_from_config(self):
        """Test loading colors from configuration."""
        # Test config with custom colors
        config = {
            'colors': {
                'GREEN': '\033[92m',
                'RED': '\033[91m',
                'BOLD': '\033[1m'
            }
        }
        
        # Load colors from config
        Colors.load_from_config(config)
        
        # Verify colors were set correctly
        self.assertEqual(Colors.GREEN, '\033[92m')
        self.assertEqual(Colors.RED, '\033[91m')
        self.assertEqual(Colors.BOLD, '\033[1m')
        
        # Verify other colors remain unchanged
        self.assertEqual(Colors.BLUE, self.original_colors['BLUE'])
        self.assertEqual(Colors.CYAN, self.original_colors['CYAN'])
    
    def test_colors_reset_to_defaults(self):
        """Test resetting colors to default values."""
        # First change some colors
        Colors.GREEN = '\033[92m'
        Colors.RED = '\033[91m'
        
        # Reset to defaults
        Colors.reset_to_defaults()
        
        # Verify colors were reset
        self.assertEqual(Colors.GREEN, self.original_colors['GREEN'])
        self.assertEqual(Colors.RED, self.original_colors['RED'])
    
    @patch('builtins.print')
    def test_print_cool_header(self, mock_print):
        """Test printing the cool ASCII art header."""
        print_cool_header()
        
        # Verify print was called at least twice (header and subtitle)
        self.assertGreaterEqual(mock_print.call_count, 2)
        
        # Get all printed content
        printed_text = "\n".join(args[0] for args, _ in mock_print.call_args_list)
        
        # Verify the header contains the QCMD ASCII art
        self.assertIn("██████╗  ██████╗███╗   ███╗██████╗", printed_text)
        self.assertIn("Iraqi Excellence in Command Generation", printed_text)
    
    @patch('builtins.print')
    def test_print_examples(self, mock_print):
        """Test printing example commands."""
        print_examples()
        
        # Verify print was called
        self.assertTrue(mock_print.called)
        
        # Get all printed content
        printed_text = "\n".join(args[0] for args, _ in mock_print.call_args_list)
        
        # Verify example commands are present
        self.assertIn("qcmd 'list files sorted by size'", printed_text)
        self.assertIn("qcmd --auto 'find text in files'", printed_text)
        self.assertIn("qcmd logs", printed_text)
        self.assertIn("qcmd --shell", printed_text)
    
    @patch('builtins.print')
    def test_print_iraq_banner(self, mock_print):
        """Test printing the Iraqi-themed banner."""
        print_iraq_banner()
        
        # Verify print was called at least twice (title and flag)
        self.assertGreaterEqual(mock_print.call_count, 2)
        
        # Get all printed content
        printed_text = "\n".join(args[0] for args, _ in mock_print.call_args_list)
        
        # Verify the banner contains the Iraqi flag colors and title
        self.assertIn("Iraqi-Powered Command Generation", printed_text)
        self.assertIn("█", printed_text)  # Check for flag blocks
    
    @patch('sys.stdout')
    @patch('time.sleep')
    @patch('shutil.get_terminal_size')
    def test_show_download_progress(self, mock_terminal_size, mock_sleep, mock_stdout):
        """Test showing download progress bar."""
        # Mock terminal size
        mock_terminal_size.return_value = MagicMock(columns=80)
        
        show_download_progress(total=5, message="Testing progress")
        
        # Verify stdout.write was called for each progress update
        self.assertTrue(mock_stdout.write.called)
        
        # Get all written content
        written_text = "".join(args[0] for args, _ in mock_stdout.write.call_args_list)
        
        # Verify progress bar elements
        self.assertIn("Testing progress", written_text)
        self.assertIn("[", written_text)
        self.assertIn("]", written_text)
        self.assertIn("100.0%", written_text)
        
        # Verify flush was called
        self.assertTrue(mock_stdout.flush.called)
    
    @patch('builtins.print')
    def test_display_help_command(self, mock_print):
        """Test displaying help information."""
        display_help_command(
            current_model="test-model",
            current_temperature=0.7,
            auto_mode_enabled=True,
            max_attempts=3
        )
        
        # Verify print was called
        self.assertTrue(mock_print.called)
        
        # Get all printed content
        printed_text = "\n".join(args[0] for args, _ in mock_print.call_args_list)
        
        # Verify help content
        self.assertIn("QCMD Interactive Shell Help", printed_text)
        self.assertIn("Current Settings:", printed_text)
        self.assertIn("test-model", printed_text)
        self.assertIn("0.7", printed_text)
        self.assertIn("Enabled", printed_text)
        self.assertIn("3", printed_text)
        self.assertIn("Available Commands:", printed_text)
        self.assertIn("!help", printed_text)
        self.assertIn("!exit", printed_text)
        self.assertIn("!quit", printed_text)


if __name__ == '__main__':
    unittest.main() 