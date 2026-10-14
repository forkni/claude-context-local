"""Unit tests for embeddings.vram_budget (VRAM cap and batch sizing)."""

from unittest.mock import MagicMock, patch


class TestSetVramLimitEffective:
    """Tests for set_vram_limit() effective-fraction computation.

    Verifies that the VRAM cap accounts for memory already held by other
    processes, preventing Windows WDDM shared-memory spillover when external
    GPU allocations are present at call time.
    """

    # Helpers to build mock torch with configurable mem_get_info / memory_allocated
    @staticmethod
    def _make_torch(
        free_gb: float,
        total_gb: float,
        us_gb: float = 0.0,
        reserved_gb: float | None = None,
    ):
        """Return a MagicMock that mimics torch with the given VRAM readings.

        ``reserved_gb`` defaults to ``us_gb`` (no cached-but-unused blocks).
        """
        m = MagicMock()
        m.cuda.is_available.return_value = True
        m.cuda.mem_get_info.return_value = (
            int(free_gb * 1024**3),
            int(total_gb * 1024**3),
        )
        m.cuda.memory_allocated.return_value = int(us_gb * 1024**3)
        m.cuda.memory_reserved.return_value = int(
            (us_gb if reserved_gb is None else reserved_gb) * 1024**3
        )
        return m

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_no_external_pressure(self, mock_torch, mock_cfg):
        """GPU is idle: effective fraction equals the requested fraction."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(24 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.memory_reserved.return_value = 0
        mock_cfg.return_value = None  # no config → skip allow_ram_fallback check

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_called_once()
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # With no external pressure physical_cap == user_cap → effective == r
        assert 0.79 <= eff <= 0.81, f"expected ~0.80, got {eff:.4f}"

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_other_process_holds_10gb_bug_scenario(self, mock_torch, mock_cfg):
        """Bug scenario: other process holds 10 GB on a 24 GB GPU.

        Expected: effective fraction is reduced so our process + other ≤ 19.2 GB.
        """
        mock_torch.cuda.is_available.return_value = True
        # free=14 GB, total=24 GB, we hold 0 → other = 10 GB
        mock_torch.cuda.mem_get_info.return_value = (
            int(14 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.memory_reserved.return_value = 0
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_called_once()
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # physical_cap = 0 + 14 - 4.8 = 9.2 GB → 9.2/24 ≈ 0.383
        assert 0.36 <= eff <= 0.40, f"expected ~0.383, got {eff:.4f}"
        # Verify total physical demand at saturation doesn't exceed 24 GB
        cap_gb = eff * 24
        assert cap_gb + 10 <= 24.05, f"Would spill: cap={cap_gb:.1f} + other=10 > 24 GB"

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_reapplication_mid_run(self, mock_torch, mock_cfg):
        """Re-application while our process already holds 6 GB, others hold 4 GB."""
        mock_torch.cuda.is_available.return_value = True
        # free=14 GB, total=24 GB, us=6 GB → other=4 GB
        mock_torch.cuda.mem_get_info.return_value = (
            int(14 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = int(6 * 1024**3)
        mock_torch.cuda.memory_reserved.return_value = int(6 * 1024**3)
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # physical_cap = 6 + 14 - 4.8 = 15.2 GB → 15.2/24 ≈ 0.633
        assert 0.61 <= eff <= 0.65, f"expected ~0.633, got {eff:.4f}"
        # Cap must not be below what we already hold
        assert eff * 24 >= 6 - 0.1

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_clamp_when_physical_cap_below_current_usage(self, mock_torch, mock_cfg):
        """GPU under heavy external pressure: cap is forced up to live + working room."""
        mock_torch.cuda.is_available.return_value = True
        # free=2 GB, total=24 GB, us=12 GB → other=10 GB
        mock_torch.cuda.mem_get_info.return_value = (
            int(2 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = int(12 * 1024**3)
        mock_torch.cuda.memory_reserved.return_value = int(12 * 1024**3)
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # physical_cap = 12+2-4.8 = 9.2 < live=12 → floored at live + 0.25 GB room
        assert 0.505 <= eff <= 0.52, f"expected ~0.5104, got {eff:.4f}"

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_min_room_gb_param_sets_working_room(self, mock_torch, mock_cfg):
        """Regression (H4): a cap pinned at live tensors made even a 2 MiB segment
        OOM and batch halving could never recover.  ``min_room_gb`` keeps room."""
        mock_torch.cuda = self._make_torch(free_gb=2.0, total_gb=24.0, us_gb=12.0).cuda
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        assert set_vram_limit(0.8, min_room_gb=1.0) is True
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        assert abs(eff * 24 - 13.0) < 0.05, f"expected ~13 GB cap, got {eff * 24:.2f}"

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_no_room_physically_available_warns(self, mock_torch, mock_cfg, caplog):
        """Nothing free and no cache: room cannot be granted -> explicit WARNING."""
        mock_torch.cuda = self._make_torch(free_gb=0.0, total_gb=24.0, us_gb=12.0).cuda
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        with caplog.at_level("WARNING", logger="embeddings.vram_budget"):
            assert set_vram_limit(0.8) is True
        assert any("working room" in r.getMessage() for r in caplog.records)

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_own_cache_not_counted_as_external_pressure(self, mock_torch, mock_cfg):
        """Regression: the activation warmup leaves ~3.3 GB cached in our own
        allocator.  ``mem_get_info`` free excludes it, so counting only
        ``memory_allocated`` as "ours" misfiled it as another process's VRAM and
        pinned the cap to the model-weight size (655 MB) -> unrecoverable
        "Tried to allocate 2.00 MiB" OOM mid-index.
        """
        torch_mock = self._make_torch(
            free_gb=0.9, total_gb=8.0, us_gb=0.64, reserved_gb=3.94
        )
        mock_torch.cuda = torch_mock.cuda
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        assert set_vram_limit(0.8) is True
        eff = mock_torch.cuda.set_per_process_memory_fraction.call_args[0][0]
        # physical_cap = reserved 3.94 + free 0.9 - headroom 1.6 = 3.24 GB -> 0.405
        assert 0.38 <= eff <= 0.43, f"expected ~0.405, got {eff:.4f}"
        assert eff * 8 > 0.64 + 0.5, "cap must leave room above live allocations"

    @patch("embeddings.vram_budget.torch")
    def test_compute_cap_reports_own_reserved_as_us(self, mock_torch):
        """``us_gb`` is reserved (cache included); ``other_gb`` excludes it."""
        mock_torch.cuda = self._make_torch(
            free_gb=0.9, total_gb=8.0, us_gb=0.64, reserved_gb=3.94
        ).cuda

        from embeddings.vram_budget import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8)
        assert result is not None
        _, cap_bytes, _, us_gb, other_gb, _, _ = result
        assert abs(us_gb - 3.94) < 0.02
        assert abs(other_gb - (8.0 - 0.9 - 3.94)) < 0.02
        assert cap_bytes > int(0.64 * 1024**3)

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_allow_ram_fallback_skips_limit(self, mock_torch, mock_cfg):
        """When allow_ram_fallback=True, set_per_process_memory_fraction is NOT called."""
        mock_torch.cuda.is_available.return_value = True
        perf = MagicMock()
        perf.allow_ram_fallback = True
        cfg = MagicMock()
        cfg.performance = perf
        mock_cfg.return_value = cfg

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_not_called()

    @patch("embeddings.vram_budget.torch", None)
    def test_no_cuda_returns_false(self):
        """Returns False immediately when torch/CUDA is unavailable."""
        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)
        assert result is False

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_set_per_process_raises_returns_false(self, mock_torch, mock_cfg):
        """Returns False and logs a warning when set_per_process_memory_fraction raises."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(20 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.memory_reserved.return_value = 0
        mock_torch.cuda.set_per_process_memory_fraction.side_effect = RuntimeError(
            "CUDA error"
        )
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)
        assert result is False

    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_idempotent_same_inputs(self, mock_torch, mock_cfg):
        """Two back-to-back calls with identical inputs produce the same effective fraction."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(16 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.memory_reserved.return_value = 0
        mock_cfg.return_value = None

        from embeddings.vram_budget import set_vram_limit

        set_vram_limit(0.8)
        eff1 = mock_torch.cuda.set_per_process_memory_fraction.call_args_list[-1][0][0]
        set_vram_limit(0.8)
        eff2 = mock_torch.cuda.set_per_process_memory_fraction.call_args_list[-1][0][0]

        assert abs(eff1 - eff2) < 1e-9

    # --- indexing RAM-fallback override (commit 0e60a1d) ---------------------
    # The module-level override in search.config takes priority over the
    # persisted config value so it survives `_config_manager = None` singleton
    # resets during multi-model indexing. set_vram_limit consults it via the
    # `_get_ram_fallback_override` alias before reading config.

    @patch("embeddings.vram_budget._get_ram_fallback_override")
    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_override_false_forces_cap_over_config_true(
        self, mock_torch, mock_cfg, mock_override
    ):
        """Regression (0e60a1d): override=False applies the cap even when the
        persisted config still reads allow_ram_fallback=True."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.return_value = (
            int(24 * 1024**3),
            int(24 * 1024**3),
        )
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.memory_reserved.return_value = 0
        # Config would otherwise skip the cap...
        perf = MagicMock()
        perf.allow_ram_fallback = True
        cfg = MagicMock()
        cfg.performance = perf
        mock_cfg.return_value = cfg
        # ...but the indexing override forces it on.
        mock_override.return_value = False

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_called_once()

    @patch("embeddings.vram_budget._get_ram_fallback_override")
    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_override_true_skips_cap_over_config_false(
        self, mock_torch, mock_cfg, mock_override
    ):
        """override=True skips the cap even when config reads allow_ram_fallback=False."""
        mock_torch.cuda.is_available.return_value = True
        perf = MagicMock()
        perf.allow_ram_fallback = False
        cfg = MagicMock()
        cfg.performance = perf
        mock_cfg.return_value = cfg
        mock_override.return_value = True

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_not_called()

    @patch("embeddings.vram_budget._get_ram_fallback_override")
    @patch("embeddings.vram_budget.get_search_config")
    @patch("embeddings.vram_budget.torch")
    def test_override_none_defers_to_config(self, mock_torch, mock_cfg, mock_override):
        """override=None defers to the persisted config (here: skip the cap)."""
        mock_torch.cuda.is_available.return_value = True
        perf = MagicMock()
        perf.allow_ram_fallback = True
        cfg = MagicMock()
        cfg.performance = perf
        mock_cfg.return_value = cfg
        mock_override.return_value = None

        from embeddings.vram_budget import set_vram_limit

        result = set_vram_limit(0.8)

        assert result is True
        mock_torch.cuda.set_per_process_memory_fraction.assert_not_called()


