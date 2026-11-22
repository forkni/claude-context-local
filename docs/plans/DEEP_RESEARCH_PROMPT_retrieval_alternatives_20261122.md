# Deep-research prompt: retrieval alternatives for claude-context-local

Written 2026-11-22. Paste the block below into a deep-research agent.
Background: the e-means study (arXiv 2611.09501) found no benefit at our corpus sizes.
It only replaces IVF centroid training, so it is on the rejected list inside the prompt.

---

**Task.** Find retrieval, ranking, indexing, and evaluation algorithms published or released
2023-2026 that could raise retrieval quality or cut latency in the local code-search RAG system
below. Rank them by expected benefit for *this* system, not in general.

**System (as of 2026-11).** Local MCP server, Windows 11, one RTX 4090 (24 GB). One index per
repository. Corpora are 200 to 63K chunks (most under 15K), d = 1024.

- Chunking: tree-sitter, 9 languages (Python, JS/TS, Go, Rust, C/C++, C#, GLSL). Function, class
  and method chunks; oversized nodes are packed by size. Embedding text is a composed header plus
  body, cut to a 6,000-character budget.
- Dense: F2LLM-v2-0.6B embedder. FAISS `IndexFlatIP` (exact) up to 50K vectors, `IndexIVFFlat`
  above (nlist = 4 sqrt N, nprobe = half the lists).
- Sparse: BM25 with an identifier-preserving tokenizer (no stemming) and path/symbol token
  augmentation.
- Fusion: weighted reciprocal-rank fusion (BM25 0.35 / dense 0.65, rrf_k 100). Leg depth is
  max(reranker budget, 5 x k).
- Graph: call graph from layered resolvers (AST, pyan, LibCST, basedpyright LSP) with confidence
  tags. PageRank centrality feeds a BM25 boost and the ego-graph neighbour ordering. Multi-hop
  search. The merged pool is ordered by a 1:1 interleave of hop-1 survivors and the frontier.
- Rerank: Jina listwise reranker (v3 family) on cuDNN fused attention. Before that fix it was
  95-99% of search time; now a call takes about 0.13 s.
- Evaluation: golden sets of 63 and 133 queries plus a find-similar view. Metrics are MRR,
  recall@5/10/20 and pool_hit_rate. Runs are deterministic. A/B tests are pre-registered with
  paired bootstrap confidence intervals and a +-0.02 drift band.
  Current MRR: 0.8246 (63q), 0.6718 (133q), 0.8750 (find-similar).

**Already measured and rejected here. Do not re-propose these unless the mechanism differs:**
query expansion; intent-adaptive fusion weights; TM2C2 convex fusion at deployed depth;
personalized-PageRank ego graph; BM25 reserved slots; final-pool graph reserve; graph-hop window
cap; evidence-ordered graph band; call-evidence scoring; confidence-weighted traversal;
signature-only document representation; jina-reranker-v3.5; F2LLM-v2-1.7B embedder; ego-graph
tail cut; excluding containment edges from centrality; e-means for IVF centroids (our n is below
its 1e5 floor and recall is already 0.9997).

**Areas to cover:**

- Late interaction and multi-vector retrieval (ColBERT-v2, PLAID, MUVERA).
- Learned sparse retrieval for code (SPLADE variants).
- Code-specific embedders and instruction prefixes.
- Contextual chunking and late chunking.
- Graph-RAG for repositories (RepoGraph, CodeRAG, GraphCoder and successors).
- Fusion methods beyond RRF.
- Reranker efficiency: cascades, distillation, early exit, candidate-list pruning, KV reuse for
  listwise rerankers.
- Result diversification.
- Embedding quantization with rescoring.
- Incremental index maintenance.
- Label-noise-robust evaluation, and LLM-judged relevance for small golden sets.

**For each candidate, give:**

1. The mechanism, in two sentences.
2. The evidence: paper or repo link, dataset, n, measured gain, and whether the gain is on code.
3. The pipeline stage it replaces or adds to.
4. Regime fit: corpus size, GPU memory, latency, and Windows support. Say plainly when the
   published regime does not match ours.
5. Overlap with the rejected list.
6. A cheap offline probe that could falsify it before any build: what to measure, and the pass
   threshold.
7. Cost to integrate (S, M or L).

Mark each claim as either verified from the source or reported by the authors. Give the top 5
first, then the rest in a table. Cite every source.
