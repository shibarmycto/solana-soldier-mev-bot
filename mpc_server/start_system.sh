#!/bin/bash

echo "Starting MPC Server System..."

# Start the server in the background
echo "Starting MPC server..."
node server.js > server.log 2>&1 &
SERVER_PID=$!

# Give the server a moment to start
sleep 2

# Start a sub-agent in the background
echo "Starting sub-agent..."
node run_sub_agent.js > sub_agent.log 2>&1 &
AGENT_PID=$!

echo "MPC Server system started!"
echo "Server PID: $SERVER_PID"
echo "Sub-agent PID: $AGENT_PID"

# Function to stop the system
stop_system() {
    echo "Stopping MPC Server system..."
    kill $SERVER_PID $AGENT_PID
    echo "System stopped."
}

# Set up signal handlers
trap stop_system SIGTERM SIGINT

# Wait for processes to complete (they won't unless terminated)
wait $SERVER_PID $AGENT_PID