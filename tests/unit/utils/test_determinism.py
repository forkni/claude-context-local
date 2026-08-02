"""Tests for utils.determinism (GPU determinism pinning)."""

import os
from unittest.mock import MagicMock, patch

import pytest

import utils.determinism as determinism


@pytest.fixture(autouse=True)
def _clean_state():
    """Reset the idempotence latch and restore the env around every test."""
    determinism._applied = False
    with patch.dict(os.environ):
        os.environ.pop("CUBLAS_WORKSPACE_CONFIG", None)
        yield
    determinism._applied = False


def test_apply_sets_env_and_torch_flags():
    """apply_gpu_determinism pins env var + all three torch settings."""
    mock_torch = MagicMock()
    with patch.dict("sys.modules", {"torch": mock_torch}):
        result = determinism.apply_gpu_determinism(warn_only=False)

    assert result is True
    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == ":4096:8"
    mock_torch.use_deterministic_algorithms.assert_called_once_with(
        True, warn_only=False
    )
    assert mock_torch.backends.cudnn.deterministic is True
    assert mock_torch.backends.cudnn.benchmark is False
    assert determinism.is_applied() is True


def test_apply_respects_existing_cublas_workspace():
    """An explicit user CUBLAS_WORKSPACE_CONFIG is not overwritten."""
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":16:8"

    mock_torch = MagicMock()
    with patch.dict("sys.modules", {"torch": mock_torch}):
        determinism.apply_gpu_determinism()

    assert os.environ["CUBLAS_WORKSPACE_CONFIG"] == ":16:8"


def test_apply_is_idempotent():
    """Second call is a no-op (torch not touched again)."""
    mock_torch = MagicMock()
    with patch.dict("sys.modules", {"torch": mock_torch}):
        assert determinism.apply_gpu_determinism() is True
        assert determinism.apply_gpu_determinism() is True

    mock_torch.use_deterministic_algorithms.assert_called_once()


def test_apply_returns_false_without_torch():
    """torch unavailable: returns False, is_applied stays False."""
    with patch.dict("sys.modules", {"torch": None}):
        result = determinism.apply_gpu_determinism()

    assert result is False
    assert determinism.is_applied() is False


def test_warn_only_passthrough():
    """warn_only is forwarded to torch.use_deterministic_algorithms."""
    mock_torch = MagicMock()
    with patch.dict("sys.modules", {"torch": mock_torch}):
        determinism.apply_gpu_determinism(warn_only=True)

    mock_torch.use_deterministic_algorithms.assert_called_once_with(
        True, warn_only=True
    )


def test_fresh_process_reports_untouched():
    """Default state: nothing applied until the benchmark flag opts in
    (only run_sscg_benchmark.py --deterministic-gpu calls the helper)."""
    assert determinism.is_applied() is False
