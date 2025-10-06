# Automated Git Workflow

Execute automated commit→push→merge→push workflow using project scripts (token-efficient).

**Invocation**: `/auto-git-workflow`

**Key**: Suppress all output except errors. Show brief summary at end.

---

## Environment Detection

**Check execution environment first**:

```bash
echo $OSTYPE
# Git Bash / WSL: "msys" or "linux-gnu"
# macOS: "darwin"
# If variable empty: Windows cmd.exe
```

**Use appropriate workflow**:

- Git Bash / Linux / macOS → **Section A** (uses .sh scripts + direct git)
- Windows cmd.exe → **Section B** (uses .bat scripts)

**Why this matters**: Git Bash cannot execute .bat files directly. The `cmd.exe /c` wrapper fails silently (see GIT_WORKFLOW.md lines 1054-1117).

---

## Section A: Git Bash / Linux / macOS (Primary)

**Token-efficient execution**: All commands suppress output unless errors occur.

### Phase 1: Pre-commit Validation

```bash
# Switch to development (suppress output)
git checkout development >/dev/null 2>&1

# Check for changes
if ! git diff --quiet || ! git diff --cached --quiet; then
  : # Changes exist, continue
else
  echo "⚠ No changes to commit"
  exit 0
fi

# Run lint check (suppress unless errors)
if ! ./scripts/git/check_lint.sh >/dev/null 2>&1; then
  echo "⚠ Lint errors found, auto-fixing..."
  ./scripts/git/fix_lint.sh

  # Re-check (show output this time)
  if ! ./scripts/git/check_lint.sh; then
    echo "✗ Some lint errors remain - check output above"
    exit 1
  fi
fi
```

