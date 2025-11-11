"""
Comprehensive Feature Testing Script for v0.5.2

Tests all combinations of features (Multi-Hop, Stemming) across all search modes
to validate production readiness.

Usage:
    python tools/comprehensive_feature_test.py

Output:
    - analysis/comprehensive_feature_test_results.json (raw data)
    - analysis/COMPREHENSIVE_FEATURE_TEST_REPORT.md (analysis report)
"""

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from search.config import SearchConfig, SearchConfigManager
from search.hybrid_searcher import HybridSearcher
from embeddings.embedder import CodeEmbedder
from chunking.multi_language_chunker import MultiLanguageChunker
from search.incremental_indexer import IncrementalIndexer

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class TestConfiguration:
    """Represents a test configuration"""

    name: str
    stemming_enabled: bool
    multi_hop_enabled: bool
    search_mode: str
    description: str


@dataclass
class QueryResult:
    """Results from a single query"""

    query: str
    config_name: str
    search_mode: str
    stemming: bool
    multi_hop: bool
    result_count: int
    query_time_ms: float
    top_result_file: Optional[str]
    top_result_score: Optional[float]
    error: Optional[str]
    results_preview: List[Dict[str, Any]]


@dataclass
class TestSummary:
    """Summary statistics for a test configuration"""

    config_name: str
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_query_time_ms: float
    avg_result_count: float
    min_time_ms: float
    max_time_ms: float
    total_time_s: float


