"""Unit tests for project persistence module."""

import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_server.project_persistence import (
    clear_project_selection,
    get_project_display_name,
    get_selection_file_path,
    get_selection_for_display,
    load_project_selection,
    save_project_selection,
)


@pytest.fixture
def temp_storage_dir(tmp_path):
    """Create a temporary storage directory."""
    storage_dir = tmp_path / ".claude_code_search"
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


@pytest.fixture
def mock_storage_env(temp_storage_dir, monkeypatch):
    """Mock the storage directory environment variable."""
    monkeypatch.setenv("CODE_SEARCH_STORAGE", str(temp_storage_dir))
    yield temp_storage_dir


class TestGetSelectionFilePath:
    """Tests for get_selection_file_path()."""

    def test_default_path(self):
        """Test default path uses home directory."""
        path = get_selection_file_path()
        assert path.name == "project_selection.json"
        assert ".claude_code_search" in str(path)

    def test_env_var_override(self, mock_storage_env):
        """Test environment variable overrides default path."""
        path = get_selection_file_path()
        assert path.parent == mock_storage_env
        assert path.name == "project_selection.json"


class TestSaveProjectSelection:
    """Tests for save_project_selection()."""

    def test_save_success(self, mock_storage_env):
        """Test successful save operation."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        result = save_project_selection(project_path)
        assert result is True

        # Verify file was created
        selection_file = get_selection_file_path()
        assert selection_file.exists()

    def test_save_with_model_key(self, mock_storage_env):
        """Test saving with model key."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        result = save_project_selection(project_path, model_key="bge_m3")
        assert result is True

        # Verify content
        selection_file = get_selection_file_path()
        with open(selection_file) as f:
            data = json.load(f)

        assert data["last_model_key"] == "bge_m3"

    def test_save_creates_directory(self, mock_storage_env):
        """Test save creates parent directory if it doesn't exist."""
        # Remove storage directory
        if mock_storage_env.exists():
            for item in mock_storage_env.iterdir():
                item.unlink()
            mock_storage_env.rmdir()

        project_path = str(Path(tempfile.gettempdir()) / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        result = save_project_selection(project_path)
        assert result is True

        # Verify directory was created
        selection_file = get_selection_file_path()
        assert selection_file.parent.exists()

        # Cleanup
        Path(project_path).rmdir()

    def test_save_content_format(self, mock_storage_env):
        """Test saved content has correct format."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        save_project_selection(project_path, model_key="qwen3")

        selection_file = get_selection_file_path()
        with open(selection_file) as f:
            data = json.load(f)

        # Verify all required fields
        assert "last_project_path" in data
        assert "last_model_key" in data
        assert "updated_at" in data

        # Verify path is resolved
        assert Path(data["last_project_path"]).is_absolute()

        # Verify timestamp format
        datetime.fromisoformat(data["updated_at"])  # Should not raise

    def test_save_handles_permission_error(self, mock_storage_env, monkeypatch):
        """Test save handles file permission errors gracefully."""

        def mock_open_error(*args, **kwargs):
            raise PermissionError("Permission denied")

        with patch("builtins.open", side_effect=mock_open_error):
            project_path = str(mock_storage_env / "test_project")
            result = save_project_selection(project_path)
            assert result is False


class TestLoadProjectSelection:
    """Tests for load_project_selection()."""

    def test_load_missing_file(self, mock_storage_env):
        """Test load with missing selection file."""
        result = load_project_selection()
        assert result is None

    def test_load_success(self, mock_storage_env):
        """Test successful load operation."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Save first
        save_project_selection(project_path, model_key="bge_m3")

        # Load
        result = load_project_selection()
        assert result is not None
        assert "last_project_path" in result
        assert result["last_model_key"] == "bge_m3"

    def test_load_invalid_json(self, mock_storage_env):
        """Test load with invalid JSON."""
        selection_file = get_selection_file_path()
        selection_file.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid JSON
        with open(selection_file, "w") as f:
            f.write("{ invalid json }")

        result = load_project_selection()
        assert result is None

    def test_load_missing_required_field(self, mock_storage_env):
        """Test load with missing required fields."""
        selection_file = get_selection_file_path()
        selection_file.parent.mkdir(parents=True, exist_ok=True)

        # Write JSON without last_project_path
        with open(selection_file, "w") as f:
            json.dump({"model_key": "test"}, f)

        result = load_project_selection()
        assert result is None

    def test_load_nonexistent_project(self, mock_storage_env):
        """Test load with project path that no longer exists."""
        # Create valid selection file with nonexistent project
        selection_file = get_selection_file_path()
        selection_file.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "last_project_path": str(mock_storage_env / "nonexistent_project"),
            "last_model_key": None,
            "updated_at": datetime.now().isoformat(),
        }

        with open(selection_file, "w") as f:
            json.dump(data, f)

        result = load_project_selection()
        assert result is None

    def test_load_handles_permission_error(self, mock_storage_env):
        """Test load handles file permission errors gracefully."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Save first
        save_project_selection(project_path)

        # Mock permission error
        def mock_open_error(*args, **kwargs):
            raise PermissionError("Permission denied")

        with patch("builtins.open", side_effect=mock_open_error):
            result = load_project_selection()
            assert result is None


class TestClearProjectSelection:
    """Tests for clear_project_selection()."""

    def test_clear_existing_file(self, mock_storage_env):
        """Test clearing existing selection file."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Save first
        save_project_selection(project_path)

        # Verify file exists
        selection_file = get_selection_file_path()
        assert selection_file.exists()

        # Clear
        result = clear_project_selection()
        assert result is True
        assert not selection_file.exists()

    def test_clear_nonexistent_file(self, mock_storage_env):
        """Test clearing when no file exists."""
        result = clear_project_selection()
        assert result is True  # Should succeed even if file doesn't exist

    def test_clear_handles_permission_error(self, mock_storage_env):
        """Test clear handles permission errors gracefully."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Save first
        save_project_selection(project_path)

        # Mock permission error
        with patch(
            "pathlib.Path.unlink", side_effect=PermissionError("Permission denied")
        ):
            result = clear_project_selection()
            assert result is False


class TestGetProjectDisplayName:
    """Tests for get_project_display_name()."""

    def test_extract_name(self):
        """Test extracting project name from path."""
        path = "/home/user/projects/my-project"
        name = get_project_display_name(path)
        assert name == "my-project"

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only path handling")
    def test_windows_path(self):
        """Test extracting name from Windows path."""
        path = "C:\\Users\\user\\projects\\my-project"
        name = get_project_display_name(path)
        assert name == "my-project"

    def test_empty_path(self):
        """Test with empty path."""
        name = get_project_display_name("")
        assert name == "None"

    def test_none_path(self):
        """Test with None path."""
        name = get_project_display_name(None)
        assert name == "None"


class TestGetSelectionForDisplay:
    """Tests for get_selection_for_display()."""

    def test_no_selection(self, mock_storage_env):
        """Test display format with no selection."""
        result = get_selection_for_display()

        assert result["name"] == "None"
        assert result["path"] == ""
        assert result["model_key"] == ""
        assert result["updated_at"] == ""
        assert result["exists"] is False

    def test_with_selection(self, mock_storage_env):
        """Test display format with existing selection."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Save selection
        save_project_selection(project_path, model_key="bge_m3")

        # Get display format
        result = get_selection_for_display()

        assert result["name"] == "test_project"
        assert result["path"] == str(Path(project_path).resolve())
        assert result["model_key"] == "bge_m3"
        assert result["updated_at"] != ""
        assert result["exists"] is True

    def test_display_all_fields_present(self, mock_storage_env):
        """Test all expected fields are present in display format."""
        result = get_selection_for_display()

        required_fields = ["name", "path", "model_key", "updated_at", "exists"]
        for field in required_fields:
            assert field in result


