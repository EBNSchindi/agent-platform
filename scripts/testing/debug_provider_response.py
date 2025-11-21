#!/usr/bin/env python3
"""Debug script to understand provider response structure"""

import asyncio
import sys
from pathlib import Path
from pydantic import BaseModel, Field

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from agent_platform.llm.providers import get_llm_provider


class SimpleModel(BaseModel):
    text: str = Field(description="Some text")
    number: int = Field(description="Some number")


async def test_provider():
    provider = get_llm_provider()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say hello and give me the number 42"}
    ]

    response, provider_used = await provider.complete(
        messages=messages,
        response_format=SimpleModel,
        temperature=0.1
    )

    print(f"Provider used: {provider_used}")
    print(f"Response type: {type(response)}")
    print(f"Response: {response}")
    print(f"Has .parsed attribute: {hasattr(response, 'parsed')}")

    if hasattr(response, 'parsed'):
        print(f"Parsed type: {type(response.parsed)}")
        print(f"Parsed: {response.parsed}")
        print(f"Parsed.text: {response.parsed.text}")
        print(f"Parsed.number: {response.parsed.number}")
    else:
        print(f"Direct access - text: {response.text}")
        print(f"Direct access - number: {response.number}")


if __name__ == "__main__":
    asyncio.run(test_provider())
