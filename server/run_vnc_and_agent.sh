#!/bin/bash
set -e

# Check if the first argument is "uvicorn" - if so, run uvicorn directly
if [ "$1" = "uvicorn" ]; then
    echo "Running uvicorn server..."
    exec "$@"
fi

# --- VNC Setup ---
# The screen resolution for the virtual desktop
SCREEN_RES="1280x1024x24"
DISPLAY=":1"

# Set the VNC password
VNC_PASSWORD="agentpass123"

# Create a VNC password file
mkdir -p ~/.vnc
# x11vnc uses a special file format for the password
echo "$VNC_PASSWORD" | vncpasswd -f > ~/.vnc/passwd
chmod 600 ~/.vnc/passwd

# 1. Start Xvfb (Virtual Frame Buffer) to create the desktop
echo "Starting Xvfb..."
Xvfb $DISPLAY -screen 0 $SCREEN_RES -ac &

# 2. Start the VNC Server (x11vnc) in the background
echo "Starting x11vnc server on port 5900..."
x11vnc -display $DISPLAY -N -forever -usepw -shared -rfbport 5900 &

# Wait a moment for services to start
sleep 3

# 3. Execute the Python Agent Script
echo "Launching Python agent..."
exec python /app/agent.py "$@"