# Test Suite Documentation

This directory contains comprehensive tests for the Claude Context MCP semantic search system.

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
│   ├── test_multi_language.py # Multi-language parsing
│   ├── test_reranker.py      # RRF reranking algorithm
│   ├── test_search_config.py # Search configuration
│   ├── test_token_efficiency.py # Token efficiency evaluation
│   └── test_tree_sitter.py   # Tree-sitter parsing
└── integration/              # Integration tests (23 files)
    ├── quick_auth_test.py    # Quick authentication test
    ├── run_hybrid_tests.py   # Hybrid search runner
    ├── test_auto_reindex.py  # Auto-reindexing functionality
    ├── test_complete_workflow.py # End-to-end workflow
    ├── test_cuda_detection.py # GPU/CUDA detection
    ├── test_direct_indexing.py # Direct indexing tests
    ├── test_encoding_validation.py # Text encoding validation
    ├── test_full_flow.py     # Complete indexing flow
    ├── test_glsl_*.py        # GLSL-specific integration tests
    ├── test_hf_access.py     # Hugging Face access
    ├── test_hybrid_search_integration.py # Hybrid search integration
    ├── test_incremental_indexing.py # Incremental indexing flow
    ├── test_installation.py  # Installation verification
    ├── test_installation_flow.py # Installation workflow
    ├── test_mcp_*.py         # MCP server integration tests
    ├── test_semantic_search.py # End-to-end semantic search
    ├── test_system.py        # System-level tests
    └── test_token_efficiency_workflow.py # Token efficiency workflow
```

## Running Tests

### Using Pytest Directly

```bash
# Run all tests
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

# GLSL support
pytest tests/integration/test_glsl_*
```

## Test Categories

### Unit Tests
Fast tests that validate individual components in isolation:

- **Search Components**: BM25 indexing, hybrid search, reranking algorithms
- **Language Support**: Tree-sitter parsing, multi-language chunking
- **Core Infrastructure**: Merkle trees, incremental indexing, search configuration
- **Evaluation**: Token efficiency measurement, evaluation framework
- **MCP Integration**: Server tools, import validation

### Integration Tests
Comprehensive tests that verify component interactions and full workflows:

- **End-to-End Workflows**: Complete indexing and search flows
- **System Integration**: Installation, CUDA detection, encoding validation
- **MCP Server**: Full server functionality, project storage, indexing workflows
- **Language-Specific**: GLSL shader processing, multi-language projects
- **Performance**: Token efficiency workflows, benchmark validation

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
```

## Test Environment

### Requirements
- Python 3.11+
- pytest
- pytest-cov (for coverage)
- All project dependencies in requirements.txt

### Virtual Environment Setup
```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install pytest pytest-cov
```

## Troubleshooting

### Common Issues
- **Import errors**: Ensure project root is in PYTHONPATH
- **CUDA tests failing**: Install appropriate PyTorch version for your system
- **Slow tests**: Use `-x` flag to stop on first failure for debugging
- **Permission errors**: Check file permissions on test_data files

### Performance Tips
- Run unit tests first for quick feedback
- Use `-k` to run specific test patterns
- Mock expensive operations in unit tests
- Use temporary directories for file operations