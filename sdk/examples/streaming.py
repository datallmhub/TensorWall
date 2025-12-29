#!/usr/bin/env python3
"""Streaming examples for LLM Gateway SDK."""

from llm_gateway_sdk import LLMGateway


def main():
    client = LLMGateway(
        base_url="http://localhost:8000",
        app_id="streaming-example",
    )

    print("=== Streaming Chat ===")
    print("Prompt: Write a haiku about programming.")
    print("\nResponse:")
    print("-" * 40)

    try:
        stream = client.chat(
            messages=[
                {"role": "user", "content": "Write a haiku about programming."}
            ],
            model="gpt-4",
            stream=True,
            temperature=0.9,
        )

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)

        print("\n" + "-" * 40)
        print("Stream complete!")

    except Exception as e:
        print(f"\nError: {e}")

    client.close()


if __name__ == "__main__":
    main()
