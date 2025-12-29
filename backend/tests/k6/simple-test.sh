#!/bin/bash

# Simple test script to verify API is working

BASE_URL="http://localhost:8000"
API_KEY="gw_load_test_abcdef123456"

echo "Testing chat endpoint..."
curl -s -X POST "${BASE_URL}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${API_KEY}" \
  -d '{
    "model": "mock-gpt",
    "messages": [{"role": "user", "content": "Test message"}],
    "contract": {
      "app_id": "test-app",
      "feature": "chat-support",
      "action": "generate",
      "environment": "development"
    }
  }' | python3 -m json.tool

echo -e "\n\nTesting health endpoint..."
curl -s "${BASE_URL}/health" | python3 -m json.tool
