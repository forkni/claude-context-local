"""Regression tests for Workstream A3 -- CUDA (.cu/.cuh) registration.

`.cu`/`.cuh` route to the existing `tree_sitter_cpp` grammar (no new
tree-sitter dependency, `language_name` stays `"cpp"` -- see
`docs/adr/0054-route-cuda-extensions-to-cpp-grammar.md`). Two CUDA
extensions to plain C++ syntax break that grammar: execution-space
attributes (`__global__`, `__device__`, ...) and the `<<<grid, block>>>`
kernel-launch syntax. `CudaChunker.preprocess_source_for_parse`
(chunking/languages/cpp.py) blanks both, via the same
`LanguageChunker.preprocess_source_for_parse` seam GLSL and the C-family
preprocessor-conditional fix (A2) already use.

Measured over a CUDA sample: routing to plain `cpp` with no CUDA-specific
blanking leaves 62 ERROR lines (3.0%); with `_CUDA_ATTRS` and `_LAUNCH_CFG`
both blanked, 0 ERROR lines (0.0%).
"""

from chunking.languages.cpp import _LAUNCH_CFG, CudaChunker
from chunking.multi_language_chunker import MultiLanguageChunker
from tests.unit.chunking.conftest import assert_length_and_newline_invariants


class TestExtensionRegisteredAndChunkFileWired:
    """`.cu`/`.cuh` extension registration + `LANGUAGE_MAP` wiring.

    Regression guard mirroring `test_multi_language.py`'s
    `test_chunk_cpp_header_file` docstring: registering an extension in
    `EXT_TO_LANGUAGE` without a matching `TreeSitterChunker.LANGUAGE_MAP`
    entry silently yields zero chunks while `is_supported()` still reports
    `True` -- `is_supported()` alone would not have caught the `.h`
    regression this pattern is named after, and would not catch a missing
    `.cu`/`.cuh` LANGUAGE_MAP entry either. Both assertions are required
    together, for both extensions.
    """

    def test_cu_is_supported(self):
        chunker = MultiLanguageChunker()
        assert chunker.is_supported("kernel.cu")

    def test_cuh_is_supported(self):
        chunker = MultiLanguageChunker()
        assert chunker.is_supported("kernel.cuh")

    def test_cu_chunk_file_produces_chunks(self, tmp_path):
        source = tmp_path / "kernel.cu"
        source.write_text(
            "__global__ void kernel(int* data, int n) {\n"
            "    int idx = threadIdx.x;\n"
            "    if (idx < n) data[idx] *= 2;\n"
            "}\n",
            encoding="utf-8",
        )
        chunker = MultiLanguageChunker()
        chunks = chunker.chunk_file(str(source))

        assert len(chunks) > 0, "CUDA parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "kernel" in chunk_names

    def test_cuh_chunk_file_produces_chunks(self, tmp_path):
        header = tmp_path / "kernel.cuh"
        header.write_text(
            "__device__ float square(float x) {\n    return x * x;\n}\n",
            encoding="utf-8",
        )
        chunker = MultiLanguageChunker()
        chunks = chunker.chunk_file(str(header))

        assert len(chunks) > 0, "CUDA header parser produced no chunks"
        chunk_names = {chunk.name for chunk in chunks if chunk.name}
        assert "square" in chunk_names


class TestKernelNamesAndLineNumbers:
    """Execution-space-qualified functions resolve to correct names/lines.

    Uses the leaf `CudaChunker` directly (not `MultiLanguageChunker`) so
    `start_line`/`end_line` are asserted against `TreeSitterChunk` fields
    directly -- same pattern as `test_c_preprocessor_neutralization.py`.
    """

    def setup_method(self):
        self.chunker = CudaChunker()

    def test_device_function_gets_correct_name_and_lines(self):
        source = "__device__ float square(float x) {\n    return x * x;\n}\n"
        chunks = self.chunker.chunk_code(source)
        by_name = {c.metadata.get("name"): c for c in chunks}

        assert "square" in by_name
        chunk = by_name["square"]
        assert chunk.start_line == 1
        assert chunk.end_line == 3

    def test_global_kernel_gets_correct_name_and_lines(self):
        source = (
            "__global__ void computeSquares(const float* input, float* output, int n) {\n"
            "    int idx = blockIdx.x * blockDim.x + threadIdx.x;\n"
            "    if (idx < n) {\n"
            "        output[idx] = input[idx] * input[idx];\n"
            "    }\n"
            "}\n"
        )
        chunks = self.chunker.chunk_code(source)
        by_name = {c.metadata.get("name"): c for c in chunks}

        assert "computeSquares" in by_name
        chunk = by_name["computeSquares"]
        assert chunk.start_line == 1
        assert chunk.end_line == 6

    def test_remaining_execution_space_specifiers_all_resolve(self):
        """`__host__`, `__forceinline__`, `__restrict__`, `__managed__`,
        `__shared__` are the `_CUDA_ATTRS` tokens not exercised by the
        `__device__`/`__global__` tests above -- one combined fixture
        confirms none of them desync the parser (0 ERROR nodes), without a
        dedicated test per token.
        """
        source = (
            "__managed__ int counter;\n"
            "\n"
            "__host__ __forceinline__ int clampIdx(int idx, int n) {\n"
            "    return idx < n ? idx : n - 1;\n"
            "}\n"
            "\n"
            "__global__ void reduce(int* __restrict__ in, int* __restrict__ out) {\n"
            "    __shared__ int cache[256];\n"
            "    cache[threadIdx.x] = in[threadIdx.x];\n"
            "}\n"
        )
        source_bytes = source.encode("utf-8")
        rewritten = self.chunker.preprocess_source_for_parse(source_bytes)
        tree = self.chunker.parser.parse(rewritten)
        assert tree.root_node.has_error is False

        chunks = self.chunker.chunk_code(source)
        names = {c.metadata.get("name") for c in chunks if c.metadata.get("name")}
        assert "clampIdx" in names
        assert "reduce" in names


