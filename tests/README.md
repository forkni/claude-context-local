# Test Suite Documentation

This directory contains comprehensive tests for the Claude Context MCP semantic search system.

## Test Status

**Current Status**: ✅ All tests passing (as of 2025-01-10)

- **Unit Tests**: 204 tests passing
- **Integration Tests**: 147 tests passing
- **Regression Tests**: 1 test (15 checks) passing
- **Total Coverage**: Unit tests run in ~5s, Integration tests in ~13 minutes

### Recent Fixes (2025-01-10)

- ✅ Fixed BM25 metadata handling test (subset validation instead of exact equality)
- ✅ Fixed CUDA detection disk space assertion (0.5GB for low disk test)
- ✅ Added Mock import to token efficiency workflow test
- ✅ Added public load() method to CodeIndexManager
- ✅ Added SentenceTransformer mocking to auto-reindex test
- ✅ Created comprehensive MCP configuration regression test (15 checks)

## Test Structure

```
tests/
├── __init__.py               # Package initialization
├── conftest.py               # Global pytest configuration
├── README.md                 # This documentation
├── fixtures/                 # Test fixtures and mocks
│   ├── __init__.py
│   ├── installation_mocks.py # Installation testing mocks
│   └── sample_code.py        # Sample code for testing
├── test_data/                # Test datasets and sample projects
│   ├── glsl_project/         # GLSL shader samples
│   ├── multi_language/       # Multi-language test files
│   └── python_project/       # Python project samples
├── unit/                     # Unit tests (14 files)
│   ├── test_bm25_index.py    # BM25 index functionality
│   ├── test_bm25_population.py # BM25 document population
│   ├── test_evaluation.py    # Evaluation framework components
│   ├── test_hybrid_search.py # Hybrid search logic
│   ├── test_imports.py       # Import validation
│   ├── test_incremental_indexer.py # Incremental indexing
│   ├── test_mcp_server.py    # MCP server tools
│   ├── test_merkle.py        # Merkle tree functionality
│   ├── test_model_selection.py # Multi-model support (Gemma/BGE-M3)
│   ├── test_multi_language.py # Multi-language parsing
│   ├── test_reranker.py      # RRF reranking algorithm
│   ├── test_search_config.py # Search configuration
│   ├── test_token_efficiency.py # Token efficiency evaluation
│   └── test_tree_sitter.py   # Tree-sitter parsing
├── integration/              # Integration tests (22 files)
│   ├── quick_auth_test.py    # Quick authentication test
│   ├── run_hybrid_tests.py   # Hybrid search runner
│   ├── test_auto_reindex.py  # Auto-reindexing functionality
│   ├── test_complete_workflow.py # End-to-end workflow
│   ├── test_cuda_detection.py # GPU/CUDA detection
│   ├── test_direct_indexing.py # Direct indexing tests
│   ├── test_encoding_validation.py # Text encoding validation
│   ├── test_full_flow.py     # Complete indexing flow
│   ├── test_glsl_*.py        # GLSL-specific integration tests
│   ├── test_hf_access.py     # Hugging Face access
│   ├── test_hybrid_search_integration.py # Hybrid search integration
│   ├── test_incremental_indexing.py # Incremental indexing flow
│   ├── test_installation.py  # Installation verification
│   ├── test_installation_flow.py # Installation workflow
│   ├── test_mcp_*.py         # MCP server integration tests
│   ├── test_model_switching.py # Model switching (Gemma/BGE-M3)
│   ├── test_semantic_search.py # End-to-end semantic search
│   ├── test_system.py        # System-level tests
│   └── test_token_efficiency_workflow.py # Token efficiency workflow
└── regression/               # Regression tests (PowerShell/Bash scripts)
    └── test_mcp_configuration.ps1 # MCP config validation (15 checks)
```

## Running Tests

### Using Pytest Directly

```bash
# Run all tests (unit + integration)
pytest tests/

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run specific test files
pytest tests/unit/test_bm25_index.py
pytest tests/integration/test_complete_workflow.py

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Run tests matching a pattern
pytest tests/ -k "bm25"
pytest tests/ -k "hybrid and not slow"
```

### Using Interactive Menu

```bash
# Start interactive menu
start_mcp_server.bat

# Navigate to: Advanced Options (6)
# - Option 1: Start Server in Debug Mode
# - Option 2: Run Unit Tests
# - Option 3: Run Integration Tests
# - Option 4: Run Regression Tests
# - Option 5: Back to Main Menu
```

