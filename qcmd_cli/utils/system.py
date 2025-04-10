#!/usr/bin/env python3
"""
Utility module for system-related functions in QCMD.
"""

import os
import sys
import subprocess
import platform
import shutil
import time
import re
import tempfile
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
import requests
from importlib.metadata import version as get_version

from qcmd_cli.ui.display import Colors
from qcmd_cli.core.command_generator import analyze_error
from qcmd_cli.config.settings import OLLAMA_API, REQUEST_TIMEOUT

try:
    # For Python 3.8+
    try:
        qcmd_version = get_version("ibrahimiq-qcmd")
    except Exception:
        # Fallback to package version
        from qcmd_cli import __version__
        qcmd_version = __version__
except ImportError:
    # Fallback for older Python versions
    try:
        import pkg_resources
        qcmd_version = pkg_resources.get_distribution("ibrahimiq-qcmd").version
    except Exception:
        # Fallback to package version
        from qcmd_cli import __version__
        qcmd_version = __version__

def execute_command(command: str, analyze_errors: bool = False, model: str = None) -> Tuple[int, str]:
    """
    Execute a shell command and return the exit code and output.
    
    Args:
        command: The command to execute
        analyze_errors: Whether to analyze errors if the command fails
        model: Model to use for error analysis
        
    Returns:
        Tuple of (exit_code, output)
    """
    print(f"\n{Colors.CYAN}Executing:{Colors.END} {Colors.GREEN}{command}{Colors.END}")
    
    # Create a temporary file for command output
    with tempfile.NamedTemporaryFile(delete=False, mode='w+b') as temp_file:
        temp_file_path = temp_file.name
        
    try:
        # Run the command and capture output
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        output_lines = []
        for line in process.stdout:
            print(line, end='')
            output_lines.append(line)
            
        process.wait()
        exit_code = process.returncode
        output = ''.join(output_lines)
        
        # Also write output to temp file for potential later analysis
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            f.write(output)
            
        # If the command failed and analyze_errors is enabled
        if exit_code != 0 and analyze_errors:
            print(f"\n{Colors.YELLOW}Command failed with exit code {exit_code}.{Colors.END}")
            print(f"{Colors.CYAN}Analyzing error...{Colors.END}")
            
            # Use the analyze_error function to analyze the error
            analysis = analyze_error(output, command, model)
            print(f"\n{Colors.CYAN}Analysis:{Colors.END}\n{analysis}")
            
        return exit_code, output
        
    except Exception as e:
        error_msg = f"Error executing command: {str(e)}"
        print(f"{Colors.RED}{error_msg}{Colors.END}")
        return 1, error_msg
        
    finally:
        # Clean up the temporary file
        try:
            os.unlink(temp_file_path)
        except:
            pass