class TestCalculateOptimalBatchSizeOwnCache:
    """calculate_optimal_batch_size() must treat our own cached-but-unused VRAM
    (reserved - allocated) as available: ``mem_get_info`` free excludes it, so
    sizing from free alone under-sizes every batch right after the warmup.
    """

    @staticmethod
    def _batch(reserved_gb: float) -> int:
        from embeddings.vram_budget import calculate_optimal_batch_size

        with patch("embeddings.vram_budget.torch") as mock_torch:
            mock_torch.cuda.is_available.return_value = True
            mock_torch.cuda.mem_get_info.return_value = (
                int(0.9 * 1024**3),
                int(8.0 * 1024**3),
            )
            mock_torch.cuda.memory_allocated.return_value = int(0.64 * 1024**3)
            mock_torch.cuda.memory_reserved.return_value = int(reserved_gb * 1024**3)
            return calculate_optimal_batch_size(
                min_batch=4,
                max_batch=256,
                memory_fraction=0.65,
                activation_gb_per_item=0.2,
            )

    def test_cached_vram_counts_as_available(self):
        no_cache = self._batch(reserved_gb=0.64)
        with_cache = self._batch(reserved_gb=3.94)
        assert no_cache == 4  # 0.9 GB free -> floor (laptop min_batch)
        assert with_cache > no_cache
        assert with_cache >= 10  # ~(0.9 + 3.3) x 0.65 x frag / 0.2


