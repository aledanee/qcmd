#!/usr/bin/env python3
"""
Tests for the command_generator module.
"""
import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock
import subprocess
import requests

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.core.command_generator import (
    generate_command, analyze_error, fix_command, 
    list_models, execute_command, is_dangerous_command,
    CommandExecutionError, ProcessTimeoutError,
    APIConnectionError, APITimeoutError, APIResponseError,
    DangerousCommandError, ProcessCreationError, CommandOutputError,
    ModelUnavailableError
)


class TestCommandGenerator(unittest.TestCase):
    """Test the command generator functions."""
    
    @patch('qcmd_cli.core.command_generator.list_models')
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_generate_command(self, mock_post, mock_list_models):
        """Test that command generation works correctly."""
        # Mock list_models to return our test model
        mock_list_models.return_value = ['qwen2.5-coder:0.5b']
        
        # Mock the API response for streaming
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            '{"response": "ls", "done": false}'.encode(),
            '{"response": " -la", "done": true}'.encode()
        ]
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test command generation
        command = generate_command("list all files in current directory")
        
        # Verify the command is correct
        self.assertEqual(command, "ls -la")
        
        # Verify the API was called correctly
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("generate", args[0])
        self.assertEqual(kwargs["json"]["model"], "qwen2.5-coder:0.5b")  # Default model
        self.assertIn("list all files", kwargs["json"]["prompt"])
        self.assertTrue(kwargs["json"]["stream"])  # Verify streaming is enabled
    
    @patch('qcmd_cli.core.command_generator.list_models')
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_generate_command_with_markdown_format(self, mock_post, mock_list_models):
        """Test command generation with different markdown formats."""
        # Mock list_models to return our test model
        mock_list_models.return_value = ['qwen2.5-coder:0.5b']
        
        # Test with triple backticks code block
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            '{"response": "```", "done": false}'.encode(),
            '{"response": "ls", "done": false}'.encode(),
            '{"response": " -la", "done": false}'.encode(),
            '{"response": "```", "done": true}'.encode()
        ]
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        command = generate_command("list files")
        self.assertEqual(command, "ls -la")
        
        # Test with single backticks
        mock_response.iter_lines.return_value = [
            '{"response": "`", "done": false}'.encode(),
            '{"response": "ls", "done": false}'.encode(),
            '{"response": " -la", "done": false}'.encode(),
            '{"response": "`", "done": true}'.encode()
        ]
        command = generate_command("list files")
        self.assertEqual(command, "ls -la")
        
        # Test with no markdown
        mock_response.iter_lines.return_value = [
            '{"response": "ls", "done": false}'.encode(),
            '{"response": " -la", "done": true}'.encode()
        ]
        command = generate_command("list files")
        self.assertEqual(command, "ls -la")
    
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_analyze_error(self, mock_post):
        """Test error analysis functionality."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "The file does not exist. Try using 'ls' to check available files."}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        analysis = analyze_error("cat: file.txt: No such file or directory", "cat file.txt")
        
        self.assertIn("file does not exist", analysis.lower())
        mock_post.assert_called_once()
    
    @patch('qcmd_cli.core.command_generator.requests.post')
    def test_fix_command(self, mock_post):
        """Test command fixing functionality."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "The command should be 'ls -la' to show all files including hidden ones."}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        fixed_command = fix_command("ls -l", "Some error output")
        
        self.assertIn("ls -la", fixed_command.lower())
        mock_post.assert_called_once()
    
    @patch('qcmd_cli.core.command_generator.requests.get')
    def test_list_models(self, mock_get):
        """Test listing models functionality."""
        # Test successful response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:0.5b", "size": 1073741824, "modified": "2023-01-01"},
                {"name": "llama2:7b", "size": 1073741824, "modified": "2023-01-01"},
                {"name": "test-model", "size": 1073741824, "modified": "2023-01-01"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        models = list_models()
        self.assertEqual(len(models), 3)
        self.assertIn("qwen2.5-coder:0.5b", models)
        self.assertIn("llama2:7b", models)
        self.assertIn("test-model", models)
        mock_get.assert_called_once()
        
        # Test connection error
        mock_get.reset_mock()
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")
        with self.assertRaises(APIConnectionError) as cm:
            list_models()
        self.assertIn("Could not connect to Ollama API", str(cm.exception))
        
        # Test timeout error
        mock_get.reset_mock()
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        with self.assertRaises(APITimeoutError) as cm:
            list_models()
        self.assertIn("API request timed out", str(cm.exception))
        
        # Test HTTP error
        mock_get.reset_mock()
        mock_response = MagicMock()  # Create new mock response
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.side_effect = None
        mock_get.return_value = mock_response
        with self.assertRaises(APIResponseError) as cm:
            list_models()
        self.assertIn("API returned HTTP error", str(cm.exception))
        
        # Test invalid response format
        mock_get.reset_mock()
        mock_response = MagicMock()  # Create new mock response
        mock_response.raise_for_status.return_value = None  # Reset raise_for_status
        mock_response.json.return_value = {"invalid": "response"}
        mock_get.return_value = mock_response
        with self.assertRaises(APIResponseError) as cm:
            list_models()
        self.assertIn("Invalid API response format", str(cm.exception))
        
        # Test empty models list
        mock_get.reset_mock()
        mock_response = MagicMock()  # Create new mock response
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"models": []}
        mock_get.return_value = mock_response
        with self.assertRaises(ModelUnavailableError) as cm:
            list_models()
        self.assertIn("No models available", str(cm.exception))
    
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.is_dangerous_command')
    def test_execute_command(self, mock_is_dangerous, mock_popen):
        """Test command execution."""
        # Mock is_dangerous_command to return False
        mock_is_dangerous.return_value = False
        
        # Setup process mock
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = ("Command output line 1\nCommand output line 2", "")
        mock_popen.return_value = process_mock
        
        # Execute the command
        stdout, stderr, returncode = execute_command("ls -la")
        
        # Verify the results
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, "Command output line 1\nCommand output line 2")
        self.assertEqual(stderr, "")
        mock_popen.assert_called_once()
    
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_process_creation_error(self, mock_popen):
        """Test command execution when process creation fails."""
        mock_popen.side_effect = OSError("Failed to create process")
        with self.assertRaises(CommandExecutionError) as cm:
            execute_command("test-command", max_retries=1, timeout=1)  # Short timeout
        self.assertIn("Command failed after 1 attempt: Failed to create process", str(cm.exception))
        mock_popen.reset_mock()

    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_timeout_error(self, mock_popen):
        """Test command execution when process times out."""
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("test-command", 1)
        process_mock.pid = 12345  # Mock pid for cleanup
        # Mock the os.killpg and os.getpgid functions to prevent "No such process" error
        with patch('os.killpg'), patch('os.getpgid'):
            mock_popen.return_value = process_mock
            with self.assertRaises(CommandExecutionError) as cm:
                execute_command("test-command", max_retries=1, timeout=1)  # Short timeout
            self.assertIn("Command failed after 1 attempt: Command timed out after 1 seconds", str(cm.exception))
        mock_popen.reset_mock()

    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    def test_execute_command_nonzero_exit(self, mock_popen):
        """Test command execution when process returns non-zero exit code."""
        process_mock = MagicMock()
        process_mock.returncode = 1
        process_mock.communicate.return_value = ("", "Error: Command failed")
        mock_popen.return_value = process_mock
        
        with self.assertRaises(CommandExecutionError) as cm:
            execute_command("test-command", max_retries=1, timeout=1)  # Short timeout
        self.assertIn("Command failed after 1 attempt: Command failed with exit code 1: Error: Command failed", str(cm.exception))
        mock_popen.reset_mock()
    
    def test_is_dangerous_command(self):
        """Test dangerous command detection."""
        # Dangerous commands
        dangerous_commands = [
            "rm -rf /",
            "rm -r /home",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            ":(){:|:&};:",
            "chmod -R 777 /",
        ]
        
        # Safe commands
        safe_commands = [
            "ls -la",
            "cd /home",
            "cat file.txt",
            "echo 'hello world'",
            "find . -name '*.py'",
        ]
        
        for cmd in dangerous_commands:
            self.assertTrue(is_dangerous_command(cmd), f"Should detect {cmd} as dangerous")
            
        for cmd in safe_commands:
            self.assertFalse(is_dangerous_command(cmd), f"Should not detect {cmd} as dangerous")


if __name__ == '__main__':
    unittest.main() 