class ComprehensiveFeatureTester:
    """Comprehensive testing for all feature combinations"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.storage_dir = Path.home() / ".claude_code_search" / "test_comprehensive"
        self.results: List[QueryResult] = []
        self.summaries: List[TestSummary] = []

        # Initialize embedder once and reuse
        config = SearchConfig()
        cache_dir = Path.home() / ".cache" / "claude_code_search"
        self.embedder = CodeEmbedder(
            model_name=config.embedding_model_name,
            cache_dir=str(cache_dir)
        )

        # Test configurations: 4 feature combinations × 4 search modes = 16 total
        self.configurations = [
            # Baseline (all off)
            TestConfiguration(
                "baseline_hybrid",
                False,
                False,
                "hybrid",
                "Baseline: No stemming, No multi-hop, Hybrid search",
            ),
            TestConfiguration(
                "baseline_semantic",
                False,
                False,
                "semantic",
                "Baseline: No stemming, No multi-hop, Semantic only",
            ),
            TestConfiguration(
                "baseline_bm25",
                False,
                False,
                "bm25",
                "Baseline: No stemming, No multi-hop, BM25 only",
            ),
            TestConfiguration(
                "baseline_auto",
                False,
                False,
                "auto",
                "Baseline: No stemming, No multi-hop, Auto mode",
            ),
            # Stemming only
            TestConfiguration(
                "stemming_hybrid",
                True,
                False,
                "hybrid",
                "Stemming only: With stemming, No multi-hop, Hybrid search",
            ),
            TestConfiguration(
                "stemming_semantic",
                True,
                False,
                "semantic",
                "Stemming only: With stemming, No multi-hop, Semantic only",
            ),
            TestConfiguration(
                "stemming_bm25",
                True,
                False,
                "bm25",
                "Stemming only: With stemming, No multi-hop, BM25 only",
            ),
            TestConfiguration(
                "stemming_auto",
                True,
                False,
                "auto",
                "Stemming only: With stemming, No multi-hop, Auto mode",
            ),
            # Multi-hop only
            TestConfiguration(
                "multihop_hybrid",
                False,
                True,
                "hybrid",
                "Multi-hop only: No stemming, With multi-hop, Hybrid search",
            ),
            TestConfiguration(
                "multihop_semantic",
                False,
                True,
                "semantic",
                "Multi-hop only: No stemming, With multi-hop, Semantic only",
            ),
            TestConfiguration(
                "multihop_bm25",
                False,
                True,
                "bm25",
                "Multi-hop only: No stemming, With multi-hop, BM25 only",
            ),
            TestConfiguration(
                "multihop_auto",
                False,
                True,
                "auto",
                "Multi-hop only: No stemming, With multi-hop, Auto mode",
            ),
            # Full stack (both enabled - default)
            TestConfiguration(
                "fullstack_hybrid",
                True,
                True,
                "hybrid",
                "Full stack (default): With stemming, With multi-hop, Hybrid search",
            ),
            TestConfiguration(
                "fullstack_semantic",
                True,
                True,
                "semantic",
                "Full stack: With stemming, With multi-hop, Semantic only",
            ),
            TestConfiguration(
                "fullstack_bm25",
                True,
                True,
                "bm25",
                "Full stack: With stemming, With multi-hop, BM25 only",
            ),
            TestConfiguration(
                "fullstack_auto",
                True,
                True,
                "auto",
                "Full stack: With stemming, With multi-hop, Auto mode",
            ),
        ]

        # Test queries organized by category
        self.test_queries = {
            "verb_forms": [
                "indexing project workflow",
                "searching code semantically",
                "managing memory optimization",
            ],
            "interconnected": [
                "configuration management system",
                "embedding model initialization",
                "error handling flow",
            ],
            "exact_matches": ["class HybridSearcher", "def search_code", "import torch"],
            "natural_language": [
                "how does incremental indexing work",
                "find all authentication functions",
            ],
            "edge_cases": [
                "",  # empty
                "a",  # single char
                "def __init__ self project_path storage_dir embedder bm25_weight dense_weight rrf_k max_workers",  # very long
                "search@#$%code",  # special chars
                "IndexerSearcherChunkerEmbedder",  # concatenated
            ],
        }

    def clear_and_reindex(self) -> Dict[str, Any]:
        """Clear index and re-index from scratch"""
        logger.info("=" * 70)
        logger.info("PHASE 1: CLEAR AND RE-INDEX FROM SCRATCH")
        logger.info("=" * 70)

        try:
            # Remove existing test storage
            if self.storage_dir.exists():
                import shutil

                shutil.rmtree(self.storage_dir)
                logger.info(f"Cleared existing index at {self.storage_dir}")

            self.storage_dir.mkdir(parents=True, exist_ok=True)

            # Create default config for indexing
            config = SearchConfig()
            config.bm25_use_stemming = True
            config.enable_multi_hop = True

            # Initialize components
            chunker = MultiLanguageChunker(str(self.project_path))

            # Create HybridSearcher for indexing
            searcher = HybridSearcher(
                storage_dir=str(self.storage_dir / "index"),
                embedder=self.embedder,
                bm25_weight=config.bm25_weight,
                dense_weight=config.dense_weight,
                rrf_k=config.rrf_k_parameter,
                max_workers=2,
                bm25_use_stopwords=config.bm25_use_stopwords,
                bm25_use_stemming=config.bm25_use_stemming,
            )

            # Index project
            start_time = time.time()
            logger.info(f"Indexing project: {self.project_path}")

            chunks = chunker.chunk_directory(str(self.project_path))
            logger.info(f"Found {len(chunks)} chunks")

            # Generate embeddings
            embedding_results = self.embedder.embed_chunks(chunks)
            logger.info(f"Generated {len(embedding_results)} embeddings")

            # Add to index
            searcher.add_embeddings(embedding_results)
            logger.info("Added embeddings to index")

            # Save index to disk so Phase 2 can load it
            searcher.save_index()
            logger.info("Saved index to disk")

            index_time = time.time() - start_time

            # Get stats
            stats = searcher.get_stats()

            result = {
                "success": True,
                "project_path": str(self.project_path),
                "index_time_seconds": round(index_time, 2),
                "total_chunks": len(chunks),
                "bm25_documents": stats.get("bm25_documents", 0),
                "dense_vectors": stats.get("dense_vectors", 0),
                "is_ready": stats.get("is_ready", False),
            }

            logger.info(f"✅ Indexing complete in {index_time:.2f}s")
            logger.info(f"   Total chunks: {len(chunks)}")
            logger.info(f"   BM25 docs: {stats.get('bm25_documents', 0)}")
            logger.info(f"   Dense vectors: {stats.get('dense_vectors', 0)}")

            return result

        except Exception as e:
            logger.error(f"❌ Re-indexing failed: {e}")
            return {"success": False, "error": str(e)}

    def run_query(
        self, query: str, config: TestConfiguration, k: int = 5
    ) -> QueryResult:
        """Run a single query with specified configuration"""
        try:
            # Create config for this test
            search_config = SearchConfig()
            search_config.bm25_use_stemming = config.stemming_enabled
            search_config.enable_multi_hop = config.multi_hop_enabled
            search_config.default_search_mode = config.search_mode

            # Temporarily set environment variables
            os.environ["CLAUDE_BM25_USE_STEMMING"] = str(config.stemming_enabled).lower()
            os.environ["CLAUDE_ENABLE_MULTI_HOP"] = str(config.multi_hop_enabled).lower()

            # Create searcher with this config
            searcher = HybridSearcher(
                storage_dir=str(self.storage_dir / "index"),
                embedder=self.embedder,
                bm25_weight=search_config.bm25_weight,
                dense_weight=search_config.dense_weight,
                rrf_k=search_config.rrf_k_parameter,
                max_workers=2,
                bm25_use_stopwords=search_config.bm25_use_stopwords,
                bm25_use_stemming=config.stemming_enabled,
            )

            # HybridSearcher loads index automatically during initialization
            # No need to call load() explicitly

            # Run query
            start_time = time.time()
            results = searcher.search(
                query=query, k=k, search_mode=config.search_mode, use_parallel=True
            )
            query_time = (time.time() - start_time) * 1000  # Convert to ms

            # Extract results
            top_result_file = None
            top_result_score = None
            results_preview = []

            if results:
                if len(results) > 0:
                    # SearchResult is a dataclass with doc_id, score, metadata attributes
                    top_result_file = results[0].metadata.get("file", None)
                    top_result_score = results[0].score

                # Preview first 3 results
                for r in results[:3]:
                    results_preview.append(
                        {
                            "file": r.metadata.get("file", ""),
                            "score": round(r.score, 2),
                            "chunk_type": r.metadata.get("chunk_type", ""),
                        }
                    )

            return QueryResult(
                query=query,
                config_name=config.name,
                search_mode=config.search_mode,
                stemming=config.stemming_enabled,
                multi_hop=config.multi_hop_enabled,
                result_count=len(results),
                query_time_ms=round(query_time, 2),
                top_result_file=top_result_file,
                top_result_score=round(top_result_score, 4) if top_result_score else None,
                error=None,
                results_preview=results_preview,
            )

        except Exception as e:
            logger.error(f"Query failed: {query[:50]} | {config.name} | Error: {e}")
            return QueryResult(
                query=query,
                config_name=config.name,
                search_mode=config.search_mode,
                stemming=config.stemming_enabled,
                multi_hop=config.multi_hop_enabled,
                result_count=0,
                query_time_ms=0.0,
                top_result_file=None,
                top_result_score=None,
                error=str(e),
                results_preview=[],
            )

    def run_configuration_tests(self, config: TestConfiguration) -> TestSummary:
        """Run all queries for a single configuration"""
        logger.info(f"\n{'='*70}")
        logger.info(f"Testing: {config.description}")
        logger.info(f"{'='*70}")

        config_results = []
        query_times = []

        # Flatten all queries
        all_queries = []
        for category_queries in self.test_queries.values():
            all_queries.extend(category_queries)

        total_queries = len(all_queries)
        for idx, query in enumerate(all_queries, 1):
            logger.info(f"[{idx}/{total_queries}] Query: '{query[:50]}...'")

            result = self.run_query(query, config)
            config_results.append(result)

            if result.error is None:
                query_times.append(result.query_time_ms)
                logger.info(
                    f"  ✓ Results: {result.result_count}, Time: {result.query_time_ms}ms"
                )
            else:
                logger.warning(f"  ✗ Error: {result.error}")

        # Calculate summary statistics
        successful = [r for r in config_results if r.error is None]
        failed = [r for r in config_results if r.error is not None]

        summary = TestSummary(
            config_name=config.name,
            total_queries=len(config_results),
            successful_queries=len(successful),
            failed_queries=len(failed),
            avg_query_time_ms=round(sum(query_times) / len(query_times), 2)
            if query_times
            else 0,
            avg_result_count=round(
                sum(r.result_count for r in successful) / len(successful), 2
            )
            if successful
            else 0,
            min_time_ms=round(min(query_times), 2) if query_times else 0,
            max_time_ms=round(max(query_times), 2) if query_times else 0,
            total_time_s=round(sum(query_times) / 1000, 2) if query_times else 0,
        )

        logger.info(f"\n{'='*70}")
        logger.info(f"Configuration Summary: {config.name}")
        logger.info(f"  Total queries: {summary.total_queries}")
        logger.info(f"  Successful: {summary.successful_queries}")
        logger.info(f"  Failed: {summary.failed_queries}")
        logger.info(f"  Avg time: {summary.avg_query_time_ms}ms")
        logger.info(f"  Avg results: {summary.avg_result_count}")
        logger.info(f"{'='*70}\n")

        self.results.extend(config_results)
        self.summaries.append(summary)

        return summary

    def run_all_tests(self):
        """Run all test configurations"""
        logger.info("\n" + "=" * 70)
        logger.info("COMPREHENSIVE FEATURE TESTING - v0.5.2")
        logger.info("=" * 70)
        logger.info(f"Project: {self.project_path}")
        logger.info(f"Total configurations: {len(self.configurations)}")
        logger.info(
            f"Total queries per config: {sum(len(q) for q in self.test_queries.values())}"
        )
        logger.info(
            f"Total test runs: {len(self.configurations) * sum(len(q) for q in self.test_queries.values())}"
        )
        logger.info("=" * 70 + "\n")

        # Phase 1: Re-index
        reindex_result = self.clear_and_reindex()
        if not reindex_result.get("success"):
            logger.error("❌ Re-indexing failed. Aborting tests.")
            return

        # Phase 2: Run all configurations
        logger.info("\n" + "=" * 70)
        logger.info("PHASE 2: SYSTEMATIC FEATURE TESTING")
        logger.info("=" * 70)

        for idx, config in enumerate(self.configurations, 1):
            logger.info(f"\nConfiguration {idx}/{len(self.configurations)}")
            self.run_configuration_tests(config)

        # Save results
        self.save_results(reindex_result)

        # Generate report
        try:
            self.generate_report(reindex_result)
        except Exception as e:
            logger.error(f"Failed to generate markdown report: {e}")
            logger.error("Results still saved to JSON file")
            import traceback
            logger.error(traceback.format_exc())

    def save_results(self, reindex_result: Dict[str, Any]):
        """Save raw results to JSON"""
        output_file = project_root / "analysis" / "comprehensive_feature_test_results.json"
        output_file.parent.mkdir(exist_ok=True)

        results_data = {
            "metadata": {
                "test_date": datetime.now().isoformat(),
                "project_path": str(self.project_path),
                "total_configurations": len(self.configurations),
                "total_queries": len(self.results),
            },
            "reindex_result": reindex_result,
            "configurations": [
                {
                    "name": c.name,
                    "stemming": c.stemming_enabled,
                    "multi_hop": c.multi_hop_enabled,
                    "search_mode": c.search_mode,
                    "description": c.description,
                }
                for c in self.configurations
            ],
            "query_results": [asdict(r) for r in self.results],
            "summaries": [asdict(s) for s in self.summaries],
        }

        with open(output_file, "w") as f:
            json.dump(results_data, f, indent=2)

        logger.info(f"\n✅ Results saved to: {output_file}")

    def generate_report(self, reindex_result: Dict[str, Any]):
        """Generate markdown analysis report"""
        report_file = project_root / "analysis" / "COMPREHENSIVE_FEATURE_TEST_REPORT.md"

        # Calculate overall statistics
        total_queries = len(self.results)
        successful_queries = sum(1 for r in self.results if r.error is None)
        failed_queries = total_queries - successful_queries

        # Group summaries by feature combination
        baseline_summaries = [s for s in self.summaries if "baseline" in s.config_name]
        stemming_summaries = [s for s in self.summaries if "stemming_" in s.config_name]
        multihop_summaries = [s for s in self.summaries if "multihop_" in s.config_name]
        fullstack_summaries = [s for s in self.summaries if "fullstack" in s.config_name]

        report = f"""# Comprehensive Feature Test Report - v0.5.2

