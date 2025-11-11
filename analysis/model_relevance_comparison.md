# Model Relevance Comparison: Qwen3-0.6B vs BGE-M3 vs CodeRankEmbed

**Purpose**: Compare general-purpose (Qwen3, BGE-M3) vs code-specific (CodeRankEmbed) models

**Models**:
- **Qwen3-0.6B** (1024d) - General-purpose, MTEB: 75.42 (+21.9% vs BGE-M3)
- **BGE-M3** (1024d) - General-purpose baseline, MTEB: 61.85
- **CodeRankEmbed** (768d) - Code-specific, CoIR: 60.1

**Method**: Side-by-side comparison of top-5 results for 8 queries

**Search mode**: Semantic only (no BM25, no multi-hop)

---

## Query: "error handling patterns"

### Qwen3-0.6B Results

**#1** `test_extract_multiple_calls` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8270
- **Preview**: `...`

**#2** `BaseHandler` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7831
- **Preview**: `...`

**#3** `_handle_download_failure` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5239
- **Preview**: `def _handle_download_failure(self):
        """Handle download failure."""
        return {"retry_suggested": True, "error_type": "network"}...`

**#4** `test_syntax_error_handling` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5234
- **Preview**: `def test_syntax_error_handling(self, extractor, chunk_metadata):
        """Test handling of syntax errors."""
        code = """
def foo(:
    bar()  # Missing closing paren
"""
        # Should not ...`

**#5** `handle_error` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5079
- **Preview**: `def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle and format errors for API response."""
        if isinstance(error, HTTPError):
            return self.create_response({"...`

### BGE-M3 Results

**#1** `test_missing_python_error` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8160
- **Preview**: `...`

**#2** `create_response` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7656
- **Preview**: `...`

**#3** `TestErrorHandling` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6344
- **Preview**: `class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_missing_python_error(self):
        """Test handling of missing Python."""
        with patch("subprocess.run", sid...`

**#4** `test_error_handling_and_recovery` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6278
- **Preview**: `def test_error_handling_and_recovery(self, test_project_path, mock_storage_dir):
        """Test error handling and recovery mechanisms."""
        chunker = MultiLanguageChunker(str(test_project_path...`

**#5** `test_error_handling_and_recovery` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6171
- **Preview**: `def test_error_handling_and_recovery(self):
        """Test error handling and recovery in evaluation workflow."""
        # Test with invalid project path
        invalid_evaluator = TokenEfficiencyE...`

### CodeRankEmbed Results

**#1** `test_search_not_ready` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7659
- **Preview**: `...`

**#2** `test_multi_language_indexing` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7268
- **Preview**: `...`

**#3** `test_empty_code` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6129
- **Preview**: `...`

**#4** `TestHardwareCompatibility` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5741
- **Preview**: `...`

**#5** `TestErrorHandling` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.3443
- **Preview**: `class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_missing_python_error(self):
        """Test handling of missing Python."""
        with patch("subprocess.run", sid...`

### Overlap Analysis

- **All 3 models agree**: 0/5
- **Qwen3 + BGE-M3 only**: 0/5
- **Qwen3 + CodeRankEmbed only**: 0/5
- **BGE-M3 + CodeRankEmbed only**: 1/5
- **Unique to Qwen3**: 5/5
- **Unique to BGE-M3**: 4/5
- **Unique to CodeRankEmbed**: 4/5

**Qwen3 unique results:**
- `handle_error` in `unknown`
- `BaseHandler` in `unknown`
- `test_extract_multiple_calls` in `unknown`
- `test_syntax_error_handling` in `unknown`
- `_handle_download_failure` in `unknown`

**BGE-M3 unique results:**
- `create_response` in `unknown`
- `test_missing_python_error` in `unknown`
- `test_error_handling_and_recovery` in `unknown`
- `test_error_handling_and_recovery` in `unknown`

**CodeRankEmbed unique results:**
- `TestHardwareCompatibility` in `unknown`
- `test_search_not_ready` in `unknown`
- `test_empty_code` in `unknown`
- `test_multi_language_indexing` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Query: "configuration loading system"

### Qwen3-0.6B Results

