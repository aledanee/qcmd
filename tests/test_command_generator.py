#!/usr/bin/env python3
"""
Tests for the command generator functionality.
"""

import unittest
import os
import sys
import subprocess
from unittest.mock import patch, MagicMock, call

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions to test
try:
    from qcmd_cli.core.command_generator import (
        execute_command, is_dangerous_command, 
        generate_command, analyze_error, fix_command
    )
except ImportError:
    print("Could not import qcmd_cli module. Make sure it's in your PYTHONPATH.")
    sys.exit(1)


class TestCommandGenerator(unittest.TestCase):
    """Test the command generator functionality."""
    
    @patch('requests.post')
    def test_generate_command(self, mock_post):
        """Test command generation."""
        # Mock response from Ollama API
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "ls -la"}
        mock_post.return_value = mock_response
        
        # Test command generation
        result = generate_command("list all files in the current directory")
        
        # Verify
        self.assertEqual(result, "ls -la")
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_generate_command_with_markdown(self, mock_post):
        """Test command generation with markdown formatting."""
        # Test different markdown formatted responses
        tests = [
            {"response": "```\nls -la\n```", "expected": "ls -la"},
            {"response": "`ls -la`", "expected": "ls -la"},
            {"response": "```bash\nls -la\n```", "expected": "ls -la"}
        ]
        
        for i, test in enumerate(tests):
            mock_response = MagicMock()
            mock_response.json.return_value = {"response": test["response"]}
            mock_post.return_value = mock_response
            
            result = generate_command(f"test case {i}")
            self.assertEqual(result, test["expected"])
    
    @patch('requests.post')
    def test_analyze_error(self, mock_post):
        """Test error analysis functionality."""
        # Mock response from Ollama API
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "This command failed because the file does not exist."}
        mock_post.return_value = mock_response
        
        # Test error analysis
        result = analyze_error("No such file or directory", "cat nonexistent.txt")
        
        # Verify
        self.assertEqual(result, "This command failed because the file does not exist.")
        mock_post.assert_called_once()

    @patch('subprocess.Popen')
    def test_command_timeout_handling(self, mock_popen):
        """Test timeout handling during command execution."""
        # Setup mock to simulate TimeoutExpired
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired(cmd="sleep 100", timeout=5)
        mock_popen.return_value = process_mock
        
        # Test with a custom timeout
        return_code, output = execute_command("sleep 100", timeout=5)
        
        # Verify results
        self.assertEqual(return_code, 1, "Should return error code for timeout")
        self.assertTrue("timed out after 5 seconds" in output, "Output should mention timeout")
        
        # Verify process was terminated properly
        process_mock.terminate.assert_called_once()
    
    @patch('subprocess.Popen')
    def test_command_execution_success(self, mock_popen):
        """Test successful command execution."""
        # Setup mock for successful execution
        process_mock = MagicMock()
        process_mock.communicate.return_value = ("Command output", "")
        process_mock.returncode = 0
        mock_popen.return_value = process_mock
        
        # Execute command
        return_code, output = execute_command("echo 'test'")
        
        # Verify results
        self.assertEqual(return_code, 0, "Should return success code")
        self.assertEqual(output, "Command output", "Should return command output")
    
    @patch('subprocess.Popen')
    def test_command_execution_error(self, mock_popen):
        """Test command execution with error."""
        # Setup mock for failed execution
        process_mock = MagicMock()
        process_mock.communicate.return_value = ("", "Command error")
        process_mock.returncode = 1
        mock_popen.return_value = process_mock
        
        # Execute command
        return_code, output = execute_command("invalid_command")
        
        # Verify results
        self.assertEqual(return_code, 1, "Should return error code")
        self.assertEqual(output, "Command error", "Should return error output")
    
    @patch('subprocess.Popen')
    def test_command_execution_file_not_found(self, mock_popen):
        """Test handling of FileNotFoundError."""
        # Setup mock to raise FileNotFoundError
        mock_popen.side_effect = FileNotFoundError("No such file or command")
        
        # Execute command
        return_code, output = execute_command("nonexistent_command")
        
        # Verify results
        self.assertEqual(return_code, 127, "Should return command not found code")
        self.assertTrue("Command not found" in output, "Output should indicate command not found")
    
    @patch('subprocess.Popen')
    def test_command_execution_permission_error(self, mock_popen):
        """Test handling of PermissionError."""
        # Setup mock to raise PermissionError
        mock_popen.side_effect = PermissionError("Permission denied")
        
        # Execute command
        return_code, output = execute_command("no_permission_command")
        
        # Verify results
        self.assertEqual(return_code, 126, "Should return permission denied code")
        self.assertTrue("Permission denied" in output, "Output should indicate permission denied")
    
    def test_dangerous_command_detection(self):
        """Test detection of dangerous commands."""
        dangerous_commands = [
            "rm -rf /",
            "rm -r /home",
            "sudo rm -rf /",
            "dd if=/dev/zero of=/dev/sda",
            "sudo mkfs.ext4 /dev/sda1",
            ":(){:|:&};:",
            "chmod -R 777 /"
        ]
        
        safe_commands = [
            "ls -la",
            "cd /home/user",
            "cat file.txt",
            "grep 'pattern' file.txt",
            "echo 'hello world'"
        ]
        
        # Test commands with relative paths
        relative_path_commands = {
            "rm -rf ./test_dir": False,  # Should be safe (current directory)
            "rm -rf ../test_dir": False, # Should be safe (parent directory)
            "rm -rf /test_dir": True,    # Should be dangerous (absolute path)
            "rm file.txt": False         # Should be safe (no path)
        }
        
        # Test dangerous commands
        for cmd in dangerous_commands:
            self.assertTrue(is_dangerous_command(cmd), f"Should detect '{cmd}' as dangerous")
        
        # Test safe commands
        for cmd in safe_commands:
            self.assertFalse(is_dangerous_command(cmd), f"Should not detect '{cmd}' as safe")
        
        # Test relative path handling
        for cmd, should_be_dangerous in relative_path_commands.items():
            if should_be_dangerous:
                self.assertTrue(is_dangerous_command(cmd),
                             f"Should detect '{cmd}' as dangerous")
            else:
                self.assertFalse(is_dangerous_command(cmd),
                             f"Should detect '{cmd}' as safe")


if __name__ == '__main__':
    unittest.main() 