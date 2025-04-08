#!/usr/bin/env python3
"""
Command history functionality for QCMD.
"""
import os
import json
import time
import sys
from datetime import datetime
from typing import List, Dict, Optional

# Import from config once it's implemented
from ..config.settings import DEFAULT_MODEL

# Constants for history management
CONFIG_DIR = os.path.expanduser("~/.qcmd")
HISTORY_FILE = os.path.join(CONFIG_DIR, "history.txt")
MAX_HISTORY = 1000  # Maximum number of history entries to keep

# Import for colored output
from ..ui.display import Colors

def save_to_history(prompt: str) -> None:
    """
    Save a command prompt to the history file
    
    Args:
        prompt: The command prompt to save
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
        
        # Read existing history
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                    history = [line.strip() for line in f.readlines()]
            except UnicodeDecodeError:
                # If UTF-8 fails, try with a more permissive encoding
                with open(HISTORY_FILE, 'r', encoding='latin-1') as f:
                    history = [line.strip() for line in f.readlines()]
        
        # Add new entry with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.append(f"{timestamp} | {prompt}")
        
        # Trim history if needed
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        
        # Write back to file
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(history))
    except Exception as e:
        # Don't crash the program if history saving fails
        print(f"{Colors.YELLOW}Could not save to history: {e}{Colors.END}", file=sys.stderr)

def load_history(count: int = 10) -> List[str]:
    """
    Load recent command history
    
    Args:
        count: Number of history entries to load
        
    Returns:
        List of recent command prompts
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            return []
        
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = [line.strip() for line in f.readlines()]
        except UnicodeDecodeError:
            # If UTF-8 fails, try with a more permissive encoding
            with open(HISTORY_FILE, 'r', encoding='latin-1') as f:
                history = [line.strip() for line in f.readlines()]
            
        # Extract just the prompts (remove timestamps)
        prompts = []
        for entry in reversed(history[-count:]):
            parts = entry.split(" | ", 1)
            if len(parts) > 1:
                prompts.append(parts[1])
                
        return prompts
    except Exception as e:
        print(f"{Colors.YELLOW}Could not load history: {e}{Colors.END}", file=sys.stderr)
        return []

def show_history(count: int = 20, search_term: str = None) -> None:
    """
    Display command history with optional search
    
    Args:
        count: Number of history entries to show
        search_term: Optional search term to filter history
    """
    try:
        if not os.path.exists(HISTORY_FILE):
            print(f"{Colors.YELLOW}No command history found.{Colors.END}")
            return
            
        with open(HISTORY_FILE, 'r') as f:
            history = [line.strip() for line in f.readlines()]
        
        if not history:
            print(f"{Colors.YELLOW}No command history found.{Colors.END}")
            return
            
        # Filter history if search term is provided
        if search_term:
            search_term = search_term.lower()
            filtered_history = []
            for entry in history:
                if search_term in entry.lower():
                    filtered_history.append(entry)
            history = filtered_history
            
            if not history:
                print(f"{Colors.YELLOW}No matching history entries found for '{search_term}'.{Colors.END}")
                return
                
            print(f"\n{Colors.GREEN}{Colors.BOLD}Command History matching '{search_term}':{Colors.END}")
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}Command History:{Colors.END}")
            
        print(f"{Colors.CYAN}{'#':<4} {'Timestamp':<20} {'Command'}{Colors.END}")
        print("-" * 80)
        
        # Show the most recent entries first, up to the count limit
        for i, entry in enumerate(reversed(history[-count:])):
            idx = len(history) - count + i + 1
            parts = entry.split(" | ", 1)
            if len(parts) > 1:
                timestamp, prompt = parts
                print(f"{i+1:<4} {timestamp:<20} {prompt}")
            else:
                print(f"{i+1:<4} {'Unknown':<20} {entry}")
                
    except Exception as e:
        print(f"{Colors.YELLOW}Could not display history: {e}{Colors.END}", file=sys.stderr) 