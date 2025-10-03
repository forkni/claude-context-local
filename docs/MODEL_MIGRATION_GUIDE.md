# Model Migration Guide: Gemma → BGE-M3

## 📊 Should You Upgrade?

### ✅ Upgrade to BGE-M3 if

- You have **16GB+ VRAM** available
- You need **3-6% better retrieval accuracy**
- You want **hybrid search capabilities** (dense + sparse + multi-vector)
- You're building **production systems** requiring high accuracy
- You have **large codebases** (>10,000 files)

### ⏸️ Stay on Gemma if

- You have **<8GB VRAM**
- Current performance meets your needs
- You prioritize **speed over accuracy**
- You're working on **smaller projects**
- Hardware constraints are important

---

## 📈 Performance Comparison

| Metric | Gemma-300m | BGE-M3 | Change |
|--------|------------|---------|--------|
| **Token Efficiency** | 97.1% savings | 93.4% savings | Slightly lower |
| **F1-Score (Accuracy)** | 0.280 | **0.318** | 📈 **+13.6% better** |
| **Precision** | - | 0.290 | Higher |
| **Recall** | - | 0.400 | Better coverage |
| **Best Search Method** | Dense (F1=0.385) | Dense (F1=0.378) | Comparable |
| **Index Build Time** | 27.28s | 39.46s | 44% slower |
| **Embedding Dimension** | 768 | 1024 | Higher capacity |
| **Context Length** | 2048 tokens | **8192 tokens** | 📈 4x longer |
| **Memory Usage** | 4-8GB VRAM | 8-16GB VRAM | ⚠️ Higher |
| **Hybrid Search** | Dense only | **Dense + Sparse + Multi-vector** | 🎯 Advanced |

**Key Benefits:**

- **Better semantic understanding** - More nuanced code relationships
- **Longer context** - Handle larger code files without truncation
- **Hybrid search** - Combine semantic + exact keyword matching
- **Production-proven** - One of the most popular open-source models

---

## 🚀 Migration Steps

### Step 0: Verify PyTorch 2.6.0+ (Required for BGE-M3)

BGE-M3 requires PyTorch 2.6.0+ due to torch.load security improvements.

**Note:** New installations via `install-windows.bat` automatically include PyTorch 2.6.0+. This step is only needed for older installations.

**Verification:**

```bash
.venv\Scripts\python.exe -c "import torch; print('PyTorch:', torch.__version__)"
# Should show: PyTorch: 2.6.0+cu118 or higher
```

**If upgrade needed:**

```bash
# Option 1: Reinstall (recommended)
install-windows.bat

# Option 2: Manual upgrade
.venv\Scripts\uv.exe pip install "torch==2.6.0" "torchvision==0.21.0" "torchaudio==2.6.0" --index-url https://download.pytorch.org/whl/cu118
```

**Why?** PyTorch 2.6.0 fixes critical security vulnerabilities in model loading that BGE-M3 depends on.

**Supported CUDA versions:** 11.8, 12.4, 12.6 (CUDA 12.1 systems use CUDA 11.8 build, fully compatible)

### Step 1: Check Hardware Requirements

```bash
# Check available VRAM
.venv\Scripts\python.exe -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only'); print('VRAM:', torch.cuda.get_device_properties(0).total_memory // (1024**3), 'GB' if torch.cuda.is_available() else '')"
```

**Minimum:** 8GB VRAM
**Recommended:** 16GB VRAM for optimal performance

### Step 2: Backup Current Indexes (Optional)

```bash
# Backup existing indexes
xcopy /E /I "%USERPROFILE%\.claude-context-mcp\storage" "%USERPROFILE%\.claude-context-mcp\storage_backup"
```

### Step 3: Switch Model via Interactive Menu

**Option A: Interactive Menu** (Recommended)

```bash
# Launch the menu
start_mcp_server.bat

# Navigate:
# Main Menu → 3 (Search Configuration) → 4 (Select Embedding Model) → 2 (BGE-M3)
```

**Option B: Environment Variable**

```bash
# Set environment variable
set CLAUDE_EMBEDDING_MODEL=BAAI/bge-m3

# Restart MCP server for changes to take effect
```

**Option C: Configuration File**

```bash
# Via Python
.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding_model_name = 'BAAI/bge-m3'; mgr.save_config(cfg); print('Model updated to BGE-M3')"
```

### Step 4: Clear Old Indexes

When prompted by the menu, select **"Yes"** to clear old indexes, or manually:

