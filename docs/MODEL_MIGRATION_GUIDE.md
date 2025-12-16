# Model Migration Guide: Comprehensive Model Selection & Switching

## 📊 Available Models (4 Total)

| Model | Dimensions | VRAM | Best For | Special Features |
|-------|------------|------|----------|------------------|
| **EmbeddingGemma-300m** | 768 | 4-8GB | Speed, low VRAM | Fast inference, default model |
| **BGE-M3** ⭐ | 1024 | 3-4GB | Production baseline | Hybrid search (dense + sparse + multi-vector) |
| **Qwen3-0.6B** 🆕 | 1024 | 2.3GB | Best value | Instruction tuning, code-optimized |
| **Qwen3-4B** 🆕 | 1024* | 8-10GB | Best quality | MRL enabled, 4B quality @ 0.6B storage |
| **CodeRankEmbed** | 768 | 2GB | Code-specific | Specialized code retrieval |

*Qwen3-4B uses Matryoshka Representation Learning (MRL): full dimension 2560 truncated to 1024

---

## 🎯 VRAM Tier Recommendations

The system automatically recommends models based on your available GPU memory:

### Minimal Tier (<6GB VRAM)

- **Recommended:** EmbeddingGemma-300m OR CodeRankEmbed
- **Features:** Multi-model routing DISABLED, Neural reranking DISABLED
- **Use Case:** Limited hardware, single-model setup

### Laptop Tier (6-10GB VRAM)

- **Recommended:** BGE-M3 OR Qwen3-0.6B
- **Features:** Multi-model routing ENABLED, Neural reranking ENABLED
- **Use Case:** Balanced performance, production-ready

### Desktop Tier (10-18GB VRAM)

- **Recommended:** Qwen3-4B (primary) + BGE-M3 + CodeRankEmbed (multi-model)
- **Features:** Full multi-model routing, Neural reranking ENABLED
- **Use Case:** Best quality, comprehensive model pool

### Workstation Tier (18GB+ VRAM)

- **Recommended:** Full 3-model pool with neural reranking
- **Features:** All features ENABLED, maximum quality
- **Use Case:** Production deployments, large codebases

---

## 📈 Performance Comparison

### Accuracy & Speed

| Model | F1-Score | Precision | Recall | Context Length | Speed |
|-------|----------|-----------|--------|---------------|-------|
| EmbeddingGemma-300m | 0.280 | - | - | 2048 tokens | ⚡ Fastest |
| BGE-M3 | **0.318** | 0.290 | 0.400 | **8192 tokens** | Fast |
| Qwen3-0.6B | 0.310 | 0.285 | 0.390 | 8192 tokens | Fast |
| Qwen3-4B | **0.330** | **0.300** | **0.410** | 8192 tokens | Moderate |
| CodeRankEmbed | 0.295 | 0.275 | 0.380 | 4096 tokens | ⚡ Very Fast |

### VRAM Usage

| Model | Model Loading | + Multi-Model Routing | + Neural Reranking | Total (Max) |
|-------|---------------|----------------------|-------------------|-------------|
| EmbeddingGemma-300m | 4-8GB | +0.5GB | +1.5GB | 10GB |
| BGE-M3 | 3-4GB | +5.3GB (3 models) | +1.5GB | 10GB |
| Qwen3-0.6B | 2.3GB | +5.3GB | +1.5GB | 9GB |
| Qwen3-4B | 8-10GB | +5.3GB | +1.5GB | 15GB |
| CodeRankEmbed | 2GB | +5.3GB | +1.5GB | 9GB |

**Note:** Multi-model routing loads all 3 models (BGE-M3, Qwen3, CodeRankEmbed) = 5.3GB additional VRAM

---

## 🚀 Quick Start: Choosing Your Model

### Decision Tree

```
What's your VRAM?
│
├─ <6GB  ──────► EmbeddingGemma-300m (fast, low VRAM)
│                OR CodeRankEmbed (code-specific, even lower VRAM)
│
├─ 6-10GB ─────► Qwen3-0.6B (best value, instruction tuning)
│                OR BGE-M3 (production baseline, hybrid search)
│
├─ 10-18GB ────► Qwen3-4B (best quality, MRL enabled)
│                + Multi-model routing recommended
│
└─ 18GB+ ──────► Full 3-model pool + neural reranking
                 (maximum quality, all features)
```

### Use Case Recommendations

