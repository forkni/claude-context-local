"""Unit tests for per-field validation in MCP config handlers.

Covers the validation branches in handle_configure_search_mode and
handle_configure_chunking that each return specific error dicts on bad input.
"""

import ast
import dataclasses
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from mcp_server.tools.config_handlers import (
    handle_configure_chunking,
    handle_configure_search_mode,
)
from search.config import ChunkingConfig, SearchModeConfig


@pytest.fixture
def mock_config_manager():
    """Mock config manager whose load_config returns a plain Mock config."""
    mgr = Mock()
    mgr.load_config.return_value = Mock()
    return mgr


@pytest.fixture
def mock_state():
    """Mock app state used by handle_configure_search_mode on success."""
    state = Mock()
    return state


# ============================================================================
# handle_configure_search_mode
# ============================================================================


@pytest.mark.asyncio
async def test_configure_search_mode_invalid_returns_error(mock_config_manager):
    """Invalid search_mode returns an error dict without calling save_config."""
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_search_mode({"search_mode": "fuzzy"})

    assert "error" in result
    assert "fuzzy" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.parametrize("mode", ["hybrid", "semantic", "bm25", "auto"])
@pytest.mark.asyncio
async def test_configure_search_mode_valid_saves_config(
    mode, mock_config_manager, mock_state
):
    """Each valid search_mode succeeds and persists via save_config."""
    with (
        patch(
            "mcp_server.tools.config_handlers.get_config_manager",
            return_value=mock_config_manager,
        ),
        patch(
            "mcp_server.tools.config_handlers.get_state",
            return_value=mock_state,
        ),
    ):
        result = await handle_configure_search_mode({"search_mode": mode})

    assert "error" not in result
    assert result.get("success") is True
    mock_config_manager.save_config.assert_called_once()


# ============================================================================
# handle_configure_chunking — per-field validation
# ============================================================================


@pytest.mark.asyncio
async def test_chunking_community_resolution_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"community_resolution": 0.05})

    assert "error" in result
    assert "community_resolution" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_max_phantom_degree_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"max_phantom_degree": 0})

    assert "error" in result
    assert "max_phantom_degree" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_token_estimation_invalid(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"token_estimation": "gpt4"})

    assert "error" in result
    assert "token_estimation" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_split_size_method_invalid(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"split_size_method": "tokens"})

    assert "error" in result
    assert "split_size_method" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_max_split_chars_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"max_split_chars": 500})

    assert "error" in result
    assert "max_split_chars" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_sizing_mode_invalid(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"sizing_mode": "dynamic"})

    assert "error" in result
    assert "sizing_mode" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_adaptive_multiplier_max_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"adaptive_multiplier_max": 3.0})

    assert "error" in result
    assert "adaptive_multiplier_max" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_adaptive_multiplier_min_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"adaptive_multiplier_min": 0.0})

    assert "error" in result
    assert "adaptive_multiplier_min" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_max_complexity_cap_out_of_range(mock_config_manager):
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking({"max_complexity_cap": 200})

    assert "error" in result
    assert "max_complexity_cap" in result["error"]
    mock_config_manager.save_config.assert_not_called()


@pytest.mark.asyncio
async def test_chunking_all_valid_saves_config(mock_config_manager):
    """A fully valid chunking call succeeds and calls save_config once."""
    with patch(
        "mcp_server.tools.config_handlers.get_config_manager",
        return_value=mock_config_manager,
    ):
        result = await handle_configure_chunking(
            {
                "community_resolution": 1.0,
                "max_phantom_degree": 50,
                "token_estimation": "whitespace",
                "split_size_method": "lines",
                "max_split_chars": 5000,
                "sizing_mode": "adaptive",
                "adaptive_multiplier_max": 1.5,
                "adaptive_multiplier_min": 0.5,
                "max_complexity_cap": 20,
            }
        )

    assert "error" not in result
    assert result.get("success") is True
    mock_config_manager.save_config.assert_called_once()


# ============================================================================
# TestConfigValidationOwnership — P3-C gate
# ============================================================================


