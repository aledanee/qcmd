#!/usr/bin/env python3
"""
Tests for the post_install module.
"""
import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import function to test
from qcmd_cli.post_install import main
from qcmd_cli.ui.display import Colors


class TestPostInstall(unittest.TestCase):
    """Test the post-installation script functionality."""
    
    @patch('qcmd_cli.post_install.print_iraq_banner')
    @patch('qcmd_cli.post_install.print')
    @patch('qcmd_cli.post_install.__version__', '1.0.0')  # Mock the version
    def test_main_function(self, mock_print, mock_print_banner):
        """Test that the main function displays the correct information."""
        # Call the main function
        result = main()
        
        # Verify return code
        self.assertEqual(result, 0)
        
        # Verify the environment variable is set
        self.assertEqual(os.environ.get('QCMD_FORCE_BANNER'), 'true')
        
        # Verify the banner was printed
        mock_print_banner.assert_called_once()
        
        # Verify the success messages were printed with color
        success_msg = f"{Colors.GREEN}Thank you for installing QCMD version 1.0.0!{Colors.END}"
        mock_print.assert_any_call(success_msg)
        
        # Check for help message
        help_call_found = False
        for call_args in mock_print.call_args_list:
            if len(call_args[0]) > 0 and "--help" in str(call_args[0][0]):
                help_call_found = True
                break
        
        self.assertTrue(help_call_found, "Help message not found in output")
        
        # Check for shell message
        shell_call_found = False
        for call_args in mock_print.call_args_list:
            if len(call_args[0]) > 0 and "--shell" in str(call_args[0][0]):
                shell_call_found = True
                break
        
        self.assertTrue(shell_call_found, "Shell message not found in output")


if __name__ == '__main__':
    unittest.main() 