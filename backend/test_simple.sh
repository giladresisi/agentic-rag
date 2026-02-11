#!/bin/bash
# Simple curl test

# Get token first
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@...","password":"***"}' | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

echo "Token: ${TOKEN:0:30}..."

# Test threads endpoint
echo ""
echo "Testing /chat/threads endpoint..."
curl -v -H "Authorization: Bearer $TOKEN" http://localhost:8000/chat/threads
