#!/bin/bash
# NOMARK Preview Server - Starts dev server with Cloudflare Tunnel
# Usage: preview-server.sh <project>

set -e

PROJECT=$1

if [ -z "$PROJECT" ]; then
    echo "Usage: preview-server.sh <project>"
    exit 1
fi

PROJECT_PATH="$HOME/repos/$PROJECT"

if [ ! -d "$PROJECT_PATH" ]; then
    echo "Project not found: $PROJECT_PATH"
    exit 1
fi

cd "$PROJECT_PATH"

# Determine the dev command and port based on project type
DEV_COMMAND=""
DEV_PORT=3000

if [ -f "package.json" ]; then
    # Check for Next.js
    if grep -q '"next"' package.json; then
        DEV_COMMAND="npm run dev"
        DEV_PORT=3000
    # Check for Vite
    elif grep -q '"vite"' package.json; then
        DEV_COMMAND="npm run dev"
        DEV_PORT=5173
    # Check for Create React App
    elif grep -q '"react-scripts"' package.json; then
        DEV_COMMAND="npm start"
        DEV_PORT=3000
    # Default npm dev
    elif grep -q '"dev"' package.json; then
        DEV_COMMAND="npm run dev"
        DEV_PORT=3000
    fi
elif [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    # Python project - assume Flask or Django
    if [ -f "manage.py" ]; then
        DEV_COMMAND="python manage.py runserver"
        DEV_PORT=8000
    else
        DEV_COMMAND="python -m flask run"
        DEV_PORT=5000
    fi
fi

if [ -z "$DEV_COMMAND" ]; then
    echo "Could not determine dev command for project"
    exit 1
fi

echo "Starting dev server: $DEV_COMMAND on port $DEV_PORT"

# Start the dev server in background
$DEV_COMMAND &
DEV_PID=$!

# Wait for server to start
echo "Waiting for dev server to start..."
for i in {1..30}; do
    if curl -s "http://localhost:$DEV_PORT" > /dev/null 2>&1; then
        echo "Dev server is ready on port $DEV_PORT"
        break
    fi
    sleep 1
done

# Start Cloudflare Tunnel
echo "Starting Cloudflare Tunnel..."
cloudflared tunnel --url "http://localhost:$DEV_PORT" 2>&1 | while read line; do
    echo "$line"
    # Look for the tunnel URL and output it
    if echo "$line" | grep -q "trycloudflare.com"; then
        # Extract and echo the URL
        URL=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com')
        if [ -n "$URL" ]; then
            echo "TUNNEL_URL: $URL"
        fi
    fi
done

# Cleanup on exit
cleanup() {
    echo "Stopping preview server..."
    kill $DEV_PID 2>/dev/null || true
    pkill -f cloudflared 2>/dev/null || true
}

trap cleanup EXIT

# Keep running
wait