class TestConfigValidationOwnership:
    """Completeness gate: field-spec validation must live on the dataclass fields,
    not as inline bounds/enum checks in config_handlers.py.

    Mirrors TestTokenizationOwnership (tests/unit/search/test_tokenization.py).
    """

    _HANDLER_FILE = Path("mcp_server/tools/config_handlers.py")
    _CONFIG_FILE = Path("search/config.py")

    # ------------------------------------------------------------------
    # 1. Specs live on ChunkingConfig and SearchModeConfig fields
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "field_name,spec_key,expected",
        [
            ("community_resolution", "range", (0.1, 2.0)),
            ("max_phantom_degree", "range", (1, 1000)),
            ("max_split_chars", "range", (1000, 10000)),
            ("adaptive_multiplier_max", "range", (1.0, 2.0)),
            ("adaptive_multiplier_min", "range", (0.1, 1.0)),
            ("max_complexity_cap", "range", (5, 100)),
            ("token_estimation", "choices", ("whitespace", "tiktoken")),
            ("split_size_method", "choices", ("lines", "characters")),
            ("sizing_mode", "choices", ("fixed", "adaptive")),
        ],
    )
    def test_chunking_field_carries_spec(self, field_name, spec_key, expected):
        """Each constrained ChunkingConfig field must have its spec in field metadata."""
        fields = {f.name: f for f in dataclasses.fields(ChunkingConfig)}
        assert field_name in fields, f"ChunkingConfig has no field '{field_name}'"
        meta = fields[field_name].metadata
        assert spec_key in meta, (
            f"ChunkingConfig.{field_name}.metadata missing '{spec_key}' — "
            "spec must live on the field, not in the handler."
        )
        assert meta[spec_key] == expected, (
            f"ChunkingConfig.{field_name}.metadata['{spec_key}'] = {meta[spec_key]!r}, "
            f"expected {expected!r}"
        )

    def test_search_mode_default_mode_carries_choices(self):
        """SearchModeConfig.default_mode must carry choices metadata."""
        fields = {f.name: f for f in dataclasses.fields(SearchModeConfig)}
        meta = fields["default_mode"].metadata
        assert "choices" in meta, (
            "SearchModeConfig.default_mode.metadata missing 'choices' — "
            "spec must live on the field."
        )
        assert set(meta["choices"]) == {"hybrid", "semantic", "bm25", "auto"}

    # ------------------------------------------------------------------
    # 2. No chained comparison (lo <= x <= hi) in handler bodies
    # ------------------------------------------------------------------

    def test_no_chained_bounds_in_handlers(self):
        """config_handlers.py must not contain inline chained comparisons (lo <= x <= hi).

        All validation is routed through validate_field_value / apply_config_patch.
        """
        source = self._HANDLER_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        violations: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and len(node.ops) >= 2:
                violations.append(f"line {node.lineno}: chained comparison")
        assert not violations, (
            f"Inline chained bounds check(s) found in {self._HANDLER_FILE}:\n"
            + "\n".join(violations)
            + "\nRoute validation through validate_field_value() instead."
        )

    # ------------------------------------------------------------------
    # 3. validate_field_value is imported into config_handlers
    # ------------------------------------------------------------------

    def test_validate_field_value_imported_in_handlers(self):
        """config_handlers.py must import validate_field_value from search.config."""
        source = self._HANDLER_FILE.read_text(encoding="utf-8")
        assert "validate_field_value" in source, (
            f"{self._HANDLER_FILE} does not import validate_field_value — "
            "the validation owner is not wired in."
        )

    # ------------------------------------------------------------------
    # 4. Owner (validate_field_value) exists in config.py
    # ------------------------------------------------------------------

    def test_validate_field_value_defined_in_config(self):
        """validate_field_value must be defined in search/config.py (not deleted)."""
        source = self._CONFIG_FILE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        names = {
            node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
        }
        assert "validate_field_value" in names, (
            f"validate_field_value not found in {self._CONFIG_FILE} — "
            "the validation owner was deleted."
        )
