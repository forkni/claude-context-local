# Contributing to Claude Context Local

Thank you for your interest in contributing to Claude Context Local!

## Quick Start

1. **Fork and clone** the repository
2. **Install dependencies**: `install-windows.cmd` or `pip install -e .[dev,test]`
3. **Run tests**: `pytest tests/ -v`
4. **Create a branch** from `development`
5. **Submit a PR** targeting the `development` branch

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/claude-context-local.git
cd claude-context-local

# Install in development mode
install-windows.cmd  # Windows
# or manually:
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev,test]
```

## Running Tests

```bash
# Run all tests
pytest tests/ -v --tb=short

# Run by module (recommended for faster iteration)
pytest tests/unit/chunking/ -v
pytest tests/unit/embeddings/ -v
pytest tests/unit/graph/ -v
pytest tests/unit/merkle/ -v
pytest tests/unit/search/ -v
pytest tests/unit/mcp_server/ -v

# Or use the automated test runner
cd tests && run_all_tests.bat
```

See [tests/TESTING_GUIDE.md](tests/TESTING_GUIDE.md) for detailed testing documentation.

## Code Style

This project uses automated code quality tools:

- **ruff**: Python linting
- **black**: Code formatting
- **isort**: Import sorting
- **markdownlint**: Documentation formatting

```bash
# Check code style
./scripts/git/check_lint.sh

# Auto-fix issues
./scripts/git/fix_lint.sh
```

All linting must pass before submitting a PR.

## Branch Strategy

- **development**: Active development branch (submit PRs here)
- **main**: Stable release branch (merged from development)

### Workflow

1. Create a feature branch from `development`:
   ```bash
   git checkout development
   git pull origin development
   git checkout -b feature/your-feature-name
   ```

2. Make your changes and commit:
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

3. Push and create a PR:
   ```bash
   git push origin feature/your-feature-name
   # Then create PR on GitHub targeting 'development' branch
   ```

## Pull Request Guidelines

- Target the `development` branch
- Include tests for new functionality
- Follow existing code style (enforced by ruff, black, isort)
- Write clear commit messages using [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat:` - New feature
  - `fix:` - Bug fix
  - `docs:` - Documentation changes
  - `test:` - Test changes
  - `refactor:` - Code refactoring
  - `chore:` - Maintenance tasks

## Local-Only Files

These files should NEVER be committed (automatically excluded by `.gitignore`):

- `CLAUDE.md`, `MEMORY.md` - Personal development context
- `_archive/` - Historical files
- `benchmark_results/` - Generated test data

These are protected by pre-commit hooks.

## Documentation

- [Installation Guide](docs/INSTALLATION_GUIDE.md)
- [Testing Guide](tests/TESTING_GUIDE.md)
- [Git Workflow](docs/GIT_WORKFLOW.md)
- [MCP Tools Reference](docs/MCP_TOOLS_REFERENCE.md)
- [Advanced Features](docs/ADVANCED_FEATURES_GUIDE.md)

## Getting Help

- Check [existing issues](https://github.com/forkni/claude-context-local/issues)
- Review [documentation](docs/)
- Ask questions in [discussions](https://github.com/forkni/claude-context-local/discussions)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
