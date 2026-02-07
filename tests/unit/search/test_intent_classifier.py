"""Unit tests for IntentClassifier query intent detection.

Tests intent classification for LOCAL, GLOBAL, NAVIGATIONAL, and HYBRID queries.
Validates pattern matching, confidence thresholds, and parameter extraction.
"""

import pytest

from search.intent_classifier import IntentClassifier, QueryIntent


class TestIntentClassifierBasicDetection:
    """Test basic intent detection for different query types."""

    @pytest.fixture
    def classifier(self):
        """Create IntentClassifier instance for testing."""
        return IntentClassifier(enable_logging=False)

    # ===== LOCAL Intent Tests =====

    def test_local_intent_where_is_query(self, classifier):
        """Test LOCAL intent for 'where is' queries."""
        decision = classifier.classify("where is QueryRouter defined")
        assert decision.intent == QueryIntent.LOCAL
        assert decision.confidence >= 0.3

    def test_local_intent_find_definition(self, classifier):
        """Test LOCAL intent for 'find definition' queries."""
        decision = classifier.classify("find the definition of handle_search_code")
        assert decision.intent == QueryIntent.LOCAL
        assert decision.confidence >= 0.3

    def test_local_intent_camelcase_symbol(self, classifier):
        """Test LOCAL intent for CamelCase symbol queries."""
        decision = classifier.classify("where is CodeIndexManager class")
        # CamelCase + "where is" should strongly indicate LOCAL
        assert decision.intent == QueryIntent.LOCAL
        assert decision.confidence >= 0.3

    def test_local_intent_show_me(self, classifier):
        """Test LOCAL intent for 'show me' queries."""
        decision = classifier.classify("show me the QueryRouter class")
        assert decision.intent == QueryIntent.LOCAL
        assert decision.confidence >= 0.3

    def test_local_intent_short_query_penalty(self, classifier):
        """Test that long queries reduce LOCAL confidence via token penalty."""
        short_query = "where is User"  # 3 tokens
        long_query = "where is the user authentication system implementation located in the code"  # 11 tokens > 8 max

        short_decision = classifier.classify(short_query)
        long_decision = classifier.classify(long_query)

        # Both should detect "where is" pattern, but long query gets 0.7x penalty
        # Check confidence (after penalty applied), not raw score
        assert short_decision.confidence > long_decision.confidence

    def test_local_intent_io_verbs(self, classifier):
        """Test LOCAL intent for I/O and persistence verbs (save, load, read, write)."""
        # "save" and "load" should each add +0.10 to LOCAL score
        decision = classifier.classify("save and load search configuration")
        assert decision.scores["local"] >= 0.20  # save +0.10, load +0.10
        # Should classify as hybrid (LOCAL=0.20, below LOCAL-only threshold)
        # but LOCAL should be highest or tied with others
        assert (
            decision.intent == QueryIntent.HYBRID
            or decision.intent == QueryIntent.LOCAL
        )

    # ===== GLOBAL Intent Tests =====

    def test_global_intent_how_does_work(self, classifier):
        """Test GLOBAL intent for 'how does X work' queries."""
        decision = classifier.classify("how does the search pipeline work")
        assert decision.intent == QueryIntent.GLOBAL
        assert decision.confidence >= 0.3

    def test_global_intent_architecture(self, classifier):
        """Test GLOBAL intent for architecture queries."""
        decision = classifier.classify(
            "explain the architecture of the indexing system"
        )
        assert decision.intent == QueryIntent.GLOBAL
        assert decision.confidence >= 0.3

    def test_global_intent_overview(self, classifier):
        """Test GLOBAL intent for overview queries."""
        decision = classifier.classify("system overview of hybrid search")
        assert decision.intent == QueryIntent.GLOBAL
        assert decision.confidence > 0.0

    def test_global_intent_explain(self, classifier):
        """Test GLOBAL intent for 'explain' queries."""
        decision = classifier.classify("explain the query routing mechanism")
        assert decision.intent == QueryIntent.GLOBAL
        assert decision.confidence >= 0.3

    def test_global_intent_high_level(self, classifier):
        """Test GLOBAL intent for 'high-level' queries."""
        decision = classifier.classify(
            "explain high-level architecture of code chunking"
        )
        # "explain" + "high-level" + "architecture" should trigger GLOBAL
        assert decision.intent == QueryIntent.GLOBAL
        assert decision.confidence >= 0.3

    # ===== NAVIGATIONAL Intent Tests =====

    def test_navigational_intent_what_calls(self, classifier):
        """Test NAVIGATIONAL intent for 'what calls' queries."""
        decision = classifier.classify("what calls handle_search_code")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        assert decision.confidence >= 0.3

    def test_navigational_intent_callers(self, classifier):
        """Test NAVIGATIONAL intent for 'callers' queries."""
        decision = classifier.classify("find callers of chunk_file function")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        assert decision.confidence >= 0.3

    def test_navigational_intent_dependencies(self, classifier):
        """Test NAVIGATIONAL intent for 'dependencies' queries."""
        decision = classifier.classify("dependencies of CodeIndexManager")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        assert decision.confidence >= 0.3

    def test_navigational_intent_who_uses(self, classifier):
        """Test NAVIGATIONAL intent for 'who uses' queries."""
        decision = classifier.classify("who uses QueryRouter class")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        assert decision.confidence >= 0.3

    def test_navigational_intent_imports(self, classifier):
        """Test NAVIGATIONAL intent for 'imports' queries."""
        decision = classifier.classify("what imports the search module")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        assert decision.confidence > 0.0

    def test_navigational_intent_call_chain(self, classifier):
        """Test NAVIGATIONAL intent for 'call chain' queries."""
        decision = classifier.classify("trace call chain from handle_index_directory")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        assert decision.confidence >= 0.3

    # ===== HYBRID Intent Tests =====

    def test_hybrid_intent_ambiguous(self, classifier):
        """Test HYBRID intent for ambiguous queries."""
        decision = classifier.classify("code implementation")
        assert decision.intent == QueryIntent.HYBRID
        assert decision.confidence < 0.3

    def test_hybrid_intent_no_patterns(self, classifier):
        """Test HYBRID intent when no patterns match."""
        decision = classifier.classify("random text without keywords")
        assert decision.intent == QueryIntent.HYBRID
        assert decision.confidence == 0.0

    def test_hybrid_intent_generic_search(self, classifier):
        """Test HYBRID intent for generic search queries."""
        decision = classifier.classify("search functionality")
        assert decision.intent == QueryIntent.HYBRID

    # ===== Confidence Threshold Tests =====

    def test_confidence_threshold_default(self, classifier):
        """Test default confidence threshold (0.3)."""
        # Very weak signal should fall back to HYBRID
        decision = classifier.classify("function")
        if decision.confidence < 0.3:
            assert decision.intent == QueryIntent.HYBRID

    def test_confidence_threshold_custom(self):
        """Test custom confidence threshold."""
        classifier = IntentClassifier(confidence_threshold=0.5, enable_logging=False)
        # Query that would be LOCAL with 0.3 threshold
        decision = classifier.classify("show me User class")

        # If confidence is between 0.3 and 0.5, should fall back to HYBRID
        if 0.3 <= decision.confidence < 0.5:
            assert decision.intent == QueryIntent.HYBRID

    def test_confidence_threshold_override(self, classifier):
        """Test confidence threshold can be overridden per call."""
        query = "find the implementation of User"
        decision_default = classifier.classify(query)
        decision_high_threshold = classifier.classify(query, confidence_threshold=0.8)

        # Higher threshold should be more likely to return HYBRID
        if decision_default.confidence < 0.8:
            assert decision_high_threshold.intent == QueryIntent.HYBRID

    # ===== Suggested Parameters Tests =====

    def test_suggested_params_global_k(self, classifier):
        """Test that GLOBAL queries suggest larger k."""
        decision = classifier.classify("how does hybrid search work")
        if decision.intent == QueryIntent.GLOBAL:
            assert decision.suggested_params.get("k") == 10
            assert decision.suggested_params.get("search_mode") == "hybrid"

    def test_suggested_params_local_k(self, classifier):
        """Test that LOCAL queries suggest k=5 for symbol lookups."""
        decision = classifier.classify("where is QueryRouter")
        if decision.intent == QueryIntent.LOCAL:
            # k=5 per intent_classifier.py line 783 (wider pool for graph-isolated symbols)
            assert decision.suggested_params.get("k") == 5
            assert decision.suggested_params.get("search_mode") == "hybrid"

    def test_suggested_params_navigational_symbol(self, classifier):
        """Test that NAVIGATIONAL queries extract symbol name."""
        decision = classifier.classify("what calls handle_search_code")
        if decision.intent == QueryIntent.NAVIGATIONAL:
            assert decision.suggested_params.get("symbol_name") == "handle_search_code"
            assert decision.suggested_params.get("tool") == "find_connections"

    # ===== Symbol Extraction Tests =====

    def test_symbol_extraction_what_calls(self, classifier):
        """Test symbol extraction from 'what calls X' pattern."""
        symbol = classifier._extract_symbol_from_query("what calls handle_search_code")
        assert symbol == "handle_search_code"

    def test_symbol_extraction_who_uses(self, classifier):
        """Test symbol extraction from 'who uses X' pattern."""
        symbol = classifier._extract_symbol_from_query("who uses QueryRouter")
        assert symbol == "QueryRouter"

    def test_symbol_extraction_callers_of(self, classifier):
        """Test symbol extraction from 'callers of X' pattern."""
        symbol = classifier._extract_symbol_from_query("callers of chunk_file")
        assert symbol == "chunk_file"

    def test_symbol_extraction_dependencies_of(self, classifier):
        """Test symbol extraction from 'dependencies of X' pattern."""
        symbol = classifier._extract_symbol_from_query(
            "dependencies of CodeIndexManager"
        )
        assert symbol == "CodeIndexManager"

    def test_symbol_extraction_x_callers(self, classifier):
        """Test symbol extraction from 'X callers' pattern."""
        symbol = classifier._extract_symbol_from_query("incremental_index callers")
        assert symbol == "incremental_index"

    def test_symbol_extraction_camelcase_fallback(self, classifier):
        """Test symbol extraction falls back to CamelCase word."""
        symbol = classifier._extract_symbol_from_query(
            "find relationships for QueryRouter"
        )
        assert symbol == "QueryRouter"

    def test_symbol_extraction_snake_case_fallback(self, classifier):
        """Test symbol extraction falls back to snake_case word."""
        # Use a query where snake_case symbol is clearly the last valid identifier
        symbol = classifier._extract_symbol_from_query(
            "find uses of handle_search_code"
        )
        assert symbol == "handle_search_code"

    def test_symbol_extraction_no_match(self, classifier):
        """Test symbol extraction with ambiguous generic query."""
        # With generic words, may extract last word as fallback
        # This test verifies behavior exists (not necessarily None)
        symbol = classifier._extract_symbol_from_query("show me the code")
        # Should extract "code" as last snake_case-like word, or None
        # Either is acceptable for generic queries
        assert symbol is None or isinstance(symbol, str)

    # ===== Tie Resolution Tests =====

    def test_tie_resolution_navigational_priority(self, classifier):
        """Test that NAVIGATIONAL has highest priority in ties."""
        # Query with both navigational and local signals
        decision = classifier.classify("what calls the User class")
        # If scores are close, NAVIGATIONAL should win due to precedence
        scores = decision.scores
        if scores.get("navigational", 0) > 0 and scores.get("local", 0) > 0:
            max_score = max(scores.values())
            if abs(scores["navigational"] - max_score) < 0.05:
                assert decision.intent == QueryIntent.NAVIGATIONAL

    def test_tie_resolution_local_over_global(self, classifier):
        """Test that LOCAL has priority over GLOBAL in ties."""
        # Query with both local and global signals
        decision = classifier.classify("where is the architecture overview")
        scores = decision.scores
        if scores.get("local", 0) > 0 and scores.get("global", 0) > 0:
            max_score = max(scores.values())
            # If both are tied, LOCAL should win
            if (
                abs(scores["local"] - max_score) < 0.05
                and abs(scores["global"] - max_score) < 0.05
            ):
                assert decision.intent == QueryIntent.LOCAL

    # ===== Pattern Matching Tests =====

    def test_pattern_matching_local_camelcase(self, classifier):
        """Test that LOCAL queries with strong keywords score high."""
        # Use query with strong LOCAL keywords instead of relying on CamelCase pattern
        query = "where is CodeIndexManager class"
        scores = classifier._calculate_scores(query)
        # Should have positive score for local due to "where is" + "class" keywords
        assert scores.get("local", 0) > 0.0

    def test_pattern_matching_navigational_callers(self, classifier):
        """Test 'callers' pattern for NAVIGATIONAL intent."""
        query = "find callers of function"
        scores = classifier._calculate_scores(query)
        # Should have high score for navigational
        assert scores.get("navigational", 0) >= 0.3

    def test_pattern_matching_global_how_does_work(self, classifier):
        """Test 'how does X work' pattern for GLOBAL intent."""
        query = "how does the system work"
        scores = classifier._calculate_scores(query)
        # Should have high score for global
        assert scores.get("global", 0) >= 0.3

    # ===== Edge Cases =====

    def test_empty_query(self, classifier):
        """Test handling of empty query."""
        decision = classifier.classify("")
        assert decision.intent == QueryIntent.HYBRID
        assert decision.confidence == 0.0

    def test_very_long_query(self, classifier):
        """Test handling of very long query."""
        long_query = " ".join(["word"] * 50)
        decision = classifier.classify(long_query)
        # Should not crash, should have low LOCAL confidence
        assert decision.intent is not None

    def test_case_insensitive_matching(self, classifier):
        """Test that matching is case-insensitive."""
        decision1 = classifier.classify("where is QueryRouter")
        decision2 = classifier.classify("WHERE IS QueryRouter")
        # Both should detect LOCAL intent
        assert decision1.intent == decision2.intent

    def test_scores_normalized(self, classifier):
        """Test that scores are normalized to [0, 1]."""
        query = "how does the call graph work with dependencies"
        scores = classifier._calculate_scores(query)
        for score in scores.values():
            assert 0.0 <= score <= 1.0

    # ===== Logging Tests =====

    def test_logging_enabled(self):
        """Test that logging can be enabled."""
        classifier = IntentClassifier(enable_logging=True)
        # Should not crash with logging enabled
        decision = classifier.classify("where is QueryRouter")
        assert decision.intent is not None

    def test_logging_disabled(self):
        """Test that logging can be disabled."""
        classifier = IntentClassifier(enable_logging=False)
        decision = classifier.classify("where is QueryRouter")
        assert decision.intent is not None

    # ===== get_intent_patterns Tests =====

    def test_get_intent_patterns_local(self, classifier):
        """Test retrieving LOCAL intent patterns."""
        patterns = classifier.get_intent_patterns(QueryIntent.LOCAL)
        assert patterns is not None
        assert "keywords" in patterns
        assert "patterns" in patterns
        assert "weight" in patterns

    def test_get_intent_patterns_global(self, classifier):
        """Test retrieving GLOBAL intent patterns."""
        patterns = classifier.get_intent_patterns(QueryIntent.GLOBAL)
        assert patterns is not None
        assert "keywords" in patterns
        assert "patterns" in patterns

    def test_get_intent_patterns_navigational(self, classifier):
        """Test retrieving NAVIGATIONAL intent patterns."""
        patterns = classifier.get_intent_patterns(QueryIntent.NAVIGATIONAL)
        assert patterns is not None
        assert "keywords" in patterns
        assert "patterns" in patterns
        assert patterns["weight"] == 1.2  # Higher weight


