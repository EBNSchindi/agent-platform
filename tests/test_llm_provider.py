"""
Test Script for LLM Provider (Ollama-First with OpenAI Fallback)

This script tests:
1. Ollama connection and basic completion
2. Automatic fallback to OpenAI when Ollama fails
3. Provider statistics tracking
4. Performance metrics

Usage:
    python tests/test_llm_provider.py
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent_platform.llm.providers import get_llm_provider


async def test_ollama_connection():
    """Test 1: Basic Ollama connection"""
    print("\n" + "=" * 70)
    print("TEST 1: OLLAMA CONNECTION")
    print("=" * 70)

    provider = get_llm_provider()

    try:
        messages = [
            {"role": "user", "content": "Say 'Hello from Ollama!' and nothing else."}
        ]

        print("\n🤖 Testing Ollama connection...")
        print(f"   Endpoint: {provider.ollama.base_url}")
        print(f"   Model: {provider.ollama_model}")

        response, provider_used = await provider.complete(messages)

        print(f"\n✅ Success!")
        print(f"   Provider: {provider_used}")
        print(f"   Response: {response.choices[0].message.content}")

        return True

    except Exception as e:
        print(f"\n❌ Ollama connection failed: {e}")
        return False


async def test_openai_fallback():
    """Test 2: OpenAI Fallback when Ollama fails"""
    print("\n" + "=" * 70)
    print("TEST 2: OPENAI FALLBACK (Simulated Ollama Failure)")
    print("=" * 70)

    provider = get_llm_provider()

    # Force a bad Ollama endpoint to trigger fallback
    original_url = provider.ollama.base_url
    provider.ollama.base_url = "http://localhost:99999/v1"  # Invalid endpoint

    try:
        messages = [
            {"role": "user", "content": "Say 'Hello from OpenAI!' and nothing else."}
        ]

        print("\n🔄 Simulating Ollama failure...")
        print(f"   Using invalid endpoint: {provider.ollama.base_url}")

        response, provider_used = await provider.complete(messages)

        print(f"\n✅ Fallback successful!")
        print(f"   Provider: {provider_used}")
        print(f"   Response: {response.choices[0].message.content}")

        # Restore original URL
        provider.ollama.base_url = original_url

        return True

    except Exception as e:
        print(f"\n❌ Fallback failed: {e}")
        provider.ollama.base_url = original_url
        return False


async def test_force_openai():
    """Test 3: Force OpenAI (skip Ollama)"""
    print("\n" + "=" * 70)
    print("TEST 3: FORCE OPENAI (Direct Call)")
    print("=" * 70)

    provider = get_llm_provider()

    try:
        messages = [
            {"role": "user", "content": "Say 'Direct OpenAI call!' and nothing else."}
        ]

        print("\n☁️  Forcing OpenAI (bypassing Ollama)...")

        response, provider_used = await provider.complete(
            messages,
            force_provider="openai"
        )

        print(f"\n✅ Success!")
        print(f"   Provider: {provider_used}")
        print(f"   Response: {response.choices[0].message.content}")

        return True

    except Exception as e:
        print(f"\n❌ Direct OpenAI call failed: {e}")
        print(f"   Make sure OPENAI_API_KEY is set in .env")
        return False


async def test_statistics():
    """Test 4: Statistics Tracking"""
    print("\n" + "=" * 70)
    print("TEST 4: STATISTICS TRACKING")
    print("=" * 70)

    provider = get_llm_provider(reset=True)  # Fresh provider
    provider.reset_stats()

    print("\n📊 Running multiple calls to track statistics...")

    # Make several calls
    messages = [
        {"role": "user", "content": "Count to 3."}
    ]

    for i in range(3):
        print(f"\n   Call {i+1}/3...")
        try:
            response, provider_used = await provider.complete(messages)
            print(f"   ✅ Success via {provider_used}")
        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:100]}")

    # Print statistics
    print("\n" + "-" * 70)
    provider.print_stats()

    return True


async def test_performance():
    """Test 5: Performance Comparison"""
    print("\n" + "=" * 70)
    print("TEST 5: PERFORMANCE COMPARISON")
    print("=" * 70)

    provider = get_llm_provider(reset=True)
    provider.reset_stats()

    messages = [
        {"role": "user", "content": "What is 2+2? Answer with just the number."}
    ]

    print("\n⏱️  Testing Ollama performance...")
    try:
        response, provider_used = await provider.complete(messages)
        stats = provider.get_stats()
        if stats['ollama_call_count'] > 0:
            print(f"   ✅ Ollama avg time: {stats['ollama_avg_time']:.2f}s")
    except:
        print(f"   ❌ Ollama not available")

    print("\n⏱️  Testing OpenAI performance...")
    try:
        response, provider_used = await provider.complete(messages, force_provider="openai")
        stats = provider.get_stats()
        if stats['openai_call_count'] > 0:
            print(f"   ✅ OpenAI avg time: {stats['openai_avg_time']:.2f}s")
    except:
        print(f"   ❌ OpenAI not available")

    return True


async def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("LLM PROVIDER TEST SUITE")
    print("=" * 70)
    print("\nThis will test:")
    print("  1. Ollama connection")
    print("  2. Automatic fallback to OpenAI")
    print("  3. Force OpenAI (skip Ollama)")
    print("  4. Statistics tracking")
    print("  5. Performance comparison")

    # Check configuration
    from agent_platform.core.config import Config

    print("\n" + "-" * 70)
    print("CONFIGURATION:")
    print("-" * 70)
    print(f"Ollama URL: {Config.OLLAMA_BASE_URL}")
    print(f"Ollama Model: {Config.OLLAMA_MODEL}")
    print(f"OpenAI Model: {Config.OPENAI_MODEL}")
    print(f"Fallback Enabled: {Config.LLM_FALLBACK_ENABLED}")
    print(f"OpenAI Key Set: {'Yes' if Config.OPENAI_API_KEY else 'No'}")

    # Run tests
    results = {
        'ollama_connection': False,
        'openai_fallback': False,
        'force_openai': False,
        'statistics': False,
        'performance': False
    }

    try:
        results['ollama_connection'] = await test_ollama_connection()
    except Exception as e:
        print(f"\n❌ Test 1 crashed: {e}")

    try:
        results['openai_fallback'] = await test_openai_fallback()
    except Exception as e:
        print(f"\n❌ Test 2 crashed: {e}")

    try:
        results['force_openai'] = await test_force_openai()
    except Exception as e:
        print(f"\n❌ Test 3 crashed: {e}")

    try:
        results['statistics'] = await test_statistics()
    except Exception as e:
        print(f"\n❌ Test 4 crashed: {e}")

    try:
        results['performance'] = await test_performance()
    except Exception as e:
        print(f"\n❌ Test 5 crashed: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name.replace('_', ' ').title():.<50} {status}")

    print("\n" + "-" * 70)
    print(f"Total: {passed}/{total} tests passed ({passed/total*100:.0f}%)")
    print("=" * 70 + "\n")

    # Recommendations
    print("RECOMMENDATIONS:")

    if not results['ollama_connection']:
        print("  ⚠️  Ollama is not running or not configured correctly.")
        print("     Start Ollama: ollama serve")
        print("     Pull model: ollama pull gptoss20b")

    if not results['force_openai'] and Config.OPENAI_API_KEY:
        print("  ⚠️  OpenAI API key is set but calls are failing.")
        print("     Check your API key and network connection.")

    if not Config.OPENAI_API_KEY:
        print("  ⚠️  No OpenAI API key configured - fallback will not work.")
        print("     Add OPENAI_API_KEY to your .env file.")

    if results['ollama_connection'] and results['openai_fallback']:
        print("  ✅ System ready! Ollama-first with OpenAI fallback is working.")

    print()

    # Exit code
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user\n")
        sys.exit(1)
