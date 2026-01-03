"""Manual test for SSE BrokenResourceError defense.

This script verifies that the application-level protection against
BrokenResourceError is working correctly.

Run this test while the SSE server is running to simulate error conditions.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import anyio

from mcp_server.tools.decorators import error_handler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Test 1: Verify CancelledError propagation
@error_handler("Test operation")
async def _simulate_cancelled_error(arguments):
    """Test that CancelledError is propagated, not caught."""
    await asyncio.sleep(0.1)
    raise asyncio.CancelledError()


# Test 2: Verify BrokenResourceError handling
@error_handler("Test operation")
async def _simulate_broken_resource(arguments):
    """Test that BrokenResourceError is caught gracefully."""
    await asyncio.sleep(0.1)
    raise anyio.BrokenResourceError()


# Test 3: Verify ClosedResourceError handling
@error_handler("Test operation")
async def _simulate_closed_resource(arguments):
    """Test that ClosedResourceError is caught gracefully."""
    await asyncio.sleep(0.1)
    raise anyio.ClosedResourceError()


# Test 4: Verify normal exceptions still work
@error_handler("Test operation")
async def _simulate_normal_exception(arguments):
    """Test that normal exceptions are handled as before."""
    await asyncio.sleep(0.1)
    raise ValueError("Test error")


async def run_tests():
    """Run all tests."""
    print("=" * 70)
    print("SSE BrokenResourceError Defense Tests")
    print("=" * 70)
    print()

    # Test 1: CancelledError should propagate
    print("[TEST 1] CancelledError propagation...")
    try:
        await _simulate_cancelled_error({})
        print("  [FAIL] CancelledError was caught (should propagate)")
        return False
    except asyncio.CancelledError:
        print("  [PASS] CancelledError propagated correctly")
    print()

    # Test 2: BrokenResourceError should be caught
    print("[TEST 2] BrokenResourceError handling...")
    result = await _simulate_broken_resource({})
    if (
        result.get("error") == "Client disconnected"
        and result.get("status") == "cancelled"
    ):
        print("  [PASS] BrokenResourceError caught and handled gracefully")
    else:
        print(f"  [FAIL] Unexpected result: {result}")
        return False
    print()

    # Test 3: ClosedResourceError should be caught
    print("[TEST 3] ClosedResourceError handling...")
    result = await _simulate_closed_resource({})
    if (
        result.get("error") == "Client disconnected"
        and result.get("status") == "cancelled"
    ):
        print("  [PASS] ClosedResourceError caught and handled gracefully")
    else:
        print(f"  [FAIL] Unexpected result: {result}")
        return False
    print()

    # Test 4: Normal exceptions should still work
    print("[TEST 4] Normal exception handling...")
    result = await _simulate_normal_exception({})
    if "error" in result and "Test error" in result["error"]:
        print("  [PASS] Normal exceptions handled as before")
    else:
        print(f"  [FAIL] Unexpected result: {result}")
        return False
    print()

    print("=" * 70)
    print("All tests PASSED!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