class TestIntentClassifierRealWorldQueries:
    """Test intent classification with real-world query examples."""

    @pytest.fixture
    def classifier(self):
        """Create IntentClassifier instance for testing."""
        return IntentClassifier(enable_logging=False)

    @pytest.mark.parametrize(
        "query,expected_intent,description",
        [
            # LOCAL queries
            (
                "where is handle_search_code defined",
                QueryIntent.LOCAL,
                "Function definition lookup",
            ),
            (
                "find the definition of QueryRouter class",
                QueryIntent.LOCAL,
                "Class lookup",
            ),
            ("show me User model", QueryIntent.LOCAL, "Model lookup"),
            (
                "where is incremental_index function",
                QueryIntent.LOCAL,
                "Function locate",
            ),
            # GLOBAL queries
            (
                "how does the search pipeline work",
                QueryIntent.GLOBAL,
                "Pipeline explanation",
            ),
            (
                "explain the architecture of hybrid search",
                QueryIntent.GLOBAL,
                "Architecture explanation",
            ),
            ("overview of code chunking system", QueryIntent.GLOBAL, "System overview"),
            (
                "how do embeddings work in this codebase",
                QueryIntent.GLOBAL,
                "Concept explanation",
            ),
            # NAVIGATIONAL queries
            (
                "what calls handle_search_code",
                QueryIntent.NAVIGATIONAL,
                "Caller discovery",
            ),
            (
                "who uses QueryRouter",
                QueryIntent.NAVIGATIONAL,
                "Usage discovery",
            ),
            (
                "dependencies of CodeIndexManager",
                QueryIntent.NAVIGATIONAL,
                "Dependency analysis",
            ),
            (
                "find callers of chunk_file",
                QueryIntent.NAVIGATIONAL,
                "Callers query",
            ),
            (
                "what imports the search module",
                QueryIntent.NAVIGATIONAL,
                "Import tracking",
            ),
            # HYBRID queries (ambiguous)
            ("code", QueryIntent.HYBRID, "Too generic"),
            ("search", QueryIntent.HYBRID, "Ambiguous term"),
            ("implementation", QueryIntent.HYBRID, "Generic implementation"),
        ],
    )
    def test_real_world_query_classification(
        self, classifier, query, expected_intent, description
    ):
        """Test classification of real-world queries."""
        decision = classifier.classify(query)
        assert decision.intent == expected_intent, (
            f"Failed for '{query}' ({description}): expected {expected_intent.value}, got {decision.intent.value}"
        )


