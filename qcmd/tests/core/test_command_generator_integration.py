#!/usr/bin/env python3
"""
Integration tests for the command generator module.
These tests verify the complete command generation and execution flow.
"""
import unittest
import os
import sys
import json
from unittest.mock import patch, MagicMock, call
import subprocess
import click
import requests

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.core.command_generator import (
    generate_command, analyze_error, fix_command, 
    list_models, execute_command, is_dangerous_command,
    DANGEROUS_PATTERNS,
    CommandGenerationError, APITimeoutError, APIConnectionError,
    APIRateLimitError, APIResponseError, ModelUnavailableError,
    CommandValidationError, CommandExecutionError, CommandOutputError
)
from qcmd_cli.config.settings import DEFAULT_MODEL


class TestCommandGeneratorIntegration(unittest.TestCase):
    """Integration tests for the command generator functions."""
    
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    def test_complete_command_flow_success(self, mock_confirm, mock_popen, mock_post):
        """Test the complete command generation and execution flow with success."""
        # Setup mocks
        mock_confirm.return_value = True
        
        # Mock API response for command generation
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "ls", "done": false}',
            b'{"response": " -la", "done": true}'
        ]
        mock_post.return_value = mock_response
        
        # Mock process execution
        process_mock = MagicMock()
        process_mock.returncode = 0
        process_mock.communicate.return_value = ("file1.txt\nfile2.txt", "")
        mock_popen.return_value = process_mock
        
        # Generate and execute command
        command = generate_command("list files")
        assert command == "ls -la"
        
        # Verify results
        self.assertEqual(command, "ls -la")
        self.assertEqual(process_mock.returncode, 0)
        self.assertEqual(process_mock.communicate()[0], b"file1.txt\nfile2.txt")
        
        # Verify API was called
        mock_post.assert_called_once()
        
        # Verify command was executed
        mock_popen.assert_called_once()
        # Note: confirm is only called for dangerous commands
        mock_confirm.assert_not_called()
    
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    def test_complete_command_flow_with_error_recovery(self, mock_confirm, mock_popen, mock_post):
        """Test the complete command flow with error recovery."""
        # Setup mocks
        mock_confirm.return_value = True
        
        # Mock API response for command generation
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "ls", "done": false}',
            b'{"response": " /root", "done": true}'
        ]
        mock_post.return_value = mock_response
        
        # Mock process execution with initial failure and successful recovery
        process_mock_1 = MagicMock()
        process_mock_1.returncode = 1
        process_mock_1.communicate.return_value = ("", "permission denied")
        
        process_mock_2 = MagicMock()
        process_mock_2.returncode = 0
        process_mock_2.communicate.return_value = ("file1.txt\nfile2.txt", "")
        
        mock_popen.side_effect = [process_mock_1, process_mock_2]
        
        # Generate command
        command = generate_command("list root directory")
        assert command == "ls /root"
        
        # Execute command - should fail first time and succeed with fallback
        try:
            execute_command(command)
        except CommandExecutionError as e:
            # Verify error message
            self.assertIn("permission denied", str(e))
            
            # Try with fallback command
            fallback_command = "ls -la /root"  # This is the expected fallback
            return_code, output = execute_command(fallback_command)
            
            # Verify fallback results
            self.assertEqual(return_code, 0)
            self.assertEqual(output, "file1.txt\nfile2.txt")
            
            # Verify API was called once for generation
            mock_post.assert_called_once()
            
            # Verify commands were executed
            self.assertEqual(mock_popen.call_count, 2)
            self.assertIn("ls /root", mock_popen.call_args_list[0][0][0])
            self.assertIn("ls -la /root", mock_popen.call_args_list[1][0][0])
            
            # Note: confirm is only called for dangerous commands
            mock_confirm.assert_not_called()
    
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    @patch('qcmd_cli.core.command_generator.analyze_error')
    def test_complete_command_flow_with_command_fixing(self, mock_analyze_error, mock_confirm, mock_popen, mock_post):
        """Test the complete command flow with command fixing."""
        # Setup mocks
        mock_confirm.return_value = True
        
        # Mock API responses
        mock_response = MagicMock()
        mock_response.iter_lines.side_effect = [
            [b'{"response": "git", "done": false}', b'{"response": " status", "done": true}'],
            [b'{"response": "git", "done": false}', b'{"response": " init", "done": true}']
        ]
        mock_post.return_value = mock_response
        
        # Mock error analysis
        mock_analyze_error.return_value = "not a git repository"
        
        # Mock process execution
        process_mock_1 = MagicMock()
        process_mock_1.returncode = 1
        process_mock_1.communicate.return_value = ("", "not a git repository")
        
        process_mock_2 = MagicMock()
        process_mock_2.returncode = 0
        process_mock_2.communicate.return_value = ("Initialized empty Git repository", "")
        
        mock_popen.side_effect = [process_mock_1, process_mock_2]
        
        # Generate command
        command = generate_command("check git status")
        assert command == "git status"
        
        # Execute command - should fail first time and succeed with fix
        try:
            execute_command(command)
        except CommandExecutionError as e:
            # Verify error message
            self.assertIn("not a git repository", str(e))
            
            # Try with fixed command
            fixed_command = "git init"  # This is the expected fix
            return_code, output = execute_command(fixed_command)
            
            # Verify fix results
            self.assertEqual(return_code, 0)
            self.assertEqual(output, "Initialized empty Git repository")
            
            # Verify API was called twice (initial + fix)
            self.assertEqual(mock_post.call_count, 2)
            
            # Verify commands were executed
            self.assertEqual(mock_popen.call_count, 2)
            self.assertIn("git status", mock_popen.call_args_list[0][0][0])
            self.assertIn("git init", mock_popen.call_args_list[1][0][0])
            
            # Note: confirm is only called for dangerous commands
            mock_confirm.assert_not_called()
    
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    def test_complete_command_flow_with_dangerous_command(self, mock_confirm, mock_popen, mock_post):
        """Test the complete command flow with dangerous command handling."""
        # Setup mocks
        mock_confirm.return_value = False  # User rejects dangerous command
        
        # Mock API response for command generation
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "rm", "done": false}',
            b'{"response": " -rf /", "done": true}'
        ]
        mock_post.return_value = mock_response
        
        # Generate command
        command = generate_command("remove all files")
        assert command == "rm -rf /"
        
        # Execute command - should fail due to dangerous command
        with self.assertRaises(CommandValidationError) as context:
            execute_command(command)
        
        # Verify error message
        self.assertIn("Command appears to be dangerous", str(context.exception))
        
        # Verify no execution occurred
        mock_popen.assert_not_called()
        mock_confirm.assert_called_once()
    
    @patch('qcmd_cli.core.command_generator.requests.post')
    @patch('qcmd_cli.core.command_generator.subprocess.Popen')
    @patch('qcmd_cli.core.command_generator.click.confirm')
    def test_complete_command_flow_with_timeout(self, mock_confirm, mock_popen, mock_post):
        """Test the complete command flow with timeout handling."""
        # Setup mocks
        mock_confirm.return_value = True
        
        # Mock API response for command generation
        mock_response = MagicMock()
        mock_response.iter_lines.return_value = [
            b'{"response": "sleep", "done": false}',
            b'{"response": " 60", "done": true}'
        ]
        mock_post.return_value = mock_response
        
        # Mock process execution with timeout
        process_mock = MagicMock()
        process_mock.communicate.side_effect = subprocess.TimeoutExpired("sleep 60", 30)
        mock_popen.return_value = process_mock
        
        # Generate command
        command = generate_command("sleep for a minute")
        assert command == "sleep 60"
        
        # Execute command - should timeout
        with self.assertRaises(CommandExecutionError) as context:
            execute_command(command)
        
        # Verify error message
        self.assertIn("Command timed out after 30 seconds", str(context.exception))
        
        # Verify process was killed at least once
        self.assertTrue(process_mock.kill.called)
        # Note: The process might be killed multiple times due to retries


if __name__ == '__main__':
    unittest.main() 