class TestIntegrationScenarios:
    """Integration tests for common usage scenarios."""

    def test_save_load_clear_workflow(self, mock_storage_env):
        """Test complete save -> load -> clear workflow."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Save
        assert save_project_selection(project_path, model_key="qwen3") is True

        # Load
        selection = load_project_selection()
        assert selection is not None
        assert "test_project" in selection["last_project_path"]
        assert selection["last_model_key"] == "qwen3"

        # Clear
        assert clear_project_selection() is True

        # Verify cleared
        assert load_project_selection() is None

    def test_overwrite_existing_selection(self, mock_storage_env):
        """Test saving new selection overwrites old one."""
        project1 = str(mock_storage_env / "project1")
        project2 = str(mock_storage_env / "project2")
        Path(project1).mkdir(parents=True, exist_ok=True)
        Path(project2).mkdir(parents=True, exist_ok=True)

        # Save first project
        save_project_selection(project1, model_key="bge_m3")

        # Save second project (should overwrite)
        save_project_selection(project2, model_key="qwen3")

        # Load should return second project
        selection = load_project_selection()
        assert "project2" in selection["last_project_path"]
        assert selection["last_model_key"] == "qwen3"

    def test_save_without_model_key(self, mock_storage_env):
        """Test saving without model key (None value)."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        save_project_selection(project_path)

        selection = load_project_selection()
        assert selection is not None
        assert selection["last_model_key"] is None

    def test_display_after_clear(self, mock_storage_env):
        """Test display format returns safe values after clear."""
        project_path = str(mock_storage_env / "test_project")
        Path(project_path).mkdir(parents=True, exist_ok=True)

        # Save then clear
        save_project_selection(project_path)
        clear_project_selection()

        # Display should show "None"
        result = get_selection_for_display()
        assert result["name"] == "None"
        assert result["exists"] is False
