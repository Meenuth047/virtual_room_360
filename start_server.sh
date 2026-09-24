#!/usr/bin/env bash
# Start 360 Rooms backend and Cloudflare Tunnel

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=================================================="
echo " Starting 360 Rooms + Free Cloudflare Tunnel..."
echo "=================================================="

export PATH="$DIR/bin:$PATH"

# Resolve cloudflared binary
if command -v cloudflared &> /dev/null; then
    CLOUDFLARED="cloudflared"
elif [ -x "$DIR/bin/cloudflared" ]; then
    CLOUDFLARED="$DIR/bin/cloudflared"
else
    echo "Error: cloudflared binary not found in $DIR/bin or PATH."
    exit 1
fi

# Stop any process currently using port 8000
fuser -k 8000/tcp 2>/dev/null || true

# Start backend in background
python3 -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 &
SERVER_PID=$!

# Ensure server stops when script is closed
trap "echo 'Shutting down...'; kill $SERVER_PID 2>/dev/null; exit 0" INT TERM EXIT

sleep 2

# Launch Cloudflare tunnel
echo ""
echo "Creating your secure HTTPS public URL..."
echo ""
"$CLOUDFLARED" tunnel --url http://127.0.0.1:8000