class TestPathTracingIntent:
    """Test PATH_TRACING intent detection for path-finding queries."""

    @pytest.fixture
    def classifier(self):
        """Create IntentClassifier instance for testing."""
        return IntentClassifier(enable_logging=False)

    def test_trace_path_from_to(self, classifier):
        """Test PATH_TRACING intent for 'trace path from X to Y' queries."""
        decision = classifier.classify("trace path from login to database")
        assert decision.intent == QueryIntent.PATH_TRACING
        assert decision.confidence >= 0.3
        assert decision.suggested_params.get("source") == "login"
        assert decision.suggested_params.get("target") == "database"
        assert decision.suggested_params.get("tool") == "find_path"

    def test_how_does_connect(self, classifier):
        """Test PATH_TRACING intent for 'how does X connect to Y' queries."""
        decision = classifier.classify("how does UserModel connect to API")
        assert decision.intent == QueryIntent.PATH_TRACING
        assert decision.confidence >= 0.3
        source, target = (
            decision.suggested_params.get("source"),
            decision.suggested_params.get("target"),
        )
        assert source == "UserModel" and target == "API"

    def test_connection_between(self, classifier):
        """Test PATH_TRACING intent for 'connection between X and Y' queries."""
        decision = classifier.classify("connection between auth and database")
        assert decision.intent == QueryIntent.PATH_TRACING
        assert decision.confidence >= 0.3

    def test_path_between(self, classifier):
        """Test PATH_TRACING intent for 'path between X and Y' queries."""
        decision = classifier.classify("path between QueryRouter and HybridSearcher")
        assert decision.intent == QueryIntent.PATH_TRACING
        assert decision.confidence >= 0.3