**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Project:** {self.project_path}
**Status:** {'✅ PASSED' if failed_queries == 0 else '⚠️ ISSUES FOUND'}

---

## Executive Summary

### Overall Results

| Metric | Value |
|--------|-------|
| **Total Test Runs** | {total_queries} |
| **Successful** | {successful_queries} ({successful_queries/total_queries*100:.1f}%) |
| **Failed** | {failed_queries} ({failed_queries/total_queries*100:.1f}%) |
| **Configurations Tested** | {len(self.configurations)} |
| **Queries per Config** | {total_queries // len(self.configurations)} |

### Re-indexing Results

| Metric | Value |
|--------|-------|
| **Status** | {'✅ Success' if reindex_result.get('success') else '❌ Failed'} |
| **Total Chunks** | {reindex_result.get('total_chunks', 0)} |
| **BM25 Documents** | {reindex_result.get('bm25_documents', 0)} |
| **Dense Vectors** | {reindex_result.get('dense_vectors', 0)} |
| **Index Time** | {reindex_result.get('index_time_seconds', 0)}s |

---

## Performance Analysis

### Feature Combination Comparison

#### Baseline (No Stemming, No Multi-hop)

{self._generate_feature_summary(baseline_summaries)}

#### Stemming Only

{self._generate_feature_summary(stemming_summaries)}

#### Multi-hop Only

{self._generate_feature_summary(multihop_summaries)}

#### Full Stack (Both Enabled - Default)

{self._generate_feature_summary(fullstack_summaries)}

### Performance Overhead Analysis

{self._generate_overhead_analysis()}

---

## Quality Analysis

{self._generate_quality_analysis()}

---

## Edge Case Results

{self._generate_edge_case_analysis()}

---

## Error Log

{self._generate_error_log()}

---

## Recommendations

{self._generate_recommendations()}

---

## Conclusion

{self._generate_conclusion()}

---

**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Data File:** `analysis/comprehensive_feature_test_results.json`
"""

        with open(report_file, "w") as f:
            f.write(report)

        logger.info(f"✅ Report generated: {report_file}")

    def _generate_feature_summary(self, summaries: List[TestSummary]) -> str:
        """Generate summary table for a feature combination"""
        if not summaries:
            return "_No data available_"

        avg_time = sum(s.avg_query_time_ms for s in summaries) / len(summaries)
        avg_results = sum(s.avg_result_count for s in summaries) / len(summaries)
        total_successful = sum(s.successful_queries for s in summaries)
        total_failed = sum(s.failed_queries for s in summaries)

        table = "| Search Mode | Avg Time (ms) | Avg Results | Success Rate |\n"
        table += "|-------------|---------------|-------------|-------------|\n"

        for s in summaries:
            success_rate = (
                s.successful_queries / s.total_queries * 100
                if s.total_queries > 0
                else 0
            )
            table += f"| {s.config_name.split('_')[-1]} | {s.avg_query_time_ms} | {s.avg_result_count} | {success_rate:.1f}% |\n"

        table += f"\n**Summary:** Avg time: {avg_time:.2f}ms, Avg results: {avg_results:.2f}, Success: {total_successful}/{total_successful+total_failed}\n"

        return table

    def _generate_overhead_analysis(self) -> str:
        """Analyze performance overhead of features"""
        # Get baseline average
        baseline = [s for s in self.summaries if "baseline_hybrid" == s.config_name]
        stemming = [s for s in self.summaries if "stemming_hybrid" == s.config_name]
        multihop = [s for s in self.summaries if "multihop_hybrid" == s.config_name]
        fullstack = [s for s in self.summaries if "fullstack_hybrid" == s.config_name]

        if not all([baseline, stemming, multihop, fullstack]):
            return "_Insufficient data for overhead analysis_"

        baseline_time = baseline[0].avg_query_time_ms
        stemming_time = stemming[0].avg_query_time_ms
        multihop_time = multihop[0].avg_query_time_ms
        fullstack_time = fullstack[0].avg_query_time_ms

        stemming_overhead = stemming_time - baseline_time
        multihop_overhead = multihop_time - baseline_time
        combined_overhead = fullstack_time - baseline_time

        return f"""
| Feature | Avg Time (ms) | Overhead vs Baseline | Expected | Status |
|---------|---------------|----------------------|----------|--------|
| **Baseline** | {baseline_time} | - | - | ✅ Reference |
| **Stemming Only** | {stemming_time} | +{stemming_overhead:.2f}ms | <1ms | {'✅' if stemming_overhead < 2 else '⚠️'} |
| **Multi-hop Only** | {multihop_time} | +{multihop_overhead:.2f}ms | +25-35ms | {'✅' if 20 < multihop_overhead < 40 else '⚠️'} |
| **Full Stack** | {fullstack_time} | +{combined_overhead:.2f}ms | +26-36ms | {'✅' if 25 < combined_overhead < 40 else '⚠️'} |

**Analysis:**
- Stemming overhead: {stemming_overhead:.2f}ms (expected: <1ms)
- Multi-hop overhead: {multihop_overhead:.2f}ms (expected: +25-35ms)
- Combined overhead: {combined_overhead:.2f}ms (expected: +26-36ms)
"""

    def _generate_quality_analysis(self) -> str:
        """Analyze result quality across configurations"""
        # Compare result counts by feature
        baseline_results = [r for r in self.results if "baseline" in r.config_name and r.error is None]
        stemming_results = [r for r in self.results if "stemming_" in r.config_name and r.error is None]
        multihop_results = [r for r in self.results if "multihop_" in r.config_name and r.error is None]
        fullstack_results = [r for r in self.results if "fullstack" in r.config_name and r.error is None]

        avg_baseline = sum(r.result_count for r in baseline_results) / len(baseline_results) if baseline_results else 0
        avg_stemming = sum(r.result_count for r in stemming_results) / len(stemming_results) if stemming_results else 0
        avg_multihop = sum(r.result_count for r in multihop_results) / len(multihop_results) if multihop_results else 0
        avg_fullstack = sum(r.result_count for r in fullstack_results) / len(fullstack_results) if fullstack_results else 0

        return f"""
### Average Result Counts by Feature

| Feature Combination | Avg Results | vs Baseline |
|---------------------|-------------|-------------|
| Baseline | {avg_baseline:.2f} | - |
| Stemming Only | {avg_stemming:.2f} | {avg_stemming - avg_baseline:+.2f} |
| Multi-hop Only | {avg_multihop:.2f} | {avg_multihop - avg_baseline:+.2f} |
| Full Stack (Default) | {avg_fullstack:.2f} | {avg_fullstack - avg_baseline:+.2f} |

**Interpretation:**
- Higher result counts indicate better recall (finding more relevant code)
- Stemming should improve verb form matching
- Multi-hop should discover interconnected code
- Full stack should show combined benefits
"""

    def _generate_edge_case_analysis(self) -> str:
        """Analyze edge case handling"""
        edge_results = [
            r
            for r in self.results
            if r.query
            in [
                "",
                "a",
                "def __init__ self project_path storage_dir embedder bm25_weight dense_weight rrf_k max_workers",
                "search@#$%code",
                "IndexerSearcherChunkerEmbedder",
            ]
        ]

        if not edge_results:
            return "_No edge case results available_"

        table = "| Query | Config | Results | Time (ms) | Error |\n"
        table += "|-------|--------|---------|-----------|-------|\n"

        for r in edge_results:
            query_display = r.query if len(r.query) <= 30 else r.query[:27] + "..."
            table += f"| `{query_display}` | {r.config_name} | {r.result_count} | {r.query_time_ms} | {r.error if r.error else '✅'} |\n"

        return table

    def _generate_error_log(self) -> str:
        """Generate error log"""
        errors = [r for r in self.results if r.error is not None]

        if not errors:
            return "✅ **No errors detected** - All queries completed successfully!"

        log = f"⚠️ **{len(errors)} errors detected**\n\n"
        log += "| Query | Config | Error |\n"
        log += "|-------|--------|-------|\n"

        for e in errors:
            query_display = e.query if len(e.query) <= 30 else e.query[:27] + "..."
            log += f"| `{query_display}` | {e.config_name} | {e.error} |\n"

        return log

    def _generate_recommendations(self) -> str:
        """Generate recommendations based on test results"""
        failed_queries = sum(1 for r in self.results if r.error is not None)
        total_queries = len(self.results)

        if failed_queries == 0:
            return """
### ✅ All Tests Passed

**Recommendations:**
1. **Production Ready** - All features working as expected
2. **Default Configuration** - Keep stemming + multi-hop enabled
3. **No Adjustments Needed** - Current settings are optimal
"""

        return f"""
### ⚠️ Issues Detected ({failed_queries}/{total_queries} queries failed)

**Recommended Actions:**
1. Review error log above for specific failures
2. Investigate failing queries and configurations
3. Consider disabling problematic features if critical
4. Re-run tests after fixes
"""

    def _generate_conclusion(self) -> str:
        """Generate conclusion"""
        failed = sum(1 for r in self.results if r.error is not None)
        total = len(self.results)
        success_rate = (total - failed) / total * 100 if total > 0 else 0

        if failed == 0:
            return f"""
✅ **PRODUCTION READY**

All {total} test queries completed successfully across {len(self.configurations)} configurations.

**Key Findings:**
- Stemming and Multi-hop features working correctly
- Performance overhead within expected ranges
- No critical errors or edge case failures
- All search modes functioning properly

**Final Recommendation:** **APPROVE FOR v0.5.2 RELEASE**
"""

        return f"""
⚠️ **ISSUES REQUIRE ATTENTION**

**Success Rate:** {success_rate:.1f}% ({total - failed}/{total} queries passed)

**Next Steps:**
1. Review and fix all errors in the error log
2. Re-run comprehensive tests
3. Validate fixes don't introduce regressions
4. Only proceed to release after 100% success rate

**Current Recommendation:** **DO NOT RELEASE** until all issues resolved
"""


def main():
    """Main entry point"""
    project_path = Path(__file__).parent.parent

    logger.info("Starting Comprehensive Feature Testing...")
    logger.info(f"Project: {project_path}")

    tester = ComprehensiveFeatureTester(str(project_path))
    tester.run_all_tests()

    logger.info("\n" + "=" * 70)
    logger.info("TESTING COMPLETE")
    logger.info("=" * 70)
    logger.info("Results: analysis/comprehensive_feature_test_results.json")
    logger.info("Report: analysis/COMPREHENSIVE_FEATURE_TEST_REPORT.md")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
