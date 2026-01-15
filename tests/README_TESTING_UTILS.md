# Testing Utilities Documentation

## Overview

The `tests/testing_utils.py` module provides reusable testing utilities for the claude-context-local test suite. These utilities are based on patterns from HuggingFace Transformers testing framework and designed to improve test workflow.

## Features

### 1. Hardware Requirement Decorators

Skip tests based on hardware availability:

```python
from tests.testing_utils import require_torch, require_torch_gpu

@require_torch
def test_embedding_model():
    """Test runs only if PyTorch is installed."""
    import torch
    # ... test code

@require_torch_gpu
def test_gpu_inference():
    """Test runs only if CUDA GPU is available."""
    import torch
    assert torch.cuda.is_available()
    # ... test code
```

### 2. Output Capture Utilities

Capture and verify printed output and logs:

```python
from tests.testing_utils import CaptureStdout, CaptureStderr, CaptureStd, CaptureLogger

# Capture stdout
with CaptureStdout() as cs:
    print("test message")
assert "test message" in cs.out

# Capture stderr
with CaptureStderr() as cs:
    print("error", file=sys.stderr)
assert "error" in cs.out

# Capture both stdout and stderr
with CaptureStd() as cs:
    print("stdout message")
    print("stderr message", file=sys.stderr)
assert "stdout message" in cs.out
assert "stderr message" in cs.err

# Capture logger output
with CaptureLogger("search.hybrid_searcher") as cl:
    logger = logging.getLogger("search.hybrid_searcher")
    logger.info("test log message")
assert "test log message" in cl.out
```

### 3. Environment Variable Mocking

Temporarily set environment variables for tests:

```python
from tests.testing_utils import mockenv, mockenv_context

# Context manager
with mockenv_context(CUDA_VISIBLE_DEVICES="0", MODEL_NAME="test"):
    # Environment variables set here
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "0"
# Variables automatically restored here

# Decorator
@mockenv(DEBUG="1", LOG_LEVEL="INFO")
def test_debug_mode():
    assert os.environ["DEBUG"] == "1"
    # ... test code
```

## Available Decorators

| Decorator | Purpose | Skip Condition |
|-----------|---------|----------------|
| `@require_torch` | Require PyTorch | PyTorch not installed |
| `@require_torch_gpu` | Require CUDA GPU | No GPU or PyTorch not installed |

## Available Context Managers

| Context Manager | Purpose | Attributes |
|----------------|---------|------------|
| `CaptureStdout()` | Capture stdout | `cs.out` |
| `CaptureStderr()` | Capture stderr | `cs.out` |
| `CaptureStd()` | Capture stdout + stderr | `cs.out`, `cs.err` |
| `CaptureLogger(name, level)` | Capture logger output | `cl.out` |
| `mockenv_context(**vars)` | Mock environment variables | - |

## Example Use Cases

### Testing Logging Output

```python
def test_resolution_logging():
    """Verify that add_embeddings logs resolution stats."""
    with CaptureLogger("search.hybrid_searcher") as cl:
        searcher.add_embeddings(results)

    # Verify logging contains resolution stats
    assert "resolved" in cl.out
    assert "phantom" in cl.out
```

### Testing GPU-Dependent Code

```python
@require_torch_gpu
def test_embedding_model_gpu_inference():
    """Test embedding model uses GPU when available."""
    from embeddings.code_embedder import CodeEmbedder

    embedder = CodeEmbedder()
    assert embedder.device.type == "cuda"
```

### Testing Environment-Dependent Behavior

```python
@mockenv(USE_CACHE="false")
def test_caching_disabled():
    """Test that caching can be disabled via environment variable."""
    searcher = HybridSearcher(temp_dir)
    assert not searcher.use_cache
```

## Testing the Utilities

Run tests for the testing utilities themselves:

```bash
pytest tests/unit/test_testing_utils.py -v
```

## Future Enhancements

Potential additions based on project needs:

1. **Multi-GPU decorators**: `@require_torch_multi_gpu(n)`
2. **Custom pytest fixtures**: Reusable test data factories
3. **Performance benchmarking**: Timing decorators for performance tests
4. **Test report generation**: Custom pytest hooks for CI/CD integration

## References

- Based on HuggingFace Transformers `testing_utils.py`
- Inspired by patterns from `ml-engineering/testing` repository
- See `C:\Users\INTER\.claude\plans\flickering-wondering-raccoon.md` for design decisions
