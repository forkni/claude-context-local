# Git Workflow for claude-context-local

## Overview

This repository uses a **Local-First Privacy Model** where certain development files remain strictly on your local machine and are never committed to any git branch. This ensures your development context stays private while maintaining a clean, professional public repository.

## 🔒 Local-Only Files (NEVER Committed)

| File/Directory | Size | Purpose | Status |
|----------------|------|---------|---------|
| **CLAUDE.md** | ~50KB | Development context and instructions | 🔴 Local Only |
| **MEMORY.md** | ~5KB | Session memory and notes | 🔴 Local Only |
| **_archive/** | 7.3MB (764 files) | Historical TouchDesigner documentation | 🔴 Local Only |
| **benchmark_results/** | Variable | Generated test data and results | 🔴 Local Only |

**Total saved from repository: ~7.4MB + 764 files**

## 🏗️ Two-Tier File Structure

Since you're the sole developer, we use a simplified two-tier approach:

### 1. Local Machine (Working Directory)

- **Contains EVERYTHING** including private development files
- _archive/ provides complete historical context (764 TouchDesigner files)
- CLAUDE.md and MEMORY.md give full development context
- benchmark_results/ stores local test data

### 2. Git Branches (Both Development & Main)

- **Clean public releases** without development context
- No private files (automatically excluded by .gitignore)
- Professional presentation for users
- Both branches have identical content

## 🛡️ Protection Mechanisms

### 1. .gitignore Protection

```gitignore
# Local-only content (NEVER commit to ANY branch)
_archive/
benchmark_results/
CLAUDE.md
MEMORY.md
```

### 2. Pre-commit Hook

Automatically blocks commits containing local-only files:

- Located: `.git/hooks/pre-commit`
- Scans staging area for protected files
- Prevents accidental exposure

### 3. Public Documentation Policy

The following documentation files are tracked in Git (9 files total):

- **docs/BENCHMARKS.md** - Benchmark methodology and results
- **docs/claude_code_config.md** - Claude Code configuration guide
- **docs/GIT_WORKFLOW.md** - This workflow documentation
- **docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md** - Search system configuration
- **docs/INSTALLATION_GUIDE.md** - Complete installation process
- **docs/MCP_TOOLS_REFERENCE.md** - Modular MCP tools reference
- **docs/MODEL_MIGRATION_GUIDE.md** - Model switching guide
- **docs/TESTING_GUIDE.md** - Test suite documentation

**All other docs/ files remain local-only** and are automatically excluded by .gitignore rules and blocked by the pre-commit hook.

## 🚀 Workflow Scripts

### commit.bat - Safe Committing

```batch
commit.bat "Your commit message"
```

- **Automatically excludes** local-only files
- **Double-checks** staging area
- **Shows preview** before committing
- **Confirms success** with local file privacy

### sync_branches.bat - Branch Synchronization

```batch
sync_branches.bat
```

- **Merges development → main**
- **Pushes to remote**
- **Returns to development branch**
- **Ensures both branches are identical**

## 🤖 Claude Code GitHub Integration

### Overview

This repository includes GitHub Actions integration for Claude Code, enabling interactive AI assistance through `@claude` mentions in issues and pull requests. This is **complementary** to the CI/CD automation workflows.

### Interactive AI Features

**GitHub Actions Workflow**: `.github/workflows/claude.yml`

Responds to `@claude` mentions in:
- Issue comments
- Pull request review comments
- Pull request reviews
- New issues (in title or body)

**Permissions Required**:
- Read: contents, pull requests, issues
- Write: id-token (for authentication)

**Setup Requirement**: Add `ANTHROPIC_API_KEY` to repository secrets

### Custom Commands

Located in `.claude/commands/` directory, these are reusable command templates:

#### 1. `/create-pr` - Automated PR Creation

**Purpose**: Create pull requests with clean, professional descriptions

**Features**:
- Creates feature branch from current changes
- Commits staged changes with conventional format
- Pushes to remote and creates PR via GitHub CLI
- **Never includes Claude Code attribution** in PR descriptions

**Usage**:
```bash
# Stage your changes first
git add <files>

# Run command (optional: specify branch suffix)
/create-pr feature-name
# or
/create-pr  # Uses timestamp as branch suffix
```

**Good PR Examples**:
- `feat: Add semantic search caching for 93% token reduction`
- `fix: Escape parentheses in sync_status.bat echo statements`
- `docs: Update installation guide with PyTorch 2.6.0 requirements`

#### 2. `/run-merge` - Guided Merge Workflow

**Purpose**: Safe merge workflow with .gitattributes support and validation

**Merge Types**:
- `full` - Full merge from development to main (default)
- `docs` - Documentation-only merge
- `status` - Check branch synchronization status

**Usage**:
```bash
# Full merge workflow
/run-merge full

# Documentation-only merge
/run-merge docs

# Status check only
/run-merge status
```

**Safety Features**:
- Pre-merge validation via `validate_branches.bat`
- Automatic backup tags created
- .gitattributes enforcement (tests/ excluded from main)
- Post-merge verification
- Rollback script available (`rollback_merge.bat`)

#### 3. `/validate-changes` - Pre-Commit Validation

**Purpose**: Comprehensive pre-commit checklist to catch issues early

**Checks Performed**:
1. Verifies changes are staged
2. Blocks local-only files (CLAUDE.md, MEMORY.md, _archive/, benchmark_results/)
3. Branch-specific validations (no tests/ on main)
4. File count warnings (>50 files = large changeset)
5. Commit message format validation (conventional commits)
6. AI attribution detection (blocks commits with Claude/Generated/Co-Authored references)
7. .gitattributes consistency check

**Usage**:
```bash
# After staging changes, before committing
/validate-changes
```

**Prevents Common Mistakes**:
- ❌ Committing CLAUDE.md or MEMORY.md (local-only)
- ❌ Adding tests/ to main branch (development-only)
- ❌ Using AI attribution in commit messages
- ❌ Non-conventional commit message format

**Quick Fixes**:
```bash
# Unstage local files
git reset HEAD CLAUDE.md MEMORY.md _archive/ benchmark_results/

# Conventional commit format examples
feat: Add hybrid search with BM25 + semantic fusion
fix: Escape parentheses in batch file echo statements
docs: Update installation guide with PyTorch requirements
chore: Add GitHub Actions workflows for CI/CD
test: Add integration tests for incremental indexing
```

### CI/CD Workflows vs Claude Code Integration

**They are COMPLEMENTARY, not mutually exclusive:**

#### CI/CD Workflows (Automated)
- **branch-protection.yml** - Validates every push (test files, linting, local-only file checks)
- **merge-development-to-main.yml** - Manual merge workflow with .gitattributes support
- **docs-validation.yml** - Documentation quality checks (markdown lint, link checking)

**Purpose**: Automatic validation and quality assurance

#### Claude Code Integration (Interactive)
- **claude.yml** - Responds to @claude mentions in issues/PRs
- **Custom commands** - Reusable workflow templates

**Purpose**: Interactive AI assistance for development tasks

### Using @claude in GitHub

**In Issues**:
```markdown
@claude can you review this error message and suggest a fix?

[error log here]
```

**In Pull Requests**:
```markdown
@claude please review these changes for potential issues
```

**In PR Comments**:
```markdown
@claude what's the best way to implement caching for this function?
```

### Configuration Files

#### .gitignore Rules
```gitignore
# Claude Code user settings (local-only)
.claude/*
# But allow shared custom commands
!.claude/commands/
```

**This ensures**:
- User-specific settings remain private (`.claude/*`)
- Shared custom commands are version controlled (`.claude/commands/`)

#### Required Secrets

Add to repository settings → Secrets and variables → Actions:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### Integration Benefits

| Benefit | Description |
|---------|-------------|
| **Interactive Help** | @claude mentions provide context-aware assistance |
| **Workflow Automation** | Custom commands standardize common tasks |
| **Quality Enforcement** | Validation prevents common mistakes |
| **Clean Commits** | Automatic checks ensure professional commit messages |
| **Safe Merging** | Guided workflows with rollback support |

## 📋 Daily Workflow

### 1. Normal Development

```batch
# Work with full context (CLAUDE.md, MEMORY.md, _archive/)
# Edit code, run tests, develop features

# Validate changes before committing
/validate-changes

# When ready to commit:
commit.bat "feat: Add new search functionality"
```

### 2. Creating Pull Requests

```batch
# Stage your changes
git add <files>

# Use custom command for clean PR creation
/create-pr feature-name

# Or create manually with gh CLI
gh pr create --title "feat: ..." --body "..."
```

### 3. Public Release

```batch
# Option 1: Use guided merge workflow
/run-merge full

# Option 2: Use traditional script
sync_branches.bat

# Both branches now have identical public content
# Local files remain private
```

### 4. Fresh Clone Setup

```batch
# After cloning repository:
git clone <repo-url>
cd claude-context-local

# Note: CLAUDE.md, MEMORY.md, and _archive/ are not tracked in git
# These files remain on your portable drive
```

## 🔄 File Lifecycle

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Local Work    │    │   Git Tracking   │    │ Public Release  │
│                 │    │                  │    │                 │
│ • CLAUDE.md     │───▶│ • Core code      │───▶│ • Clean repo    │
│ • MEMORY.md     │    │ • Tests          │    │ • Professional  │
│ • _archive/     │    │ • Scripts        │    │ • No dev files  │
│ • Full context  │    │ • Documentation  │    │ • User-ready    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
     ↑ Private               ↑ Tracked              ↑ Public
```

## ⚡ Quick Commands Reference

| Task | Command | Result |
|------|---------|---------|
| **Safe commit** | `commit.bat "message"` | Commits without local files |
| **Sync to main** | `sync_branches.bat` | Development → Main → Remote |
| **Check status** | `git status` | Shows staged changes |
| **View branches** | `git branch -a` | Lists all branches |

## 🚨 Critical Rules

### ✅ DO

- Use `commit.bat` for all commits
- Keep CLAUDE.md and MEMORY.md updated locally
- Use `sync_branches.bat` for releases
- Backup local files before major changes

### ❌ NEVER

- Manually add local files to git: `git add CLAUDE.md` ❌
- Commit without using commit.bat ❌
- Push local files to any branch ❌

## 🔧 Troubleshooting

### "Local files in staging area" Error

```bash
# Remove local files from staging:
git reset HEAD CLAUDE.md MEMORY.md
git reset HEAD _archive/ benchmark_results/
```

### Missing Local Files

```bash
# If working from a fresh clone, recreate minimal versions:
echo "# Development context" > CLAUDE.md
echo "# Session memory" > MEMORY.md
```

Note: If working from a portable drive, local files remain with the repository.

### Pre-commit Hook Not Working

```bash
# Ensure hook is executable:
chmod +x .git/hooks/pre-commit

# Test hook manually:
.git/hooks/pre-commit
```

## 📊 Benefits

| Benefit | Impact |
|---------|---------|
| **Privacy** | Development context never exposed |
| **Clean repo** | Professional public presentation |
| **Space efficiency** | 7.4MB + 764 files excluded |
| **Fail-safe** | Multiple protection layers |
| **Easy workflow** | Automated scripts reduce errors |
| **Solo development** | Optimized for single developer |

## 🔄 Branch Strategy

```
Local Machine:
├── CLAUDE.md (private context)
├── MEMORY.md (private notes)
├── _archive/ (764 historical files)
└── Public code files

           ↓ commit.bat

Development Branch:
├── Core application code
├── Test suites
├── Documentation (public)
├── Scripts and tools
└── Configuration files

           ↓ sync_branches.bat

Main Branch:
├── Identical to development
├── Clean public release
├── No development context
└── User-ready repository
```

## 📝 Implementation Summary

✅ **Complete Setup:**

- .gitignore excludes all local-only files
- Pre-commit hook prevents accidental commits
- Backup system preserves local files
- Automation scripts ensure correct workflow
- Documentation provides clear guidance

✅ **Protection Layers:**

1. .gitignore (automatic exclusion)
2. Pre-commit hook (staging area check)
3. Backup system (recovery mechanism)
4. Automated scripts (reduce human error)

✅ **Benefits Achieved:**

- **100% privacy** for development context
- **Professional repository** presentation
- **Minimal overhead** for daily workflow
- **Fail-safe protection** against exposure
- **Easy maintenance** for solo development

## 📝 Commit Message Guidelines

### IMPORTANT: Clean Commit Messages

When writing commit messages, they should be clean and simple. Never add any reference to being created by Claude Code, or add yourself as a co-author, as this can lead to confusion.

### Good Examples

- `fix: Add test_evaluation folder for benchmark support`
- `feat: Implement hybrid search functionality`
- `chore: Update dependencies`

### Bad Examples (AVOID)

- Messages with "Generated with Claude Code"
- Messages with "Co-Authored-By: Claude"
- Any AI-related attribution

## 📋 CHANGELOG & Versioning

### CHANGELOG.md Maintenance

- **Location**: Root directory (`CHANGELOG.md`)
- **Format**: Follows [Keep a Changelog](https://keepachangelog.com/) standard
- **Update timing**: Update with each significant change or release
- **Structure**: Organized by version with Added/Changed/Fixed/Removed sections

### Version Bumping Strategy

This project follows [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

- **PATCH (0.1.x)**: Bug fixes, documentation corrections, small improvements
  - Example: 0.1.0 → 0.1.1 for fixing documentation typos

- **MINOR (0.x.0)**: New features, significant enhancements, backward-compatible changes
  - Example: 0.1.0 → 0.2.0 for adding auto-tuning feature

- **MAJOR (x.0.0)**: Breaking changes, major architecture updates
  - Example: 0.9.0 → 1.0.0 for first stable release

### Release Workflow

1. Update `CHANGELOG.md` with new version section
2. Bump version in `pyproject.toml`
3. Commit changes: `docs: Prepare v0.x.0 release`
4. Push to development branch
5. Sync to main branch
6. Create annotated git tag: `git tag -a v0.x.0 -m "Release notes"`
7. Push tag: `git push origin v0.x.0`
8. Create GitHub release (optional, via web interface)

### Current Version

Check `pyproject.toml` for the current version number.

## 📦 Test Data Management

### test_evaluation/ Folder

- **Status**: ✅ Tracked in Git (NOT gitignored)
- **Purpose**: Required sample project for benchmarks
- **Contents**: Synthetic test project for evaluation
- **Critical**: Must be present for benchmarks to work

### Files to Keep vs Ignore

- **Keep**: test_evaluation/ (required for benchmarks)
- **Ignore**: benchmark_results/ (generated output)
- **Ignore**: custom_evaluation_results/ (temporary results)

This workflow ensures your development context remains completely private while maintaining a clean, professional public repository suitable for users and collaborators.