**#1** `TestSearchConfigManager` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8873
- **Preview**: `...`

**#2** `test_default_values` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8497
- **Preview**: `...`

**#3** `test_config_manager_default_model` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4974
- **Preview**: `def test_config_manager_default_model(self):
        """Test that config manager loads default model."""
        import tempfile
        from pathlib import Path

        # Use temp config file to avo...`

**#4** `test_load_default_config` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4972
- **Preview**: `def test_load_default_config(self):
        """Test loading default configuration."""
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        assert isi...`

**#5** `get_config_manager` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4951
- **Preview**: `def get_config_manager(config_file: Optional[str] = None) -> SearchConfigManager:
    """Get or create global configuration manager."""
    global _config_manager
    if _config_manager is None:
     ...`

### BGE-M3 Results

**#1** `load_config` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6432
- **Preview**: `def load_config(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
            self.l...`

**#2** `load_config` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6355
- **Preview**: `def load_config(self) -> SearchConfig:
        """Load configuration from file and environment variables."""
        if self._config is not None:
            return self._config

        # Start with ...`

**#3** `_load_from_environment` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6349
- **Preview**: `def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_mapping = {
            "CLAUDE_EMBEDDING_MODEL": ("embedding_model_name", ...`

**#4** `test_load_default_config` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6280
- **Preview**: `def test_load_default_config(self):
        """Test loading default configuration."""
        manager = SearchConfigManager(self.config_file)
        config = manager.load_config()

        assert isi...`

**#5** `test_config_file_loading` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6213
- **Preview**: `def test_config_file_loading(self):
        """Test loading configuration from file."""
        # Create test config
        config_data = {
            "default_search_mode": "hybrid",
            "e...`

### CodeRankEmbed Results

**#1** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.9092
- **Preview**: `...`

**#2** `save_config` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6893
- **Preview**: `...`

**#3** `main` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6744
- **Preview**: `...`

**#4** `ConfigManager` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.3620
- **Preview**: `class ConfigManager:
    """Manages application configuration."""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config = {}
        se...`

**#5** `load_config` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.3592
- **Preview**: `def load_config(self) -> None:
        """Load configuration from file."""
        try:
            with open(self.config_file, "r") as f:
                self.config = json.load(f)
            self.l...`

### Overlap Analysis

- **All 3 models agree**: 0/5
- **Qwen3 + BGE-M3 only**: 1/5
- **Qwen3 + CodeRankEmbed only**: 0/5
- **BGE-M3 + CodeRankEmbed only**: 1/5
- **Unique to Qwen3**: 4/5
- **Unique to BGE-M3**: 3/5
- **Unique to CodeRankEmbed**: 4/5

**Qwen3 unique results:**
- `test_default_values` in `unknown`
- `TestSearchConfigManager` in `unknown`
- `test_config_manager_default_model` in `unknown`
- `get_config_manager` in `unknown`

**BGE-M3 unique results:**
- `test_config_file_loading` in `unknown`
- `load_config` in `unknown`
- `_load_from_environment` in `unknown`

**CodeRankEmbed unique results:**
- `ConfigManager` in `unknown`
- `main` in `unknown`
- `save_config` in `unknown`
- `__init__` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Query: "BM25 index implementation"

### Qwen3-0.6B Results

**#1** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.9132
- **Preview**: `...`

**#2** `_search_bm25` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7774
- **Preview**: `def _search_bm25(self, query: str, k: int, min_score: float) -> List[Tuple]:
        """Search using BM25 index."""
        start_time = time.time()
        try:
            results = self.bm25_index....`

**#3** `BM25OnlyEvaluator` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7525
- **Preview**: `class BM25OnlyEvaluator(SemanticSearchEvaluator):
    """Evaluator using only BM25 search (no dense vectors)."""

    def __init__(self, *args, **kwargs):
        kwargs.update({"bm25_weight": 1.0, "d...`

**#4** `search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7167
- **Preview**: `def search(self, query: str, k: int) -> List[RetrievalResult]:
        """Execute BM25-only search."""
        if not self.hybrid_searcher:
            raise RuntimeError("Index not built. Call build_...`

