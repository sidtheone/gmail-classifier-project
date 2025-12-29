#!/usr/bin/env python3
"""
Quick test to demonstrate retry mechanism
"""

import time
from gmail_client import retry_with_backoff
from ai_classifier import retry_ai_call


def test_retry_mechanism():
    """Test that retry mechanism works with print statements"""

    print("=" * 80)
    print("Testing Retry Mechanism")
    print("=" * 80)

    # Test 1: Successful call on first try
    print("\n1. Testing successful call (no retry needed):")
    attempt = 0
    def success_func():
        nonlocal attempt
        attempt += 1
        print(f"   Call attempt {attempt} - Success!")
        return "Success"

    result = retry_with_backoff(success_func)
    print(f"   Result: {result}\n")

    # Test 2: Fail twice, succeed on third
    print("2. Testing call that fails twice then succeeds:")
    attempt = 0
    def fail_twice():
        nonlocal attempt
        attempt += 1
        if attempt < 3:
            raise Exception(f"Simulated failure {attempt}")
        print(f"   Call attempt {attempt} - Success!")
        return "Success after retries"

    try:
        result = retry_with_backoff(fail_twice)
        print(f"   Final result: {result}\n")
    except Exception as e:
        print(f"   Failed: {e}\n")

    # Test 3: AI retry test
    print("3. Testing AI retry mechanism:")
    attempt = 0
    def ai_call():
        nonlocal attempt
        attempt += 1
        if attempt < 2:
            raise Exception(f"AI API rate limit")
        print(f"   AI call attempt {attempt} - Success!")
        return "AI response"

    try:
        result = retry_ai_call(ai_call)
        print(f"   Final result: {result}\n")
    except Exception as e:
        print(f"   Failed: {e}\n")

    print("=" * 80)
    print("Retry mechanism test complete!")
    print("=" * 80)


if __name__ == "__main__":
    test_retry_mechanism()
