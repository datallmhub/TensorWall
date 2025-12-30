#!/usr/bin/env python3
"""Error handling examples for LLM Gateway SDK."""

from llm_gateway_sdk import LLMGateway
from llm_gateway_sdk.exceptions import (
    LLMGatewayError,
    AuthenticationError,
    RateLimitError,
    ValidationError,
    ServerError,
    PolicyDeniedError,
    BudgetExceededError,
)


def main():
    client = LLMGateway(
        base_url="http://localhost:8000",
        app_id="error-handling-example",
    )

    print("=== Error Handling Examples ===\n")

    # Example 1: Invalid model
    print("1. Testing with invalid model...")
    try:
        response = client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="non-existent-model",
        )
    except ValidationError as e:
        print(f"   ValidationError: {e.message}")
        print(f"   Status code: {e.status_code}")
    except LLMGatewayError as e:
        print(f"   Error: {e}")

    # Example 2: Empty messages
    print("\n2. Testing with empty messages...")
    try:
        response = client.chat(
            messages=[],
            model="gpt-4",
        )
    except ValidationError as e:
        print(f"   ValidationError: {e.message}")
    except LLMGatewayError as e:
        print(f"   Error: {e}")

    # Example 3: Handling auth errors
    print("\n3. Testing with invalid API key...")
    bad_client = LLMGateway(
        base_url="http://localhost:8000",
        api_key="invalid-key",
    )
    try:
        response = bad_client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4",
        )
    except AuthenticationError as e:
        print(f"   AuthenticationError: {e.message}")
    except LLMGatewayError as e:
        print(f"   Error: {e}")
    finally:
        bad_client.close()

    # Example 4: Generic error handling
    print("\n4. Generic error handling pattern...")
    try:
        response = client.chat(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4",
        )
        print(f"   Success: {response.choices[0].message.content[:50]}...")
    except AuthenticationError:
        print("   Handle: Re-authenticate or check API key")
    except RateLimitError as e:
        print(f"   Handle: Wait {e.retry_after}s and retry")
    except PolicyDeniedError as e:
        print(f"   Handle: Request denied by policy '{e.policy_name}'")
    except BudgetExceededError as e:
        print(f"   Handle: Budget {e.current}/{e.limit} exceeded")
    except ValidationError:
        print("   Handle: Fix request parameters")
    except ServerError:
        print("   Handle: Retry with backoff or alert ops")
    except LLMGatewayError as e:
        print(f"   Handle: Generic error - {e}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