**#5** `BM25Index` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7117
- **Preview**: `class BM25Index:
    """BM25 sparse index manager (CPU-only)."""

    # Index version for compatibility tracking
    INDEX_VERSION = 2  # Version 2: Added stemming support

    def __init__(self, stor...`

### BGE-M3 Results

**#1** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8677
- **Preview**: `...`

**#2** `add_embeddings` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8533
- **Preview**: `...`

**#3** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8383
- **Preview**: `...`

**#4** `test_save_and_load_indices` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8148
- **Preview**: `...`

**#5** `setup_method` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7979
- **Preview**: `...`

### CodeRankEmbed Results

**#1** `search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8169
- **Preview**: `...`

**#2** `_build_fresh_index` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7188
- **Preview**: `...`

**#3** `setup_method` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7075
- **Preview**: `...`

**#4** `BM25Index` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6010
- **Preview**: `class BM25Index:
    """BM25 sparse index manager (CPU-only)."""

    # Index version for compatibility tracking
    INDEX_VERSION = 2  # Version 2: Added stemming support

    def __init__(self, stor...`

**#5** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5722
- **Preview**: `def __init__(self, storage_dir: str, use_stopwords: bool = True, use_stemming: bool = True):
        """Initialize BM25 index.

        Args:
            storage_dir: Directory to store index files
  ...`

### Overlap Analysis

- **All 3 models agree**: 1/5
- **Qwen3 + BGE-M3 only**: 0/5
- **Qwen3 + CodeRankEmbed only**: 1/5
- **BGE-M3 + CodeRankEmbed only**: 1/5
- **Unique to Qwen3**: 3/5
- **Unique to BGE-M3**: 3/5
- **Unique to CodeRankEmbed**: 2/5

**Qwen3 unique results:**
- `_search_bm25` in `unknown`
- `BM25OnlyEvaluator` in `unknown`
- `search` in `unknown`

**BGE-M3 unique results:**
- `add_embeddings` in `unknown`
- `test_save_and_load_indices` in `unknown`
- `__init__` in `unknown`

**CodeRankEmbed unique results:**
- `search` in `unknown`
- `_build_fresh_index` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Query: "incremental indexing logic"

### Qwen3-0.6B Results

**#1** `TestIncrementalIndexResult` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8911
- **Preview**: `...`

**#2** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8827
- **Preview**: `...`

**#3** `TestIncrementalIndexing` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7082
- **Preview**: `class TestIncrementalIndexing(TestCase):
    """Test incremental indexing functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    ...`

**#4** `test_file_addition` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6768
- **Preview**: `@pytest.mark.skipif(not _has_hf_token(), reason="HuggingFace token not available")
    def test_file_addition(self):
        """Test incremental indexing when files are added."""
        indexer = Ind...`

**#5** `IncrementalIndexer` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6761
- **Preview**: `class IncrementalIndexer:
    """Handles incremental indexing of code changes."""

    def __init__(
        self,
        indexer: Optional[Indexer] = None,
        embedder: Optional[CodeEmbedder] =...`

### BGE-M3 Results

**#1** `_full_index` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8107
- **Preview**: `...`

**#2** `test_result_to_dict` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7990
- **Preview**: `...`

**#3** `IncrementalIndexResult` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6874
- **Preview**: `@dataclass
class IncrementalIndexResult:
    """Result of incremental indexing operation."""

    files_added: int
    files_removed: int
    files_modified: int
    chunks_added: int
    chunks_remov...`

**#4** `IncrementalIndexer` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6710
- **Preview**: `class IncrementalIndexer:
    """Handles incremental indexing of code changes."""

    def __init__(
        self,
        indexer: Optional[Indexer] = None,
        embedder: Optional[CodeEmbedder] =...`

**#5** `test_initialization` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6600
- **Preview**: `def test_initialization(self):
        """Test incremental indexer initialization."""
        indexer = IncrementalIndexer(
            indexer=self.mock_indexer,
            embedder=self.mock_embedd...`

### CodeRankEmbed Results

**#1** `_full_index` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7870
- **Preview**: `...`

**#2** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7056
- **Preview**: `...`

**#3** `TestIncrementalIndexResult` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6835
- **Preview**: `...`

