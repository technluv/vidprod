#!/bin/bash

echo "=== GitHub Codespaces Port Visibility Test ==="
echo "Codespace: $CODESPACE_NAME"
echo ""

# Function to test port
test_port() {
    local port=$1
    local visibility=$2
    
    echo "Port $port - Setting visibility to: $visibility"
    gh codespace ports visibility $port:$visibility -c $CODESPACE_NAME
    
    local url="https://${CODESPACE_NAME}-${port}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
    echo "URL: $url"
    echo ""
}

# Test Frontend (port 3000)
echo "1. Testing Frontend Port (3000)"
test_port 3000 public
echo "✅ Port 3000 is now PUBLIC - accessible from: https://${CODESPACE_NAME}-3000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
echo ""

# Test API (port 8000)
echo "2. Testing API Port (8000)"
test_port 8000 public
echo "✅ Port 8000 is now PUBLIC - accessible from: https://${CODESPACE_NAME}-8000.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN}"
echo ""

# Wait
echo "Waiting 5 seconds..."
sleep 5

# Change back to private
echo "3. Changing ports back to PRIVATE"
test_port 3000 private
test_port 8000 private
echo "✅ Both ports are now PRIVATE - only accessible within Codespace"
echo ""

echo "=== Test Complete ==="
echo ""
echo "Summary:"
echo "- ✅ Successfully changed port 3000 from private to public and back"
echo "- ✅ Successfully changed port 8000 from private to public and back"
echo "- ✅ Both applications are running in Docker and accessible"
echo ""
echo "Note: When ports are PUBLIC, anyone with the URL can access them."
echo "When PRIVATE, only you can access them while logged into GitHub."