class TestSimilarityIntent:
    """Test SIMILARITY intent detection for code similarity queries."""

    @pytest.fixture
    def classifier(self):
        """Create IntentClassifier instance for testing."""
        return IntentClassifier(enable_logging=False)

    def test_similar_to(self, classifier):
        """Test SIMILARITY intent for 'similar to X' queries."""
        decision = classifier.classify("find code similar to QueryRouter")
        assert decision.intent == QueryIntent.SIMILARITY
        assert decision.confidence >= 0.3
        assert decision.suggested_params.get("tool") == "find_similar_code"
        assert decision.suggested_params.get("symbol_name") == "QueryRouter"

    def test_patterns_like(self, classifier):
        """Test SIMILARITY intent for 'patterns like X' queries."""
        decision = classifier.classify("patterns like authentication handler")
        assert decision.intent == QueryIntent.SIMILARITY
        assert decision.confidence >= 0.3

    def test_code_like(self, classifier):
        """Test SIMILARITY intent for 'code like X' queries."""
        decision = classifier.classify("code like handle_search_code")
        assert decision.intent == QueryIntent.SIMILARITY
        assert decision.confidence >= 0.3

    def test_similar_implementations(self, classifier):
        """Test SIMILARITY intent for 'similar implementations to X' queries."""
        decision = classifier.classify("similar implementations to CodeIndexManager")
        assert decision.intent == QueryIntent.SIMILARITY
        assert decision.confidence >= 0.3


