# Automated Git Workflow

Execute automated commit→push→merge→push workflow using project scripts (token-efficient).

**Invocation**: `/auto-git-workflow`

---

## Instructions for Claude

Execute workflow phases using dedicated scripts. Show output only if errors occur.

### Phase 1: Pre-commit Validation

```bash
git checkout development
./scripts/git/check_lint.sh
```

- If lint errors: Run `./scripts/git/fix_lint.sh` and retry
- Ignore markdown errors in CLAUDE.md/MEMORY.md (local-only files)

### Phase 2: Commit to Development

```bash
scripts\git\commit_enhanced.bat --non-interactive "descriptive commit message"
```

- Captures commit hash automatically
- Script handles staging and pre-commit hooks

### Phase 3: Push Development

```bash
git push origin development
```

### Phase 4: Merge to Main

```bash
scripts\git\merge_with_validation.bat --non-interactive
```

- Script handles: backup tag, checkout main, merge, conflict resolution
- Auto-resolves modify/delete conflicts for test files

### Phase 5: Push Main

```bash
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

**Lint failures**: `./scripts/git/fix_lint.sh` auto-fixes, then retry

**Merge conflicts**: `merge_with_validation.bat --non-interactive` handles automatically

**Push failures**: Show error output, user must resolve

**Script failures**: Show error output, check script documentation
