#!/usr/bin/env python3
"""
Generate test data for TensorWall dashboard.

This script makes HTTP requests to the gateway to create sample traces
in the database for testing the frontend.
"""

import requests
import random
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"
API_KEY = "gw_load_test_abcdef123456"

# Test scenarios
# NOTE: Only use registered apps/features!
# Check with: SELECT app_id FROM applications; SELECT feature_id, app_id FROM features;
APPS = ["test-app"]  # Only test-app is registered in the database
FEATURES = ["default"]  # Only 'default' feature is registered for test-app
MODELS = ["mock-gpt"]  # Use mock-gpt for faster testing
USERS = [
    "alice@example.com",
    "bob@example.com",
    "charlie@example.com",
    "diana@example.com",
    "anonymous",
]
ENVIRONMENTS = ["development", "staging", "production"]

# Normal prompts (should be allowed)
NORMAL_PROMPTS = [
    "Hello, how are you?",
    "Write a Python function to calculate fibonacci",
    "Summarize this article about AI",
    "Translate to French: Good morning",
    "What is machine learning?",
    "Help me debug this code",
    "Generate a creative story",
    "Explain quantum computing",
    "What are best practices for REST APIs?",
    "How do I optimize database queries?",
]

# Risky prompts (should be blocked)
RISKY_PROMPTS = [
    "SELECT * FROM users WHERE password = 'admin'",  # SQL injection
    "My credit card is 4532-1234-5678-9010",  # PII
    "<script>alert('XSS')</script>",  # XSS
    "rm -rf / --no-preserve-root",  # Dangerous command
    "'; DROP TABLE users; --",  # SQL injection
]


def make_request(
    prompt: str, app: str, feature: str, model: str, user: str, env: str
) -> dict:
    """Make a chat completion request to the gateway."""

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "contract": {
            "app_id": app,
            "feature": feature,
            "action": "generate",
            "environment": env,
        },
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/v1/chat/completions", json=payload, headers=headers, timeout=10
        )

        return {
            "status": response.status_code,
            "success": response.status_code == 200,
            "data": (
                response.json() if response.status_code in [200, 403, 400] else None
            ),
        }
    except Exception as e:
        return {"status": 500, "success": False, "error": str(e)}


def generate_normal_requests(count: int = 50):
    """Generate normal requests that should be allowed."""
    print(f"\n🟢 Generating {count} normal requests...")

    success_count = 0
    for i in range(count):
        prompt = random.choice(NORMAL_PROMPTS)
        app = random.choice(APPS)
        feature = random.choice(FEATURES)
        model = random.choice(MODELS)
        user = random.choice(USERS)
        env = random.choice(ENVIRONMENTS)

        result = make_request(prompt, app, feature, model, user, env)

        if result["success"]:
            success_count += 1
            print(
                f"  ✓ [{i + 1}/{count}] {app}/{feature} - {model} - {result['status']}"
            )
        else:
            print(
                f"  ✗ [{i + 1}/{count}] {app}/{feature} - ERROR: {result.get('error', result['status'])}"
            )

        time.sleep(0.1)  # Small delay to avoid overwhelming the server

    print(f"\n✅ Created {success_count}/{count} normal requests")


def generate_risky_requests(count: int = 10):
    """Generate risky requests that should be blocked."""
    print(f"\n🔴 Generating {count} risky requests (should be blocked)...")

    blocked_count = 0
    for i in range(count):
        prompt = random.choice(RISKY_PROMPTS)
        app = random.choice(APPS)
        feature = random.choice(FEATURES)
        model = "mock-gpt"  # Use mock for risky requests
        user = "hacker@example.com"
        env = "production"

        result = make_request(prompt, app, feature, model, user, env)

        # For risky requests, we expect 403 or 400
        if result["status"] in [403, 400]:
            blocked_count += 1
            print(f"  ✓ [{i + 1}/{count}] BLOCKED - {prompt[:50]}...")
        elif result["status"] == 200:
            print(
                f"  ⚠ [{i + 1}/{count}] ALLOWED (should be blocked!) - {prompt[:50]}..."
            )
        else:
            print(
                f"  ✗ [{i + 1}/{count}] ERROR: {result.get('error', result['status'])}"
            )

        time.sleep(0.1)

    print(f"\n✅ Blocked {blocked_count}/{count} risky requests")


def main():
    print("=" * 70)
    print("TensorWall Test Data Generator")
    print("=" * 70)
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 70)

    # Generate normal requests
    generate_normal_requests(count=100)

    # Generate risky requests
    generate_risky_requests(count=20)

    print("\n" + "=" * 70)
    print("✅ Test data generation complete!")
    print("=" * 70)
    print("\nYou can now:")
    print("1. Visit http://localhost:3000 to see the dashboard")
    print("2. Check the audit logs and metrics")
    print("3. Verify that blocking reasons are populated")


if __name__ == "__main__":
    main()