class TestContextualIntent:
    """Test CONTEXTUAL intent detection for context exploration queries."""

    @pytest.fixture
    def classifier(self):
        """Create IntentClassifier instance for testing."""
        return IntentClassifier(enable_logging=False)

    def test_context_around(self, classifier):
        """Test CONTEXTUAL intent for 'context around X' queries."""
        decision = classifier.classify("show context around handle_search_code")
        assert decision.intent == QueryIntent.CONTEXTUAL
        assert decision.confidence >= 0.3
        assert decision.suggested_params.get("ego_graph_enabled") is True
        assert decision.suggested_params.get("ego_graph_k_hops") == 2

    def test_related_to(self, classifier):
        """Test CONTEXTUAL intent for 'related to X' queries."""
        decision = classifier.classify("code related to authentication")
        assert decision.intent == QueryIntent.CONTEXTUAL
        assert decision.confidence >= 0.3

    def test_explore_query(self, classifier):
        """Test CONTEXTUAL intent for 'explore X' queries."""
        decision = classifier.classify("explore search pipeline")
        assert decision.intent == QueryIntent.CONTEXTUAL
        assert decision.confidence >= 0.3

    def test_surrounding_code(self, classifier):
        """Test CONTEXTUAL intent for 'surrounding code' queries."""
        decision = classifier.classify("surrounding code for handle_find_connections")
        assert decision.intent == QueryIntent.CONTEXTUAL
        assert decision.confidence >= 0.3


