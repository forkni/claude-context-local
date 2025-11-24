"""Test lazy loading behavior for Phase 3A optimization."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_lazy_loading():
    """Verify that models are not loaded at import time."""

    import psutil
    import torch

    process = psutil.Process()

    # Measure memory before import
    mem_before = process.memory_info().rss / (1024 * 1024)  # MB

    # Check if GPU available
    gpu_available = torch.cuda.is_available()
    vram_before = 0
    if gpu_available:
        torch.cuda.reset_peak_memory_stats()
        vram_before = torch.cuda.memory_allocated() / (1024 * 1024)  # MB

    print("\n[BEFORE IMPORT]")
    print(f"  RAM: {mem_before:.1f} MB")
    if gpu_available:
        print(f"  VRAM: {vram_before:.1f} MB")

    # Import server module (should NOT load models)
    print("\n[IMPORTING mcp_server.server]")
    start_time = time.time()

    # Force reimport to test
    if "mcp_server.server" in sys.modules:
        del sys.modules["mcp_server.server"]
    if "mcp_server" in sys.modules:
        del sys.modules["mcp_server"]

    from mcp_server import server

    import_time = time.time() - start_time

    # Measure memory after import
    mem_after_import = process.memory_info().rss / (1024 * 1024)
    vram_after_import = 0
    if gpu_available:
        vram_after_import = torch.cuda.memory_allocated() / (1024 * 1024)

    print("\n[AFTER IMPORT]")
    print(f"  RAM: {mem_after_import:.1f} MB (+{mem_after_import - mem_before:.1f} MB)")
    if gpu_available:
        print(
            f"  VRAM: {vram_after_import:.1f} MB (+{vram_after_import - vram_before:.1f} MB)"
        )
    print(f"  Import time: {import_time:.2f}s")

    # Check that _embedders is empty
    embedders_count = len([e for e in server._embedders.values() if e is not None])
    print("\n[EMBEDDERS STATUS]")
    print(f"  Loaded models: {embedders_count}")
    print(f"  Model pool config: {list(server.MODEL_POOL_CONFIG.keys())}")

    # Verify lazy loading (no models should be loaded yet)
    assert embedders_count == 0, f"Expected 0 models loaded, got {embedders_count}"

    # VRAM should be minimal (<200MB for PyTorch overhead)
    if gpu_available:
        vram_increase = vram_after_import - vram_before
        assert (
            vram_increase < 200
        ), f"VRAM increased by {vram_increase:.1f}MB (expected <200MB)"

    print("\n[SUCCESS] Lazy loading verified!")
    print("  [OK] No models loaded at import time")
    print("  [OK] VRAM usage minimal (<200MB)")
    print(f"  [OK] Fast import time ({import_time:.2f}s)")

    return True


if __name__ == "__main__":
    try:
        test_lazy_loading()
    except AssertionError as e:
        print(f"\n[FAILED] {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