```bash
.venv\Scripts\python.exe -c "from pathlib import Path; import shutil; storage = Path.home() / '.claude-context-mcp' / 'storage'; cleared = sum(1 for p in storage.glob('*/faiss_index') if p.exists() and shutil.rmtree(p.parent)); print(f'Cleared {cleared} project indexes')"
```

**Why?** Gemma (768 dim) and BGE-M3 (1024 dim) are incompatible. Old indexes must be rebuilt.

### Step 5: Re-index Your Projects

```bash
# Using Claude Code
/index_directory "C:\Your\Project\Path"

# Or via tools
.venv\Scripts\python.exe tools\index_project.py
```

**Expected Time:**

- Small project (<1,000 files): 5-10 minutes
- Medium project (1,000-10,000 files): 30-60 minutes
- Large project (>10,000 files): 1-3 hours

### Step 6: Verify the Switch

```bash
# Check current model
.venv\Scripts\python.exe -c "from search.config import get_search_config; print('Current model:', get_search_config().embedding_model_name)"

# Test search
/search_code "your test query"
```

---

## 🔄 Rollback to Gemma

If you need to revert:

```bash
# Via menu: start_mcp_server.bat → 3 → 4 → 1
# Or via command:
.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding_model_name = 'google/embeddinggemma-300m'; mgr.save_config(cfg); print('Rolled back to Gemma')"

# Re-index projects
/index_directory "your-project-path"
```

---

## 🐛 Troubleshooting

### Issue: "Dimension mismatch detected"

**Symptom:** Warning about stored index (768) vs current model (1024)

**Solution:**

```bash
# Clear the specific project index
rm -rf "%USERPROFILE%\.claude-context-mcp\storage\<project-hash>\faiss_index"

# Re-index
/index_directory "project-path"
```

### Issue: Out of Memory (OOM)

**Symptom:** CUDA out of memory error when loading BGE-M3

**Solutions:**

1. **Close other GPU applications** (browsers, games, etc.)
2. **Reduce batch size** in indexing
3. **Use CPU mode:** Set `CUDA_VISIBLE_DEVICES=` before starting
4. **Rollback to Gemma** if VRAM is insufficient

### Issue: Slower Indexing

**Symptom:** BGE-M3 indexing takes longer than Gemma

**Expected:** BGE-M3 is ~10% slower due to larger model size. This is normal.

**Optimization:**

```bash
# Use smaller batch sizes for better memory management
# Edit tools/index_project.py and reduce batch_size parameter
```

### Issue: No Performance Improvement

**Symptom:** Search quality seems the same after switching

**Checks:**

1. Verify model switch: Check menu shows BGE-M3
2. Ensure re-indexing completed successfully
3. Test on semantic queries (not just exact keyword matches)
4. BGE-M3 shines with **semantic understanding**, not exact matches

---

## 📚 Additional Resources

- **Model Comparison:** `docs/Local_embedding_models.txt` - Full technical analysis
- **Configuration Guide:** `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`
- **Installation Guide:** `docs/INSTALLATION_GUIDE.md`
- **Upgrade Plan:** `docs/BGE_M3_UPGRADE_PLAN.md` - Technical implementation details

---

## ❓ FAQ

**Q: Can I switch models without re-indexing?**
A: No. Different models produce incompatible embeddings (768 vs 1024 dimensions).

**Q: Will my old searches still work?**
A: Yes, but you need to re-index first. The search API remains unchanged.

**Q: Can I use both models for different projects?**
A: Currently, the model is global. All projects use the same configured model.

**Q: How much better is BGE-M3 really?**
A: 3-6% average improvement on MTEB retrieval benchmarks. More noticeable on complex semantic queries.

**Q: Does BGE-M3 work on CPU?**
A: Yes, but it's slower. GPU is strongly recommended for reasonable performance.

**Q: Can I use other models besides Gemma and BGE-M3?**
A: Yes! Select option 3 (Custom model path) in the menu and enter any HuggingFace model path compatible with sentence-transformers.

---

## 🎯 Quick Reference

| Action | Command |
|--------|---------|
| **View current model** | Menu → 3 → 1 |
| **Switch to BGE-M3** | Menu → 3 → 4 → 2 |
| **Switch to Gemma** | Menu → 3 → 4 → 1 |
| **Re-index project** | `/index_directory "path"` |
| **Check dimensions** | See model info in menu |
| **Clear all indexes** | Menu → 3 → 4 → (select model) → Yes |

---

*Last Updated: 2025-01-30*
*Version: 0.4.0*
