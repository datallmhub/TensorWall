#!/bin/bash
# =============================================================================
# Budget Load Test Runner
# =============================================================================
# Tests budget enforcement with real LLM requests
#
# Prerequisites:
#   - LLM Gateway running on localhost:8000
#   - LM Studio running with phi-2 or another model loaded
#   - Admin credentials configured
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=============================================="
echo "  Budget Enforcement Load Test"
echo "=============================================="
echo ""

# Check if k6 is installed
if ! command -v k6 &> /dev/null; then
    echo "ERROR: k6 is not installed"
    echo "Install with: brew install k6"
    exit 1
fi

# Check if gateway is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "ERROR: LLM Gateway is not running on localhost:8000"
    echo "Start it with: docker-compose up -d"
    exit 1
fi

echo "Gateway: http://localhost:8000 ✓"

# Check if LM Studio is running
if curl -s http://localhost:11434/v1/models > /dev/null 2>&1; then
    echo "LM Studio: http://localhost:11434 ✓"
    MODELS=$(curl -s http://localhost:11434/v1/models | grep -o '"id":"[^"]*"' | head -3 | cut -d'"' -f4)
    echo "Available models:"
    echo "$MODELS" | while read model; do
        echo "  - $model"
    done
else
    echo "WARNING: LM Studio not detected on localhost:11434"
    echo "The test may fail if no LLM provider is available"
fi

echo ""
echo "Starting budget enforcement test..."
echo "This will:"
echo "  1. Create a budget with very low limit (\$0.001)"
echo "  2. Send requests until budget is exceeded"
echo "  3. Verify requests are blocked"
echo "  4. Reset budget and verify requests work again"
echo ""

# Run the test
k6 run \
    --env BASE_URL=${BASE_URL:-http://localhost:8000} \
    --env ADMIN_EMAIL=${ADMIN_EMAIL:-admin@example.com} \
    --env ADMIN_PASSWORD=${ADMIN_PASSWORD:?ADMIN_PASSWORD is required} \
    --env TEST_MODEL=${TEST_MODEL:-lmstudio/phi-2} \
    budget-load-test.js

echo ""
echo "=============================================="
echo "  Test Complete"
echo "=============================================="
