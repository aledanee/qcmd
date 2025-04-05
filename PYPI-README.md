# qcmd - AI-powered Command Generator

A simple command-line tool that generates shell commands using local AI models via Ollama.

**Version 1.0.9**

## Overview

**qcmd** is a powerful command-line tool that generates shell commands using AI language models via Ollama. Simply describe what you want to do in natural language, and qcmd will generate the appropriate command.

## Key Features

- **Natural Language Inputs**: Describe what you want to do in plain English
- **Auto-fix Mode**: Automatically fixes failed commands and retries
- **AI Error Analysis**: Explains errors and suggests solutions
- **Interactive Shell**: Continuous operation with command history
- **Multiple Models**: Works with any Ollama model (default: qwen2.5-coder:0.5b)
- **Safety First**: Always asks for confirmation before executing any command
- **Log Analysis**: Find and analyze system log files with real-time monitoring

## Installation

### Prerequisites

- Python 3.6 or higher
- [Ollama](https://ollama.ai/) installed and running
- At least one language model pulled (e.g., qwen2.5-coder:0.5b)

### Install from PyPI

```bash
pip install ibrahimiq-qcmd
```

Make sure Ollama is running before using qcmd:
```bash
ollama serve
```

## Basic Usage

```bash
# Generate and confirm a command
qcmd "list all files in the current directory"

# Auto-execute mode
qcmd -e "find large log files"

# Smart auto-fix mode
qcmd -A "find Python files modified today"

# Interactive shell
qcmd -s
```

## What's New in 1.0.9

- **Fixed Cross-Process Tracking**: Log monitors now appear in status even when started from different processes
- **Persistent Monitor Storage**: Monitor status is now tracked across different terminal sessions
- **Improved Status Display**: Added PID tracking to show which process owns each monitor
- **Automatic Cleanup**: Stale monitor processes get automatically removed from status
- **Enhanced Reliability**: Better error handling and cleanup for monitor processes

## What's New in 1.0.8

- Added ability to toggle AI analysis on/off while monitoring logs (press 'a' key)
- Enhanced `/watch` command to list all available log files when no path is provided
- Enhanced `/monitor` command to list all available log files when no path is provided
- Added `/status` command and `--status` flag to show system and QCMD status
- Improved real-time log watching with keyboard control (press 'q' to quit, 'a' to toggle analysis)
- Added tracking of active log monitors and sessions

## What's New in 1.0.7

- Added `--watch` option to monitor log files without AI analysis
- Added `/watch` command to interactive shell
- Improved log monitoring functionality with separate watching and analysis modes
- Enhanced user experience with more file monitoring options
- Added ability to view log updates in real-time (like `tail -f`)

## What's New in 1.0.6

- Fixed shell mode bug on macOS and Python 3.12+ 
- Improved interactive shell functionality
- Fixed missing temperature parameter issue
- Enhanced user experience in interactive mode

## What's New in 1.0.5

- Fixed compatibility with Python 3.12+ by removing pkg_resources dependency
- Improved version detection using Python standard library (importlib.metadata)
- Removed external dependency requirements for better cross-version compatibility
- Enhanced installation reliability across all Python versions
- Simplified update checking mechanism

## What's New in 1.0.4

- Initial attempt at fixing Python 3.12+ compatibility issues
- Updated documentation for better clarity
- Minor code improvements

## What's New in 1.0.3

- Implemented improved release automation workflow
- Enhanced package publishing process
- Updated GitHub Actions configuration 
- Streamlined deployment process
- Documentation improvements for contributors

## What's New in 1.0.2

- Fixed undefined variable errors in interactive shell and auto mode
- Improved error handling and command detection for dangerous operations
- Streamlined GitHub Actions workflow for Python 3.10 and 3.11
- Enhanced compatibility with continuous integration systems
- Fixed tab completion issues in interactive shell

## What's New in 1.0.1

- Updated documentation with improved installation instructions
- Fixed package structure for better compatibility
- Added PyPI integration for easier installation

## Release Notes

### 1.0.10
* Fixed command-line argument handling to properly support utility commands like `--monitor`, `--watch`, and `--status` without requiring a prompt.
* Improved monitor persistence tracking to show correct status across processes.

## Full Documentation

For full documentation and source code, visit the [GitHub repository](https://github.com/aledanee/qcmd). 