class TestComputeEffectiveVramCap:
    """Tests for compute_effective_vram_cap() — the pure helper used by
    set_vram_limit (PyTorch cap).
    """

    @patch("embeddings.vram_budget.torch")
    def test_no_external_pressure_cap_equals_user_request(self, mock_torch):
        """Idle GPU: cap_bytes ≈ fraction × total."""
        mock_torch.cuda.is_available.return_value = True
        total = int(24 * 1024**3)
        mock_torch.cuda.mem_get_info.return_value = (total, total)
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.memory_reserved.return_value = 0

        from embeddings.vram_budget import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8)
        assert result is not None
        eff_frac, cap_bytes, free_gb, us_gb, other_gb, headroom_gb, _ = result
        # cap_bytes should be ≈ 0.80 × 24 GB
        expected_bytes = int(0.8 * total)
        assert abs(cap_bytes - expected_bytes) < 1024**2  # within 1 MB
        assert 0.79 <= eff_frac <= 0.81

    @patch("embeddings.vram_budget.torch")
    def test_other_process_holds_10gb_reduces_cap(self, mock_torch):
        """Bug scenario: other process holds 10 GB on 24 GB GPU.

        physical_cap = 0 + 14 − 4.8 = 9.2 GB → cap_bytes ≈ 9.2 GB.
        """
        mock_torch.cuda.is_available.return_value = True
        total = int(24 * 1024**3)
        mock_torch.cuda.mem_get_info.return_value = (int(14 * 1024**3), total)
        mock_torch.cuda.memory_allocated.return_value = 0
        mock_torch.cuda.memory_reserved.return_value = 0

        from embeddings.vram_budget import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8)
        assert result is not None
        eff_frac, cap_bytes, free_gb, us_gb, other_gb, headroom_gb, _ = result
        cap_gb = cap_bytes / 1024**3
        # physical_cap = 14 − 4.8 = 9.2 GB
        assert 9.0 <= cap_gb <= 9.4, f"expected ~9.2 GB cap, got {cap_gb:.2f} GB"
        assert 0.36 <= eff_frac <= 0.40
        # Diagnostic fields
        assert abs(free_gb - 14.0) < 0.1
        assert abs(other_gb - 10.0) < 0.1
        assert abs(headroom_gb - 4.8) < 0.1

    @patch("embeddings.vram_budget.torch")
    def test_reapplication_mid_run(self, mock_torch):
        """Re-application while holding 6 GB, others hold 4 GB.

        physical_cap = 6 + 14 − 4.8 = 15.2 GB.
        """
        mock_torch.cuda.is_available.return_value = True
        total = int(24 * 1024**3)
        mock_torch.cuda.mem_get_info.return_value = (int(14 * 1024**3), total)
        mock_torch.cuda.memory_allocated.return_value = int(6 * 1024**3)
        mock_torch.cuda.memory_reserved.return_value = int(6 * 1024**3)

        from embeddings.vram_budget import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8)
        assert result is not None
        eff_frac, cap_bytes, free_gb, us_gb, other_gb, headroom_gb, _ = result
        cap_gb = cap_bytes / 1024**3
        # physical_cap = 6 + 14 - 4.8 = 15.2 GB
        assert 15.0 <= cap_gb <= 15.4, f"expected ~15.2 GB cap, got {cap_gb:.2f} GB"
        # cap must never be below current us (6 GB)
        assert cap_gb >= 5.9

    @patch("embeddings.vram_budget.torch")
    def test_floor_leaves_working_room(self, mock_torch):
        """Pinned at live tensors (external squeeze): ``min_room_b`` lifts the cap
        above them, bounded by what is physically free."""
        mock_torch.cuda = TestSetVramLimitEffective._make_torch(
            free_gb=2.0, total_gb=24.0, us_gb=12.0
        ).cuda

        from embeddings.vram_budget import compute_effective_vram_cap

        legacy = compute_effective_vram_cap(0.8)
        assert legacy is not None
        assert abs(legacy.cap_bytes / 1024**3 - 12.0) < 0.01  # default = no room
        assert legacy.room_gb == 0.0

        result = compute_effective_vram_cap(0.8, min_room_b=1024**3)
        assert result is not None
        assert abs(result.cap_bytes / 1024**3 - 13.0) < 0.01
        assert abs(result.room_gb - 1.0) < 0.01

    @patch("embeddings.vram_budget.torch")
    def test_room_bounded_by_physical(self, mock_torch):
        """Room is never granted from memory that does not exist:
        own cache 0.2 GB + system free 0.3 GB = 0.5 GB at most."""
        mock_torch.cuda = TestSetVramLimitEffective._make_torch(
            free_gb=0.3, total_gb=24.0, us_gb=12.0, reserved_gb=12.2
        ).cuda

        from embeddings.vram_budget import compute_effective_vram_cap

        result = compute_effective_vram_cap(0.8, min_room_b=1024**3)
        assert result is not None
        assert abs(result.room_gb - 0.5) < 0.01
        assert abs(result.cap_bytes / 1024**3 - 12.5) < 0.01

    @patch("embeddings.vram_budget.torch", None)
    def test_no_cuda_returns_none(self):
        """Returns None when torch is unavailable."""
        from embeddings.vram_budget import compute_effective_vram_cap

        assert compute_effective_vram_cap(0.8) is None

    @patch("embeddings.vram_budget.torch")
    def test_no_cuda_available_returns_none(self, mock_torch):
        """Returns None when CUDA is not available."""
        mock_torch.cuda.is_available.return_value = False

        from embeddings.vram_budget import compute_effective_vram_cap

        assert compute_effective_vram_cap(0.8) is None

    @patch("embeddings.vram_budget.torch")
    def test_mem_get_info_raises_returns_none(self, mock_torch):
        """Returns None when GPU measurement fails."""
        mock_torch.cuda.is_available.return_value = True
        mock_torch.cuda.mem_get_info.side_effect = RuntimeError("CUDA error")

        from embeddings.vram_budget import compute_effective_vram_cap

        assert compute_effective_vram_cap(0.8) is None


class TestReapplyVramCap:
    """reapply_vram_cap(): the non-fatal re-apply rerankers run before loading."""

    @patch("embeddings.vram_budget.set_vram_limit")
    @patch("embeddings.vram_budget.get_search_config")
    def test_applies_configured_fraction(self, mock_get_cfg, mock_set):
        mock_get_cfg.return_value.performance.vram_limit_fraction = 0.75

        from embeddings.vram_budget import reapply_vram_cap

        reapply_vram_cap()

        mock_set.assert_called_once_with(0.75)

    @patch("embeddings.vram_budget.set_vram_limit")
    @patch("embeddings.vram_budget.get_search_config")
    def test_failure_is_swallowed_and_logged_on_given_logger(
        self, mock_get_cfg, mock_set
    ):
        mock_get_cfg.side_effect = RuntimeError("config unavailable")
        logger = MagicMock()

        from embeddings.vram_budget import reapply_vram_cap

        reapply_vram_cap(logger)

        mock_set.assert_not_called()
        logger.debug.assert_called_once()
        assert "non-fatal" in logger.debug.call_args.args[0]
