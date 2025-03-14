#!/bin/bash

# Start the API server

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Function to handle cleanup on exit
cleanup() {
    echo "Shutting down services..."
    
    # Kill the API server process if it exists
    if [ -n "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
    fi
    
    exit 0
}

# Set up trap to catch SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Create necessary directories
mkdir -p tmp/agent_history
mkdir -p tmp/record_videos
mkdir -p tmp/traces

# Start the API server
echo "Starting API server..."
python3 api.py --host 0.0.0.0 &
API_PID=$!

# Check if API server started successfully
sleep 2
if ! kill -0 $API_PID 2>/dev/null; then
    echo "Failed to start API server. Please check the API server configuration."
    cleanup
    exit 1
fi

echo "Services started successfully!"
echo "API server running with PID: $API_PID"
echo "Press Ctrl+C to stop all services."

# Wait for user to press Ctrl+C
wait 