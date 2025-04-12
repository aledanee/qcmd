#!/usr/bin/env python3
"""
Tests for UI display functionality.
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions to test
from qcmd_cli.ui.display import (
    Colors, display_system_status, display_help_command,
    clear_screen, print_cool_header
)


class TestDisplayFunctions(unittest.TestCase):
    """Test the display functions in the UI module."""
    
    @patch('builtins.print')
    def test_display_system_status(self, mock_print):
        """Test that system status is displayed correctly."""
        # Mock system status data
        status_data = {
            'os': 'Linux 6.1.0-kali1-amd64',
            'python_version': '3.11.2',
            'qcmd_version': '0.4.1',
            'ollama_status': {
                'running': True,
                'version': '0.1.19',
                'models': ['llama3', 'phi3']
            },
            'cpu_info': {
                'cores': 8,
                'usage': 35.2
            },
            'memory_info': {
                'total': 16000000000,
                'available': 9000000000,
                'percent': 44.5
            },
            'disk_info': {
                'total': 250000000000,
                'free': 150000000000,
                'percent': 40.0
            }
        }
        
        # Call the function
        display_system_status(status_data)
        
        # Verify that print was called
        mock_print.assert_called()
        
        # Just verify that some of the data was used in print calls
        all_print_output = ''.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('Linux 6.1.0-kali1-amd64', all_print_output)
        self.assertIn('3.11.2', all_print_output)
        self.assertIn('0.4.1', all_print_output)
        
    @patch('builtins.print')
    def test_display_help_command(self, mock_print):
        """Test that help command is displayed correctly."""
        # Call the function
        display_help_command("llama3", 0.7, False, 3)
        
        # Verify that print was called
        mock_print.assert_called()
        
        # Just verify that some of the expected data appears in the output
        all_print_output = ''.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('QCMD', all_print_output)
        self.assertIn('llama3', all_print_output)
        self.assertIn('0.7', all_print_output)
        
    @patch('os.system')
    def test_clear_screen(self, mock_system):
        """Test clear_screen function."""
        # Call the function
        clear_screen()
        
        # Verify system call was made
        mock_system.assert_called_once()
        
    @patch('builtins.print')
    def test_print_cool_header(self, mock_print):
        """Test print_cool_header function."""
        # Call the function
        print_cool_header()
        
        # Verify header was printed
        mock_print.assert_called()
        
        # Check that the output includes ASCII art - look for typical parts
        all_print_output = ''.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('█', all_print_output)
        self.assertIn('AI-Powered', all_print_output)
        
    @patch('builtins.print')
    def test_colors(self, mock_print):
        """Test that the Colors class works correctly."""
        # Test using colors
        print(f"{Colors.RED}Red Text{Colors.END}")
        print(f"{Colors.GREEN}Green Text{Colors.END}")
        print(f"{Colors.BOLD}Bold Text{Colors.END}")
        
        # Verify that print was called
        mock_print.assert_called()
        
        # Check that the text appears in output
        all_print_output = ''.join(str(call) for call in mock_print.call_args_list)
        self.assertIn('Red Text', all_print_output)
        self.assertIn('Green Text', all_print_output)
        self.assertIn('Bold Text', all_print_output)


if __name__ == '__main__':
    unittest.main() 