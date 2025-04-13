# Log Monitoring Sessions in QCMD

This document describes the log monitoring session features in QCMD, which allow you to track, manage, and interact with log monitors.

## Overview

Log monitoring sessions in QCMD provide a way to:

1. Monitor log files in real-time with AI-powered analysis
2. Track active log monitors across multiple terminals
3. Start background log monitors that persist even when you close your terminal
4. View and manage all active log monitoring sessions

## Command Line Usage

### Starting a Log Monitor

```bash
# Analyze logs interactively with monitor options
qcmd --logs

# Monitor a specific log file
qcmd --logs --log-file /var/log/syslog
```

### Managing Log Monitors

```bash
# List all active log monitors
qcmd --list-monitors

# Stop a specific log monitor by session ID
qcmd --stop-monitor 3fa85f64-5717-4562-b3fc-2c963f66afa6
```

## Interactive Shell Commands

When using the QCMD interactive shell (`qcmd --shell` or `qcmd -s`), you can use these commands:

```
/logs                     - Find and analyze log files or manage log monitors
/list-monitors, /lm       - List active log monitoring sessions
/stop-monitor ID, /sm ID  - Stop a log monitor by session ID
/monitor PATH, /mon PATH  - Start monitoring a specific log file
/status                   - Show system status including active log monitors
```

Example session:
```
qcmd> /logs
# Choose a log file and monitoring option

qcmd> /lm
Active Log Monitors (2):
1. syslog
   Path: /var/log/syslog
   Started: 2023-06-01 12:34:56
   Model: qwen2.5-coder:0.5b
   Mode: with analysis
   Session ID: 3fa85f64...

qcmd> /sm 3fa85f64-5717-4562-b3fc-2c963f66afa6
Log monitor session ended.
```

## Interactive Mode

When using the interactive log analysis menu (`qcmd --logs`), you'll see options to:

1. View existing log monitors
2. Stop active monitors
3. Analyze log files
4. Start new monitors

## Technical Details

### Session Management

Each log monitor is tracked as a session with the following information:
- Session ID (unique identifier)
- Log file path
- Start time
- Process ID (PID)
- Analysis model
- Analysis mode

### Monitor Types

- **Foreground Monitors**: Run in the current terminal and show analysis results in real-time
- **Background Monitors**: Run as separate processes that continue monitoring even if you close your terminal

### Integration Points

The log monitoring session system integrates with:
- Process management
- Session tracking
- Signal handling
- File system monitoring

## Examples

### Example 1: Monitor System Logs

```bash
# Start monitoring the system log in the background
qcmd --logs --log-file /var/log/syslog
# Choose option 3 when prompted
```

### Example 2: List and Manage Monitors

```bash
# List all active monitors
qcmd --list-monitors

# Output:
# Active Log Monitors (2):
# 1. syslog
#    Path: /var/log/syslog
#    Started: 2023-06-01 12:34:56
#    Model: qwen2.5-coder:0.5b
#    Mode: with analysis
#    Session ID: 3fa85f64...

# Stop a specific monitor
qcmd --stop-monitor 3fa85f64-5717-4562-b3fc-2c963f66afa6
```

## Best Practices

1. Use background monitors for long-term monitoring of critical logs
2. Check for active monitors before starting new ones on the same file
3. Properly stop monitors when they're no longer needed to free up resources
4. Use the appropriate model for the type of log being analyzed

## Troubleshooting

If a monitor doesn't appear in the list of active monitors:
1. The process may have crashed or been terminated
2. The session file may be corrupted
3. You may not have permission to access the session information

To clean up stale monitors, use:
```bash
qcmd --logs
# Then select option to stop monitors
```