| Use Case | Primary Model | Secondary (Multi-Model) | Why |
|----------|--------------|------------------------|-----|
| **General Code Search** | BGE-M3 | Qwen3-0.6B, CodeRankEmbed | Balanced accuracy, hybrid search |
| **Code-Specific Retrieval** | CodeRankEmbed | BGE-M3, Qwen3-0.6B | Specialized for code patterns |
| **Best Quality** | Qwen3-4B | BGE-M3, CodeRankEmbed | Highest accuracy, MRL enabled |
| **Limited Hardware** | EmbeddingGemma-300m | None (single-model) | Fast, low VRAM |
| **Production Baseline** | BGE-M3 | Qwen3-0.6B, CodeRankEmbed | Proven, reliable, hybrid search |

---

## 🔄 Migration Steps (Model Switching)

### Step 0: Verify PyTorch 2.6.0+ (Required)

All models require PyTorch 2.6.0+ due to security improvements.

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

**Supported CUDA versions:** 11.8, 12.4, 12.6 (CUDA 12.1 systems use CUDA 11.8 build)

### Step 1: Check Hardware Requirements

```bash
# Check available VRAM
.venv\Scripts\python.exe -c "import torch; print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only'); print('VRAM:', torch.cuda.get_device_properties(0).total_memory // (1024**3), 'GB' if torch.cuda.is_available() else '')"
```

**Choose model based on VRAM tier (see recommendations above)**

### Step 2: Switch Model via Interactive Menu

**Option A: Interactive Menu** (Recommended)

```bash
# Launch the menu
start_mcp_server.bat

# Navigate:
# Main Menu → 3 (Search Configuration) → 4 (Select Embedding Model)
# Options:
#   1. EmbeddingGemma-300m (768d, 4-8GB VRAM)
#   2. BGE-M3 (1024d, 3-4GB VRAM) ← Production baseline
#   3. Qwen3-0.6B (1024d, 2.3GB VRAM) ← Best value
#   4. Qwen3-4B (1024d, 8-10GB VRAM) ← Best quality
#   5. CodeRankEmbed (768d, 2GB VRAM) ← Code-specific
#   6. Custom model path
```

**Option B: Environment Variable**

```bash
# Set environment variable (choose one)
set CLAUDE_EMBEDDING_MODEL=google/embeddinggemma-300m
set CLAUDE_EMBEDDING_MODEL=BAAI/bge-m3
set CLAUDE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B
set CLAUDE_EMBEDDING_MODEL=Qwen/Qwen3-Embedding-4B
set CLAUDE_EMBEDDING_MODEL=nvidia/NV-Embed-v2

# Restart MCP server for changes to take effect
```

**Option C: Configuration File**

```bash
# Via Python
.venv\Scripts\python.exe -c "from search.config import SearchConfigManager; mgr = SearchConfigManager(); cfg = mgr.load_config(); cfg.embedding_model_name = 'BAAI/bge-m3'; mgr.save_config(cfg); print('Model updated to BGE-M3')"
```

### Step 3: Handle Index Clearing (Per-Model Indices)

**Good News:** The system now supports **per-model index storage** (v0.4.0+).

**What this means:**

- Switching between models is **instant (<150ms)**
- Each model stores indices independently
- **No re-indexing needed** when switching back to a previously used model

**First-time model use:** When prompted, select **"Yes"** to index with the new model.

**Dimension compatibility:**

| From Dimension | To Dimension | Action |
|---------------|--------------|---------|
| 768 (Gemma/CodeRank) | 1024 (BGE-M3/Qwen3) | Automatic new index created |
| 1024 (BGE-M3/Qwen3) | 768 (Gemma/CodeRank) | Automatic new index created |
| Same dimension | Same dimension | Instant switch (<150ms) |

### Step 4: Re-index Your Projects (First Time Only)

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

**Progress Bars (v0.6.1+):** Real-time visual feedback during chunking and embedding phases

### Step 5: Verify the Switch

```bash
# Check current model
.venv\Scripts\python.exe -c "from search.config import get_search_config; print('Current model:', get_search_config().embedding_model_name)"

# Test search
/search_code "your test query"
```

---

## 🎁 New Qwen3 Features (v0.6.4+)

### Instruction Tuning

**What:** Code-optimized query instructions improve retrieval precision by 1-5%

**Automatic application:**

```
"Instruct: Retrieve source code implementations matching the query\nQuery: {your_query}"
```

**Configuration:**

- `instruction_mode="custom"` - Code-optimized (default for Qwen3)
- `instruction_mode="prompt_name"` - Generic prompts

**When to use:**

