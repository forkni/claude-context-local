# Auto-Reindex Bug Fixes Test Guide

This document explains how to test the two critical auto-reindex bug fixes:

1. **Fix 1**: `max_age_minutes` now respects config (60 min) instead of hardcoded 5
2. **Fix 2**: Multi-model cleanup clears ALL models before reindex, not just one

---

## Quick Test (Manual Script)

**Recommended for quick verification:**

```bash
# Activate venv
.venv\Scripts\activate

# Run manual test script
python tools/test_auto_reindex_fixes.py
```

**Expected Output**:

```
======================================================================
Auto-Reindex Bug Fixes Verification
======================================================================

TEST 1: Verify max_age_minutes Config
======================================================================
Config max_index_age_minutes: 60.0 minutes
✅ PASS: Using config value of 60.0 minutes

TEST 2: Verify Multi-Model Cleanup
======================================================================
Step 1: Loading all 3 embedding models...
  Loaded models: ['qwen3', 'bge_m3', 'coderankembed']
  Total: 3 models

Step 2: VRAM usage BEFORE cleanup:
  Allocated: 14.52 GB
  Reserved:  15.47 GB
  Utilization: 68.8%

Step 3: Simulating auto-reindex cleanup...
  Clearing 3 cached embedder(s): ['qwen3', 'bge_m3', 'coderankembed']
  ✓ Embedder pool cleared
  ✓ ModelPoolManager singleton reset
  ✓ Garbage collection completed
  ✓ GPU cache cleared

Step 4: VRAM usage AFTER cleanup:
  Allocated: 0.02 GB
  Reserved:  0.12 GB
  VRAM freed: 15.35 GB

✅ PASS: Multi-model cleanup freed significant VRAM
   Expected: >5 GB for 3 models, Actual: 15.35 GB

======================================================================
TEST SUMMARY
======================================================================
✅ max_age_minutes Config: PASS
✅ Multi-Model Cleanup: PASS

✅ OVERALL: PASSED
   All fixes verified successfully!
```

---

## Full Integration Tests (Pytest)

**For comprehensive testing with mocking and edge cases:**

```bash
# Run integration tests
pytest tests/integration/test_auto_reindex_fixes.py -v -s
```

**What it tests**:

### Test Class 1: `TestMaxAgeMinutesConfigRespect`
- ✅ Uses config default (60 min) when parameter not specified
- ✅ Explicit parameter overrides config
- ✅ No reindex triggered before timeout expires

### Test Class 2: `TestMultiModelCleanupBeforeReindex`
- ✅ Clears all 3 models before reindex (not just 1)
- ✅ Logs multi-model cleanup messages
- ✅ Continues gracefully if cleanup fails

### Test Class 3: `TestNoOOMDuringReindex`
- ✅ VRAM freed before reindex starts
- ✅ Reindex completes without OOM
- ✅ Models reloaded after cleanup

---

## Manual Verification (Real MCP Server)

**Test auto-reindex in production environment:**

### Step 1: Check Config

```bash
# Verify config has 60-minute timeout
cat search_config.json | grep max_index_age_minutes
# Should show: "max_index_age_minutes": 60.0
```

### Step 2: Load All Models

```bash
# Start MCP server
python -m mcp_server.server

# In Claude Code, run 3 searches to load all models:
/search_code "error handling"        # Routes to Qwen3
/search_code "configuration setup"   # Routes to BGE-M3
/search_code --model_key coderankembed "data structures"  # Forces CodeRankEmbed
```

### Step 3: Check VRAM Before Cleanup

```bash
# Check memory status
/get_memory_status

# Should show ~15 GB VRAM allocated with 3 models loaded
```

### Step 4: Trigger Auto-Reindex

**Option A: Wait 60 minutes (slow)**
- Make a small edit to any indexed file
- Wait 60+ minutes
- Run another search - auto-reindex should trigger

**Option B: Temporarily reduce timeout (fast)**
```json
// Edit search_config.json
{
  "performance": {
    "max_index_age_minutes": 0.1  // 6 seconds for testing
  }
}

// Restart MCP server
// Wait 6+ seconds after last index
// Run a search - should trigger auto-reindex
```

### Step 5: Verify Cleanup in Logs

**Look for these log messages:**

```
Auto-reindexing ... (index older than 60.0 minutes)  ← Config value used
Freeing VRAM before auto-reindex (multi-model cleanup)...
Clearing 3 cached embedder(s) before reindex: ['qwen3', 'bge_m3', 'coderankembed']
Embedder pool cleared - VRAM released
ModelPoolManager singleton reset
Garbage collection completed
GPU cache cleared
Multi-model VRAM cleanup completed successfully
```

### Step 6: Verify No OOM

**Reindex should complete without errors:**

```
✓ No "OutOfMemoryError" in logs
✓ Reindex completes successfully
✓ Search still works after reindex
```

---

## Troubleshooting

### Issue: Multi-model test skipped

**Error**: `Multi-model mode disabled - skipping test`

**Solution**:
```bash
set CLAUDE_MULTI_MODEL_ENABLED=true
# Restart MCP server
```

### Issue: VRAM not freed

**Possible causes**:
1. PyTorch/CUDA not available → Script will warn, cleanup still works
2. Models not loaded initially → Run searches to trigger loading first
3. Other process holding GPU memory → Check `nvidia-smi`

**Diagnostic**:
```bash
# Check GPU usage outside Python
nvidia-smi

# Should show low usage after cleanup
```

### Issue: Config shows 5 instead of 60

**Problem**: `search_config.json` not being read

**Solution**:
```bash
# Verify file exists
ls search_config.json

# Check JSON syntax
python -c "import json; json.load(open('search_config.json'))"

# Restart MCP server to reload config
```

---

## Expected Results Summary

| Test | Before Fix | After Fix |
|------|------------|-----------|
| **max_age_minutes default** | Hardcoded 5 minutes | Config value (60 minutes) |
| **VRAM freed before reindex** | ~7.5 GB (1 model) | ~15 GB (all 3 models) |
| **OOM during reindex** | High risk | No OOM |
| **Auto-reindex frequency** | Every 5 min (too often) | Every 60 min (configurable) |

---

## Files Modified by Fixes

### Fix 1: Config Respect
- **File**: `mcp_server/tools/search_handlers.py:414-417`
- **Change**: `get_config().performance.max_index_age_minutes` instead of hardcoded `5`

### Fix 2: Multi-Model Cleanup
- **File**: `search/incremental_indexer.py:779-819`
- **Change**: Clear ALL embedders via `state.clear_embedders()` + `reset_pool_manager()`
- **Added import**: `gc` module for garbage collection

---

## Next Steps

After verifying fixes:

1. ✅ Run manual test script → Quick verification
2. ✅ Run pytest integration tests → Comprehensive coverage
3. ✅ Test in production → Real MCP environment
4. ✅ Monitor logs during auto-reindex → Verify cleanup messages
5. ✅ Check VRAM usage → Should be ~0 GB after cleanup

**All tests passing?** → Fixes verified! Auto-reindex is now safe with multi-model mode.
