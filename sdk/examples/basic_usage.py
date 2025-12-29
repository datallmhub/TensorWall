#!/usr/bin/env python3
"""Basic usage examples for LLM Gateway SDK."""

from llm_gateway_sdk import LLMGateway


def main():
    # Initialize the client
    client = LLMGateway(
        base_url="http://localhost:8000",
        app_id="example-app",
    )

    # Check health
    print("=== Health Check ===")
    health = client.health()
    print(f"Status: {health.get('status', 'unknown')}")

    # List available models
    print("\n=== Available Models ===")
    try:
        models = client.models()
        for model in models[:5]:  # Show first 5
            print(f"  - {model.get('id', 'unknown')}")
    except Exception as e:
        print(f"  Could not list models: {e}")

    # Chat completion
    print("\n=== Chat Completion ===")
    try:
        response = client.chat(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "What is the capital of France?"},
            ],
            model="gpt-4",
            temperature=0.7,
            max_tokens=100,
        )
        print(f"Response: {response.choices[0].message.content}")
        if response.usage:
            print(f"Tokens: {response.usage.total_tokens}")
    except Exception as e:
        print(f"Error: {e}")

    # Embeddings
    print("\n=== Embeddings ===")
    try:
        embeddings = client.embeddings(
            input="Hello, world!",
            model="text-embedding-ada-002",
        )
        print(f"Embedding dimension: {len(embeddings.data[0].embedding)}")
        print(f"First 5 values: {embeddings.data[0].embedding[:5]}")
    except Exception as e:
        print(f"Error: {e}")

    # Clean up
    client.close()


if __name__ == "__main__":
    main()
