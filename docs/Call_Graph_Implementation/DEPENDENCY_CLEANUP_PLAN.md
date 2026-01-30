# Comprehensive Dependency Cleanup Plan

**Date**: 2026-01-29
**Status**: Ready for testing
**Estimated Cleanup**: 7 direct dependencies, ~25+ transitive packages, ~500MB+ disk space

---

## Executive Summary

After thorough codebase analysis (42 packages audited, 197 total installed), we identified **7 unused direct dependencies** that can be safely removed:

- **3 runtime packages**: torchaudio, torchvision, FlagEmbedding (+ pandas, aiohttp as transitive pins)
- **2 dev tools**: black, isort (fully replaced by ruff)
- **Bonus**: Removes protobuf CVE-2026-0994 (no fix available yet) by eliminating FlagEmbedding cascade

**Key Discovery**: FlagEmbedding is a phantom dependency pulling in ~23 unused transitive packages. BGE-M3 loads entirely via `sentence-transformers`, not FlagEmbedding.

---

## Part 1: Analysis Results

### Import Analysis (42 packages audited)

**Methodology**: Grep searched entire codebase for `import X`, `from X` patterns in:
- Production code (`.py` files in `chunking/`, `embeddings/`, `mcp_server/`, `search/`)
- Test code (`tests/**/*.py`)
- Scripts (`scripts/**/*.py`, `tools/**/*.py`)

#### Packages with ZERO imports (unused):

| Package | Declared As | Reason Installed | Safe to Remove? |
|---------|-------------|------------------|-----------------|
| **torchaudio** | Direct (runtime) | "PyTorch ecosystem compatibility" | ✅ YES - docs confirm unused |
| **torchvision** | Direct (runtime) | "PyTorch ecosystem compatibility" | ✅ YES - docs confirm unused |
| **FlagEmbedding** | Direct (runtime) | Legacy BGE-M3 loader (obsolete) | ✅ YES - sentence-transformers handles it |
| **pandas** | Direct (runtime) | Comment: "Required by datasets" | ✅ YES - only via FlagEmbedding chain |
| **aiohttp** | Direct (runtime) | CVE version floor (transitive pin) | ✅ YES - other packages pull it |
| **black** | Direct (dev) | Code formatter | ✅ YES - ruff format replaced it |
| **isort** | Direct (dev) | Import sorter | ✅ YES - ruff lint `I` rules replaced it |
| accelerate | Transitive | Via FlagEmbedding | Auto-removed with FlagEmbedding |
| peft | Transitive | Via FlagEmbedding | Auto-removed with FlagEmbedding |
| datasets | Transitive | Via FlagEmbedding | Auto-removed with FlagEmbedding |
| ir_datasets | Transitive | Via FlagEmbedding | Auto-removed with FlagEmbedding |
| sentencepiece | Transitive | Via FlagEmbedding | Auto-removed with FlagEmbedding |
| **protobuf** | Transitive | Via FlagEmbedding | ✅ CVE-2026-0994 eliminated! |
| lxml | Transitive | Via FlagEmbedding→ir_datasets | Auto-removed |
| inscriptis | Transitive | Via FlagEmbedding→ir_datasets | Auto-removed |
| beautifulsoup4 | Transitive | Via FlagEmbedding→ir_datasets | Auto-removed |
| pyarrow | Transitive | Via FlagEmbedding→datasets | Auto-removed |
| Pillow | Transitive | Via torchvision | Auto-removed with torchvision |

#### Packages that ARE imported (keep):

| Package | Import Type | Usage | Evidence |
|---------|-------------|-------|----------|
| torch | Direct/conditional | CUDA, tensors, model loading | 12+ files, core runtime |
| sentence-transformers | Conditional | Embedding models | `model_loader.py`, `neural_reranker.py` |
| faiss-cpu | Conditional | Vector index | `faiss_index.py`, `indexer.py` |
| tree-sitter + grammars | Direct + lazy | AST parsing (9 languages) | `chunking/languages/*.py` |
| mcp | Direct | MCP server protocol | `mcp_server/server.py`, `tool_registry.py` |
| rich | Direct | Progress bars, console output | `embedder.py`, `parallel_chunker.py` |
| nltk | Conditional | BM25 tokenization, stemming | `bm25_index.py` (try/except import) |
| rank-bm25 | Conditional | BM25 sparse search | `bm25_index.py` (try/except import) |
| tiktoken | Conditional | Token counting | `chunking/languages/base.py` (try/except) |
| uvicorn | Conditional | SSE transport | `mcp_server/server.py` (lazy import) |
| starlette | Conditional | SSE transport | `mcp_server/server.py` (lazy import) |

