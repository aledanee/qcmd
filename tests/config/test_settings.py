#!/usr/bin/env python3
"""
Tests for the configuration settings functionality.
"""
import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, mock_open, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import functions to test
from qcmd_cli.config.settings import (
    load_config, save_config, handle_config_command, get_config_path,
    CONFIG_FILE, DEFAULT_MODEL, DEFAULT_TEMPERATURE, DEFAULT_UI_SETTINGS
)


class TestConfigSettings(unittest.TestCase):
    """Test the configuration settings functions."""
    
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_config_file = os.path.join(self.temp_dir.name, 'config.json')
    
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
    
    @patch('qcmd_cli.config.settings.CONFIG_FILE')
    @patch('qcmd_cli.config.settings.os.makedirs')
    def test_load_config_default(self, mock_makedirs, mock_config_file):
        """Test loading default configuration when no file exists."""
        # Replace the CONFIG_FILE with our temp file that doesn't exist
        mock_config_file.__str__.return_value = self.temp_config_file
        
        # Test loading configuration when file doesn't exist
        config = load_config()
        
        # Verify makedirs was called to create config directory
        mock_makedirs.assert_called_once()
        
        # Verify default values
        self.assertEqual(config['model'], DEFAULT_MODEL)
        self.assertEqual(config['temperature'], DEFAULT_TEMPERATURE)
        self.assertEqual(config['ui'], DEFAULT_UI_SETTINGS)
    
    def test_load_config_existing(self):
        """Test loading configuration from existing file."""
        # Create a test config file
        test_config = {
            'model': 'test-model',
            'temperature': 0.5,
            'ui': {
                'show_iraq_banner': False,
                'compact_mode': True
            }
        }
        
        # Create parent directory
        os.makedirs(os.path.dirname(self.temp_config_file), exist_ok=True)
        
        # Write test config to the temporary file
        with open(self.temp_config_file, 'w') as f:
            json.dump(test_config, f)
        
        # Patch CONFIG_FILE and load
        with patch('qcmd_cli.config.settings.CONFIG_FILE', self.temp_config_file):
            # Test loading configuration
            config = load_config()
            
            # Verify loaded values
            self.assertEqual(config['model'], 'test-model')
            self.assertEqual(config['temperature'], 0.5)
            self.assertEqual(config['ui']['show_iraq_banner'], False)
            self.assertEqual(config['ui']['compact_mode'], True)
            # Default values should be preserved for unspecified keys
            self.assertEqual(config['ui']['show_progress_bar'], DEFAULT_UI_SETTINGS['show_progress_bar'])
    
    @patch('qcmd_cli.config.settings.os.makedirs')
    def test_save_config(self, mock_makedirs):
        """Test saving configuration to file."""
        # Create a test config
        test_config = {
            'model': 'test-model',
            'temperature': 0.5,
            'ui': {
                'show_iraq_banner': False,
                'compact_mode': True
            }
        }
        
        # Create parent directory
        os.makedirs(os.path.dirname(self.temp_config_file), exist_ok=True)
        
        # Patch CONFIG_FILE and save
        with patch('qcmd_cli.config.settings.CONFIG_FILE', self.temp_config_file):
            # Save the configuration
            save_config(test_config)
            
            # Verify the file was written with correct content
            with open(self.temp_config_file, 'r') as f:
                saved_config = json.load(f)
            
            self.assertEqual(saved_config['model'], 'test-model')
            self.assertEqual(saved_config['temperature'], 0.5)
            self.assertEqual(saved_config['ui']['show_iraq_banner'], False)
            self.assertEqual(saved_config['ui']['compact_mode'], True)
    
    @patch('qcmd_cli.config.settings.CONFIG_FILE')
    @patch('qcmd_cli.config.settings.load_config')
    @patch('qcmd_cli.config.settings.save_config')
    def test_handle_config_command_display(self, mock_save_config, mock_load_config, mock_config_file):
        """Test displaying configuration."""
        # Mock the configuration
        mock_load_config.return_value = {
            'model': 'test-model',
            'temperature': 0.5,
            'ui': {
                'show_iraq_banner': False,
                'compact_mode': True
            },
            'colors': {
                'GREEN': '\033[92m'
            }
        }
        
        # Capture stdout to verify output
        with patch('sys.stdout') as mock_stdout:
            handle_config_command("")
            
            # Verify load_config was called
            mock_load_config.assert_called_once()
            
            # Verify save_config was not called (display only)
            mock_save_config.assert_not_called()
    
    @patch('qcmd_cli.config.settings.CONFIG_FILE')
    @patch('qcmd_cli.config.settings.load_config')
    @patch('qcmd_cli.config.settings.save_config')
    def test_handle_config_command_set(self, mock_save_config, mock_load_config, mock_config_file):
        """Test setting configuration values."""
        # Mock the configuration
        mock_config = {
            'model': 'default-model',
            'temperature': 0.2,
            'ui': {},
            'colors': {}
        }
        mock_load_config.return_value = mock_config
        
        # Test setting a top-level string value
        handle_config_command("set model new-model")
        
        # Verify the config was updated correctly
        self.assertEqual(mock_config['model'], 'new-model')
        
        # Verify save_config was called
        mock_save_config.assert_called_with(mock_config)
        
        # Reset mock
        mock_save_config.reset_mock()
        
        # Test setting a top-level numeric value
        handle_config_command("set temperature 0.8")
        
        # Verify the config was updated correctly
        self.assertEqual(mock_config['temperature'], 0.8)
        
        # Verify save_config was called
        mock_save_config.assert_called_with(mock_config)
        
        # Reset mock
        mock_save_config.reset_mock()
        
        # Test setting a nested value
        handle_config_command("set ui.compact_mode true")
        
        # Verify the config was updated correctly
        self.assertEqual(mock_config['ui']['compact_mode'], True)
        
        # Verify save_config was called
        mock_save_config.assert_called_with(mock_config)
    
    @patch('qcmd_cli.config.settings.Colors.reset_to_defaults')
    def test_handle_config_command_reset(self, mock_reset_colors):
        """Test resetting configuration."""
        # Create parent directory and a test file to reset
        os.makedirs(os.path.dirname(self.temp_config_file), exist_ok=True)
        with open(self.temp_config_file, 'w') as f:
            f.write("{}")
            
        # Patch CONFIG_FILE, os.path.exists, and os.remove
        with patch('qcmd_cli.config.settings.CONFIG_FILE', self.temp_config_file):
            with patch('qcmd_cli.config.settings.os.path.exists', return_value=True):
                with patch('qcmd_cli.config.settings.os.remove') as mock_remove:
                    # Test resetting configuration
                    handle_config_command("reset")
                    
                    # Verify remove was called with the correct path
                    mock_remove.assert_called_once_with(self.temp_config_file)
                    
                    # Verify colors were reset
                    mock_reset_colors.assert_called_once()
    
    def test_get_config_path(self):
        """Test getting the configuration file path."""
        path = get_config_path()
        self.assertEqual(path, CONFIG_FILE)


if __name__ == '__main__':
    unittest.main() 