- Custom mode: Code search, implementation discovery
- Prompt_name mode: General semantic search

### Matryoshka MRL (Qwen3-4B only)

**What:** Reduces storage 2x with <1.5% quality drop

**How it works:**

- Full model dimension: 2560
- Truncated to: 1024 (same as Qwen3-0.6B and BGE-M3)
- Keeps 4B model quality (36 layers)

**Benefits:**

- 50% storage reduction
- Same dimension as other 1024d models (instant switching)
- Best quality with reasonable VRAM (8-10GB)

**Configuration:** Enabled by default for Qwen3-4B (`truncate_dim=1024`)

---

## 🐛 Troubleshooting

### Issue: "Dimension mismatch detected"

**Symptom:** Warning about stored index (768) vs current model (1024)

**Solution:** Per-model indices automatically handle this. If error persists:

```bash
# Clear the specific model's index
.venv\Scripts\python.exe -c "from pathlib import Path; import shutil; [shutil.rmtree(p.parent) for p in (Path.home() / '.claude_code_search' / 'projects').glob('*/faiss_index_<dimension>d')]; print('Cleared')"

# Re-index
/index_directory "project-path"
```

### Issue: Out of Memory (OOM)

**Symptom:** CUDA out of memory error when loading model

**Solutions:**

1. **Check VRAM tier:** Use `/get_memory_status` to check current VRAM
2. **Switch to smaller model:** Follow VRAM tier recommendations
3. **Close other GPU applications** (browsers, games, etc.)
4. **Disable multi-model routing:** Set `CLAUDE_MULTI_MODEL_ENABLED=false`
5. **Disable neural reranking:** Set `CLAUDE_RERANKER_ENABLED=false`
6. **Use CPU mode:** Set `CUDA_VISIBLE_DEVICES=` before starting

### Issue: Slower Indexing

**Symptom:** Indexing takes longer than expected

**Expected behavior:**

- Qwen3-4B: ~10-15% slower than Qwen3-0.6B (larger model)
- BGE-M3: ~10% slower than Gemma (larger embeddings)
- CodeRankEmbed: Fastest (smallest model)

**Optimization:**

```bash
# Reduce batch size in tools/batch_index.py
# VRAM tier system automatically adjusts batch sizes
```

### Issue: No Quality Improvement

**Symptom:** Search quality seems unchanged after switching

**Checks:**

1. Verify model switch: `/get_search_config_status`
2. Ensure re-indexing completed successfully
3. Test semantic queries (not exact keyword matches)
4. Qwen3/BGE-M3 excel at **semantic understanding**, not exact matches

---

## 📚 Additional Resources

- **Configuration Guide:** `docs/HYBRID_SEARCH_CONFIGURATION_GUIDE.md`
- **Installation Guide:** `docs/INSTALLATION_GUIDE.md`
- **Advanced Features:** `docs/ADVANCED_FEATURES_GUIDE.md`
- **MCP Tools Reference:** `docs/MCP_TOOLS_REFERENCE.md`

---

## ❓ FAQ

**Q: Can I switch models without re-indexing?**
A: Yes! Per-model index storage (v0.4.0+) allows instant switching (<150ms) between previously indexed models.

**Q: Will my old searches still work?**
A: Yes. The search API is unchanged. Only embeddings differ between models.

**Q: Can I use different models for different projects?**
A: Currently, the model is global. All projects use the same configured model. However, per-model indices allow instant switching.

**Q: How much better is Qwen3-4B really?**
A: ~4% improvement over BGE-M3, ~18% over Gemma. More noticeable on complex semantic queries.

**Q: Does multi-model routing work with all models?**
A: Yes, but requires 6-10GB VRAM minimum (Laptop tier). Minimal tier (<6GB) should disable multi-model routing.

**Q: What's the best model for production?**
A: **BGE-M3** for balanced quality/speed, **Qwen3-4B** for maximum quality (if VRAM allows).

**Q: Can I use custom models?**
A: Yes! Select option 6 (Custom model path) in the menu and enter any HuggingFace model path compatible with sentence-transformers.

---

## 🎯 Quick Reference

| Action | Command |
|--------|---------|
| **View current model** | Menu → 3 → 1 |
| **Switch model** | Menu → 3 → 4 → (select model) |
| **Check VRAM tier** | `/get_memory_status` |
| **Re-index project** | `/index_directory "path"` |
| **Check dimensions** | See model info in menu |
| **Instant switch** | Already indexed? <150ms switch! |

---

*Last Updated: 2025-12-16*
*Version: 0.6.4*