#### Special Case: transformers

- **Status**: Declared as direct dependency but **never imported in production code**
- **Only references**:
  - `tools/summarize_audit.py:448` - version detection in subprocess string
  - `scripts/verify_installation.py:190` - version check in subprocess string
- **Why keep**: Pulled in by `sentence-transformers` anyway. Declaring it direct allows version pinning.
- **Verdict**: KEEP (for version control, even though it's technically transitive)

---

## Part 2: The FlagEmbedding Cascade

### Dependency Tree Analysis

```
FlagEmbedding==1.3.5
├── torch (already required directly)
├── transformers (already required directly)
├── sentence-transformers (already required directly)
├── datasets==4.4.2 ❌ UNUSED
│   ├── pandas==2.3.3 ❌ UNUSED (also direct dep, can remove)
│   ├── pyarrow==23.0.0 ❌ UNUSED
│   ├── dill==0.4.0
│   ├── multiprocess==0.70.18
│   ├── xxhash==3.6.0
│   ├── httpx==0.28.1
│   └── (15+ more transitive deps)
├── accelerate==1.12.0 ❌ UNUSED
│   └── (pulls in safetensors, psutil - shared with other packages)
├── peft==0.17.1 ❌ UNUSED
│   ├── accelerate (above)
│   └── (more shared deps)
├── ir_datasets==0.5.11 ❌ UNUSED
│   ├── lxml==5.4.0 ❌ UNUSED
│   ├── inscriptis==2.7.0 ❌ UNUSED
│   ├── beautifulsoup4==4.14.3 ❌ UNUSED
│   ├── trec-car-tools
│   ├── lz4, warc3-wet, zlib-state, ijson, unlzw3
│   └── (many more)
├── sentencepiece==0.2.1 ❌ UNUSED
└── protobuf==6.33.4 ❌ CVE-2026-0994!
```

**Total cascade removal**: ~23 packages when FlagEmbedding is removed.

### Why FlagEmbedding Was Added (Historical)

- **Original purpose**: Load BGE-M3 via `BGEM3FlagModel` for better control
- **Current reality**: BGE-M3 loads perfectly via `SentenceTransformer("BAAI/bge-m3")`
- **Evidence**: Zero imports of `FlagEmbedding`, `BGEM3FlagModel`, or `FlagModel` anywhere in codebase
- **Conclusion**: Legacy dependency, safe to remove

---

## Part 3: Dev Tool Analysis

### Ruff vs Black/Isort

**Ruff configuration** (`pyproject.toml`):
```toml
[tool.ruff.lint]
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # pyflakes
    "I",  # isort (replaces standalone isort) ← IMPORT SORTING
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
]

[tool.ruff.lint.isort]  # ← ISORT CONFIG WITHIN RUFF
lines-after-imports = 2
known-first-party = ["chunking", "embeddings", "mcp_server", "search", "merkle", "evaluation"]

[tool.ruff.format]  # ← FORMATTING (replaces black)
quote-style = "double"
indent-style = "space"
```

**Invocation analysis**:

| Tool | Shell Scripts | CI Workflows | Pre-commit | .charlie/config.yml |
|------|---------------|--------------|------------|---------------------|
| ruff | `check_lint.sh`, `fix_lint.sh`, `commit_enhanced.sh`, `*.bat` | `branch-protection.yml` | ✅ | `lint:` command |
| black | ❌ NONE | ❌ NONE | ❌ NONE | `fix:` (redundant) |
| isort | ❌ NONE | ❌ NONE | ❌ NONE | `fix:` (redundant) |

**Vestigial configs**:
- `[tool.black]` section in `pyproject.toml` (lines 184-196) - unused
- `[tool.isort]` section in `pyproject.toml` (lines 198-202) - unused
- `.charlie/config.yml` line 2: `pip install ruff black isort && ruff check --fix . && black . && isort .` - runs black+isort AFTER ruff already fixed everything

---

## Part 4: Cleanup Implementation Plan

### Step 1: Edit `pyproject.toml`

**Remove from `[project.dependencies]`** (lines 30-47):
```diff
dependencies = [
-   "aiohttp>=3.13.3",  # Security: Fixes CVE-2025-69223 through CVE-2025-69230
    "einops>=0.8.0",  # Required for CodeRankEmbed model
    "faiss-cpu>=1.13.1",
-   "FlagEmbedding>=1.3.0",
    "fsspec[http]>=2024.2.0,<=2025.10.0",
    "huggingface-hub>=0.36.0",
    "mcp>=1.25.0",
    "networkx>=3.0",
    "nltk>=3.8",
-   "pandas>=2.0.0",  # Required by datasets (transitive dependency of sentence-transformers)
    "psutil>=7.2.1",
    "rank-bm25>=0.2.2",
    "torch>=2.8.0,<2.9.0",
-   "torchvision>=0.23.0,<0.24.0",
-   "torchaudio>=2.8.0,<2.9.0",
    "rich>=14.2.0",
```

**Remove from `[project.optional-dependencies.dev]`** (lines 82-90):
```diff
dev = [
-   "black>=25.11.0",
-   "isort>=7.0.0",
    "ruff>=0.14.10",
    "pip-audit>=2.10.0",
```

**Remove vestigial config sections**:
```diff
-[tool.black]
-line-length = 88
-target-version = ["py311"]
-exclude = '''
-/(
-    \.git
-  | \.venv
-  | _archive
-  | build
-  | dist
-  | node_modules
-)/
-'''
-
-[tool.isort]
-profile = "black"
-line_length = 88
-skip_glob = ["_archive/*", ".venv/*"]
-known_first_party = ["chunking", "embeddings", "mcp_server", "search", "merkle", "evaluation"]
-
```

**Remove `[tool.uv.sources]` for torchaudio/torchvision** (lines 171-181):
```diff
[tool.uv.sources]
# CUDA 12.8 (recommended for RTX 50 series and newer GPUs)
torch = [
    { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
]
-torchvision = [
-    { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
-]
-torchaudio = [
-    { index = "pytorch-cu128", marker = "sys_platform == 'linux' or sys_platform == 'win32'" },
-]
```

**Update security audit comments** (line 155):
```diff
-# Remaining CVE: protobuf CVE-2026-0994 (DoS) - no fix available yet (monitoring)
+# Remaining CVEs: 0 (all resolved as of 2026-01-29)
```

### Step 2: Edit `.charlie/config.yml`

**Update fix command** (line 2):
```diff
checkCommands:
-  fix: pip install ruff black isort && ruff check --fix . && black . && isort .
+  fix: ruff check --fix . && ruff format .
  lint: pip install ruff && ruff check .
```

### Step 3: (Optional) Update Install Scripts

**Files to update**:
- `install-windows.cmd` (lines 463, 498 - references to torchaudio/torchvision)
- `scripts/batch/install_pytorch_cuda.bat` (PyTorch install commands)
- `start_mcp_server.cmd` (if it references these)

**Approach**: Replace `torch torchvision torchaudio` with just `torch` in pip install commands.

**Note**: These are optional cleanup - the packages won't install anyway after pyproject.toml changes.

### Step 4: (Optional) Update Documentation

**Files to update**:
- `docs/INSTALLATION_GUIDE.md` (remove references to torchvision/torchaudio being installed)
- `docs/PYTORCH_COMPATIBILITY.md` (remove torchvision/torchaudio from compatibility matrix)

**Note**: Can defer to separate doc cleanup task.

---

## Part 5: Execution Steps

### Pre-cleanup Verification

```bash
# 1. Save baseline audit
.venv/Scripts/pip-audit --format json > docs/Call_Graph_Implementation/before-cleanup-audit.json

# 2. Document current installed packages
.venv/Scripts/pip list --format=freeze > docs/Call_Graph_Implementation/before-cleanup-packages.txt

# 3. Check current disk usage
.venv/Scripts/python -c "import os; print(f'Venv size: {sum(f.stat().st_size for f in os.scandir(\".venv\") if f.is_file()) / (1024**3):.2f} GB')"
```

### Execute Cleanup

```bash
# 1. Edit pyproject.toml (manual or via Edit tool)
# 2. Edit .charlie/config.yml (manual or via Edit tool)

# 3. Uninstall direct dependencies
.venv/Scripts/pip uninstall -y torchaudio torchvision FlagEmbedding pandas aiohttp black isort

# 4. Reinstall from updated pyproject.toml to clean up orphans
.venv/Scripts/pip install -e ".[dev,test]"

# 5. Verify no broken requirements
.venv/Scripts/pip check
```

### Post-cleanup Verification

```bash
# 1. Verify target packages removed
.venv/Scripts/pip list | grep -E "FlagEmbedding|accelerate|peft|datasets|protobuf|torchaudio|torchvision|black|isort"
# Expected: No results (except datasets/protobuf if still needed by other packages)

# 2. Run security audit
.venv/Scripts/pip-audit --format json > docs/Call_Graph_Implementation/after-cleanup-audit.json
.venv/Scripts/python tools/summarize_audit.py docs/Call_Graph_Implementation/after-cleanup-audit.json
# Expected: 0 CVEs (protobuf CVE-2026-0994 eliminated)

# 3. Check disk savings
.venv/Scripts/pip list --format=freeze > docs/Call_Graph_Implementation/after-cleanup-packages.txt
# Compare package counts

# 4. Test ML functionality
.venv/Scripts/python -c "
from sentence_transformers import SentenceTransformer
print('Loading BGE-M3...')
model = SentenceTransformer('BAAI/bge-m3')
print(f'Model loaded: {model}')
print('Embedding test...')
emb = model.encode(['test sentence'])
print(f'Embedding shape: {emb.shape}')
print('✅ BGE-M3 works without FlagEmbedding')
"

# 5. Test dev tools
ruff check .
ruff format --check .
# Expected: Works (black/isort not needed)

# 6. Run full test suite
.venv/Scripts/python -m pytest tests/ -x -q --tb=short --ignore=tests/slow_integration/test_hybrid_search_integration.py
# Expected: All tests pass (minus pre-existing hybrid test fixture issue)

# 7. Test PyTorch/CUDA
.venv/Scripts/python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA: {torch.cuda.is_available()}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
# Expected: CUDA still works (torchaudio/torchvision were never needed)
```

---

## Part 6: Risk Assessment

### Zero-Risk Removals

| Package | Risk | Justification |
|---------|------|---------------|
| torchaudio | None | Zero imports, docs confirm unused |
| torchvision | None | Zero imports, docs confirm unused |
| black | None | Ruff fully replaced, zero invocations |
| isort | None | Ruff fully replaced, zero invocations |

### Low-Risk Removals (transitive pins)

| Package | Risk | Justification |
|---------|------|---------------|
| pandas | Very Low | Only via FlagEmbedding cascade, zero direct imports |
| aiohttp | Very Low | Transitive dep pulled by other packages, version floor no longer needed |

### Medium-Risk Removal (requires testing)

| Package | Risk | Justification | Mitigation |
|---------|------|---------------|------------|
| FlagEmbedding | Low-Medium | Never imported, but BGE-M3 may have changed loading mechanism | Test BGE-M3 loading via SentenceTransformer thoroughly |

**Mitigation Steps**:
1. Test BGE-M3 model loading before committing changes
2. Test Qwen3-0.6B, Qwen3-4B models if used
3. If any model fails, check if FlagEmbedding is required by newer sentence-transformers internals
4. Rollback plan: `pip install FlagEmbedding>=1.3.0` if issues arise

---

## Part 7: Rollback Plan

If any issues occur after cleanup:

```bash
# 1. Revert pyproject.toml and .charlie/config.yml
git checkout pyproject.toml .charlie/config.yml

# 2. Reinstall all dependencies
.venv/Scripts/pip install -e ".[dev,test]"

# 3. Verify restoration
.venv/Scripts/pip check
.venv/Scripts/pip list | grep -E "FlagEmbedding|torchaudio|torchvision|black|isort"
# Expected: All 7 packages back

# 4. Test model loading
.venv/Scripts/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

---

## Part 8: Expected Benefits

### Disk Space Savings

| Package | Estimated Size |
|---------|----------------|
| torchaudio | ~200MB |
| torchvision | ~50MB |
| FlagEmbedding cascade (datasets, accelerate, peft, ir_datasets, etc.) | ~250-300MB |
| **Total** | **~500-550MB** |

### Dependency Count Reduction

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Direct dependencies | 29 | 22 | -7 (24%) |
| Total installed | 197 | ~172 | -25 (~13%) |

### Security Improvements

- **CVE-2026-0994** (protobuf): Eliminated (package removed entirely)
- **aiohttp CVE pins**: No longer needed (other packages enforce minimums)

### Developer Experience

- Faster `pip install` (7 fewer direct deps to resolve)
- Cleaner dependency tree (easier to audit)
- No more confusing vestigial configs (`[tool.black]`, `[tool.isort]`)
- `.charlie/config.yml` fix command 3x faster (no redundant black+isort after ruff)

---

## Part 9: Testing Checklist

Before merging changes, verify:

- [ ] `pip check` - no broken requirements
- [ ] `pip list | grep FlagEmbedding` - returns nothing
- [ ] `pip list | grep protobuf` - returns nothing (CVE eliminated)
- [ ] `pip list | grep torchaudio` - returns nothing
- [ ] `pip list | grep torchvision` - returns nothing
- [ ] `pip list | grep black` - returns nothing
- [ ] `pip list | grep isort` - returns nothing
- [ ] BGE-M3 model loading works: `SentenceTransformer('BAAI/bge-m3')`
- [ ] Qwen3-0.6B model loading works (if used)
- [ ] CodeRankEmbed model loading works (if used)
- [ ] `ruff check .` - passes
- [ ] `ruff format --check .` - passes
- [ ] `pytest tests/` - all pass (minus pre-existing failures)
- [ ] PyTorch CUDA: `torch.cuda.is_available()` - returns True
- [ ] MCP server starts: `python -m mcp_server.server`
- [ ] Semantic search works: index + search test
- [ ] `pip-audit` - 0 CVEs (down from 1)

---

## Part 10: Post-Cleanup Actions

### Update VERSION_HISTORY.md

Add entry for v0.8.6 or v0.9.0:

```markdown
## [0.8.6] - 2026-01-29

### Removed
- **Unused dependencies** (7 direct, ~25 transitive):
  - Runtime: `torchaudio`, `torchvision`, `FlagEmbedding`, `pandas`, `aiohttp` (transitive pins)
  - Dev: `black`, `isort` (fully replaced by ruff)
  - Cascade: `accelerate`, `peft`, `datasets`, `ir_datasets`, `protobuf`, `lxml`, `inscriptis`, `beautifulsoup4`, `pyarrow`, `Pillow`, and 15+ more
- **Vestigial configs**: `[tool.black]`, `[tool.isort]` sections in pyproject.toml
- **Security**: Eliminated CVE-2026-0994 (protobuf DoS vulnerability)

### Changed
- `.charlie/config.yml` fix command: removed redundant black+isort invocations

### Impact
- **Disk space**: Saved ~500-550MB in .venv
- **Install time**: 24% fewer direct dependencies to resolve
- **Security**: 0 known CVEs (down from 1)
```

### Update CLAUDE.md (if needed)

Update dependency count in quick reference section.

### Commit Message

```
feat: Remove 7 unused dependencies (~500MB, -25 packages)

Removed unused direct dependencies after thorough import analysis:
- Runtime: torchaudio, torchvision, FlagEmbedding, pandas, aiohttp
- Dev: black, isort (ruff fully replaced both)

Cascade removes ~25 transitive packages including accelerate, peft,
datasets, ir_datasets, protobuf (CVE-2026-0994 eliminated).

Verified:
- BGE-M3 loads via sentence-transformers (FlagEmbedding not needed)
- Ruff handles formatting + import sorting (black/isort obsolete)
- All tests pass, CUDA works, pip check clean
- pip-audit: 0 CVEs (down from 1)

Cleanup also removed vestigial [tool.black] and [tool.isort] configs.

Disk savings: ~500-550MB
Dependency reduction: 197 → ~172 packages (-13%)