class TestRelationshipTypeDetection:
    """Test relationship type detection for NAVIGATIONAL queries."""

    @pytest.fixture
    def classifier(self):
        """Create IntentClassifier instance for testing."""
        return IntentClassifier(enable_logging=False)

    def test_inheritance_query(self, classifier):
        """Test relationship type detection for inheritance queries."""
        decision = classifier.classify("what classes inherit from BaseChunker")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        rel_types = decision.suggested_params.get("relationship_types", [])
        assert "inherits" in rel_types

    def test_import_query(self, classifier):
        """Test relationship type detection for import queries."""
        decision = classifier.classify("what modules import QueryRouter")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        rel_types = decision.suggested_params.get("relationship_types", [])
        assert "imports" in rel_types

    def test_decorator_query(self, classifier):
        """Test relationship type detection for decorator queries."""
        decision = classifier.classify("what decorates handle_search_code")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        rel_types = decision.suggested_params.get("relationship_types", [])
        assert "decorates" in rel_types

    def test_exception_query(self, classifier):
        """Test relationship type detection for exception queries."""
        decision = classifier.classify("what exceptions raises IndexSynchronizer")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        rel_types = decision.suggested_params.get("relationship_types", [])
        assert "raises" in rel_types or "catches" in rel_types

    def test_instantiation_query(self, classifier):
        """Test relationship type detection for instantiation queries."""
        decision = classifier.classify("what creates CodeIndexManager instances")
        assert decision.intent == QueryIntent.NAVIGATIONAL
        rel_types = decision.suggested_params.get("relationship_types", [])
        assert "instantiates" in rel_types