### Running Regression Tests

```powershell
# MCP configuration validation
.\tests\regression\test_mcp_configuration.ps1

# Or via interactive menu: Advanced Options → Run Regression Tests
```

### Running Specific Test Categories

```bash
# Core search functionality
pytest tests/unit/test_bm25_index.py tests/unit/test_hybrid_search.py

# MCP server functionality
pytest tests/unit/test_mcp_server.py tests/integration/test_mcp_functionality.py

# Evaluation framework
pytest tests/unit/test_evaluation.py tests/unit/test_token_efficiency.py

# Installation and setup
pytest tests/integration/test_installation.py tests/integration/test_installation_flow.py

# Multi-language support
pytest tests/unit/test_multi_language.py tests/unit/test_tree_sitter.py

# Model support (Gemma/BGE-M3)
pytest tests/unit/test_model_selection.py tests/integration/test_model_switching.py

# GLSL support
pytest tests/integration/test_glsl_*
```

## Test Categories

### Unit Tests

Fast tests that validate individual components in isolation:

- **Search Components**: BM25 indexing, hybrid search, reranking algorithms
- **Language Support**: Tree-sitter parsing, multi-language chunking
- **Model Support**: Multi-model configuration (Gemma/BGE-M3), model selection
- **Core Infrastructure**: Merkle trees, incremental indexing, search configuration
- **Evaluation**: Token efficiency measurement, evaluation framework
- **MCP Integration**: Server tools, import validation

### Integration Tests

Comprehensive tests that verify component interactions and full workflows:

- **End-to-End Workflows**: Complete indexing and search flows
- **System Integration**: Installation, CUDA detection, encoding validation
- **MCP Server**: Full server functionality, project storage, indexing workflows
- **Model Switching**: Embedding generation with Gemma and BGE-M3, model switching workflows
- **Language-Specific**: GLSL shader processing, multi-language projects
- **Performance**: Token efficiency workflows, benchmark validation

### Regression Tests

Standalone validation scripts that ensure configurations and system state remain correct. These tests prevent previously fixed bugs from reoccurring and validate system configuration integrity.

- **MCP Configuration** (`test_mcp_configuration.ps1`): Validates `.claude.json` structure and required fields (15 checks)
  - Checks for required 'args' and 'env' fields
  - Validates PYTHONPATH and PYTHONUNBUFFERED environment variables
  - Ensures correct Python executable paths
  - Verifies working directory configuration
- **Script Validation**: Ensures PowerShell/Bash scripts work correctly
- **Configuration Integrity**: Checks environment variables and paths
- **Deployment Validation**: Pre-deployment configuration checks

#### Running Regression Tests

**MCP Configuration Validation:**

```powershell
# Run from project root
.\tests\regression\test_mcp_configuration.ps1

# Test specific config file
.\tests\regression\test_mcp_configuration.ps1 -ConfigPath "C:\path\to\.claude.json"
```

**Expected Output:**

```
=== MCP Configuration Structure Test ===
[PASS] Configuration file exists
[PASS] Server has 'args' field
[PASS] Server has 'env' field
[PASS] PYTHONPATH is set in env
...
Total Tests: 15
Passed: 15
Failed: 0
```

#### When to Add Regression Tests

Add new regression tests when:

- **Bug Fix**: A critical bug was fixed and you want to prevent it from reoccurring
- **Configuration Change**: System configuration structure has changed
- **Script Validation**: Need to validate batch/PowerShell scripts work correctly
- **Deployment Validation**: Pre-deployment checks for configuration integrity

## Test Fixtures and Data

### fixtures/

- **installation_mocks.py**: Mocks for installation testing
- **sample_code.py**: Comprehensive sample codebase for testing

### test_data/

