# Testing Guide

## Overview

This comprehensive guide covers the testing infrastructure for the Claude Context MCP semantic search system. The project maintains a professional test suite with 37 test files organized into clear categories for effective quality assurance and continuous integration.

## Table of Contents

1. [Test Organization](#test-organization)
2. [Running Tests](#running-tests)
3. [Test Categories](#test-categories)
4. [Creating New Tests](#creating-new-tests)
5. [Coverage Requirements](#coverage-requirements)
6. [Pre-commit Testing](#pre-commit-testing)
7. [Debugging Failed Tests](#debugging-failed-tests)
8. [Continuous Integration](#continuous-integration)

## Test Organization

### Directory Structure

```
tests/
├── __init__.py               # Package initialization
├── conftest.py               # Global pytest configuration
├── README.md                 # Detailed test documentation (285 lines)
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
    ├── test_complete_workflow.py # End-to-end workflow
    ├── test_cuda_detection.py # GPU/CUDA detection
    ├── test_encoding_validation.py # Text encoding validation
    ├── test_glsl_*.py        # GLSL-specific integration tests
    ├── test_hybrid_search_integration.py # Hybrid search integration
    ├── test_installation.py  # Installation verification
    ├── test_mcp_*.py         # MCP server integration tests
    ├── test_semantic_search.py # End-to-end semantic search
    └── test_token_efficiency_workflow.py # Token efficiency workflow
```

### Design Principles

- **Separation of Concerns**: Unit tests focus on individual components, integration tests verify interactions
- **Professional Organization**: Clear categorization improves maintainability and test discovery
- **Comprehensive Coverage**: All major components and workflows have corresponding tests
- **Realistic Test Data**: Sample projects mirror real-world usage patterns

## Running Tests

### Basic Test Execution

```bash
# Run all tests (37 files)
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
# Unit tests only (14 files) - Fast component testing
pytest tests/unit/

# Integration tests only (23 files) - Workflow validation
pytest tests/integration/

# Specific test files
pytest tests/unit/test_bm25_index.py
pytest tests/integration/test_complete_workflow.py
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

### Unit Tests (14 files)

**Purpose**: Test individual components in isolation with mocked dependencies.

**Key Areas**:

- **Search Components**: BM25 indexing, hybrid search algorithms, reranking
- **Language Support**: Tree-sitter parsing, multi-language chunking
- **Core Infrastructure**: Merkle trees, incremental indexing, search configuration
- **Evaluation Framework**: Token efficiency measurement, evaluation components
- **MCP Integration**: Server tools, import validation

**Characteristics**:

- Fast execution (typically < 1 second per test)
- Isolated from external dependencies
- Extensive use of mocks and fixtures
- High code coverage targets (>90%)

### Integration Tests (23 files)

**Purpose**: Verify component interactions and complete workflows.

**Key Areas**:

- **End-to-End Workflows**: Complete indexing and search processes
- **System Integration**: Installation verification, CUDA detection, encoding validation
- **MCP Server**: Full server functionality, project management, indexing workflows
- **Language-Specific**: GLSL shader processing, multi-language project handling
- **Performance**: Token efficiency workflows, benchmark validation

**Characteristics**:

- Longer execution time (seconds to minutes)
- Real component interactions
- File system and network operations
- Comprehensive workflow validation

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
# 1. Run fast unit tests first
pytest tests/unit/ -q

# 2. Check import validation
pytest tests/unit/test_imports.py -v

# 3. Run specific feature tests
pytest tests/unit/test_hybrid_search.py tests/integration/test_hybrid_search_integration.py

# 4. Full test suite with coverage
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

# Import validation
echo "2. Checking imports..."
pytest tests/unit/test_imports.py -q
if [ $? -ne 0 ]; then
    echo "❌ Import validation failed!"
    exit 1
fi

# Coverage check
echo "3. Checking coverage..."
pytest tests/ --cov=. --cov-fail-under=75 -q --tb=no
if [ $? -ne 0 ]; then
    echo "❌ Coverage below threshold!"
    exit 1
fi

echo "✅ All pre-commit tests passed!"
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

### Troubleshooting Checklist

- [ ] **Environment**: Virtual environment activated and dependencies installed
- [ ] **Imports**: All required modules can be imported
- [ ] **Permissions**: Read/write access to test directories
- [ ] **GPU**: CUDA drivers and PyTorch compatibility
- [ ] **Memory**: Sufficient RAM for test operations
- [ ] **Network**: Internet access for model downloads (if needed)

## Continuous Integration

### CI-Friendly Test Commands

```bash
# Fast test run (skip slow tests)
pytest tests/ -m "not slow" --cov=. --cov-fail-under=75

# Full test suite with XML output
pytest tests/ --cov=. --cov-report=xml --junit-xml=test-results.xml

# Parallel execution
pytest tests/ -n auto --dist=loadfile
```

### CI Configuration Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
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
      run: pytest tests/unit/ --cov=. --cov-report=xml

    - name: Run integration tests
      run: pytest tests/integration/ --cov=. --cov-append --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Performance Testing in CI

```bash
# Quick performance validation
pytest tests/integration/test_token_efficiency_workflow.py --benchmark-only

# Memory usage testing
pytest tests/ --memory-profile

# Time-limited testing
timeout 300 pytest tests/
```

## Best Practices Summary

### For Test Writers

1. **Write tests first** (TDD approach when possible)
2. **Use descriptive names** that explain the behavior
3. **Keep tests simple** and focused on one concept
4. **Mock external dependencies** in unit tests
5. **Use real interactions** in integration tests
6. **Test both success and failure paths**
7. **Include edge cases** and boundary conditions

### For Test Maintenance

1. **Run tests frequently** during development
2. **Keep test data current** with code changes
3. **Refactor tests** when refactoring production code
4. **Monitor coverage trends** over time
5. **Update fixtures** when APIs change
6. **Document complex test scenarios**

### For CI/CD

1. **Run fast tests first** for quick feedback
2. **Use parallel execution** for speed
3. **Generate coverage reports** for analysis
4. **Fail fast** on critical test failures
5. **Archive test results** for historical analysis

This comprehensive testing guide ensures high-quality, maintainable code through systematic testing practices and clear documentation.
