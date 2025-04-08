import unittest
from unittest.mock import patch, mock_open, MagicMock, call
import os
import tempfile
import time
from qcmd_cli.log_analysis.monitor import monitor_log
from qcmd_cli.ui.display import Colors

class TestMonitorCore(unittest.TestCase):
    def setUp(self):
        """Set up temporary files for testing."""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_log_file = os.path.join(self.temp_dir, "test.log")
        with open(self.temp_log_file, 'w') as f:
            f.write("Initial log content\n")

    def tearDown(self):
        """Clean up temporary files."""
        if os.path.exists(self.temp_dir):
            for f in os.listdir(self.temp_dir):
                os.remove(os.path.join(self.temp_dir, f))
            os.rmdir(self.temp_dir)

    @patch('qcmd_cli.log_analysis.monitor.time.sleep')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    def test_monitor_log_initial_content(self, mock_analyze, mock_print, mock_open, mock_getsize, mock_sleep):
        """Test that monitor_log correctly handles initial content and new content."""
        # Mock initial file size and then a larger size to simulate file growth
        mock_getsize.side_effect = [100, 150]

        # Mock file content
        mock_file = mock_open.return_value
        mock_file.read.return_value = "New content"

        # Mock sleep to raise KeyboardInterrupt after first iteration
        mock_sleep.side_effect = [None, KeyboardInterrupt]

        # Call monitor_log without background mode
        monitor_log(self.temp_log_file, background=False, analyze=True)

        # Verify that analyze_log_content was called only for new content
        mock_analyze.assert_called_once_with("New content", self.temp_log_file, "llama3:latest")

        # Verify monitoring messages for the new content
        mock_print.assert_any_call(f"\n{Colors.CYAN}New log entries detected at {time.strftime('%H:%M:%S')}:{Colors.END}")
        mock_print.assert_any_call(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
        mock_print.assert_any_call("New content")
        mock_print.assert_any_call(f"\n{Colors.YELLOW}Stopped monitoring log file.{Colors.END}")

    @patch('qcmd_cli.log_analysis.monitor.time.sleep')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    def test_monitor_log_file_growth(self, mock_analyze, mock_print, mock_open, mock_getsize, mock_sleep):
        """Test that monitor_log detects and handles file growth."""
        # Mock file size changes
        call_count = 0
        def getsize_with_growth(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 100
            elif call_count == 2:
                return 150
            raise KeyboardInterrupt()
        mock_getsize.side_effect = getsize_with_growth

        # Mock file content for different reads
        mock_file = mock_open.return_value
        mock_file.read.side_effect = [
            "Initial content",
            "New content 1"
        ]

        # Call monitor_log without background mode
        monitor_log(self.temp_log_file, background=False, analyze=True)

        # Verify monitoring messages
        mock_print.assert_any_call(f"\n{Colors.CYAN}New log entries detected at {time.strftime('%H:%M:%S')}:{Colors.END}")
        mock_print.assert_any_call(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
        mock_print.assert_any_call(f"\n{Colors.YELLOW}Stopped monitoring log file.{Colors.END}")

    @patch('qcmd_cli.log_analysis.monitor.time.sleep')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    def test_monitor_log_file_errors(self, mock_analyze, mock_print, mock_open, mock_getsize, mock_sleep):
        """Test error handling in monitor_log."""
        # Mock getsize to raise different errors
        call_count = 0
        def getsize_with_errors(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 100
            elif call_count == 2:
                raise FileNotFoundError()
            raise KeyboardInterrupt()
        mock_getsize.side_effect = getsize_with_errors

        # Mock file content
        mock_file = mock_open.return_value
        mock_file.read.return_value = "Test content"

        # Call monitor_log without background mode
        monitor_log(self.temp_log_file, background=False, analyze=True)

        # Verify error messages were printed with color formatting
        expected_error = f"\n{Colors.RED}Error: Log file {self.temp_log_file} no longer exists.{Colors.END}"
        mock_print.assert_any_call(expected_error)

    @patch('qcmd_cli.log_analysis.monitor.time.sleep')
    @patch('qcmd_cli.log_analysis.monitor.os.path.getsize')
    @patch('builtins.open', new_callable=mock_open)
    @patch('builtins.print')
    @patch('qcmd_cli.log_analysis.monitor.analyze_log_content')
    def test_monitor_log_watch_only(self, mock_analyze, mock_print, mock_open, mock_getsize, mock_sleep):
        """Test monitor_log in watch-only mode (no analysis)."""
        # Mock file size changes
        call_count = 0
        def getsize_with_growth(*args):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return 100
            elif call_count == 2:
                return 150
            raise KeyboardInterrupt()
        mock_getsize.side_effect = getsize_with_growth

        # Mock file content
        mock_file = mock_open.return_value
        mock_file.read.side_effect = [
            "Initial content",
            "New log entries"
        ]

        # Call monitor_log in watch-only mode without background mode
        monitor_log(self.temp_log_file, background=False, analyze=False)

        # Verify analyze_log_content was not called
        mock_analyze.assert_not_called()

        # Verify monitoring messages
        mock_print.assert_any_call(f"\n{Colors.CYAN}New log entries detected at {time.strftime('%H:%M:%S')}:{Colors.END}")
        mock_print.assert_any_call(f"{Colors.YELLOW}" + "-" * 40 + f"{Colors.END}")
        mock_print.assert_any_call(f"\n{Colors.YELLOW}Stopped monitoring log file.{Colors.END}")

if __name__ == '__main__':
    unittest.main()