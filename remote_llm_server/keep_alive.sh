#!/bin/bash

# Configuration
LOG_FILE="server_crash.log"
OUTPUT_LOG="server_output.log"

# Function to ensure we are in the correct directory
cd "$(dirname "$0")"

echo "Starting Keep-Alive Monitor for Remote LLM Server..."
echo "Crash logs: $LOG_FILE"
echo "Output logs: $OUTPUT_LOG"

# Function to kill child processes on exit
cleanup() {
    echo "Stopping Keep-Alive Monitor..."
    # Find and kill the python server process started by this script
    pkill -P $$ 
    exit 0
}

# Trap termination signals
trap cleanup SIGINT SIGTERM

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "----------------------------------------" >> "$LOG_FILE"
    echo "[$TIMESTAMP] Starting server..." >> "$LOG_FILE"
    
    # Run the start script in background so we can wait on it
    bash start.sh >> "$OUTPUT_LOG" 2>&1 &
    SERVER_PID=$!
    
    # Wait for the specific process
    wait $SERVER_PID
    EXIT_CODE=$?
    
    TIMESTAMP_END=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "[$TIMESTAMP_END] CRASH DETECTED! (Exit Code: $EXIT_CODE)" >> "$LOG_FILE"
        echo "Capturing last 20 lines of output for context:" >> "$LOG_FILE"
        echo "..." >> "$LOG_FILE"
        tail -n 20 "$OUTPUT_LOG" >> "$LOG_FILE"
        echo "..." >> "$LOG_FILE"
        
        echo "Restarting in 5 seconds..."
        sleep 5
    else
        echo "[$TIMESTAMP_END] Server stopped gracefully (Exit Code: 0)." >> "$LOG_FILE"
        echo "Restarting in 2 seconds..."
        sleep 2
    fi
done
