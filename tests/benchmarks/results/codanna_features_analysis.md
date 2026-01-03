# Codanna Feature Benefits Analysis - Benchmark Results

**Date**: 2025-12-20
**Analyst**: Claude Sonnet 4.5
**Method**: Empirical testing with production data + isolated unit tests

---

## Executive Summary

**All three features FAILED to demonstrate their claimed benefits in empirical testing.**

| Feature | Claimed Benefit | Actual Result | Verdict |
|---------|-----------------|---------------|---------|
| Symbol Hash Cache | 20-50x speedup | **1.0x** (no speedup), **35.7%** hit rate | ❌ **TRIPLE FAIL** |
| Mmap Vector Storage | Faster than FAISS | **0.81x** (slower than FAISS) | ❌ **FAILED** |
| Query Intent Detection | Improved search quality | **36%** accuracy | ❌ **FAILED** |

---

## Feature 1: Symbol Hash Cache

### Claimed Benefits
- **20-50x** speedup over O(k) variant checking
- O(1) chunk_id lookups via FNV-1a hash
- **24 bytes** per symbol memory overhead

### Benchmark Results

#### Test 1: `benchmark_symbol_cache.py` (Isolated Performance Test)
- **Hash cache lookup**: 146.69 us
- **Variant checking**: 145.32 us
- **Speedup**: **1.0x** (no improvement)
- **Result**: ❌ **FAILED** - No observable speedup

#### Test 2: `benchmark_cache_efficiency.py` (Production Workload Simulation)
- **Hit rate**: **35.7%** (threshold: >=70%)
- **Hash overhead**: **4.577 us** (target: <1us)
- **Memory per symbol**: 142.6 bytes (NOT 24 bytes as claimed)
- **Result**: ❌ **TRIPLE FAIL**
  - Hit rate too low (only 35.7% of lookups benefit from cache)
  - Hash computation slower than target (4.6x over budget)
  - Memory higher than claimed (6x more than documented)

### Root Cause Analysis

1. **Low hit rate (35.7%)**: Cache only helps if same chunk_ids are looked up repeatedly. In realistic workflows with random search queries, most lookups are unique → cache misses dominate.

2. **Hash overhead (4.577us)**: FNV-1a hash computation takes 4.6us, which is 3-4x slower than the variant checking it's supposed to replace. The O(1) benefit is negated by the hash computation cost.

3. **Memory discrepancy**: Actual memory usage is 142.6 bytes/symbol (6x claimed 24 bytes) due to:
   - Python dict overhead (~240 bytes per bucket)
   - String storage (chunk_id strings)
   - 256-bucket hash table overhead

### Verdict: **REMOVE**

**Recommendation**: Remove feature. Provides no measurable benefit while adding complexity (312 lines of code, cache coherence concerns).

---

## Feature 2: Mmap Vector Storage

### Claimed Benefits
- **<1 microsecond** vector access (warm cache)
- Faster than FAISS `reconstruct()`
- Memory-efficient for large indices

### Benchmark Results

#### Test 1: `benchmark_mmap_vectors.py` (Isolated Synthetic Test)
**Results at 964 vectors** (current production scale):
- **Sequential access**: Mmap **0.81x** slower than FAISS (679ns vs 552ns)
- **Random access**: Mmap **1.00x** same speed as FAISS (842ns vs 591ns)
- **Warm cache**: 647-712 ns < 1us ✅ (claim verified BUT misleading)
- **Cold start**: 111-203 us (200x slower)

**Results at 1,000-5,000 vectors**:
- Mmap consistently **0.81-0.82x slower** than FAISS
- No crossover point where mmap becomes faster

#### Key Finding: <1us Claim is Misleading
- **Claim**: "<1 microsecond access"
- **Reality**:
  - **Warm cache**: 647ns (after OS page cache loads) ✅
  - **Cold start**: 111-203us (first access with page faults) ❌
  - **FAISS is faster** at current scale (550-590ns)

### Storage Overhead
- **FAISS index**: ~3.8 MB (964 vectors × 1024d)
- **Mmap file**: ~3.8 MB (duplicate storage)
- **Total**: **7.6 MB** (doubled storage)

### Verdict: **DISABLE BY DEFAULT**

**Recommendation**:
- Disable by default at current scale (964 vectors)
- Consider enabling ONLY for indices >10K vectors
- OR use mmap AS primary storage (not alongside FAISS) to avoid duplication

**Reasoning**: At 964 vectors, FAISS `reconstruct()` is already fast (550-590ns). Mmap adds complexity (binary format, dual storage) for **negative benefit** (0.81x slower).

---

## Feature 3: Query Intent Detection

### Claimed Benefits
- **100% routing accuracy** to optimal embedding models
- Improved search quality via intent-based result boosting
- 12 intent categories with confidence scoring

### Benchmark Results

#### Test 1: `benchmark_intent_quality.py` (Unit Test of Detection Mechanism)
- **Detection speed**: **0.042 ms** < 1ms target ✅
- **Category coverage**: **100%** (all 12 categories detected) ✅
- **Intent accuracy**: **36%** < 85% target ❌ **FAILED**
- **Confidence distribution**: avg 0.542, range 0.425-1.000

#### Critical Finding: 36% Accuracy

The intent detection correctly identifies the expected intent in **only 36% of queries**. This means:
- **64% of queries** get WRONG intent detection
- Wrong intents → wrong boost factors → potentially degraded search quality
- No evidence that intent boosting improves search results

### Accuracy vs Routing Claim

