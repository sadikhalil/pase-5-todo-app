#!/bin/bash

# Script to start both the main Todo application server and MCP server simultaneously

echo "Starting both Todo application servers..."

# Start the main server in the background
echo "Starting Main Todo Application Server..."
echo "Server will be available at http://localhost:8000"
cd backend && python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload &
MAIN_SERVER_PID=$!

# Small delay to let main server start first
sleep 2

# Start the MCP server in the background
echo "Starting MCP Server for Todo Chat..."
echo "Server will be available at http://localhost:8001"
cd backend && python -m uvicorn mcp.server:app --host 0.0.0.0 --port 8001 --reload &
MCP_SERVER_PID=$!

echo "Both servers are running:"
echo "- Main Todo API PID: $MAIN_SERVER_PID (http://localhost:8000)"
echo "- MCP Chat Server PID: $MCP_SERVER_PID (http://localhost:8001)"
echo ""
echo "Press Ctrl+C to stop both servers"

# Function to handle cleanup
cleanup() {
    echo ""
    echo "Stopping both servers..."
    kill $MAIN_SERVER_PID $MCP_SERVER_PID 2>/dev/null
    exit 0
}

# Set up trap to handle Ctrl+C
trap cleanup INT

# Wait for both processes
wait $MAIN_SERVER_PID
wait $MCP_SERVER_PID