#!/bin/bash
# Launch Chrome with DevTools Protocol enabled for agent self-validation
# Usage: ./scripts/dev-chrome.sh [url]
#
# This enables the Chrome DevTools MCP to:
# - Take screenshots of the app
# - Inspect DOM snapshots
# - Read console errors
# - Click elements and navigate
# - Validate UI changes without human testing

URL="${1:-http://localhost:8000}"
PORT=9222

# Check if Chrome is already running with debugging
if lsof -i :$PORT >/dev/null 2>&1; then
  echo "Chrome DevTools already running on port $PORT"
  echo "Navigate to: $URL"
  exit 0
fi

echo "Launching Chrome with DevTools on port $PORT..."
echo "App URL: $URL"

/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=$PORT \
  --user-data-dir="/tmp/chrome-devtools-mentorlab" \
  --no-first-run \
  --window-size=390,844 \
  "$URL" &

echo "Chrome launched. Agent can now use Chrome DevTools MCP tools."
echo "To verify: curl -s http://localhost:$PORT/json/version | python3 -m json.tool"
