#!/bin/bash
# Test on port 8001

# Get token
TOKEN=$(curl -s -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"123456"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo "Token obtained: ${TOKEN:0:30}..."

# Test threads endpoint
echo ""
echo "Testing /chat/threads endpoint on port 8001..."
curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8001/chat/threads | python -m json.tool
