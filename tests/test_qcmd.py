#!/usr/bin/env python3
"""
Basic tests for qcmd functionality.
"""

import unittest
import os
import sys
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions to test
try:
    from qcmd import is_dangerous_command, save_config, load_config
except ImportError:
    # If running as script
    print("Could not import qcmd module. Make sure it's in your PYTHONPATH.")
    sys.exit(1)


class TestQcmdSafety(unittest.TestCase):
    """Test the safety features of qcmd."""
    
    def test_dangerous_command_detection(self):
        """Test that dangerous commands are properly detected."""
        dangerous_commands = [
            "rm -rf /",
            "rm -r /home",
            "dd if=/dev/zero of=/dev/sda",
            "mkfs.ext4 /dev/sda1",
            ":(){:|:&};:",
            "chmod -R 777 /",
        ]
        
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


class TestQcmdConfig(unittest.TestCase):
    """Test the configuration management of qcmd."""
    
    def setUp(self):
        """Set up a temporary config file for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config")
        
    def tearDown(self):
        """Clean up temporary files."""
        self.temp_dir.cleanup()
        
    def test_config_save_load(self):
        """Test that config can be saved and loaded."""
        test_config = {
            "model": "test-model",
            "temperature": 0.5,
            "timeout": 30,
            "favorite_logs": ["/var/log/test.log"],
            "auto_mode": False
        }
        
        with patch('qcmd.CONFIG_FILE', self.config_path):
            save_config(test_config)
            loaded_config = load_config()
            
        self.assertEqual(loaded_config["model"], test_config["model"])
        self.assertEqual(loaded_config["temperature"], test_config["temperature"])
        self.assertEqual(loaded_config["timeout"], test_config["timeout"])
        self.assertEqual(loaded_config["favorite_logs"], test_config["favorite_logs"])


if __name__ == '__main__':
    unittest.main() 