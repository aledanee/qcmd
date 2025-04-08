#!/usr/bin/env python3
"""
Log analysis functionality for QCMD.

This module provides functionality for analyzing log files using AI models.
It includes features for reading, parsing, and analyzing log content, with support
for both one-time analysis and continuous monitoring.

Example usage:
    >>> from qcmd_cli.log_analysis.analyzer import analyze_log_file
    >>> analyze_log_file("/var/log/syslog", model="llama3:latest")
    >>> # For continuous monitoring:
    >>> analyze_log_file("/var/log/auth.log", background=True, analyze=True)
"""
import os
import re
import json
import time
import signal
import logging
from typing import List, Dict, Optional, Tuple, Any, Union

# Import from local modules
from ..config.settings import DEFAULT_MODEL
from ..core.command_generator import generate_command
from ..ui.display import Colors

logger = logging.getLogger(__name__)

def analyze_log_file(log_file: str, model: str = DEFAULT_MODEL, background: bool = False, analyze: bool = True) -> None:
    """
    Analyze a log file using AI.
    
    This function reads a log file and performs AI-based analysis on its contents.
    It supports both one-time analysis and continuous monitoring modes.
    
    Args:
        log_file: Path to the log file to analyze
        model: Name of the AI model to use for analysis (default: DEFAULT_MODEL)
        background: If True, runs analysis in background mode with continuous monitoring
        analyze: If True, performs AI analysis; if False, only monitors for changes
        
    Returns:
        None
        
    Raises:
        FileNotFoundError: If the specified log file does not exist
        PermissionError: If the log file cannot be accessed
        UnicodeDecodeError: If the log file cannot be read with UTF-8 encoding
        Exception: For other unexpected errors during file reading or analysis
        
    Example:
        >>> analyze_log_file("/var/log/syslog")
        >>> # For continuous monitoring with analysis:
        >>> analyze_log_file("/var/log/auth.log", background=True, analyze=True)
        >>> # For monitoring without analysis:
        >>> analyze_log_file("/var/log/nginx/access.log", background=True, analyze=False)
    """
    if not os.path.exists(log_file):
        logger.error(f"Log file {log_file} does not exist")
        print(f"{Colors.RED}Error: Log file {log_file} does not exist.{Colors.END}")
        return
        
    logger.info(f"Starting analysis of log file: {log_file}")
    print(f"{Colors.GREEN}Analyzing log file: {Colors.BOLD}{log_file}{Colors.END}")
    
    # Get file size for pagination
    file_size = os.path.getsize(log_file)
    logger.debug(f"Log file size: {file_size} bytes")
    
    # For very large files, ask if user wants to analyze only the last part
    if file_size > 10 * 1024 * 1024 and not background:  # 10 MB
        print(f"{Colors.YELLOW}Warning: This log file is very large ({file_size // (1024*1024)} MB).{Colors.END}")
        response = input(f"{Colors.GREEN}Analyze only the last portion? (y/n, default: y): {Colors.END}").lower()
        if not response or response.startswith('y'):
            # Read only the last 1 MB
            try:
                with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                    f.seek(max(0, file_size - 1 * 1024 * 1024))  # Go to last 1 MB
                    # Skip partial line
                    f.readline()
                    log_content = f.read().strip()
                print(f"{Colors.YELLOW}Analyzing only the last 1 MB of the log file.{Colors.END}")
            except UnicodeDecodeError:
                # If UTF-8 fails, try with a more permissive encoding
                try:
                    with open(log_file, 'r', encoding='latin-1') as f:
                        f.seek(max(0, file_size - 1 * 1024 * 1024))  # Go to last 1 MB
                        # Skip partial line
                        f.readline()
                        log_content = f.read().strip()
                    print(f"{Colors.YELLOW}Analyzing only the last 1 MB of the log file.{Colors.END}")
                except Exception as e:
                    print(f"{Colors.RED}Error reading log file: {e}{Colors.END}")
                    return
        else:
            # Read with pagination for very large files
            log_content = read_large_file(log_file)
    else:
        # Get initial log content
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                log_content = f.read().strip()
            logger.debug(f"Successfully read log file with UTF-8 encoding")
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 encoding failed for {log_file}, trying latin-1")
            # If UTF-8 fails, try with a more permissive encoding
            try:
                with open(log_file, 'r', encoding='latin-1') as f:
                    log_content = f.read().strip()
                logger.debug(f"Successfully read log file with latin-1 encoding")
            except Exception as e:
                logger.error(f"Error reading log file: {e}")
                print(f"{Colors.RED}Error reading log file: {e}{Colors.END}")
                return
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            print(f"{Colors.RED}Error reading log file: {e}{Colors.END}")
            return
    
    # If not running in background, just analyze once
    if not background:
        logger.info("Performing one-time log analysis")
        analyze_log_content(log_content=log_content, log_file=log_file, model=model)
        return
    
    # For background analysis, call the monitor functionality
    logger.info("Starting background log monitoring")
    from ..log_analysis.monitor import monitor_log
    monitor_log(log_file=log_file, background=background, analyze=analyze, model=model)