def get_system_status() -> Dict[str, Any]:
    """
    Get detailed system status information.
    
    Returns:
        Dictionary containing system status information
    """
    status = {}
    
    # Basic system info
    status['os'] = platform.system()
    status['kernel'] = platform.release()
    status['python_version'] = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    status['qcmd_version'] = qcmd_version
    status['current_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Get hostname
    try:
        status['hostname'] = platform.node()
    except:
        status['hostname'] = "Unknown"
    
    # Get uptime
    try:
        if platform.system() == 'Linux':
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                
            # Format uptime
            days = int(uptime_seconds / 86400)
            hours = int((uptime_seconds % 86400) / 3600)
            minutes = int((uptime_seconds % 3600) / 60)
            
            uptime_str = ""
            if days > 0:
                uptime_str += f"{days} day{'s' if days != 1 else ''}, "
            uptime_str += f"{hours}h {minutes}m"
            
            status['uptime'] = uptime_str
            
        elif platform.system() == 'Darwin':  # macOS
            # Use uptime command on macOS
            uptime_output = subprocess.check_output(['uptime']).decode('utf-8')
            status['uptime'] = uptime_output.strip()
            
        else:
            status['uptime'] = "Unknown"
            
    except Exception as e:
        status['uptime'] = f"Error getting uptime: {e}"
    
    # Check Ollama status
    status['ollama'] = {}
    try:
        response = requests.get(f"{OLLAMA_API}/tags", timeout=REQUEST_TIMEOUT)
        status['ollama']['running'] = True
        status['ollama']['api_url'] = OLLAMA_API
        
        # Get available models
        if response.status_code == 200:
            result = response.json()
            if 'models' in result:
                status['ollama']['models'] = [model['name'] for model in result['models']]
            else:
                status['ollama']['models'] = []
        else:
            status['ollama']['error'] = f"Status code: {response.status_code}"
            status['ollama']['models'] = []
            
    except requests.exceptions.RequestException as e:
        status['ollama']['running'] = False
        status['ollama']['error'] = str(e)
        status['ollama']['models'] = []
    
    # Get CPU load average
    try:
        if platform.system() in ['Linux', 'Darwin']:
            load1, load5, load15 = os.getloadavg()
            status['load_avg'] = f"{load1:.2f}, {load5:.2f}, {load15:.2f}"
        else:
            status['load_avg'] = "Not available on this platform"
    except Exception as e:
        status['load_avg'] = f"Error getting load average: {e}"
    
    # Get CPU usage (requires psutil for accurate measurement)
    try:
        import psutil
        status['cpu_percent'] = f"{psutil.cpu_percent(interval=1):.1f}"
        
        # Memory info
        memory = psutil.virtual_memory()
        status['mem_total'] = format_bytes(memory.total)
        status['mem_used'] = format_bytes(memory.used)
        status['mem_free'] = format_bytes(memory.available)
        status['mem_percent'] = f"{memory.percent:.1f}"
        
        # Disk info
        status['disks'] = []
        for part in psutil.disk_partitions(all=False):
            if os.name == 'nt' and ('cdrom' in part.opts or part.fstype == ''):
                # Skip CD-ROM drives on Windows
                continue
                
            usage = psutil.disk_usage(part.mountpoint)
            status['disks'].append({
                'device': part.device,
                'mount': part.mountpoint,
                'fstype': part.fstype,
                'total': format_bytes(usage.total),
                'used': format_bytes(usage.used),
                'free': format_bytes(usage.free),
                'percent': f"{usage.percent:.1f}"
            })
        
        # Get log directory disk space
        log_dir = os.path.expanduser("~/.qcmd")
        if os.path.exists(log_dir):
            try:
                usage = psutil.disk_usage(log_dir)
                status['log_dir_space'] = {
                    'path': log_dir,
                    'total': format_bytes(usage.total),
                    'used': format_bytes(usage.used),
                    'free': format_bytes(usage.free),
                    'percent': f"{usage.percent:.1f}"
                }
            except Exception as e:
                status['log_dir_space'] = {'error': str(e)}
            
        # Network info
        status['network'] = {}
        net_io = psutil.net_io_counters(pernic=True)
        for nic, io in net_io.items():
            status['network'][nic] = f"↑{format_bytes(io.bytes_sent)} ↓{format_bytes(io.bytes_recv)}"
            
        # Top processes
        status['top_processes'] = []
        for proc in sorted(psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']), 
                          key=lambda p: p.info['cpu_percent'] or 0, 
                          reverse=True)[:5]:
            try:
                status['top_processes'].append({
                    'pid': proc.info['pid'],
                    'user': proc.info.get('username', '')[:10],
                    'cpu': f"{proc.info.get('cpu_percent', 0):.1f}",
                    'mem': f"{proc.info.get('memory_percent', 0):.1f}",
                    'command': proc.info.get('name', '')
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Find all qcmd processes
        status['qcmd_processes'] = []
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time', 'status']):
            try:
                # Look for qcmd processes in different ways
                if any(x for x in proc.info['cmdline'] if 'qcmd' in x.lower()):
                    proc_info = {
                        'pid': proc.info['pid'],
                        'start_time': datetime.fromtimestamp(proc.info['create_time']).strftime('%Y-%m-%d %H:%M:%S'),
                        'status': proc.info['status'],
                        'command': ' '.join(proc.info['cmdline']),
                        'type': 'unknown'
                    }
                    
                    # Try to determine type of qcmd process
                    cmdline = ' '.join(proc.info['cmdline'])
                    if '-s' in cmdline or '--shell' in cmdline:
                        proc_info['type'] = 'interactive_shell'
                    elif '--monitor' in cmdline:
                        proc_info['type'] = 'log_monitor'
                    elif any(x in cmdline for x in ['--analyze-file', '--logs']):
                        proc_info['type'] = 'log_analyzer'
                    
                    status['qcmd_processes'].append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
    except ImportError:
        # Fallback for systems without psutil
        status['cpu_percent'] = "psutil not available"
        status['mem_total'] = "psutil not available"
        status['mem_used'] = "psutil not available"
        status['mem_free'] = "psutil not available"
        status['mem_percent'] = "N/A"
        
        # Also add a message about qcmd processes
        status['qcmd_processes'] = "psutil not available - cannot detect running processes"

    # Get active sessions from session.py
    from qcmd_cli.utils.session import get_active_sessions
    sessions = get_active_sessions()
    
    # Ensure sessions are properly assigned to status
    status['active_sessions'] = sessions
    
    # As a fallback, also scan running processes for QCMD
    if 'qcmd_processes' in status and isinstance(status['qcmd_processes'], list) and status['qcmd_processes']:
        # If we have processes but no sessions, create session entries from process info
        if not sessions:
            fallback_sessions = []
            for proc in status['qcmd_processes']:
                if proc.get('type') == 'interactive_shell':
                    fallback_sessions.append({
                        'session_id': f"proc-{proc.get('pid', '0')}",
                        'type': proc.get('type', 'unknown'),
                        'pid': proc.get('pid', 0),
                        'start_time': proc.get('start_time', 'Unknown')
                    })
            if fallback_sessions:
                status['active_sessions'] = fallback_sessions
    
    # Get active monitors
    from qcmd_cli.log_analysis.monitor import get_active_monitors
    monitors = get_active_monitors()
    status['active_monitors'] = monitors
    
    return status

def format_bytes(bytes_value: int) -> str:
    """
    Format bytes value to human-readable string.
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Formatted string (e.g., "4.2 GB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024 or unit == 'TB':
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024

def is_process_running(pid: int) -> bool:
    """
    Check if a process is running.
    
    Args:
        pid: Process ID
        
    Returns:
        True if process is running, False otherwise
    """
    try:
        # Send signal 0 to the process - doesn't kill it, just checks if it exists
        os.kill(pid, 0)
        return True
    except OSError:
        return False
    except Exception:
        return False

def which(command: str) -> Optional[str]:
    """
    Find the path to an executable.
    
    Args:
        command: Command name
        
    Returns:
        Path to the executable, or None if not found
    """
    return shutil.which(command)

def check_for_updates():
    """
    Check if there is a newer version of QCMD available on PyPI.
    
    Returns:
        dict: A dictionary containing update information:
            - 'current_version': The currently installed version
            - 'latest_version': The latest version available on PyPI
            - 'update_available': Boolean indicating if an update is available
            - 'update_url': URL to the package on PyPI
            - 'error': Error message if any issue occurred during check
    """
    result = {
        'current_version': None,
        'latest_version': None,
        'update_available': False,
        'update_url': 'https://pypi.org/project/ibrahimiq-qcmd/',
        'error': None
    }
    
    try:
        # Get current version
        try:
            current_version = get_version('ibrahimiq-qcmd')
            result['current_version'] = current_version
        except Exception as e:
            result['error'] = f"Failed to get current version: {str(e)}"
            return result
        
        # Get latest version from PyPI
        try:
            pypi_url = 'https://pypi.org/pypi/ibrahimiq-qcmd/json'
            response = requests.get(pypi_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data['info']['version']
                result['latest_version'] = latest_version
                
                # Compare versions
                # Convert versions to tuples of integers for proper comparison
                def parse_version(version_str):
                    return tuple(map(int, re.findall(r'\d+', version_str)))
                
                current_tuple = parse_version(current_version)
                latest_tuple = parse_version(latest_version)
                
                result['update_available'] = latest_tuple > current_tuple
            else:
                result['error'] = f"Failed to fetch PyPI data: HTTP {response.status_code}"
        except Exception as e:
            result['error'] = f"Failed to check for updates: {str(e)}"
    
    except Exception as e:
        result['error'] = f"Unexpected error during update check: {str(e)}"
    
    return result

def display_update_status():
    """
    Display information about available updates in a user-friendly format.
    
    Returns:
        bool: True if updates are available, False otherwise
    """
    from qcmd_cli.ui.colors import Colors  # Import locally to avoid circular imports
    
    update_info = check_for_updates()
    
    if update_info['error']:
        print(f"{Colors.YELLOW}Could not check for updates: {update_info['error']}{Colors.END}")
        return False
    
    if update_info['update_available']:
        print(f"\n{Colors.GREEN}┌─ QCMD Update Available ────────────────────────────────────┐{Colors.END}")
        print(f"{Colors.GREEN}│{Colors.END} Current version: {Colors.YELLOW}{update_info['current_version']}{Colors.END}")
        print(f"{Colors.GREEN}│{Colors.END} Latest version:  {Colors.CYAN}{update_info['latest_version']}{Colors.END}")
        print(f"{Colors.GREEN}│{Colors.END}")
        print(f"{Colors.GREEN}│{Colors.END} To update, run: {Colors.CYAN}pip install --upgrade ibrahimiq-qcmd{Colors.END}")
        print(f"{Colors.GREEN}└────────────────────────────────────────────────────────────┘{Colors.END}")
        return True
    
    return False

# For testing only
if __name__ == "__main__":
    status = get_system_status()
    for key, value in status.items():
        if isinstance(value, (list, dict)):
            print(f"{key}: {len(value)} items")
        else:
            print(f"{key}: {value}") 