#!/usr/bin/env python3
"""
Test script to verify LLM API configuration and agent functionality
"""

import asyncio
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from agent_framework.llm_client import OpenAICompatibleResponsesClient
from agent_framework.config import get_config


def test_llm_client():
    """Test LLM client configuration and connectivity"""
    print("=" * 60)
    print("Testing LLM Client Configuration")
    print("=" * 60)

    # Check environment variables
    print("\n1. Checking environment variables:")
    print(f"   OPENAI_API_KEY: {'*' * 20}... (set: {bool(os.environ.get('OPENAI_API_KEY'))})")
    print(f"   OPENAI_BASE_URL: {os.environ.get('OPENAI_BASE_URL', 'Not set')}")
    print(f"   OPENAI_MODEL: {os.environ.get('OPENAI_MODEL', 'Not set')}")

    # Create client from config
    print("\n2. Creating LLM client from environment...")
    client = OpenAICompatibleResponsesClient.from_config({})

    print(f"   Client enabled: {client.config.enabled}")
    print(f"   Base URL: {client.config.base_url}")
    print(f"   Model: {client.config.model}")
    print(f"   API Key present: {bool(client.config.api_key)}")
    print(f"   is_enabled: {client.is_enabled}")

    if not client.is_enabled:
        print("\n   ERROR: LLM client is not properly configured!")
        return False

    # Health check
    print("\n3. Running health check...")
    health_result = client.health_check()

    if health_result.get("success"):
        print(f"   ✓ Health check PASSED")
        print(f"   Model: {health_result.get('model')}")
        print(f"   Response: {health_result.get('response_text')}")
    else:
        print(f"   ✗ Health check FAILED")
        print(f"   Error: {health_result.get('error')}")
        return False

    return True


async def test_translation():
    """Test translation functionality"""
    print("\n" + "=" * 60)
    print("Testing Translation Feature")
    print("=" * 60)

    client = OpenAICompatibleResponsesClient.from_config({})

    if not client.is_enabled:
        print("   LLM not enabled, skipping translation test")
        return False

    test_text = "Hello, world!"
    print(f"\n   Translating: '{test_text}'")

    result = await client.translate(test_text, "en", "zh")

    if result:
        print(f"   ✓ Translation result: '{result}'")
        return True
    else:
        print(f"   ✗ Translation failed")
        return False


async def test_issue_analysis():
    """Test issue analysis functionality"""
    print("\n" + "=" * 60)
    print("Testing Issue Analysis Feature")
    print("=" * 60)

    client = OpenAICompatibleResponsesClient.from_config({})

    if not client.is_enabled:
        print("   LLM not enabled, skipping issue analysis test")
        return False

    title = "Fix typo in README"
    body = "There's a spelling error in the documentation that needs to be fixed."
    labels = ["good first issue", "documentation"]

    print(f"\n   Analyzing issue: '{title}'")

    result = await client.analyze_issue(title, body, labels)

    if result and result.get("difficulty") != "intermediate":
        print(f"   ✓ Analysis result:")
        print(f"     - Difficulty: {result.get('difficulty')}")
        print(f"     - Type: {result.get('type')}")
        print(f"     - Estimated hours: {result.get('estimated_hours')}")
        return True
    else:
        print(f"   ✗ Analysis returned default values (may indicate failure)")
        print(f"   Result: {result}")
        return False


async def main():
    """Main test function"""
    print("\n" + "=" * 60)
    print("LLM AGENT FUNCTIONALITY TEST")
    print("=" * 60)

    # Test basic LLM client
    llm_ok = test_llm_client()

    if not llm_ok:
        print("\n" + "!" * 60)
        print("LLM CLIENT TEST FAILED - Cannot proceed with agent tests")
        print("!" * 60)
        return 1

    # Test translation
    translation_ok = await test_translation()

    # Test issue analysis
    analysis_ok = await test_issue_analysis()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"   LLM Client:     {'✓ PASS' if llm_ok else '✗ FAIL'}")
    print(f"   Translation:    {'✓ PASS' if translation_ok else '✗ FAIL'}")
    print(f"   Issue Analysis: {'✓ PASS' if analysis_ok else '✗ FAIL'}")

    all_passed = llm_ok and translation_ok and analysis_ok

    if all_passed:
        print("\n   🎉 All tests PASSED! Agent is ready to use.")
        return 0
    else:
        print("\n   ⚠️  Some tests failed. Check the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
