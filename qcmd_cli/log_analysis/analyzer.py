#!/usr/bin/env python3
"""
Log analysis functionality for QCMD.
"""
import os
import re
import json
import time
import signal
import threading
from typing import List, Dict, Optional, Tuple, Any

# Import from local modules once they are created
from ..config.settings import DEFAULT_MODEL
from ..ui.display import Colors
from .monitor_state import (
    active_log_monitors,
    save_active_monitors,
    load_active_monitors
)

def handle_log_analysis(model: str = DEFAULT_MODEL, specific_file: str = None) -> None:
    """
    Handle log analysis workflow - prompting user to select log files and analyzing them.
    
    Args:
        model: Model to use for analysis
        specific_file: Optional specific file to analyze
    """
    if specific_file:
        if os.path.exists(specific_file):
            print(f"\n{Colors.GREEN}Analyzing log file: {specific_file}{Colors.END}")
            analyze_log_file(specific_file, model)
        else:
            print(f"\n{Colors.RED}File not found: {specific_file}{Colors.END}")
        return
    
    # Import here to avoid circular imports
    from .log_files import find_log_files, select_log_file
    
    # Find log files
    log_files = find_log_files()
    
    if not log_files:
        print(f"\n{Colors.YELLOW}No log files found.{Colors.END}")
        print(f"Try specifying a path with: qcmd logs /path/to/logs")
        return
    
    # Let user select a log file
    selected_file = select_log_file(log_files)
    
    if selected_file:
        analyze_log_file(selected_file, model)

def analyze_log_entry(entry: str) -> str:
    """
    Analyze a single log entry and generate a meaningful description.

    Args:
        entry: The log entry to analyze

    Returns:
        A description of what the log entry indicates
    """
    # Example parsing logic (can be extended for more complex analysis)
    if "error" in entry.lower():
        return "This log entry indicates an error occurred. Please check the details."
    elif "warning" in entry.lower():
        return "This log entry indicates a warning. It might require attention."
    elif "info" in entry.lower():
        return "This log entry provides informational details."
    else:
        return "This log entry does not match known patterns."

def monitor_log_file(log_file: str, model: str, stop_event: threading.Event) -> None:
    """
    Monitor a log file for new lines and analyze them in real-time.

    Args:
        log_file: Path to the log file
        model: Model to use for analysis
        stop_event: Event to signal the thread to stop
    """
    thread_id = threading.get_ident()
    active_log_monitors[thread_id] = log_file
    save_active_monitors()  # Save to persistent storage
    print(f"{Colors.GREEN}Starting live monitoring for: {log_file}{Colors.END}")

    try:
        with open(log_file, 'r') as file:
            # Move to the end of the file
            file.seek(0, os.SEEK_END)

            while not stop_event.is_set():
                line = file.readline()
                if not line:
                    time.sleep(1)  # Wait for new lines
                    continue

                # Perform Log Analysis Results
                print(f"\n{Colors.CYAN}New Log Entry:{Colors.END} {line.strip()}")
                analyze_log_content(line, log_file, model)

                # Perform Text Analysis
                description = analyze_log_entry(line)
                print(f"\n{Colors.GREEN}Text Analysis:{Colors.END}")
                print(f"Description: {description}")

    except Exception as e:
        print(f"{Colors.RED}Error during live monitoring: {e}{Colors.END}")
    finally:
        # Remove the monitor from the active list when the thread ends
        del active_log_monitors[thread_id]
        save_active_monitors()  # Update persistent storage

def analyze_log_file(log_file: str, model: str = DEFAULT_MODEL, background: bool = False, analyze: bool = True) -> None:
    """
    Analyze a log file using AI.

    Args:
        log_file: Path to the log file
        model: Model to use for analysis
        background: Whether to run in background mode
        analyze: Whether to perform analysis (vs just monitoring)
    """
    # Check if file exists
    if not os.path.exists(log_file):
        print(f"{Colors.RED}Error: File {log_file} not found.{Colors.END}")
        return

    if background:
        # Create a stop event for the monitoring thread
        stop_event = threading.Event()

        def signal_handler(sig, frame):
            if sig == signal.SIGINT:  # Control + C
                print(f"\n{Colors.RED}Terminating live monitoring session...{Colors.END}")
                stop_event.set()
                # Reset signal handler to default behavior
                signal.signal(signal.SIGINT, signal.SIG_DFL)
            elif sig == signal.SIGTSTP:  # Control + H
                print(f"\n{Colors.YELLOW}Hiding live monitoring session. Press Control + H again to show.{Colors.END}")

        # Register signal handlers in the main thread
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTSTP, signal_handler)

        # Start live monitoring in a separate thread
        monitor_thread = threading.Thread(target=monitor_log_file, args=(log_file, model, stop_event), daemon=True)
        monitor_thread.start()

        # Wait for the thread to finish
        try:
            monitor_thread.join()
        except KeyboardInterrupt:
            # Ensure proper cleanup on KeyboardInterrupt
            stop_event.set()
            monitor_thread.join()
    else:
        print(f"\n{Colors.CYAN}Analyzing log file: {log_file}{Colors.END}")

        # Read file content
        try:
            content = read_large_file(log_file)
            if not content:
                print(f"{Colors.YELLOW}Log file is empty.{Colors.END}")
                return

            # Perform analysis
            analyze_log_content(content, log_file, model)

        except Exception as e:
            print(f"{Colors.RED}Error analyzing log file: {str(e)}{Colors.END}")

def analyze_log_content(log_content: str, log_file: str, model: str = DEFAULT_MODEL) -> None:
    """
    Analyze the content of a log file.
    
    Args:
        log_content: Content of the log file
        log_file: Path to the log file (for reference)
        model: Model to use for analysis
    """
    print(f"\n{Colors.CYAN}Analyzing log content using {model}...{Colors.END}")
    
    # Basic implementation - in a real application, this would use an LLM via Ollama API
    print(f"\n{Colors.GREEN}Log Analysis Results:{Colors.END}")
    print(f"File: {log_file}")
    print(f"Size: {len(log_content)} bytes")
    
    # Count lines and errors (simple heuristic)
    lines = log_content.splitlines()
    error_count = sum(1 for line in lines if "error" in line.lower() or "exception" in line.lower())
    
    print(f"Total lines: {len(lines)}")
    print(f"Potential errors/exceptions: {error_count}")
    
    # In a complete implementation, we would call the LLM to analyze the log content

def read_large_file(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Read a large file efficiently.
    
    Args:
        file_path: Path to the file
        chunk_size: Size of each chunk to read
        
    Returns:
        Content of the file as a string
    """
    content = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            content.append(chunk)
    return "".join(content)

def get_active_log_monitors() -> List[Dict[str, Any]]:
    """
    Retrieve the list of active log monitors.

    Returns:
        A list of dictionaries containing active log monitor details.
    """
    return [{"thread_id": tid, "log_file": log_file} for tid, log_file in active_log_monitors.items()]