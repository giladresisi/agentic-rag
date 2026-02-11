#!/bin/bash
# Test backend API on default port 8000

# Get token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@...","password":"***"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo "Token obtained: ${TOKEN:0:30}..."

# Test threads endpoint
echo ""
echo "Testing /chat/threads endpoint on port 8000..."
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/chat/threads | python -m json.tool