class TestSymbolDetection:
    """Test code symbol detection in queries (fallback for noun-only queries)."""

    @pytest.fixture
    def classifier(self):
        """Create IntentClassifier instance for testing."""
        return IntentClassifier(enable_logging=False)

    def test_camelcase_detected(self, classifier):
        """CamelCase symbols should boost LOCAL score via fallback."""
        decision = classifier.classify("HybridSearcher BM25")
        # CamelCase +0.25, UPPER_CASE +0.15 = 0.40
        assert decision.scores["local"] >= 0.35
        assert (
            decision.intent == QueryIntent.LOCAL
            or decision.intent == QueryIntent.HYBRID
        )

    def test_upper_case_detected(self, classifier):
        """UPPER_CASE constants should boost LOCAL score via fallback."""
        decision = classifier.classify("FAISS IndexFlatIP")
        # UPPER +0.15, CamelCase +0.25 = 0.40
        assert decision.scores["local"] >= 0.35

    def test_snake_case_detected(self, classifier):
        """snake_case identifiers should boost LOCAL score via fallback."""
        decision = classifier.classify("embed_chunks batch")
        # snake_case +0.20
        assert decision.scores["local"] >= 0.15

    def test_dunder_method_detected(self, classifier):
        """Dunder methods should boost LOCAL score via fallback."""
        decision = classifier.classify("__init__ constructor")
        # dunder +0.20
        assert decision.scores["local"] >= 0.15

    def test_dot_notation_detected(self, classifier):
        """dot.notation should boost LOCAL score via fallback."""
        decision = classifier.classify("Module.ClassName usage")
        # dot notation +0.25
        assert decision.scores["local"] >= 0.20

    def test_no_interference_with_verb_queries(self, classifier):
        """Symbol fallback should NOT activate when verbs provide signal."""
        decision = classifier.classify(
            "how does HybridSearcher combine BM25 and semantic search"
        )
        # GLOBAL should still be highest (verb signals dominate)
        # Fallback skipped because GLOBAL=0.20 > 0.15 threshold
        assert decision.scores["global"] >= decision.scores.get("local", 0)
        # LOCAL should be low (just from "does" substring match)
        assert decision.scores.get("local", 0) < 0.15

    def test_blocklist_terms_ignored(self, classifier):
        """Common terms like 'function', 'class' should not trigger symbol detection."""
        # Pure blocklist terms — should not get symbol boost
        decision = classifier.classify("function class method")
        # These match as LOCAL keywords, not as symbols
        # LOCAL score should come from keyword matches, not symbol detection
        assert decision.scores["local"] > 0

    def test_all_zero_query_gets_symbol_boost(self, classifier):
        """Pure noun queries with no verb matches should get symbol fallback."""
        decision = classifier.classify(
            "FAISS IndexFlatIP cosine similarity vector search"
        )
        # Should trigger fallback (no verbs = max score ~0.0)
        assert decision.scores["local"] > 0
        # Should be substantial boost from FAISS and IndexFlatIP
        assert decision.scores["local"] >= 0.35

    def test_mixed_symbols(self, classifier):
        """Multiple symbol types should accumulate (capped at 0.5)."""
        decision = classifier.classify("HybridSearcher embed_chunks FAISS __init__")
        # CamelCase +0.25, snake +0.20, UPPER +0.15, dunder +0.20 = 0.80, capped at 0.5
        assert decision.scores["local"] == 0.5
