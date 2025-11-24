# Testing Guide

## Overview

This comprehensive guide covers the testing infrastructure for the Claude Context MCP semantic search system. The project maintains a professional test suite with 38 test files (227 passing tests) organized into clear categories for effective quality assurance and continuous integration.

### Current Test Status

✅ **All tests passing** (as of 2025-11-20):

- **Unit Tests**: 82 tests passing (16 files, < 1s each)
- **Fast Integration Tests**: 77 tests passing (11 files, < 5s each)
- **Slow Integration Tests**: 67 tests passing (10 files, > 10s each)
- **Regression Tests**: 1 test (15 checks) passing
- **Test Execution Time**: Unit ~5s, Fast Integration ~2 min, Slow Integration ~10 min

## Table of Contents

1. [Test Organization](#test-organization)
2. [Running Tests](#running-tests)
3. [Test Categories](#test-categories)
4. [Fast vs Slow Test Organization](#fast-vs-slow-test-organization)
5. [Creating New Tests](#creating-new-tests)
6. [Test Isolation and Production Directory Protection](#test-isolation-and-production-directory-protection)
7. [Coverage Requirements](#coverage-requirements)
8. [Pre-commit Testing](#pre-commit-testing)
9. [Debugging Failed Tests](#debugging-failed-tests)
10. [Continuous Integration](#continuous-integration)

## Test Organization

### Directory Structure

```
tests/
├── __init__.py               # Package initialization
├── conftest.py               # Global pytest configuration
├── README.md                 # Detailed test documentation (407 lines)
├── fixtures/                 # Test fixtures and mocks
│   ├── __init__.py
│   ├── installation_mocks.py # Installation testing mocks
│   └── sample_code.py        # Sample code for testing
├── test_data/                # Test datasets and sample projects
│   ├── glsl_project/         # GLSL shader samples
│   ├── multi_language/       # Multi-language test files
│   └── python_project/       # Python project samples
├── unit/                     # Unit tests (16 files, 82 tests)
│   ├── test_bm25_index.py    # BM25 index functionality
│   ├── test_bm25_population.py # BM25 document population
│   ├── test_embedder.py      # Embedding generation
│   ├── test_evaluation.py    # Evaluation framework components
│   ├── test_hybrid_search.py # Hybrid search logic
│   ├── test_import_resolution.py # Import-based call graph resolution (26 tests)
│   ├── test_incremental_indexer.py # Incremental indexing
│   ├── test_mcp_server.py    # MCP server tools
│   ├── test_merkle.py        # Merkle tree functionality
│   ├── test_model_selection.py # Multi-model support (Gemma/BGE-M3)
│   ├── test_multi_language.py # Multi-language parsing
│   ├── test_reranker.py      # RRF reranking algorithm
│   ├── test_search_config.py # Search configuration
│   ├── test_token_efficiency.py # Token efficiency evaluation
│   └── test_tree_sitter.py   # Tree-sitter parsing
├── fast_integration/         # Fast integration tests (11 files, 77 tests, < 5s each)
│   ├── test_complete_workflow.py # End-to-end workflow
│   ├── test_cuda_detection.py # GPU/CUDA detection
│   ├── test_encoding_validation.py # Text encoding validation
│   ├── test_glsl_chunking.py # GLSL chunking validation
│   ├── test_import_resolution_integration.py # Import resolution end-to-end (11 tests)
│   ├── test_installation.py  # Installation verification
│   ├── test_installation_flow.py # Installation workflow
│   ├── test_mcp_project_management.py # MCP project management
│   ├── test_model_switching.py # Model switching (Gemma/BGE-M3)
│   ├── test_token_efficiency_workflow.py # Token efficiency workflow
│   └── test_tree_sitter_*.py # Tree-sitter parsing tests
├── slow_integration/         # Slow integration tests (10 files, 67 tests, > 10s each)
│   ├── helpers/              # Test helper utilities
│   │   ├── __init__.py
│   │   ├── check_auth.py     # Authentication validation
│   │   └── run_hybrid_tests.py # Hybrid search test runner
│   ├── test_auto_reindex.py  # Auto-reindexing functionality
│   ├── test_direct_indexing.py # Direct indexing tests
│   ├── test_full_flow.py     # Complete search workflow
│   ├── test_glsl_advanced.py # Advanced GLSL features
│   ├── test_hybrid_search_integration.py # Hybrid search integration
│   ├── test_incremental_indexing.py # Incremental indexing
│   ├── test_mcp_indexing.py  # MCP indexing workflow
│   ├── test_multi_hop_flow.py # Multi-hop semantic search
│   ├── test_relationship_extraction_integration.py # Code relationship extraction
│   ├── test_semantic_search.py # End-to-end semantic search
│   └── test_system.py        # System integration tests
└── regression/               # Regression tests (1 file, 15 checks)
    └── test_mcp_configuration.ps1 # MCP config validation (PowerShell)
```

### Design Principles

- **Separation of Concerns**: Unit tests focus on individual components, integration tests verify interactions
- **Professional Organization**: Clear categorization improves maintainability and test discovery
- **Comprehensive Coverage**: All major components and workflows have corresponding tests
- **Realistic Test Data**: Sample projects mirror real-world usage patterns

## Running Tests

### Basic Test Execution

```bash
# Run all tests (38 files, 227 tests)
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with brief output
pytest tests/ -q

# Stop on first failure
pytest tests/ -x
```

### Category-Specific Testing

```bash
# Unit tests only (16 files, 82 tests, < 1s each) - Fast component testing
pytest tests/unit/

# Fast integration tests only (11 files, 77 tests, < 5s each) - Quick workflow validation
pytest tests/fast_integration/

# Slow integration tests only (10 files, 67 tests, > 10s each) - Comprehensive workflow validation
pytest tests/slow_integration/

# All integration tests (21 files, 144 tests)
pytest tests/fast_integration/ tests/slow_integration/

# Regression tests (PowerShell, 1 file, 15 checks)
tests\regression\test_mcp_configuration.ps1

# Specific test files
pytest tests/unit/test_bm25_index.py
pytest tests/fast_integration/test_complete_workflow.py
pytest tests/slow_integration/test_full_flow.py
```

### Interactive Menu Testing

```bash
# Launch interactive menu
start_mcp_server.bat

# Navigate: Advanced Options (6) → Testing Options
# - Option 1: Start Server in Debug Mode
# - Option 2: Run Unit Tests
# - Option 3: Run Integration Tests
# - Option 4: Run Regression Tests
# - Option 5: Back to Main Menu
```

### Pattern-Based Testing

```bash
# Test specific functionality
pytest tests/ -k "bm25"
pytest tests/ -k "hybrid and not slow"
pytest tests/ -k "installation"

# Test specific components
pytest tests/unit/test_hybrid_search.py tests/integration/test_hybrid_search_integration.py
```

### Coverage Testing

```bash
# Run with coverage report
pytest tests/ --cov=. --cov-report=html

# Coverage with specific threshold
pytest tests/ --cov=. --cov-fail-under=80

# Terminal coverage report
pytest tests/ --cov=. --cov-report=term-missing
```

### Performance and Debugging

```bash
# Run last failed tests first
pytest tests/ --lf

# Show detailed failure information
pytest tests/ --tb=long

# Run tests in parallel (if pytest-xdist installed)
pytest tests/ -n auto

# Time the slowest tests
pytest tests/ --durations=10
```

## Test Categories

### Unit Tests (16 files, 82 tests)

**Purpose**: Test individual components in isolation with mocked dependencies.

**Key Areas**:

- **Search Components**: BM25 indexing, hybrid search algorithms, reranking
- **Language Support**: Tree-sitter parsing, multi-language chunking
- **Model Support**: Multi-model configuration (Gemma/BGE-M3), model selection
- **Core Infrastructure**: Merkle trees, incremental indexing, search configuration
- **Evaluation Framework**: Token efficiency measurement, evaluation components
- **MCP Integration**: Server tools, import validation
- **Call Graph Resolution**: Import-based resolution (`ImportResolver`), type annotations (`TypeResolver`), assignment tracking (`AssignmentTracker`) - v0.5.12-v0.5.16

**Characteristics**:

- Very fast execution (< 1 second per test)
- Isolated from external dependencies
- Extensive use of mocks and fixtures
- High code coverage targets (>90%)

### Fast Integration Tests (11 files, 77 tests)

**Purpose**: Verify component interactions with quick feedback cycles for CI/CD.

**Key Areas**:

- **Quick Workflows**: End-to-end workflow validation, installation verification
- **System Integration**: CUDA detection, encoding validation
- **MCP Server**: Project management, basic indexing workflows
- **Model Switching**: Embedding generation with Gemma and BGE-M3
- **Language-Specific**: GLSL chunking validation, tree-sitter parsing
- **Performance**: Token efficiency workflows, import resolution integration

**Characteristics**:

- Fast execution (< 5 seconds per test)
- Real component interactions with mocked slow operations
- File system operations (using temporary directories)
- Ideal for CI fast feedback loops

### Slow Integration Tests (10 files, 67 tests)

**Purpose**: Comprehensive end-to-end validation of complete workflows.

**Key Areas**:

- **Complete Workflows**: Full indexing and search processes with real embeddings
- **Advanced Features**: Multi-hop search, hybrid search integration, auto-reindexing
- **Code Relationships**: Phase 3 relationship extraction and call graph analysis
- **System Tests**: Complete system integration, semantic search end-to-end
- **Performance**: Large codebase performance testing, incremental indexing
- **GLSL Advanced**: Advanced GLSL shader processing features

**Characteristics**:

- Longer execution time (> 10 seconds per test, some minutes)
- Real component interactions without mocking
- File system and potentially network operations
- Comprehensive workflow validation
- Marked with `@pytest.mark.slow` decorator

### Regression Tests (1 file, 15 checks)

**Purpose**: Prevent previously fixed bugs from reoccurring and validate system configuration integrity.

**Key Areas**:

- **MCP Configuration**: Validates `.claude.json` structure and required fields
  - Checks for required 'args' and 'env' fields
  - Validates PYTHONPATH and PYTHONUNBUFFERED environment variables
  - Ensures correct Python executable paths
  - Verifies working directory configuration
- **Configuration Integrity**: Checks environment variables and paths
- **Deployment Validation**: Pre-deployment configuration checks

**Characteristics**:

- Standalone PowerShell scripts
- Fast execution (< 5 seconds)
- No Python dependencies required
- Can be run independently of pytest
- Validates system state and configuration

**When to Add Regression Tests**:

- Critical bug was fixed and you want to prevent it from reoccurring
- System configuration structure has changed
- Need to validate batch/PowerShell scripts work correctly
- Pre-deployment checks for configuration integrity

## Fast vs Slow Test Organization

### 3-Tier Test Organization

The test suite uses a 3-tier system optimized for CI/CD performance:

| Tier | Location | Count | Execution Time | Purpose |
|------|----------|-------|----------------|---------|
| **Unit** | `tests/unit/` | 82 tests | < 1s per test | Component isolation testing |
| **Fast Integration** | `tests/fast_integration/` | 77 tests | < 5s per test | Quick workflow validation |
| **Slow Integration** | `tests/slow_integration/` | 67 tests | > 10s per test | Comprehensive end-to-end |

### Slow Test Marker

All slow integration tests are marked with the `@pytest.mark.slow` decorator:

```python
import pytest

@pytest.mark.slow
def test_full_indexing_workflow(tmp_path):
    """Complete indexing workflow with real embeddings."""
    # Test implementation...

@pytest.mark.slow
class TestComprehensiveSearch:
    """Comprehensive search integration tests."""

    def test_multi_hop_search(self):
        """Test multi-hop semantic search."""
        # Test implementation...
```

**Benefits**:
- Skip slow tests during development: `pytest tests/ -m "not slow"`
- Run only slow tests for comprehensive validation: `pytest tests/ -m slow`
- Separate fast CI pipeline from comprehensive nightly builds

### CI/CD Optimization Strategy

**Fast CI Pipeline** (< 3 minutes):
```bash
# Run unit + fast integration only
pytest tests/unit/ tests/fast_integration/ --cov=. --cov-fail-under=75
```

**Comprehensive CI Pipeline** (10-15 minutes):
```bash
# Run all tests including slow integration
pytest tests/ --cov=. --cov-fail-under=80
```

**Development Workflow**:
```bash
# Quick validation during development (< 3 min)
pytest tests/unit/ tests/fast_integration/ -x

# Pre-commit validation (< 5 min)
pytest tests/ -m "not slow" -v

# Full validation before PR (10-15 min)
pytest tests/ -v
```

### When to Add Tests to Each Tier

**Unit Tests** (`tests/unit/`):
- Testing individual functions, classes, or modules
- All external dependencies mocked
- No file system operations (or using in-memory alternatives)
- No network calls
- Execution time < 1 second

**Fast Integration Tests** (`tests/fast_integration/`):
- Quick end-to-end workflows with mocked slow operations
- File system operations using `tmp_path` fixture
- Mocked model loading (avoid downloading 4GB+ models)
- Basic MCP server operations
- System integration checks (CUDA detection, encoding validation)
- Execution time < 5 seconds

**Slow Integration Tests** (`tests/slow_integration/`):
- Complete workflows with real embeddings and models
- Large codebase indexing and search
- Multi-hop search, hybrid search with real data
- Performance benchmarking
- Comprehensive relationship extraction
- Execution time > 10 seconds (mark with `@pytest.mark.slow`)

### Test Fixtures (tests/fixtures/)

**Purpose**: Provide reusable test data and mocks.

**Components**:

- **installation_mocks.py**: Mock components for installation testing
- **sample_code.py**: Comprehensive sample codebase with realistic patterns
- **Shared fixtures**: Common test data and configuration

### Test Data (tests/test_data/)

**Purpose**: Sample projects for realistic testing scenarios.

**Projects**:

- **python_project/**: Python codebase with various architectural patterns
- **multi_language/**: Files in multiple programming languages
- **glsl_project/**: GLSL shader files for graphics programming validation

## Creating New Tests

### Test Naming Convention

```python
# Test files
test_<component>.py

# Test classes
class Test<ComponentName>:

# Test methods
def test_<specific_behavior>(self):
```

### Example Test Structure

```python
"""
tests/unit/test_new_component.py
"""
import pytest
from unittest.mock import Mock, patch

from your_module import NewComponent


class TestNewComponent:
    """Test cases for NewComponent."""

    @pytest.fixture
    def component(self):
        """Create a test instance of NewComponent."""
        return NewComponent(config={'test': True})

    def test_basic_functionality(self, component):
        """Test basic operation."""
        # Arrange
        input_data = "test input"
        expected_output = "expected result"

        # Act
        result = component.process(input_data)

        # Assert
        assert result == expected_output

    def test_error_handling(self, component):
        """Test error conditions."""
        with pytest.raises(ValueError, match="Invalid input"):
            component.process(None)

    def test_edge_cases(self, component):
        """Test boundary conditions."""
        # Test empty input
        assert component.process("") == ""

        # Test large input
        large_input = "x" * 10000
        result = component.process(large_input)
        assert len(result) > 0

    @patch('your_module.external_dependency')
    def test_mocked_dependency(self, mock_dependency, component):
        """Test with mocked external dependency."""
        # Arrange
        mock_dependency.return_value = "mocked result"

        # Act
        result = component.process_with_dependency("input")

        # Assert
        assert result == "mocked result"
        mock_dependency.assert_called_once_with("input")
```

### Integration Test Example

```python
"""
tests/integration/test_new_workflow.py
"""
import pytest
import tempfile
from pathlib import Path

from your_module import WorkflowManager


class TestNewWorkflow:
    """Integration tests for complete workflow."""

    @pytest.fixture
    def temp_project(self):
        """Create temporary project structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_path = Path(temp_dir) / "test_project"
            project_path.mkdir()

            # Create sample files
            (project_path / "main.py").write_text("print('hello')")
            (project_path / "config.json").write_text('{"setting": "value"}')

            yield project_path

    def test_complete_workflow(self, temp_project):
        """Test end-to-end workflow."""
        # Arrange
        manager = WorkflowManager()

        # Act
        result = manager.process_project(temp_project)

        # Assert
        assert result.success is True
        assert len(result.processed_files) == 2
        assert result.errors == []
```

### Guidelines for New Tests

1. **Use descriptive test names** that explain the behavior being tested
2. **Follow AAA pattern**: Arrange, Act, Assert
3. **One assertion per concept** - avoid testing multiple unrelated things
4. **Use fixtures** for common setup and teardown
5. **Mock external dependencies** in unit tests
6. **Test both success and failure paths**
7. **Include edge cases and boundary conditions**
8. **Use temporary directories** for file system operations

### Best Practices from Recent Fixes (2025-01-10)

**Critical lessons learned from recent test fixes:**

1. **Always mock model loading**: Never let tests download 4GB+ models

   ```python
   from unittest.mock import Mock, patch

   @patch('embeddings.embedder.SentenceTransformer')
   def test_with_mocked_model(mock_transformer):
       mock_model = Mock()
       mock_model.encode.return_value = np.random.randn(768).astype('float32')
       mock_transformer.return_value = mock_model
       # Test logic here
   ```

2. **Use subset validation for metadata**: Don't assume exact field matches

   ```python
   # Bad: Exact equality fails when BM25 adds extra fields
   assert meta == expected

   # Good: Subset validation
   for key, value in expected.items():
       assert key in meta, f"Expected key '{key}' not found"
       assert meta[key] == value
   ```

3. **Import Mock explicitly**: Don't rely on it being available

   ```python
   from unittest.mock import Mock, patch  # Always import explicitly
   ```

4. **Verify test data accuracy**: Ensure fixture values match actual behavior

   ```python
   # Update test assertions to match actual implementation
   assert env.disk_space_gb == 0.5  # Not 1.0 for low disk test
   ```

5. **Add public methods for testing**: Don't test private methods directly

   ```python
   # Added public load() method to CodeIndexManager for test access
   def load(self) -> bool:
       """Public method for loading index (used by tests)."""
       if self._index is not None and len(self._chunk_ids) > 0:
           return True
       # Load logic here
   ```

6. **Mock at the right level**: Mock external dependencies, not internal logic

   ```python
   # Mock SentenceTransformer to avoid downloads
   @patch('embeddings.embedder.SentenceTransformer')
   ```

7. **Test error messages flexibly**: Accept reasonable variations

   ```python
   # Allow multiple acceptable error messages
   assert any(msg in str(exc.value) for msg in [
       "Project directory not found",
       "Invalid project path"
   ])
   ```

8. **Create regression tests for bugs**: Prevent fixed issues from reoccurring
   - MCP configuration validation test created after fixing missing 'args'/'env' fields
   - 15 checks ensure configuration integrity

## Test Isolation and Production Directory Protection

### Overview

**CRITICAL**: All tests MUST use isolated temporary directories to prevent production directory pollution. Tests that write to `~/.claude_code_search` in the user's home directory will cause:

- Conflicts with production index data
- Test artifacts persisting after test completion
- Unreliable test results due to shared state
- Data corruption in production usage

### Production Directory Structure

The following directories are production-only and MUST NOT be accessed by tests:

```
~/.claude_code_search/
├── graphs/                  # CodeGraphStorage data
├── merkle/                  # SnapshotManager data
│   └── *_metadata.json     # Merkle tree snapshots
└── projects/               # Project-specific indices
    └── project_name_*/     # Per-project storage
```

### Required Isolation Practices

#### 1. Always Use `tmp_path` Fixture

```python
def test_with_graph_storage(tmp_path):
    """Correct: Use tmp_path for isolated testing."""
    from graph.graph_storage import CodeGraphStorage

    # Create storage in temporary directory
    storage_dir = tmp_path / "graphs"
    graph = CodeGraphStorage("test_project", storage_dir=storage_dir)

    # Test logic here
    # Cleanup is automatic via pytest's tmp_path
```

**Bad Example (Production Pollution)**:
```python
def test_with_graph_storage_bad():
    """WRONG: Creates data in production directory."""
    from graph.graph_storage import CodeGraphStorage

    # ❌ No storage_dir - defaults to ~/.claude_code_search/graphs
    graph = CodeGraphStorage("test_project")
```

#### 2. Use Provided Fixtures

The test suite provides reusable fixtures in `tests/conftest.py`:

```python
@pytest.fixture
def graph_storage(tmp_path: Path):
    """Isolated CodeGraphStorage fixture."""
    # Use this fixture instead of creating CodeGraphStorage manually

@pytest.fixture
def snapshot_manager(tmp_path: Path):
    """Isolated SnapshotManager fixture."""
    # Use this fixture instead of creating SnapshotManager manually
```

**Usage Example**:
```python
def test_with_fixture(graph_storage):
    """Use provided fixtures for automatic isolation."""
    # graph_storage is already configured with tmp_path
    graph_storage.add_node(
        chunk_id="test.py:1-10:function:test",
        name="test",
        chunk_type="function",
        file_path="test.py"
    )
    # Cleanup is automatic
```

#### 3. Mock Production Components in Unit Tests

For unit tests, mock components that would access production directories:

```python
from unittest.mock import Mock, patch

def test_initialization_with_defaults(tmp_path):
    """Mock SnapshotManager to prevent production access."""
    with patch("search.incremental_indexer.SnapshotManager") as mock_snapshot_class:
        # Configure mock to use temp directory
        mock_snapshot_instance = Mock()
        mock_snapshot_instance.storage_dir = tmp_path / "merkle"
        mock_snapshot_class.return_value = mock_snapshot_instance

        # Test logic here - no production pollution
```

#### 4. Provide Explicit Paths for Integration Tests

Integration tests should provide explicit temporary paths:

```python
def test_full_indexing_workflow(tmp_path):
    """Integration test with explicit temporary paths."""
    from search.incremental_indexer import IncrementalIndexer
    from merkle.snapshot_manager import SnapshotManager

    # Create components with temporary storage
    snapshot_manager = SnapshotManager(storage_dir=str(tmp_path / "merkle"))
    indexer = IncrementalIndexer(snapshot_manager=snapshot_manager)

    # Test logic here
```

### Common Violations and Fixes

| Violation | Problem | Fix |
|-----------|---------|-----|
| `CodeGraphStorage("test_project")` | No `storage_dir` → writes to `~/.claude_code_search/graphs` | Add `storage_dir=tmp_path / "graphs"` |
| `SnapshotManager()` | No `storage_dir` → writes to `~/.claude_code_search/merkle` | Add `storage_dir=str(tmp_path / "merkle")` |
| `IncrementalIndexer()` | Creates default SnapshotManager → production pollution | Provide explicit `snapshot_manager` instance or mock |
| Missing `tmp_path` parameter | Can't create isolated directories | Add `tmp_path` to test function signature |

### Validation Checklist

Before committing new tests, verify:

- [ ] Test function has `tmp_path` parameter
- [ ] All storage components use `tmp_path` subdirectories
- [ ] No hardcoded paths to `~/.claude_code_search`
- [ ] Fixtures used instead of manual instantiation
- [ ] Unit tests mock production components
- [ ] Test cleanup is automatic (via `tmp_path` or teardown)

### Verification Command

Run this command to detect production directory access:

```bash
# Run tests and check for production directory artifacts
pytest tests/unit/ tests/fast_integration/ -v
ls -la ~/.claude_code_search/graphs/
ls -la ~/.claude_code_search/merkle/

# Should see: "No such file or directory" (good!)
# If you see test artifacts, tests are polluting production
```

### Related Resources

- **Fixture Definitions**: `tests/conftest.py` lines 261-302
- **Example Fixes**:
  - `tests/fast_integration/test_type_annotation_integration.py` (lines 26, 290)
  - `tests/unit/test_incremental_indexer.py` (line 119)
  - `tests/slow_integration/test_direct_indexing.py` (line 117)

## Coverage Requirements

### Target Coverage by Component

| Component | Target Coverage | Priority |
|-----------|----------------|----------|
| **Core search logic** | >90% | Critical |
| **MCP server tools** | >85% | High |
| **Language parsing** | >85% | High |
| **Evaluation framework** | >80% | Medium |
| **Error handling** | >75% | Medium |
| **Utility functions** | >70% | Low |

### Generating Coverage Reports

```bash
# HTML coverage report (recommended)
pytest tests/ --cov=. --cov-report=html
# View: htmlcov/index.html

# Terminal coverage report
pytest tests/ --cov=. --cov-report=term-missing

# XML coverage report (for CI)
pytest tests/ --cov=. --cov-report=xml

# Fail if coverage below threshold
pytest tests/ --cov=. --cov-fail-under=80
```

### Coverage Analysis

```bash
# Show missing lines
pytest tests/ --cov=. --cov-report=term-missing

# Coverage for specific modules
pytest tests/ --cov=mcp_server --cov=search --cov-report=html

# Branch coverage (more comprehensive)
pytest tests/ --cov=. --cov-branch --cov-report=html
```

## Pre-commit Testing

### Quick Validation Checklist

```bash
# 1. Run fast tests first (unit + fast integration, < 3 min)
pytest tests/unit/ tests/fast_integration/ -q

# 2. Run specific feature tests
pytest tests/unit/test_hybrid_search.py tests/slow_integration/test_hybrid_search_integration.py

# 3. Fast test suite with coverage (skip slow tests)
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75

# 4. Full test suite with coverage (includes slow tests, ~15 min)
pytest tests/ --cov=. --cov-fail-under=75
```

### Automated Pre-commit Hook Example

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "Running pre-commit tests..."

# Fast unit tests
echo "1. Running unit tests..."
pytest tests/unit/ -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ Unit tests failed!"
    exit 1
fi

# Fast integration tests
echo "2. Running fast integration tests..."
pytest tests/fast_integration/ -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ Fast integration tests failed!"
    exit 1
fi

# Coverage check (excluding slow tests for speed)
echo "3. Checking coverage..."
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75 -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ Coverage below threshold!"
    exit 1
fi

echo "✅ All pre-commit tests passed (slow tests skipped)!"
echo "💡 Run 'pytest tests/' for full validation including slow tests"
```

## Debugging Failed Tests

### Common Debugging Commands

```bash
# Run with detailed output
pytest tests/failing_test.py -v --tb=long

# Drop into debugger on failure
pytest tests/failing_test.py --pdb

# Show local variables in traceback
pytest tests/failing_test.py --tb=auto -vvv

# Run only failed tests from last run
pytest tests/ --lf

# Show output from print statements
pytest tests/failing_test.py -s
```

### Debugging Strategies

#### 1. Import Errors

```bash
# Test imports specifically
pytest tests/unit/test_imports.py -v

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify module structure
python -c "from mcp_server import server; print('Import successful')"
```

#### 2. CUDA/GPU Issues

```bash
# Test CUDA detection
pytest tests/integration/test_cuda_detection.py -v

# Force CPU mode
pytest tests/ --cpu-only

# Check GPU availability
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

#### 3. File System Issues

```bash
# Check permissions
pytest tests/integration/test_encoding_validation.py -v

# Use temporary directories
pytest tests/ --basetemp=/tmp/pytest_temp
```

#### 4. Mock-related Issues

```bash
# Run without mocks (integration focus)
pytest tests/integration/ -v

# Debug mock calls
pytest tests/unit/test_component.py -v -s
```

#### 5. Regression Test Issues

```powershell
# Run MCP configuration validation
tests\regression\test_mcp_configuration.ps1

# Test specific config file
tests\regression\test_mcp_configuration.ps1 -ConfigPath "C:\path\to\.claude.json"

# Check Claude Code configuration
.venv\Scripts\python.exe scripts\manual_configure.py --validate-only
```

**Common regression test failures:**

- Missing 'args' or 'env' fields in `.claude.json`
- Incorrect PYTHONPATH configuration
- Invalid Python executable paths
- Wrong working directory in MCP config

### Troubleshooting Checklist

- [ ] **Environment**: Virtual environment activated and dependencies installed
- [ ] **Imports**: All required modules can be imported
- [ ] **Permissions**: Read/write access to test directories
- [ ] **GPU**: CUDA drivers and PyTorch compatibility
- [ ] **Memory**: Sufficient RAM for test operations
- [ ] **Network**: Internet access for model downloads (if needed)
- [ ] **MCP Config**: Valid `.claude.json` with required fields (run regression tests)

## Continuous Integration

### CI-Friendly Test Commands

```bash
# Fast CI pipeline (unit + fast integration, < 3 min)
pytest tests/unit/ tests/fast_integration/ --cov=. --cov-fail-under=75

# Fast test run (skip slow tests using marker)
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75

# Full test suite with XML output (includes slow tests, ~15 min)
pytest tests/ --cov=. --cov-report=xml --junit-xml=test-results.xml

# Parallel execution (fast tests only)
pytest tests/unit/ tests/fast_integration/ -n auto --dist=loadfile

# Parallel execution (all tests)
pytest tests/ -n auto --dist=loadfile
```

### CI Pipeline Strategies

**Fast Feedback Pipeline** (runs on every commit, < 3 min):
- Unit tests (82 tests, ~5s)
- Fast integration tests (77 tests, ~2 min)
- Coverage check with 75% threshold
- **Total time**: ~3 minutes
- **Purpose**: Quick feedback for developers

**Comprehensive Pipeline** (runs on PR/nightly, ~15 min):
- All unit tests
- All fast integration tests
- All slow integration tests (67 tests)
- Coverage check with 80% threshold
- **Total time**: ~15 minutes
- **Purpose**: Complete validation before merge

### CI Configuration Examples

#### Fast Feedback Workflow

```yaml
# .github/workflows/fast-tests.yml
name: Fast Tests

on: [push]

jobs:
  fast-tests:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run unit tests
      run: pytest tests/unit/ --cov=. --cov-report=xml -v

    - name: Run fast integration tests
      run: pytest tests/fast_integration/ --cov=. --cov-append --cov-report=xml -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: fast-tests
```

#### Comprehensive Validation Workflow

```yaml
# .github/workflows/comprehensive-tests.yml
name: Comprehensive Tests

on:
  pull_request:
  schedule:
    - cron: '0 2 * * *'  # Run nightly at 2 AM

jobs:
  comprehensive-tests:
    runs-on: windows-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v3
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov

    - name: Run all tests
      run: pytest tests/ --cov=. --cov-report=xml --junit-xml=test-results.xml -v

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: comprehensive-tests

    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: test-results.xml
```

### Performance Testing in CI

```bash
# Quick performance validation (fast integration)
pytest tests/fast_integration/test_token_efficiency_workflow.py --benchmark-only

# Comprehensive performance testing (slow integration)
pytest tests/slow_integration/test_full_flow.py::TestFullSearchFlow::test_performance_with_large_codebase -v

# Memory usage testing (all tests)
pytest tests/ --memory-profile

# Time-limited testing (fast tests only)
timeout 180 pytest tests/unit/ tests/fast_integration/

# Time-limited testing (all tests)
timeout 900 pytest tests/
```

## Best Practices Summary

### For Test Writers

1. **Write tests first** (TDD approach when possible)
2. **Use descriptive names** that explain the behavior
3. **Keep tests simple** and focused on one concept
4. **Mock external dependencies** in unit tests (especially model loading)
5. **Use real interactions** in integration tests
6. **Test both success and failure paths**
7. **Include edge cases** and boundary conditions
8. **Use subset validation for metadata** (don't assume exact matches)
9. **Import Mock explicitly** from unittest.mock
10. **Create regression tests for critical bugs**

### For Test Maintenance

1. **Run tests frequently** during development
2. **Keep test data current** with code changes
3. **Refactor tests** when refactoring production code
4. **Monitor coverage trends** over time
5. **Update fixtures** when APIs change
6. **Document complex test scenarios**
7. **Review recent fixes** for lessons learned
8. **Update regression tests** when configuration changes

### For CI/CD

1. **Run fast tests first** for quick feedback
2. **Use parallel execution** for speed
3. **Generate coverage reports** for analysis
4. **Fail fast** on critical test failures
5. **Archive test results** for historical analysis
6. **Include regression tests** in CI pipeline
7. **Validate configuration** before deployment

### Recent Test Improvements (2025-11-19)

**All 389 tests now passing:**

- ✅ Fixed BM25 metadata handling with subset validation
- ✅ Fixed CUDA detection disk space assertions
- ✅ Added proper Mock imports to all test files
- ✅ Added public load() method to CodeIndexManager
- ✅ Added SentenceTransformer mocking to prevent downloads
- ✅ Created comprehensive MCP configuration regression test (15 checks)
- ✅ **Phase 4 Import Resolution Tests** (v0.5.15):
  - `test_import_resolution.py` - 26 unit tests for import extraction and resolution
  - `test_import_resolution_integration.py` - 11 integration tests for end-to-end import resolution

This comprehensive testing guide ensures high-quality, maintainable code through systematic testing practices and clear documentation.