class TestLaunchConfigNewlinePreservation:
    """Multi-line `<<<grid, block>>>` launch config: length/newline
    invariants + 0 ERROR nodes. Mirrors A2's
    `TestByteLengthAndNewlinePositionInvariants` -- a multi-line regex match
    is exactly the shape a naive `b" " * len(match)` blanker would silently
    corrupt (see `blank_preserving_layout`'s docstring in `_c_family.py`).
    """

    def setup_method(self):
        self.chunker = CudaChunker()

    def test_multiline_launch_config_preserves_length_and_newlines(self):
        source = (
            "void launch(int* data, int n) {\n"
            "    kernel<<<\n"
            "        (n + 255) / 256,\n"
            "        256\n"
            "    >>>(data, n);\n"
            "}\n"
        )
        source_bytes = source.encode("utf-8")
        rewritten = self.chunker.preprocess_source_for_parse(source_bytes)
        assert_length_and_newline_invariants(source_bytes, rewritten)

    def test_launch_config_with_inner_gt_is_blanked_whole(self):
        """A `>` inside the config (ternary / comparison / shift) must not
        terminate the match early -- `[^>]*` used to stop at the first `>`
        and leave the launch unblanked."""
        source = (
            "void launch(int* data, int n) {\n"
            "    kernel<<<n > 0 ? n : 1, n >> 2>>>(data, n);\n"
            "}\n"
        )
        source_bytes = source.encode("utf-8")
        match = _LAUNCH_CFG.search(source_bytes)
        assert match is not None
        assert match.group(0) == b"<<<n > 0 ? n : 1, n >> 2>>>"

        rewritten = self.chunker.preprocess_source_for_parse(source_bytes)
        assert_length_and_newline_invariants(source_bytes, rewritten)
        assert b"<<<" not in rewritten
        tree = self.chunker.parser.parse(rewritten)
        assert tree.root_node.has_error is False

    def test_multiline_launch_config_yields_zero_error_lines(self):
        source = (
            "__global__ void kernel(int* data, int n) {\n"
            "    int idx = threadIdx.x;\n"
            "    if (idx < n) data[idx] *= 2;\n"
            "}\n"
            "\n"
            "void launch(int* data, int n) {\n"
            "    kernel<<<\n"
            "        (n + 255) / 256,\n"
            "        256\n"
            "    >>>(data, n);\n"
            "}\n"
        )
        source_bytes = source.encode("utf-8")
        rewritten = self.chunker.preprocess_source_for_parse(source_bytes)
        tree = self.chunker.parser.parse(rewritten)

        assert tree.root_node.has_error is False

    def test_launch_call_content_preserves_original_text(self):
        """The blanked `<<<...>>>` bytes only feed the parser buffer --
        `chunk.content` is sliced from the original, un-rewritten source
        (the same content/parse separation A2 relies on), so the real
        launch syntax is visible in the indexed text.
        """
        source = (
            "__global__ void kernel(int* data, int n) {}\n"
            "\n"
            "void launch(int* data, int n) {\n"
            "    kernel<<<blocks, threads>>>(data, n);\n"
            "}\n"
        )
        chunks = self.chunker.chunk_code(source)
        by_name = {c.metadata.get("name"): c for c in chunks}

        assert "launch" in by_name
        assert "kernel<<<blocks, threads>>>(data, n);" in by_name["launch"].content

    def test_naive_multiply_blanker_would_have_collapsed_the_newlines(self):
        """Contrast case: `b" " * len(match)` -- the rejected form -- would
        destroy newline positions inside a multi-line `<<<...>>>` match.
        Confirms the invariant tests above are actually discriminating, not
        vacuous, for `_LAUNCH_CFG` specifically.
        """
        source = "kernel<<<\n    blocks,\n    threads\n>>>(data, n);\n"
        source_bytes = source.encode("utf-8")
        match = _LAUNCH_CFG.search(source_bytes)
        assert match is not None

        naive = b" " * len(match.group(0))
        assert len(naive) == len(match.group(0))
        assert naive.count(b"\n") == 0
        assert match.group(0).count(b"\n") == 3


class TestCudaLanguageNameStaysCpp:
    """Design decision: CUDA chunks report `language == "cpp"`, not a new
    `"cuda"` language name -- see `docs/adr/0054-...`. No `LANGUAGE_SPECS`
    entry, no `EXPECTED_LANGUAGES` churn.
    """

    def test_cuda_chunks_report_cpp_language(self):
        chunker = CudaChunker()
        source = "__global__ void kernel(int* data) {}\n"
        chunks = chunker.chunk_code(source)

        assert chunks
        assert all(c.language == "cpp" for c in chunks)