- **python_project/**: Sample Python project with various patterns
- **multi_language/**: Files in multiple programming languages
- **glsl_project/**: GLSL shader files for graphics programming tests

## Configuration

### conftest.py

Global pytest configuration including:

- Test discovery patterns
- Fixture definitions
- Path configuration
- Temporary directory management

### Key Test Patterns

#### Mocking Expensive Operations

Tests mock expensive operations for speed:

- EmbeddingGemma model loading
- FAISS index operations
- Hugging Face API calls
- Large file processing

#### Temporary Resources

Tests use temporary directories for:

- Mock project structures
- Index storage during tests
- Model cache simulation
- File system operations

## Development Workflow

### Quick Validation

```bash
# Fast unit tests only
pytest tests/unit/ -q

# Test specific functionality
pytest tests/unit/test_bm25_index.py -v
```

### Pre-commit Testing

```bash
# Full test suite with coverage
pytest tests/ --cov=. --cov-report=term-missing

# Unit tests with coverage threshold
pytest tests/unit/ --cov=. --cov-fail-under=85
```

### Debugging Failed Tests

```bash
# Run last failed tests first
pytest tests/ --lf -v

# Stop on first failure for debugging
pytest tests/ -x --tb=long
```

## Coverage Targets

Target coverage areas:

- **Core search logic**: >90%
- **MCP server tools**: >85%
- **Language parsing**: >85%
- **Evaluation framework**: >80%
- **Error handling**: >75%

Generate coverage reports:

```bash
pytest tests/ --cov=. --cov-report=html
# View: htmlcov/index.html
```

## Continuous Integration

For CI/CD pipelines:

```bash
# Fast test run (skip slow tests)
pytest tests/ -m "not slow" --cov=. --cov-fail-under=80

# Full test suite
pytest tests/ --cov=. --cov-fail-under=75
```

## Adding New Tests

### Guidelines

1. **Unit tests**: Test individual functions/classes in `tests/unit/`
2. **Integration tests**: Test component interactions in `tests/integration/`
3. **Fixtures**: Add reusable test data to `tests/fixtures/`
4. **Sample data**: Add test projects to `tests/test_data/`

### Test Naming Convention

- Test files: `test_<component>.py`
- Test classes: `Test<ComponentName>`
- Test methods: `test_<specific_behavior>`

### Example Test Structure

```python
from unittest.mock import Mock, patch

class TestNewComponent:
    """Test cases for NewComponent."""

    def test_basic_functionality(self):
        """Test basic operation."""
        pass

    def test_error_handling(self):
        """Test error conditions."""
        pass

    def test_edge_cases(self):
        """Test boundary conditions."""
        pass

    @patch('embeddings.embedder.SentenceTransformer')
    def test_with_mocked_model(self, mock_transformer):
        """Test with mocked model to avoid downloads."""
        # Mock the model to avoid downloading
        mock_model = Mock()
        mock_model.encode.return_value = np.random.randn(768).astype('float32')
        mock_transformer.return_value = mock_model

        # Test logic here
        pass
```

### Best Practices

1. **Always mock expensive operations**: Model loading, API calls, file I/O
2. **Use subset validation for metadata**: Don't assume exact field matches (BM25 adds fields)
3. **Import Mock explicitly**: `from unittest.mock import Mock, patch`
4. **Verify test data accuracy**: Ensure test fixtures match actual system behavior
5. **Add regression tests for bugs**: Prevent fixed issues from reoccurring
6. **Document test purpose**: Clear docstrings explaining what's being tested
7. **Keep tests isolated**: No shared state between tests
8. **Mock at the right level**: Mock external dependencies, not internal logic

## Test Environment

### Requirements

- Python 3.11+
- pytest
- pytest-cov (for coverage)
- All project dependencies (managed via pyproject.toml)

### Virtual Environment Setup

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install project and dependencies (editable mode)
pip install -e .

# pytest and pytest-cov are included in project dependencies
```

## Troubleshooting

### Common Issues

- **Import errors**: Ensure project root is in PYTHONPATH
- **CUDA tests failing**: Install appropriate PyTorch version for your system
- **Slow tests**: Use `-x` flag to stop on first failure for debugging
- **Permission errors**: Check file permissions on test_data files
- **Mock import errors**: Add `from unittest.mock import Mock, patch` to test files
- **Model loading in tests**: Always mock SentenceTransformer to avoid downloading large models
- **Metadata assertion failures**: Use subset validation when testing metadata (BM25 adds extra fields)
- **Index loading errors**: Ensure CodeIndexManager has public load() method available

### Performance Tips

- Run unit tests first for quick feedback
- Use `-k` to run specific test patterns
- Mock expensive operations in unit tests
- Use temporary directories for file operations
- Always mock model loading in tests (avoid 4GB+ downloads)
- Use `@patch('embeddings.embedder.SentenceTransformer')` for embedding tests
