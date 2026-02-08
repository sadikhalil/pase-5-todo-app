#!/usr/bin/env python3
"""
Script to start the consolidated Todo application server (main + MCP functionality)
"""

import subprocess
import sys
import os
import threading
import signal
import time

def start_main_server():
    """Start the consolidated Todo application server (main + MCP functionality)"""
    print("Starting Consolidated Todo Application Server...")
    print("Server will be available at http://localhost:8000")
    print("Includes both main API and MCP endpoints")

    # Change to backend directory
    backend_dir = os.path.join(os.path.dirname(__file__), "backend")

    # Start the main server (now includes MCP functionality)
    cmd = [
        sys.executable,
        "-m", "uvicorn",
        "main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ]

    os.chdir(backend_dir)

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting main server: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nMain server stopped.")

def main():
    # Start the consolidated server
    main_thread = threading.Thread(target=start_main_server, daemon=True)

    # Start the server
    main_thread.start()

    print("Server is running:")
    print("- Main Todo API: http://localhost:8000")
    print("- Includes all MCP endpoints at /mcp/*")
    print("\nPress Ctrl+C to stop the server")

    try:
        # Wait for the thread to complete
        main_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)

if __name__ == "__main__":
    main()