#!/bin/bash
# Quick start demo for QCMD log monitoring

# Create a test log file
TEST_LOG="/tmp/qcmd_demo.log"
echo "[$(date)] Starting application..." > $TEST_LOG
echo "[$(date)] Initializing components..." >> $TEST_LOG
echo "[$(date)] ERROR: Failed to connect to database" >> $TEST_LOG
echo "[$(date)] Using fallback connection..." >> $TEST_LOG
echo "[$(date)] Application ready" >> $TEST_LOG

echo "Created test log file: $TEST_LOG"
echo ""

# Start monitoring in background
echo "Starting log monitor in background..."
qcmd --logs --log-file $TEST_LOG --monitor-analyze
echo ""

# Add more log entries
echo "Adding more log entries to the monitored file..."
sleep 2
echo "[$(date)] Processing request #1234" >> $TEST_LOG
sleep 2
echo "[$(date)] ERROR: Invalid input received" >> $TEST_LOG
sleep 2
echo "[$(date)] Request #1234 failed" >> $TEST_LOG
sleep 2
echo "[$(date)] Processing request #1235" >> $TEST_LOG
sleep 2
echo "[$(date)] Request #1235 completed successfully" >> $TEST_LOG

# List active monitors
echo ""
echo "Listing active monitors..."
qcmd --list-monitors

echo ""
echo "Demo completed. You can:"
echo "1. View the monitor output: qcmd --list-monitors (then select 'v' and the monitor number)"
echo "2. Stop the monitor: qcmd --list-monitors (then select 's' and the monitor number)"
echo "3. Add more log entries: echo \"[$(date)] New log entry\" >> $TEST_LOG"
echo "" 