**#4** `TestIncrementalIndexing` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5180
- **Preview**: `class TestIncrementalIndexing(TestCase):
    """Test incremental indexing functionality."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
    ...`

**#5** `IncrementalIndexer` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5056
- **Preview**: `class IncrementalIndexer:
    """Handles incremental indexing of code changes."""

    def __init__(
        self,
        indexer: Optional[Indexer] = None,
        embedder: Optional[CodeEmbedder] =...`

### Overlap Analysis

- **All 3 models agree**: 0/5
- **Qwen3 + BGE-M3 only**: 1/5
- **Qwen3 + CodeRankEmbed only**: 3/5
- **BGE-M3 + CodeRankEmbed only**: 0/5
- **Unique to Qwen3**: 1/5
- **Unique to BGE-M3**: 4/5
- **Unique to CodeRankEmbed**: 2/5

**Qwen3 unique results:**
- `test_file_addition` in `unknown`

**BGE-M3 unique results:**
- `_full_index` in `unknown`
- `IncrementalIndexResult` in `unknown`
- `test_initialization` in `unknown`
- `test_result_to_dict` in `unknown`

**CodeRankEmbed unique results:**
- `_full_index` in `unknown`
- `IncrementalIndexer` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Query: "embedding generation workflow"

### Qwen3-0.6B Results

**#1** `TestGemmaEmbeddingGeneration` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.9387
- **Preview**: `...`

**#2** `main` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7190
- **Preview**: `...`

**#3** `None` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6828
- **Preview**: `"""Embedding generation module."""
...`

**#4** `EmbeddingResult` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5612
- **Preview**: `@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: np.ndarray
    chunk_id: str
    metadata: Dict[str, Any]...`

**#5** `test_gemma_batch_embedding` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5471
- **Preview**: `def test_gemma_batch_embedding(self, sample_code_chunk):
        """Test batch embedding generation with Gemma."""
        embedder = CodeEmbedder(model_name="google/embeddinggemma-300m")

        # C...`

### BGE-M3 Results

**#1** `test_gemma_chunk_embedding` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.9210
- **Preview**: `...`

**#2** `None` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7447
- **Preview**: `"""Embedding generation module."""
...`

**#3** `TestGemmaEmbeddingGeneration` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6425
- **Preview**: `class TestGemmaEmbeddingGeneration:
    """Test embedding generation with Gemma model."""

    def test_gemma_chunk_embedding(self, sample_code_chunk):
        """Test generating embedding for a singl...`

**#4** `embed_chunks` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6251
- **Preview**: `def embed_chunks(
        self, chunks: List[CodeChunk], batch_size: Optional[int] = None
    ) -> List[EmbeddingResult]:
        """Generate embeddings for multiple chunks with batching."""
        r...`

**#5** `EmbeddingResult` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6201
- **Preview**: `@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: np.ndarray
    chunk_id: str
    metadata: Dict[str, Any]...`

### CodeRankEmbed Results

**#1** `test_embedder_with_bge_m3` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7925
- **Preview**: `...`

**#2** `TestFullSearchFlow` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6609
- **Preview**: `...`

**#3** `None` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6147
- **Preview**: `"""Embedding generation module."""
...`

**#4** `EmbeddingResult` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4864
- **Preview**: `@dataclass
class EmbeddingResult:
    """Result of embedding generation."""

    embedding: np.ndarray
    chunk_id: str
    metadata: Dict[str, Any]...`

**#5** `TestBGEM3EmbeddingGeneration` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.3978
- **Preview**: `@pytest.mark.slow
class TestBGEM3EmbeddingGeneration:
    """Test embedding generation with BGE-M3 model.

    Marked as slow because BGE-M3 is a larger model.
    """

    def test_bge_m3_chunk_embed...`

### Overlap Analysis

- **All 3 models agree**: 2/5
- **Qwen3 + BGE-M3 only**: 1/5
- **Qwen3 + CodeRankEmbed only**: 0/5
- **BGE-M3 + CodeRankEmbed only**: 0/5
- **Unique to Qwen3**: 2/5
- **Unique to BGE-M3**: 2/5
- **Unique to CodeRankEmbed**: 3/5

