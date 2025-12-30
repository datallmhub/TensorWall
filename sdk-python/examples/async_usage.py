#!/usr/bin/env python3
"""Async usage examples for LLM Gateway SDK."""

import asyncio
from llm_gateway_sdk import AsyncLLMGateway


async def main():
    # Use async context manager
    async with AsyncLLMGateway(
        base_url="http://localhost:8000",
        app_id="async-example",
    ) as client:
        # Check health
        print("=== Health Check ===")
        health = await client.health()
        print(f"Status: {health.get('status', 'unknown')}")

        # Parallel requests
        print("\n=== Parallel Chat Requests ===")
        tasks = [
            client.chat(
                messages=[{"role": "user", "content": f"What is {i} + {i}?"}],
                model="gpt-4",
                max_tokens=50,
            )
            for i in range(1, 4)
        ]

        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for i, resp in enumerate(responses, 1):
                if isinstance(resp, Exception):
                    print(f"  Request {i}: Error - {resp}")
                else:
                    print(f"  Request {i}: {resp.choices[0].message.content}")
        except Exception as e:
            print(f"Error: {e}")

        # Streaming
        print("\n=== Streaming ===")
        try:
            stream = await client.chat(
                messages=[{"role": "user", "content": "Count from 1 to 5."}],
                model="gpt-4",
                stream=True,
                max_tokens=50,
            )
            print("Response: ", end="")
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end="", flush=True)
            print()
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
