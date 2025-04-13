# QCMD Log Monitoring Demos

This directory contains demo scripts that showcase the log monitoring features in QCMD.

## Log Monitor Demo

The `log_monitor_demo.py` script demonstrates the following features:

1. **Analyze Once**: Analyze a log file without continuous monitoring
2. **Monitor with Analysis**: Monitor a log file with real-time AI analysis
3. **Watch Only**: Monitor a log file without analysis (just watching for changes)
4. **List Monitors**: Display all active log monitors
5. **View Monitor**: Connect to a running monitor to see its output
6. **Stop Monitor**: Stop a running monitor

## Running the Demo

1. Make sure you have QCMD installed:
   ```
   pip install -e /path/to/qcmd
   ```

2. Run the demo script:
   ```
   python log_monitor_demo.py
   ```

## Command Line Usage

You can also use these features directly from the command line:

### Analyze a log file once
```
qcmd --logs --log-file /var/log/syslog --analyze-once
```

### Monitor a log file with analysis
```
qcmd --logs --log-file /var/log/syslog --monitor-analyze
```

### Monitor a log file without analysis (just watch)
```
qcmd --logs --log-file /var/log/syslog --monitor-watch
```

### List active monitors
```
qcmd --list-monitors
```

### View a monitor
```
qcmd --view-monitor SESSION_ID
```

### Stop a monitor
```
qcmd --stop-monitor SESSION_ID
```

## Creating a Test Log File

If you want to create a test log file for monitoring:

```bash
# Create an initial log file
echo "[$(date)] Starting application..." > test.log

# Add new log entries periodically in another terminal
echo "[$(date)] New log entry - INFO: Normal operation" >> test.log
echo "[$(date)] New log entry - ERROR: Connection failed" >> test.log
```

This lets you test the monitoring features with real log updates. 