**Qwen3 unique results:**
- `main` in `unknown`
- `test_gemma_batch_embedding` in `unknown`

**BGE-M3 unique results:**
- `embed_chunks` in `unknown`
- `test_gemma_chunk_embedding` in `unknown`

**CodeRankEmbed unique results:**
- `TestBGEM3EmbeddingGeneration` in `unknown`
- `TestFullSearchFlow` in `unknown`
- `test_embedder_with_bge_m3` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Query: "multi-hop search algorithm"

### Qwen3-0.6B Results

**#1** `search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8929
- **Preview**: `...`

**#2** `run_single_hop_search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8838
- **Preview**: `...`

**#3** `_multi_hop_search_internal` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7039
- **Preview**: `def _multi_hop_search_internal(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        hops: int = 2,
        expansion_factor: float = 0.3,
        use_par...`

**#4** `search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6502
- **Preview**: `def search(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filters: Optional...`

**#5** `run_multi_hop_search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6468
- **Preview**: `def run_multi_hop_search(
        self,
        query: str,
        k: int = 10,
        hops: int = 2,
        expansion: float = 0.3
    ) -> Tuple[List, float]:
        """Run multi-hop search.

  ...`

### BGE-M3 Results

**#1** `run_single_hop_search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.9177
- **Preview**: `...`

**#2** `PresetComparator` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8595
- **Preview**: `...`

**#3** `_multi_hop_search_internal` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7026
- **Preview**: `def _multi_hop_search_internal(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        hops: int = 2,
        expansion_factor: float = 0.3,
        use_par...`

**#4** `test_multi_hop_hop_count` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6899
- **Preview**: `def test_multi_hop_hop_count(self, test_project_path, mock_storage_dir):
        """Test multi-hop search with different hop counts."""
        # Setup
        chunker = MultiLanguageChunker(str(test_...`

**#5** `SearchMethodComparator` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6870
- **Preview**: `class SearchMethodComparator:
    """Compare single-hop and multi-hop search methods."""

    def __init__(self, project_path: str, storage_dir: str):
        """Initialize comparator.

        Args:
...`

### CodeRankEmbed Results

**#1** `measure_search_performance` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7786
- **Preview**: `...`

**#2** `run_multi_hop_search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6080
- **Preview**: `def run_multi_hop_search(
        self,
        query: str,
        k: int = 10,
        hops: int = 2,
        expansion: float = 0.3
    ) -> Tuple[List, float]:
        """Run multi-hop search.

  ...`

**#3** `_multi_hop_search_internal` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5689
- **Preview**: `def _multi_hop_search_internal(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        hops: int = 2,
        expansion_factor: float = 0.3,
        use_par...`

**#4** `test_multi_hop_basic_functionality` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4681
- **Preview**: `def test_multi_hop_basic_functionality(self, test_project_path, mock_storage_dir):
        """Test basic multi-hop search with 2 hops."""
        # Setup: Chunk project
        chunker = MultiLanguage...`

**#5** `_single_hop_search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4631
- **Preview**: `def _single_hop_search(
        self,
        query: str,
        k: int = 5,
        search_mode: str = "hybrid",
        use_parallel: bool = True,
        min_bm25_score: float = 0.0,
        filte...`

### Overlap Analysis

- **All 3 models agree**: 1/5
- **Qwen3 + BGE-M3 only**: 1/5
- **Qwen3 + CodeRankEmbed only**: 1/5
- **BGE-M3 + CodeRankEmbed only**: 0/5
- **Unique to Qwen3**: 2/5
- **Unique to BGE-M3**: 3/5
- **Unique to CodeRankEmbed**: 3/5

**Qwen3 unique results:**
- `search` in `unknown`
- `search` in `unknown`

**BGE-M3 unique results:**
- `test_multi_hop_hop_count` in `unknown`
- `SearchMethodComparator` in `unknown`
- `PresetComparator` in `unknown`

**CodeRankEmbed unique results:**
- `_single_hop_search` in `unknown`
- `measure_search_performance` in `unknown`
- `test_multi_hop_basic_functionality` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Query: "Merkle tree change detection"

### Qwen3-0.6B Results

