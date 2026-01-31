#!/bin/bash

# Bot Monitoring Script
# Checks if Clawdbot services are running and restarts them if they're down

LOG_FILE="/Users/anthonypium/clawd/bot_monitor.log"
PID_FILE="/Users/anthonypium/clawd/bot_monitor.pid"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check if clawdbot gateway is running
check_gateway_status() {
    if pgrep -f "clawdbot.*gateway" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to restart clawdbot gateway
restart_gateway() {
    log_message "Gateway service is DOWN. Attempting restart..."
    
    # Try to stop the gateway first to ensure clean state
    clawdbot gateway stop
    
    # Wait a moment
    sleep 2
    
    # Start the gateway
    if clawdbot gateway start; then
        log_message "Gateway service restarted successfully"
    else
        log_message "ERROR: Failed to restart gateway service"
        return 1
    fi
}

# Function to get gateway status details
get_gateway_status() {
    clawdbot gateway status
}

# Main monitoring function
main() {
    log_message "Starting bot monitoring check"
    
    if check_gateway_status; then
        log_message "Gateway service is RUNNING"
        # Optionally log the detailed status
        STATUS=$(get_gateway_status 2>&1)
        log_message "Gateway status: $STATUS"
    else
        log_message "Gateway service is NOT RUNNING"
        restart_gateway
    fi
    
    log_message "Bot monitoring check completed"
    echo "---"
}

# Create PID file with current process ID
echo $$ > "$PID_FILE"

# Execute main function
main

# Clean up PID file on exit
trap 'rm -f "$PID_FILE"' EXIT