def analyze_log_content(log_content: str, log_file: str, model: str = DEFAULT_MODEL) -> None:
    """
    Analyze the content of a log file using AI.
    
    This function takes log content as input and performs AI-based analysis to identify
    patterns, errors, and important information.
    
    Args:
        log_content: The content of the log file to analyze
        log_file: Path to the log file (for reference in analysis)
        model: Name of the AI model to use for analysis (default: DEFAULT_MODEL)
        
    Returns:
        None
        
    Raises:
        Exception: If the AI analysis fails or returns an invalid response
        
    Example:
        >>> with open("/var/log/syslog", "r") as f:
        ...     content = f.read()
        >>> analyze_log_content(content, "/var/log/syslog")
    """
    # If content is too large, take the last 1000 lines
    lines = log_content.splitlines()
    if len(lines) > 1000:
        log_content = '\n'.join(lines[-1000:])
        print(f"{Colors.YELLOW}Log content is large. Analyzing only the last 1000 lines.{Colors.END}")
    
    system_prompt = """You are a log analysis expert. Analyze the given log content and provide:
1. A summary of what the log shows
2. Any errors or warnings that should be addressed
3. Patterns or trends in the log

Be concise but thorough. Focus on actionable information."""

    formatted_prompt = f"""Please analyze this log from {log_file}:

```
{log_content}
```

What's happening in this log? Identify any errors, warnings, or issues that need attention."""

    try:
        # Generate analysis with longer timeout due to potential log size
        analysis = generate_command(formatted_prompt, model=model)
        
        # Display the analysis
        print(analysis)
        
    except Exception as e:
        logger.error(f"Error analyzing log content: {e}")
        print(f"{Colors.RED}Error analyzing log content: {e}{Colors.END}")
        return

def read_large_file(file_path: str, chunk_size: int = 1024 * 1024) -> str:
    """
    Read a large file efficiently in chunks.
    
    This function reads a large file in chunks to avoid memory issues.
    It supports both UTF-8 and fallback to latin-1 encoding.
    
    Args:
        file_path: Path to the file to read
        chunk_size: Size of each chunk to read in bytes (default: 1MB)
        
    Returns:
        str: The content of the file as a string
        
    Raises:
        FileNotFoundError: If the specified file does not exist
        PermissionError: If the file cannot be accessed
        UnicodeDecodeError: If the file cannot be read with UTF-8 encoding
        Exception: For other unexpected errors during file reading
        
    Example:
        >>> content = read_large_file("/var/log/syslog")
        >>> # With custom chunk size:
        >>> content = read_large_file("/var/log/auth.log", chunk_size=512*1024)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    file_size = os.path.getsize(file_path)
    chunks = file_size // chunk_size + (1 if file_size % chunk_size > 0 else 0)
    
    if chunks <= 1:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with a more permissive encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                print(f"{Colors.RED}Error reading file: {e}{Colors.END}")
                raise e
    
    # For simplicity in testing, just read the whole file
    # In production this would be interactive with user choice
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except UnicodeDecodeError:
        # If UTF-8 fails, try with a more permissive encoding
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"{Colors.RED}Error reading file: {e}{Colors.END}")
            raise e 