**#1** `test_detect_changes_from_snapshot` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8822
- **Preview**: `...`

**#2** `test_detect_changes_between_dags` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8760
- **Preview**: `...`

**#3** `test_change_detection` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7474
- **Preview**: `def test_change_detection(self):
        """Test change detection using Merkle trees."""
        detector = ChangeDetector(self.snapshot_manager)

        # Build initial DAG
        dag1 = MerkleDAG(...`

**#4** `None` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7032
- **Preview**: `"""Merkle tree-based change detection for efficient incremental indexing."""

from .change_detector import ChangeDetector
from .merkle_dag import MerkleDAG, MerkleNode
from .snapshot_manager import Sn...`

**#5** `test_no_changes_detection` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6990
- **Preview**: `def test_no_changes_detection(self):
        """Test when no changes occur."""
        dag1 = MerkleDAG(str(self.test_path))
        dag1.build()

        dag2 = MerkleDAG(str(self.test_path))
       ...`

### BGE-M3 Results

**#1** `test_detect_changes_from_snapshot` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8374
- **Preview**: `...`

**#2** `test_change_detection` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7473
- **Preview**: `def test_change_detection(self):
        """Test change detection using Merkle trees."""
        detector = ChangeDetector(self.snapshot_manager)

        # Build initial DAG
        dag1 = MerkleDAG(...`

**#3** `None` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7065
- **Preview**: `"""Merkle tree-based change detection for efficient incremental indexing."""

from .change_detector import ChangeDetector
from .merkle_dag import MerkleDAG, MerkleNode
from .snapshot_manager import Sn...`

**#4** `test_incremental_indexing_with_merkle` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6965
- **Preview**: `def test_incremental_indexing_with_merkle(
        self, test_project_path, mock_storage_dir
    ):
        """Test incremental indexing using Merkle tree change detection."""
        # Initial indexi...`

**#5** `ChangeDetector` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6323
- **Preview**: `class ChangeDetector:
    """Detects changes between Merkle DAGs."""

    def __init__(self, snapshot_manager: SnapshotManager = None):
        """Initialize change detector.

        Args:
          ...`

### CodeRankEmbed Results

**#1** `test_incremental_indexing_mcp_path` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7704
- **Preview**: `...`

**#2** `None` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6349
- **Preview**: `"""Merkle tree-based change detection for efficient incremental indexing."""

from .change_detector import ChangeDetector
from .merkle_dag import MerkleDAG, MerkleNode
from .snapshot_manager import Sn...`

**#3** `test_change_detection` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6070
- **Preview**: `def test_change_detection(self):
        """Test change detection using Merkle trees."""
        detector = ChangeDetector(self.snapshot_manager)

        # Build initial DAG
        dag1 = MerkleDAG(...`

**#4** `ChangeDetector` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4830
- **Preview**: `class ChangeDetector:
    """Detects changes between Merkle DAGs."""

    def __init__(self, snapshot_manager: SnapshotManager = None):
        """Initialize change detector.

        Args:
          ...`

**#5** `detect_changes` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4386
- **Preview**: `def detect_changes(self, old_dag: MerkleDAG, new_dag: MerkleDAG) -> FileChanges:
        """Detect file changes between two Merkle DAGs.

        Args:
            old_dag: Previous state DAG
        ...`

### Overlap Analysis

- **All 3 models agree**: 2/5
- **Qwen3 + BGE-M3 only**: 1/5
- **Qwen3 + CodeRankEmbed only**: 0/5
- **BGE-M3 + CodeRankEmbed only**: 1/5
- **Unique to Qwen3**: 2/5
- **Unique to BGE-M3**: 1/5
- **Unique to CodeRankEmbed**: 2/5

**Qwen3 unique results:**
- `test_no_changes_detection` in `unknown`
- `test_detect_changes_between_dags` in `unknown`

**BGE-M3 unique results:**
- `test_incremental_indexing_with_merkle` in `unknown`

**CodeRankEmbed unique results:**
- `test_incremental_indexing_mcp_path` in `unknown`
- `detect_changes` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Query: "hybrid search RRF reranking"

### Qwen3-0.6B Results