**Note**: Markdown errors in CLAUDE.md/MEMORY.md are expected (local-only files, won't be committed).

### Phase 2: Commit to Development

```bash
# Stage all changes (suppress output)
git add . 2>/dev/null

# VALIDATION: Check for local-only files
if git diff --cached --name-only | grep -qE "(CLAUDE\.md|MEMORY\.md|_archive|benchmark_results)"; then
  echo "✗ ERROR: Local-only files are staged!"
  echo "Files:"
  git diff --cached --name-only | grep -E "(CLAUDE\.md|MEMORY\.md|_archive|benchmark_results)"
  echo ""
  echo "Remove with: git reset HEAD CLAUDE.md MEMORY.md _archive/ benchmark_results/"
  exit 1
fi

# VALIDATION: Branch-specific check
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ]; then
  if git diff --cached --name-only | grep -q "^tests/"; then
    echo "✗ ERROR: Test files staged on main branch"
    exit 1
  fi
fi

# Create commit (suppress output)
git commit -m "feat: Add automated git workflow slash command" >/dev/null 2>&1
if [ $? -ne 0 ]; then
  echo "✗ Commit failed:"
  git commit -m "feat: Add automated git workflow slash command"  # Show error
  exit 1
fi

# Capture hash for final report
DEV_COMMIT_HASH=$(git log -1 --format="%h")
DEV_COMMIT_MSG=$(git log -1 --format="%s")
```

**Commit message**: Replace "feat: Add automated git workflow slash command" with appropriate message using conventional commit format (feat:, fix:, docs:, chore:, test:).

### Phase 3: Push Development

```bash
# Push (suppress unless error)
if ! git push origin development >/dev/null 2>&1; then
  echo "✗ Push to development failed:"
  git push origin development  # Show error
  exit 1
fi
```

### Phase 4: Merge to Main

```bash
# Optional: Pre-merge validation
# ./scripts/git/validate_branches.sh >/dev/null 2>&1

# Switch to main (suppress output)
git checkout main >/dev/null 2>&1

# Perform merge (suppress unless conflicts)
git merge development --no-ff -m "Merge development into main" >/dev/null 2>&1
MERGE_EXIT=$?

if [ $MERGE_EXIT -ne 0 ]; then
  # Check for expected modify/delete conflicts
  if git status --short | grep -q "^DU "; then
    echo "⚠ Resolving expected test file conflicts..."

    # Auto-resolve: Remove test files from main
    git status --short | grep "^DU " | awk '{print $2}' | while read file; do
      git rm "$file" >/dev/null 2>&1
    done

    # Complete merge (suppress output)
    if ! git commit --no-edit >/dev/null 2>&1; then
      echo "✗ Failed to complete merge"
      exit 1
    fi
  # Check for content conflicts
  elif git status --short | grep -q "^UU "; then
    echo "✗ Content conflicts require manual resolution:"
    git status --short | grep "^UU "
    echo ""
    echo "Abort with: git merge --abort && git checkout development"
    exit 1
  fi
fi

# VALIDATION: CI documentation policy (optional but recommended)
# Only these 8 docs allowed on main:
# BENCHMARKS.md, claude_code_config.md, GIT_WORKFLOW.md,
# HYBRID_SEARCH_CONFIGURATION_GUIDE.md, INSTALLATION_GUIDE.md,
# MCP_TOOLS_REFERENCE.md, MODEL_MIGRATION_GUIDE.md, PYTORCH_COMPATIBILITY.md

# Capture merge hash for final report
MAIN_COMMIT_HASH=$(git log -1 --format="%h")
```

**Expected**: Modify/delete conflicts for test files are normal (see GIT_WORKFLOW.md lines 745-842).

### Phase 5: Push Main

```bash
# Push main (suppress unless error)
if ! git push origin main >/dev/null 2>&1; then
  echo "✗ Push to main failed:"
  git push origin main  # Show error
  exit 1
fi

# Return to development (suppress output)
git checkout development >/dev/null 2>&1
```

### Final Report

```bash
echo "✅ Workflow complete"
echo ""
echo "Development: $DEV_COMMIT_HASH \"$DEV_COMMIT_MSG\""
echo "Main: $MAIN_COMMIT_HASH merged & pushed"
```

---

## Section B: Windows cmd.exe (Alternative)

**Environment**: Windows Command Prompt only
**Scripts**: Use .bat files with --non-interactive flag (already token-efficient)

### Phase 1: Pre-commit Validation

```batch
git checkout development
scripts\git\check_lint.bat
```

If lint errors:

```batch
scripts\git\fix_lint.bat
```

### Phase 2: Commit to Development

```batch
scripts\git\commit_enhanced.bat --non-interactive "feat: Descriptive commit message"
```

**Note**: Script automatically:

- Stages all changes
- Validates local-only files
- Checks branch-specific rules
- Suppresses prompts

### Phase 3: Push Development

```batch
git push origin development
```

### Phase 4: Merge to Main

```batch
scripts\git\merge_with_validation.bat --non-interactive
```

**Note**: Script automatically:

- Runs pre-merge validation
- Creates backup tag
- Handles modify/delete conflicts
- Validates documentation CI policy

### Phase 5: Push Main

```batch
git push origin main
```

### Final Report

Show brief summary:

```
✅ Workflow complete

Development: [hash] pushed
Main: [merge-hash] merged & pushed
```

---

## Error Handling

### Lint Failures

**When**: `check_lint.sh` exits with error

**Action**:

```bash
./scripts/git/fix_lint.sh
./scripts/git/check_lint.sh
```

**Ignore**: Markdown errors in CLAUDE.md/MEMORY.md (local-only files)

**Reference**: GIT_WORKFLOW.md lines 1972-2216

### Batch Script Fails in Git Bash

**Symptom**: `.bat` file doesn't execute or fails silently

**Cause**: Git Bash cannot run Windows batch files

**Solution**: Use Section A (Git Bash workflow) instead

**Reference**: GIT_WORKFLOW.md lines 1054-1117

### Local-Only Files Staged

**Symptom**: CLAUDE.md, MEMORY.md, _archive/, or benchmark_results/ are staged

**Solution**:

```bash
git reset HEAD CLAUDE.md MEMORY.md _archive/ benchmark_results/
```

**Reference**: GIT_WORKFLOW.md lines 677-683

### Modify/Delete Conflicts

**Symptom**: Test files show "DU" status during merge

**Status**: ✅ **EXPECTED** (see GIT_WORKFLOW.md lines 745-842)

**Resolution**: Already handled automatically in Phase 4

### Content Conflicts

**Symptom**: Files show "UU" status (both modified)

**Action**: Manual resolution required

```bash
# Edit files to resolve
git add <resolved-files>
git commit

# Or abort
git merge --abort
git checkout development
```

**Reference**: GIT_WORKFLOW.md lines 1288-1355

### Push Failures

**Possible causes**:

- Authentication issues
- Network problems
- Branch protection rules
- Remote has diverged

**Action**: Check error output, resolve manually

---

## Quick Reference

| Environment | Scripts Available | Workflow |
|-------------|-------------------|----------|
| Git Bash | .sh scripts + direct git | Section A |
| Linux | .sh scripts + direct git | Section A |
| macOS | .sh scripts + direct git | Section A |
| Windows cmd.exe | .bat scripts | Section B |

**Fallback**: If all scripts fail, use direct git commands (see GIT_WORKFLOW.md)

---

## Token Efficiency

**Output Suppression**:

- ✅ All successful commands: `>/dev/null 2>&1`
- ✅ Only show errors: Remove suppression on retry
- ✅ Final summary: 4 lines maximum

**Typical token savings**: 90% reduction vs full output (14 lines vs 170 lines)