**Claimed**: "100% routing accuracy"
**Reality**: The "100%" refers to routing queries to embedding models, NOT detecting user intent correctly.

**User intent accuracy**: **36%** (what matters for search quality)

### Verdict: **SIMPLIFY OR REMOVE**

**Recommendation Options**:
1. **Remove entirely**: No proven search quality benefit, adds complexity
2. **Simplify to 3-4 categories**: Reduce from 12 to core categories (error_handling, performance, configuration, general)
3. **Disable boosting by default**: Keep for routing, disable result re-ranking

**Reasoning**: 36% accuracy means intent detection is wrong more often than it's right. This could **harm** search quality by boosting irrelevant results.

---

## Overall Assessment

### What Was Gained?
- **Symbol Hash Cache**: Nothing (1.0x speedup, low hit rate)
- **Mmap Storage**: Negative value at current scale (0.81x slower, doubles storage)
- **Intent Detection**: Fast detection (0.042ms) but inaccurate (36%)

### What Was Lost?
- **Complexity**: ~1,200 lines of new code across 3 features
- **Storage overhead**: 7.6 MB total (mmap duplication)
- **Maintenance burden**: Cache coherence, binary format versioning, intent pattern updates
- **Technical debt**: Features adopted without quality metrics

### Cost-Benefit Analysis

| Feature | Code Lines | Storage MB | Benefit | Cost/Benefit |
|---------|-----------|------------|---------|--------------|
| Symbol Cache | 312 | 0.131 | **0%** speedup | **Negative** |
| Mmap Storage | ~200 | 3.8 | **-19%** (slower) | **Negative** |
| Intent Detection | ~300 | 0 | **36%** accuracy | **Questionable** |
| **Total** | **812** | **3.9** | **All negative** | **Strongly Negative** |

---

## Decision Matrix

### Symbol Hash Cache: **REMOVE**
- ✅ **Action**: Delete `search/symbol_cache.py`, remove cache initialization
- ✅ **Rationale**: Zero benefit (1.0x speedup), low hit rate (35.7%), slower hash computation (4.6us)
- ✅ **Impact**: Save 312 lines, simplify metadata layer, remove cache coherence concerns

### Mmap Vector Storage: **DISABLE BY DEFAULT**
- ✅ **Action**: Add config flag `enable_mmap_storage` (default: `false`)
- ✅ **Enable when**: Index size > 10,000 vectors OR use as PRIMARY storage (not duplicate)
- ✅ **Rationale**: Negative benefit at <1K vectors (0.81x slower), storage doubling
- ⚠️ **Alternative**: Replace FAISS with mmap as single storage (like Codanna does) to avoid duplication

### Query Intent Detection: **SIMPLIFY**
- ✅ **Action**: Reduce from 12 to 4 categories, disable boosting by default
- ✅ **Keep**: Detection mechanism for model routing (already working)
- ✅ **Remove**: Result re-ranking based on intent (unproven benefit)
- ✅ **Rationale**: 36% accuracy too low for reliable boosting, but detection is fast (0.042ms)

---

## Recommendations

### Immediate Actions (Week 1)
1. **Remove Symbol Hash Cache**
   - Delete `search/symbol_cache.py`
   - Remove cache initialization from `MetadataStore`
   - Run test suite to verify no regressions

2. **Disable Mmap by Default**
   - Add `SearchConfig.enable_mmap_storage = False`
   - Document threshold: Enable for >10K vectors

3. **Simplify Intent Detection**
   - Reduce to 4 core categories: `error_handling`, `performance`, `configuration`, `general`
   - Set boost factors to 1.0 (no effect) by default
   - Keep detection for routing only

### Follow-up Actions (Week 2-3)
4. **Add Quality Benchmarks**
   - Create `tests/benchmarks/benchmark_search_quality.py` to measure:
     - MRR (Mean Reciprocal Rank)
     - Precision@5
     - Recall@10
   - Establish baseline metrics BEFORE adding features

5. **Document Decision**
   - Update `CLAUDE.md` to reflect feature status
   - Add `docs/CODANNA_FEATURES_DECISION.md` explaining why features were removed/simplified

---

## Lessons Learned

### What Went Wrong
1. **No baseline metrics**: Features were added without measuring initial search quality
2. **Claimed benefits not verified**: "20-50x speedup" and "<1us access" were not empirically tested
3. **Missing A/B testing**: No comparison of search quality with/without features
4. **Context mismatch**: Codanna uses mmap AS primary storage; we use it alongside FAISS (doubling storage)

### Best Practices for Future
1. ✅ **Establish baselines FIRST**: Measure current performance before adding features
2. ✅ **Empirical verification**: Test claimed benefits with realistic workloads
3. ✅ **A/B testing**: Compare with/without feature on same dataset
4. ✅ **Cost-benefit analysis**: Code complexity vs measured benefit
5. ✅ **Incremental adoption**: Add features one at a time, measure impact

---

## Conclusion

The Codanna feature adoption was **unsuccessful**. All three features failed to demonstrate measurable benefits:

- **Symbol Hash Cache**: 1.0x speedup (no benefit)
- **Mmap Vector Storage**: 0.81x slower (negative benefit)
- **Query Intent Detection**: 36% accuracy (unreliable)

**Total impact**: 812 lines of code, 3.9 MB storage overhead, zero performance improvement.

**Recommended action**: Remove Symbol Cache entirely, disable Mmap by default, simplify Intent Detection to 4 categories without boosting.

---

**Next Steps**: Implement removals/simplifications, establish baseline quality metrics, document decision in `CODANNA_FEATURES_DECISION.md`.