**#1** `_single_hop_search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.9236
- **Preview**: `...`

**#2** `search` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8929
- **Preview**: `...`

**#3** `test_bm25_vs_dense_results_differ` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8684
- **Preview**: `...`

**#4** `rerank_simple` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8184
- **Preview**: `...`

**#5** `test_rrf_score_calculation` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8129
- **Preview**: `...`

### BGE-M3 Results

**#1** `test_single_list_reranking` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.9071
- **Preview**: `...`

**#2** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8830
- **Preview**: `...`

**#3** `test_bm25_vs_dense_results_differ` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.8653
- **Preview**: `...`

**#4** `test_multi_hop_reranking` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7746
- **Preview**: `...`

**#5** `RRFReranker` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.6823
- **Preview**: `class RRFReranker:
    """Reciprocal Rank Fusion (RRF) reranker for combining multiple result lists."""

    def __init__(self, k: int = 100, alpha: float = 0.5):
        """
        Initialize RRF re...`

### CodeRankEmbed Results

**#1** `test_performance_with_large_lists` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.7412
- **Preview**: `...`

**#2** `rerank` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5465
- **Preview**: `def rerank(
        self,
        results_lists: List[List[SearchResult]],
        weights: Optional[List[float]] = None,
        max_results: int = 10,
    ) -> List[SearchResult]:
        """
      ...`

**#3** `RRFReranker` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.5174
- **Preview**: `class RRFReranker:
    """Reciprocal Rank Fusion (RRF) reranker for combining multiple result lists."""

    def __init__(self, k: int = 100, alpha: float = 0.5):
        """
        Initialize RRF re...`

**#4** `TestRRFReranker` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4913
- **Preview**: `class TestRRFReranker:
    """Test RRF reranker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.reranker = RRFReranker(k=100, alpha=0.5)

        # Samp...`

**#5** `__init__` (unknown)
- **File**: `unknown:unknown`
- **Score**: 0.4891
- **Preview**: `def __init__(self, k: int = 100, alpha: float = 0.5):
        """
        Initialize RRF reranker.

        Args:
            k: RRF parameter for smoothing (higher = less emphasis on rank)
          ...`

### Overlap Analysis

- **All 3 models agree**: 0/5
- **Qwen3 + BGE-M3 only**: 1/5
- **Qwen3 + CodeRankEmbed only**: 0/5
- **BGE-M3 + CodeRankEmbed only**: 2/5
- **Unique to Qwen3**: 4/5
- **Unique to BGE-M3**: 2/5
- **Unique to CodeRankEmbed**: 3/5

**Qwen3 unique results:**
- `_single_hop_search` in `unknown`
- `rerank_simple` in `unknown`
- `search` in `unknown`
- `test_rrf_score_calculation` in `unknown`

**BGE-M3 unique results:**
- `test_multi_hop_reranking` in `unknown`
- `test_single_list_reranking` in `unknown`

**CodeRankEmbed unique results:**
- `test_performance_with_large_lists` in `unknown`
- `rerank` in `unknown`
- `TestRRFReranker` in `unknown`

### Manual Assessment

**Which model's results are most relevant to the query?**

- [ ] Qwen3-0.6B clearly better
- [ ] BGE-M3 clearly better
- [ ] CodeRankEmbed clearly better
- [ ] Similar quality across all models
- [ ] Mixed (different models excel)

**Notes**: [Add your observations here]

---

## Summary

### Overall Observations

[Fill in after manual inspection]

### Recommendation

Based on relevance assessment:

- [ ] **Use Qwen3-0.6B** - Clearly most relevant, justifies general-purpose model
- [ ] **Use BGE-M3** - Best balance of performance and relevance
- [ ] **Use CodeRankEmbed** - Code-specific model wins for code queries
- [ ] **Smart routing** - Different models excel at different query types
- [ ] **No clear winner** - Similar quality, use fastest/smallest model

### Next Steps

If smart routing recommended:
1. Categorize queries by type (technical/natural language)
2. Implement query classifier with keyword heuristics
3. Route to appropriate model automatically

If single model recommended:
1. Switch to recommended model
2. Document decision rationale
3. Monitor real-world performance
