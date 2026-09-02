# Our system, Arm B (retrieval-only, reranker off), Round 1 — raw results

Config: `search_config.json` with `reranker.enabled=false`, `reranker.top_k_candidates=5`,
`search_mode.leg_search_multiplier=1`, `intent.enabled=false` (all four pinned per the plan's
Arm B spec — isolates chunking + fusion + graph from the cross-encoder). `search_mode="hybrid"`
passed explicitly, `k=10`. Same index as Arm A: `F2LLM-v2-0.6B`, 1024d,
`SDTD_040_Beta_8f1a0037`.

**Verification #2 check (plan)**: A1 run first as a divergence probe before the full sweep.
Arm B's top-7 for A1 is completely different from Arm A's, and the known candidate
`_is_oom_error` (Arm A rank 1, blended_score 0.8521) does not appear in Arm B's top-10 at all.
Ablation confirmed real — proceeding with full sweep.

**Note on scores**: without the reranker, `blended_score` reflects raw fusion scores (BM25 +
dense), which are unbounded and not comparable in magnitude to Arm A's reranker-compressed
0-1 range (e.g. 20.85, 15.23). Only relative order within a query is meaningful; cross-arm
score comparison is not.

Rows = top-10 requested, non-`.py` dropped, first 7 kept per harness parity rules.

## A1 — CUDA OOM detection/classification, incl. RuntimeErrors from TensorRT

Known candidate: `wrapper.py` `_is_oom_error`

**Note**: known candidate does NOT appear in top 10 at all — full miss. Top hits are
unrelated CUDA runtime error-checking code in `td_exporter/` (`CUDARuntimeAPI.check_error`,
`CudaLinkError`, `CudaIpcError`) rather than the wrapper's OOM classifier.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCWrapper.py:688-702:method:CUDARuntimeAPI.check_error` | method | 20.8518 |
| 2 | `Scripts/td_exporter/CUDARuntimeTypes.py:204-206:method:CudaLinkError.__init__` | method | 15.2295 |
| 3 | `Scripts/td_exporter/CUDARuntimeTypes.py:209-210:class:CudaIpcError` | class | 11.3724 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:85-94:method:_BuildLogFilter.log` | method | 5.8765 |
| 5 | `Scripts/td_exporter/TDSender.py:178-237:method:TDSenderEngine.__init__` | method | 4.9168 |
| 6 | `Scripts/td_exporter/Exporter.py:536-562:split_block:Exporter.export` | split_block | 4.851 |
| 7 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:38-86:method:StreamDiffusionExt.__init__` | method | 3.9198 |

## A2 — FP8 calibration per-image retry after batch encode failure

Known candidate: `wrapper.py` `_encode_fp8_calibration_images`

**Note**: known candidate does NOT appear in top 10 at all — full miss (Arm A had it rank 1,
blended_score 0.9072). Adjacent calibration helpers (`_resolve_fp8_calibration_dir`,
`_load_fp8_calibration_style_images`, `_list_calibration_images`) and IPAdapter-calibration
test methods surface instead.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:235-272:function:_resolve_fp8_calibration_dir` | function | 46.296 |
| 2 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:326-343:method:TestResolveFp8IpadapterCalibrationTokens.test_style_images_all_encode_failures_fall_through_to_cached` | method | 33.6906 |
| 3 | `StreamDiffusion/src/streamdiffusion/wrapper.py:195-221:function:_load_fp8_calibration_style_images` | function | 34.9932 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:48-76:function:_list_calibration_images` | function | 32.802 |
| 5 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:240-257:method:TestResolveFp8IpadapterCalibrationTokens.test_style_images_restores_num_tokens_after_multi_image_encode` | method | 31.4048 |
| 6 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:305-324:method:TestResolveFp8IpadapterCalibrationTokens.test_style_images_all_encode_failures_fall_through_to_surrogate` | method | 30.1308 |
| 7 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:33-34:function:_write_tiny_image` | function | 12.8132 |

## A3 — feedback-loop blend formula (current input vs. previous frame's diffusion output)

Known candidate: `preprocessing/processors/feedback.py` `FeedbackPreprocessor`

**Note**: known candidate file present but weakly — only 1 of 7 rows (`FeedbackPreprocessor.reset`
at rank 1) comes from it, vs. Arm A's full class body + `_process_core`/`_process_tensor_core`
in top 3. The other 6 rows are the unrelated `FeedbackLoopPreprocessor` (a different TD custom
processor, `custom_processors/sdtd_fx/feedback_loop.py`) — a same-named-concept confusion the
reranker resolved in Arm A but retrieval-only ranking does not.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:81-83:method:FeedbackPreprocessor.reset` | method | 1.08 |
| 2 | `custom_processors/sdtd_fx/feedback_loop.py:330-342:method:FeedbackLoopPreprocessor._unsharp_mask` | method | 1.056 |
| 3 | `Scripts/custom_processors__Text__feedback_loop__td.py:330-342:method:FeedbackLoopPreprocessor._unsharp_mask` | method | 1.032 |
| 4 | `StreamDiffusionTD-fork/operator/custom_processors/sdtd_fx/feedback_loop.py:120-124:method:FeedbackLoopPreprocessor._get_prev_output` | method | 0.8844 |
| 5 | `StreamDiffusionTD-fork/operator/custom_processors/sdtd_fx/feedback_loop.py:169-189:method:FeedbackLoopPreprocessor._process_core` | method | 0.792 |
| 6 | `StreamDiffusionTD-fork/operator/custom_processors/sdtd_fx/feedback_loop.py:191-224:method:FeedbackLoopPreprocessor._process_tensor_core` | method | 0.78 |
| 7 | `StreamDiffusion/custom_processors/sdtd_fx/feedback_loop.py:312-328:method:FeedbackLoopPreprocessor._get_blur_kernel` | method | 0.768 |

## A4 — IPAdapter embedding preprocessor avoids re-encoding unchanged style image

Known candidate: `preprocessing/processors/ipadapter_embedding.py` `_last_input_ptr`/`_cached_embeds`

**Note**: known candidate file present at 4 of 7 ranks (1, 3, 4, 7) including `_process_core`
(rank 3, likely where the pointer-cache check lives) and `process`/`__init__`, but the specific
`_last_input_ptr`/`_cached_embeds` attributes are not directly named in any returned chunk.
Reasonable file-level coverage, weaker than Arm A's direct `_process_tensor_core` rank-1 hit.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:17-24:decorated_definition:IPAdapterEmbeddingPreprocessor.get_preprocessor_metadata` | decorated_definition | 30.404 |
| 2 | `StreamDiffusion/demo/realtime-img2img/img2img.py:368-370:method:Pipeline.update_ipadapter_style_image` | method | 24.8256 |
| 3 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:45-75:method:IPAdapterEmbeddingPreprocessor._process_core` | method | 21.864 |
| 4 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:99-107:method:IPAdapterEmbeddingPreprocessor.process` | method | 21.78 |
| 5 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/faceid_embedding.py:12-93:class:FaceIDEmbeddingPreprocessor` | class | 16.0866 |
| 6 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/faceid_embedding.py:19-42:decorated_definition:FaceIDEmbeddingPreprocessor.get_preprocessor_metadata` | decorated_definition | 14.861 |
| 7 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:26-43:method:IPAdapterEmbeddingPreprocessor.__init__` | method | 14.796 |

## A5 — calibration image set signature hashed for TensorRT engine cache-key suffix

Known candidate: `acceleration/tensorrt/engine_manager.py` `_calibration_image_signature`

Known candidate present at rank 5 (via ego_graph), in top 7 but not prioritized as in Arm A
(rank 1 there). `_trt_cc_tag` (a sibling cache-key-suffix method) ranks higher at 4.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/tests/unit/test_engine_path_ipadapter_suffixes.py:94-126:class:TestVaePathsIgnoreIpAdapterFlags` | class | 0.9524 |
| 2 | `StreamDiffusion/tests/unit/test_engine_path_controlnet_tokens.py:79-84:function:_make_engine_manager` | function | 0.92 |
| 3 | `StreamDiffusion/tests/unit/test_engine_path_ipadapter_suffixes.py:95-100:method:TestVaePathsIgnoreIpAdapterFlags.test_vae_encoder_path_unaffected_by_faceid` | method | 0.8364 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py:166-183:method:EngineManager._trt_cc_tag` | method | 0.672 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py:109-135:method:EngineManager._calibration_image_signature` | method | 0.6708 |
| 6 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:37-44:function:_make_engine_manager` | function | 0.662 |
| 7 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:112-165:class:TestListLoadHashAgreement` | class | 0.6426 |

## A6 — auth token stored via OS-native secure storage (DPAPI/Keychain)

Known candidate: `Scripts/tox_updater__Text__secure_storage__td.py` `store_token`

**Note**: the exact known candidate (`secure_storage__td.py`'s own `store_token`) does NOT
appear in top 7 (it's rank 10 in the raw 30, blended_score 37.8432) — the platform-specific
`_windows`/`_macos` `store_token`/`load_token`/`delete_token` variants dominate instead
(ranks 1-4, 7), with the base module's `load_token`/`delete_token` present at 5-6 but not
`store_token`. Partial miss on the specific candidate; file-family coverage is otherwise strong.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:51-84:function:store_token` | function | 66.0096 |
| 2 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:87-117:function:load_token` | function | 65.4912 |
| 3 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:152-165:function:store_token` | function | 64.8 |
| 4 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:189-193:function:delete_token` | function | 64.5264 |
| 5 | `Scripts/tox_updater__Text__secure_storage__td.py:56-72:function:load_token` | function | 58.5792 |
| 6 | `Scripts/tox_updater__Text__secure_storage__td.py:75-86:function:delete_token` | function | 57.8016 |
| 7 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:168-186:function:load_token` | function | 51.5952 |

## A7 — TD Script TOP pixel-format string from tensor dtype/channel count for CUDA memcpy

Known candidate: `Scripts/td_exporter/TDReceiver.py` `td_format_string`

**Note**: known candidate does NOT appear in top 10 at all — full miss (Arm A had it rank 1,
blended_score 0.7344). Top hits are unrelated OSC-handler and IPC-diagnostic code with no
connection to pixel-format computation.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/StreamDiffusionTD/td_manager.py:891-918:method:TouchDesignerManager._log_ipc_input_diagnostics` | method | 28.356 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/models/models.py:36-40:method:Optimizer.info` | method | 10.056 |
| 3 | `Scripts/td_exporter/Importer.py:1880-1883:method:Importer.close` | method | 8.808 |
| 4 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:111-128:method:OSCParameterHandler.stop` | method | 7.716 |
| 5 | `.upstream_models_dotsimulate.py:31-35:method:Optimizer.info` | method | 7.608 |
| 6 | `Scripts/td_exporter/Importer.py:268-323:decorated_definition:IPCConnection` | decorated_definition | 7.26 |
| 7 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:62-86:method:OSCParameterHandler.__init__` | method | 7.1604 |

## A8 — REST endpoint accepting uploaded ControlNet YAML config

Known candidate: `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py` `upload_controlnet_config`

**Note**: the exact known candidate function does NOT appear in top 7 — full miss on the
specific target (Arm A had it rank 1, blended_score 0.583). The known-candidate *file* is
present (module preamble rank 1, `add_controlnet`/`get_controlnet_status`/`get_controlnet_info`
— other endpoints in the same file — ranks 5-7), plus an unrelated same-named-concept
`generate_td_config_yaml` (TD-side YAML generation, not the FastAPI upload route) at ranks 2-3.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:1-18:module_preamble` | module_preamble | 14.78 |
| 2 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:3512-3561:split_block:StreamDiffusionExt.generate_td_config_yaml` | split_block | 14.74 |
| 3 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:4039-4057:split_block:StreamDiffusionExt.generate_td_config_yaml` | split_block | 1.001 |
| 4 | `StreamDiffusion/demo/realtime-img2img/main.py:320-330:method:AppState.add_controlnet` | method | 0.936 |
| 5 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:308-384:decorated_definition:add_controlnet` | decorated_definition | 0.53 |
| 6 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:387-412:decorated_definition:get_controlnet_status` | decorated_definition | 0.51 |
| 7 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:170-173:decorated_definition:get_controlnet_info` | decorated_definition | 0.5 |

## A9 — FP8 calibration prompts loaded from bundled text file

Known candidate: `acceleration/tensorrt/fp8_quantize.py` (near `_BUNDLED_PROMPTS_PATH`)

**Note**: full miss — `_load_calibration_prompts` (the actual function, named in the module's
own summary field) does not surface directly in top 7; the `fp8_quantize` module chunk that
carries that summary text sits at rank 15 in the raw 30 (blended_score 0.3132), further down
than in Arm A (rank 4 there). Top hits are calibration-*image* code, same ambiguity as Arm A
but worse-ranked.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1075-1113:split_block:capture_calibration_data` | split_block | 1.1858 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:48-76:function:_list_calibration_images` | function | 1.1088 |
| 3 | `StreamDiffusion/scripts/fp8/measure_fp8_calib_amax.py:75-157:function:main` | function | 0.972 |
| 4 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:47-109:class:TestResolveFp8CalibrationDir` | class | 0.9639 |
| 5 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:72-81:method:TestResolveFp8CalibrationDir.test_missing_subfolder_returns_original_path_unchanged_with_warning` | method | 0.8364 |
| 6 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:106-109:method:TestResolveFp8CalibrationDir.test_nonexistent_path_returns_unchanged` | method | 0.8262 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:738-753:function:load_calib_provenance` | function | 0.636 |

## A10 — TF32 matmul and cuDNN benchmark mode enabled once per CUDA device at pipeline construction

Known candidate: `pipeline.py` `StreamDiffusion.__init__`

**Note**: full miss — nothing in top 10 (or the raw 30) relates to TF32/cuDNN/pipeline
construction at all. Results are dominated by unrelated CUDA diagnostics/env-gating code
(`NVTXShim.py`, `cuda_l2_cache.py`, `test_l2_cache_gating.py`) and FP8 quantization module
preamble — a topically adjacent but wrong cluster (both are CUDA-perf-tuning-flavored, but
neither is TF32/cuDNN). Worse than Arm A, which resolved this correctly.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/NVTXShim.py:96-97:function:is_verbose` | function | 1.1454 |
| 2 | `StreamDiffusion/src/streamdiffusion/tools/cuda_l2_cache.py:58-59:function:_env_tier2` | function | 0.966 |
| 3 | `StreamDiffusion/tests/unit/test_l2_cache_gating.py:77-81:method:TestSetupL2PersistenceResolver.test_persist_mb_env_overrides_default` | method | 0.8309 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1-45:module_preamble` | module_preamble | 0.81 |
| 5 | `Scripts/td_exporter/NVTXShim.py:92-93:function:is_enabled` | function | 0.7326 |
| 6 | `StreamDiffusion/src/streamdiffusion/tools/cuda_l2_cache.py:49-51:function:_env_enabled` | function | 0.7176 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:265-281:function:_fallback_profile` | function | 0.552 |

## B1 — Sender and Receiver engines for CUDA IPC frame export/import as a matched pair

Known candidates: `Scripts/td_exporter/TDSender.py`, `TDReceiver.py`

**Note**: partial — top 7 is dominated by `CUDAIPCExtension` (the delegating orchestrator),
not the paired engine classes themselves; `TDReceiverEngine`/`TDSenderEngine` classes rank
9-10 (blended_score 0.6652/0.6614), just outside top 7. The extension's `export_frame`/
`import_frame` pair (ranks 1-2) does answer the "matched pair" framing, just one layer up
from the named candidate files.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:261-264:method:CUDAIPCExtension.export_frame` | method | 1.1076 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:266-270:method:CUDAIPCExtension.import_frame` | method | 1.0764 |
| 3 | `Scripts/td_exporter/CUDAIPCExtension.py:316-317:method:CUDAIPCExtension.is_ready` | method | 1.008 |
| 4 | `Scripts/td_exporter/CUDAIPCExtension.py:306-308:method:CUDAIPCExtension.initialize_receiver` | method | 0.9648 |
| 5 | `Scripts/td_exporter/CUDAIPCExtension.py:216-238:method:CUDAIPCExtension._make_engine` | method | 0.816 |
| 6 | `Scripts/td_exporter/CUDAIPCExtension.py:257-259:method:CUDAIPCExtension.initialize` | method | 0.792 |
| 7 | `Scripts/td_exporter/CUDAIPCExtension.py:360-363:method:CUDAIPCExtension.request_immediate_reconnect` | method | 0.78 |

## B2 — Windows and macOS secure-storage backends as parallel platform-specific modules

Known candidates: `secure_storage_windows__td.py`, `secure_storage_macos__td.py`

**Note**: full coverage — both platform modules represented in top 7 (Windows: ranks 1-3,5;
macOS: ranks 4,6-7), directly answering the "parallel platform-specific modules" framing.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:22-23:class:DATA_BLOB` | class | 28.647 |
| 2 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:147-149:function:get_storage_path` | function | 28.5258 |
| 3 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:139-144:function:get_storage_dir` | function | 27.0584 |
| 4 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:31-48:function:_run_security_command` | function | 24.5985 |
| 5 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:168-186:function:load_token` | function | 24.5295 |
| 6 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:51-84:function:store_token` | function | 24.0235 |
| 7 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:87-117:function:load_token` | function | 23.506 |

## B3 — test file for multi-ControlNet residual-merge vs. the module it tests

Known candidates: `test_controlnet_residual_merge.py` vs `modules/controlnet_module.py`

**Note**: partial — the test file is fully covered (all 7 top rows are from
`test_controlnet_residual_merge.py`), but the implementing module `ControlNetModule` (class,
`modules/controlnet_module.py`) does not appear until rank 14 (blended_score 17.6296),
outside top 7 — the query's second half ("which module implements the merge") is unanswered
within the cut.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:69-186:class:TestControlNetResidualMerge` | class | 41.3338 |
| 2 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:166-186:method:TestControlNetResidualMerge.test_install_resets_merge_buffers` | method | 37.8235 |
| 3 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:70-81:method:TestControlNetResidualMerge.test_merge_is_numerically_correct` | method | 34.7685 |
| 4 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:20-36:class:_FakeCN` | class | 34.6673 |
| 5 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:44-56:function:_make_module_with_two_controlnets` | function | 33.7899 |
| 6 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:30-36:method:_FakeCN.__call__` | method | 32.5203 |
| 7 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:104-125:method:TestControlNetResidualMerge.test_merge_reallocates_on_shape_change` | method | 32.4264 |

## B4 — single-frame and multi-frame variants of img2img/txt2img example scripts

Known candidates: `examples/{img2img,txt2img}/{single,multi}.py`

**Note**: full coverage — all four combinations (img2img/single, img2img/multi, txt2img/single,
txt2img/multi) represented in top 7.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/examples/img2img/single.py:14-102:function:main` | function | 0.696 |
| 2 | `StreamDiffusion/examples/img2img/single.py:105-106:module_preamble` | module_preamble | 0.66 |
| 3 | `StreamDiffusion/examples/txt2img/multi.py:14-82:function:main` | function | 0.66 |
| 4 | `StreamDiffusion/examples/txt2img/single.py:14-76:function:main` | function | 0.66 |
| 5 | `StreamDiffusion/examples/txt2img/multi.py:85-86:module_preamble` | module_preamble | 0.65 |
| 6 | `StreamDiffusion/examples/txt2img/single.py:79-80:module_preamble` | module_preamble | 0.64 |
| 7 | `StreamDiffusion/examples/img2img/multi.py:1-12:module_preamble` | module_preamble | 0.61 |

## B5 — shmem_in_cn_processed and shmem_out_out_ip script sets mirroring callback structure

Known candidates: `shmem_in_cn_processed__*`, `shmem_out_out_ip__*`

**Note**: only 10 raw results returned (not the usual ~30). Both set's module_preambles are
present (ranks 1-2), and `shmem_in_cn_processed` gets further coverage at 3 and 7, but
`shmem_out_out_ip`'s second file (`output_callbacks`) ranks 9, outside top 7. Three unrelated
`ParExecute` modules from other, unrelated TD extensions (`TDAsyncIO`, `local`, `Logger`)
pollute ranks 4-6 — mixed/partial coverage with noise.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/shmem_in_cn_processed__Text__SharedMemEXT__td.py:1-36:module_preamble` | module_preamble | 0.61 |
| 2 | `Scripts/shmem_out_out_ip__Text__SharedMemEXT__td.py:1-36:module_preamble` | module_preamble | 0.6 |
| 3 | `Scripts/shmem_in_cn_processed__ParExecute__parexec_color__td.py:0-0:module` | module | 0.3881 |
| 4 | `Scripts/TDAsyncIO__ParExecute__extensionParExec__td.py:0-0:module` | module | 0.3528 |
| 5 | `Scripts/local__ParExecute__parexec1__td.py:0-0:module` | module | 0.3485 |
| 6 | `Scripts/Logger__ParExecute__extensionParExec__td.py:0-0:module` | module | 0.3443 |
| 7 | `Scripts/shmem_in_cn_processed__Text__output_callbacks__td.py:0-0:module` | module | 0.3212 |

## B6 — test for FaceID LoRA fusion vs. module implementing FaceID compatibility

Known candidates: `test_faceid_lora_fusion.py` vs `modules/faceid_compat.py`

**Note**: partial — test file fully covered (all 7 top rows), but the implementing function
`fuse_faceid_lora` (`faceid_compat.py`) ranks 8th (blended_score 25.599), just outside top 7 —
same test-dominates-module pattern as B3.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:31-43:class:_FakeAttnModule` | class | 41.3276 |
| 2 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:112-125:method:TestFuseFaceIdLora.test_second_fusion_is_a_noop` | method | 32.1646 |
| 3 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:62-74:function:_make_lora_checkpoint` | function | 32.0574 |
| 4 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:142-158:method:TestFuseFaceIdLora.test_no_lora_keys_is_a_noop` | method | 30.7746 |
| 5 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:160-179:method:TestFuseFaceIdLora.test_partial_lora_only_fuses_layers_present_in_checkpoint` | method | 30.2588 |
| 6 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:99-110:method:TestFuseFaceIdLora.test_lora_scale_scales_the_delta` | method | 28.9892 |
| 7 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:127-140:method:TestFuseFaceIdLora.test_shape_mismatch_raises` | method | 27.7989 |

## C1 — StreamDiffusion pipeline class constructor (CFG type, LoRA dict, KV-cache, feature injection)

Known candidate: `pipeline.py` `class StreamDiffusion.__init__`

**Note**: partial — the full `StreamDiffusion` class chunk (which spans and includes
`__init__`) is present at rank 4 (blended_score 0.8524), but the specific `__init__` split_block
itself ranks 8th (0.5797), just outside top 7. Ranks 1,3,5-7 are noise (wrapper.py's unrelated
`_load_model`, the *demo* `Pipeline` class's `get_ipadapter_info`, and unrelated
`realtime-txt2img`/`realtime-img2img` `config.py` preambles) — considerable dilution around
the one directly-relevant class chunk.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:2371-3334:split_block:StreamDiffusionWrapper._load_model` | split_block | 0.903 |
| 2 | `StreamDiffusion/src/streamdiffusion/pipeline.py:1659-1689:decorated_definition:StreamDiffusion.txt2img` | decorated_definition | 0.891 |
| 3 | `StreamDiffusion/demo/realtime-img2img/img2img.py:387-424:method:Pipeline.get_ipadapter_info` | method | 0.8625 |
| 4 | `StreamDiffusion/src/streamdiffusion/pipeline.py:42-1754:class:StreamDiffusion` | class | 0.8524 |
| 5 | `StreamDiffusion/demo/realtime-txt2img/config.py:1-7:module_preamble` | module_preamble | 0.74 |
| 6 | `StreamDiffusion/demo/realtime-img2img/config.py:32-140:module_preamble` | module_preamble | 0.71 |
| 7 | `StreamDiffusion/demo/realtime-txt2img/config.py:10-49:decorated_definition:Config` | decorated_definition | 0.649 |

## C2 — architecture of the CUDA IPC extension delegating sender/receiver work to separate engines

Known candidate: `Scripts/td_exporter/CUDAIPCExtension.py` module docstring

**Note**: partial — functional coverage is strong (6/7 rows are `CUDAIPCExtension` methods
showing the delegation surface: `initialize_receiver`, `export_frame`/`import_frame`
elsewhere, format/resolution consumption), but the module docstring itself (the narrative
"architecture" answer) does not appear in top 7 — only method-level chunks, no overview text.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/TDReceiver.py:612-636:method:TDReceiverEngine.update_receiver_format` | method | 1.0692 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:387-396:method:CUDAIPCExtension.consume_pending_format` | method | 1.068 |
| 3 | `Scripts/td_exporter/CUDAIPCExtension.py:306-308:method:CUDAIPCExtension.initialize_receiver` | method | 1.0368 |
| 4 | `Scripts/td_exporter/CUDAIPCExtension.py:316-317:method:CUDAIPCExtension.is_ready` | method | 0.9648 |
| 5 | `Scripts/td_exporter/CUDAIPCExtension.py:216-238:method:CUDAIPCExtension._make_engine` | method | 0.924 |
| 6 | `Scripts/td_exporter/CUDAIPCExtension.py:257-259:method:CUDAIPCExtension.initialize` | method | 0.876 |
| 7 | `Scripts/td_exporter/CUDAIPCExtension.py:276-279:method:CUDAIPCExtension.update_receiver_resolution` | method | 0.8712 |

## C3 — StreamDiffusionTD extension class responsibilities (model mgmt, TRT build, version tracking)

Known candidate: `class StreamDiffusionExt` (`StreamDiffusionTD__Text__StreamDiffusionExt__td.py`)

**Note**: partial — the full `StreamDiffusionExt` class chunk is present at rank 5, but ranks
3-4 are `TouchDesignerManager.start_streaming` — a **different, adjacent class**, not
`StreamDiffusionExt` — and ranks 1-2 are a narrow `get_td_version` getter duplicated across
file copies. Overview-level coverage of the class's actual responsibility set (model
management, TRT build, version tracking) is thin; mostly narrow/adjacent methods.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:97-102:method:StreamDiffusionExt.get_td_version` | method | 1.0212 |
| 2 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:100-105:method:StreamDiffusionExt.get_td_version` | method | 1.0074 |
| 3 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:230-256:method:TouchDesignerManager.start_streaming` | method | 0.9775 |
| 4 | `StreamDiffusion/StreamDiffusionTD/td_manager.py:230-256:method:TouchDesignerManager.start_streaming` | method | 0.9775 |
| 5 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:32-6686:class:StreamDiffusionExt` | class | 0.8156 |
| 6 | `StreamDiffusion/StreamDiffusionTD/td_manager.py:1-43:module_preamble` | module_preamble | 0.7 |
| 7 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1-46:module_preamble` | module_preamble | 0.7 |

## C4 — preprocessing pipeline orchestration across ControlNet, IPAdapter, FaceID processors

Known candidates: `preprocessing_orchestrator.py`, `pipeline_preprocessing_orchestrator.py`

**Note**: full miss on the core subject — a clean illustration of the Arm B raw-score-scale
issue. Rank 1 is a single BM25-keyword-heavy `FaceIDEmbeddingPreprocessor._process_core` chunk
that score-spikes to blended_score 16.39 (far above the rest of the pool), ranks 2-7 are
unrelated noise (`DotLOPUtils._setup_logger`, `Installer._report_progress`,
`SyphonUtils.stop` — all ~3.0-3.8), and the actual `PreprocessingOrchestrator` methods
(`_group_preprocessors`, `_process_single_controlnet`, `_process_single_ipadapter`, etc.) start
at rank 8 (blended_score ≤1.08), entirely outside top 7. Arm A resolved this correctly.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/faceid_embedding.py:59-93:method:FaceIDEmbeddingPreprocessor._process_core` | method | 16.392 |
| 2 | `Scripts/shmem_in_cn_processed__Text__dot_lop_utils__td.py:14-16:method:DotLOPUtils._setup_logger` | method | 3.792 |
| 3 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/installer.py:146-150:method:Installer._report_progress` | method | 3.744 |
| 4 | `Scripts/shmem_out_out_ip__Text__dot_lop_utils__td.py:14-16:method:DotLOPUtils._setup_logger` | method | 3.18 |
| 5 | `StreamDiffusion/StreamDiffusionTD/syphon_utils.py:416-433:method:SyphonUtils.stop` | method | 3.012 |
| 6 | `Scripts/streamdiffusionTD__Text__syphon_utils__td.py:416-433:method:SyphonUtils.stop` | method | 3.0 |
| 7 | `Scripts/tox_updater__Text__dot_lop_utils__td.py:14-16:method:DotLOPUtils._setup_logger` | method | 2.796 |

## C5 — shared-memory protocol layout (header, slot size, magic number, version)

Known candidate: `Scripts/td_exporter/SHMProtocol.py`

**Note**: partial — the known candidate's own `SHMLayout`/`Metadata` classes and module
preamble are present (ranks 5-7), but ranks 1-4 are `CUDAIPCExtension` (a different, adjacent
file that consumes the protocol rather than defining it) — the direct protocol-definition
answer is pushed below the extension's own methods.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:73-396:class:CUDAIPCExtension` | class | 1.1462 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:306-308:method:CUDAIPCExtension.initialize_receiver` | method | 1.044 |
| 3 | `Scripts/td_exporter/CUDAIPCExtension.py:261-264:method:CUDAIPCExtension.export_frame` | method | 1.032 |
| 4 | `Scripts/td_exporter/CUDAIPCExtension.py:266-270:method:CUDAIPCExtension.import_frame` | method | 1.008 |
| 5 | `Scripts/td_exporter/SHMProtocol.py:130-183:decorated_definition:SHMLayout` | decorated_definition | 0.756 |
| 6 | `Scripts/td_exporter/SHMProtocol.py:191-242:decorated_definition:Metadata` | decorated_definition | 0.56 |
| 7 | `Scripts/td_exporter/SHMProtocol.py:74-117:module_preamble` | module_preamble | 0.55 |

## C6 — sd_installer CLI subsystem end to end (install, verify, report)

Known candidate: `StreamDiffusion/StreamDiffusion-installer/sd_installer/*`

**Note**: strong coverage — install (`Installer.install` rank 6), report (`cmd_report` rank 1,
`build_report_text` rank 3), the CLI entry point (rank 2), and a phase method (rank 4) are all
present. The "verify" leg specifically (`Installer.phase8_verify`) ranks 9th, just outside
top 7; rank 7 (`utils/diagnostics.py` preamble) is a different, unrelated module — mild noise.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/cli.py:206-247:function:cmd_report` | function | 24.696 |
| 2 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/__main__.py:1-6:module_preamble` | module_preamble | 16.16 |
| 3 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/report.py:64-158:function:build_report_text` | function | 1.0164 |
| 4 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/installer.py:274-280:method:Installer.phase4_streamdiffusion` | method | 0.984 |
| 5 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/installer.py:169-175:method:Installer._run_python` | method | 0.948 |
| 6 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/installer.py:477-533:method:Installer.install` | method | 0.8424 |
| 7 | `StreamDiffusion/src/streamdiffusion/utils/diagnostics.py:1-65:module_preamble` | module_preamble | 0.82 |

## E1 — frame from TouchDesigner TOP through CUDA IPC shared memory to receiver-side texture

Known chain: `TDHost.py` → `CUDAIPCExtension.py` → `TDSender.py`/`TDReceiver.py` → `SHMProtocol.py`

**Note**: partial — middle-of-chain strong (`CUDAIPCExtension` export/import/has_new_frame,
`TDReceiverEngine`), but the chain endpoints (`TDHost.py` capture side, `SHMProtocol.py`
wire-format side) are absent from top 7 — same partial pattern as Arm A's E1.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:261-264:method:CUDAIPCExtension.export_frame` | method | 1.0368 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:316-317:method:CUDAIPCExtension.is_ready` | method | 1.032 |
| 3 | `Scripts/td_exporter/CUDAIPCExtension.py:266-270:method:CUDAIPCExtension.import_frame` | method | 1.0224 |
| 4 | `Scripts/td_exporter/TDReceiver.py:100-181:decorated_definition:ReceiverConnection` | decorated_definition | 0.96 |
| 5 | `Scripts/td_exporter/CUDAIPCExtension.py:296-304:method:CUDAIPCExtension.has_new_frame` | method | 0.8712 |
| 6 | `Scripts/td_exporter/TDReceiver.py:227-271:method:TDReceiverEngine.__init__` | method | 0.8568 |
| 7 | `Scripts/td_exporter/CUDAIPCExtension.py:73-396:class:CUDAIPCExtension` | class | 0.85 |

## E2 — FP8 quantization pipeline: calibration loading, ONNX Q/DQ injection, TensorRT build

Known chain: `fp8_quantize.py` → `acceleration/tensorrt/engine_manager.py`/`builder.py`

**Note**: strong/full coverage — both ends of the named chain are present: `builder.py`
(`EngineBuilder.build` rank 2) and `fp8_quantize.py` (`quantize_onnx_fp8` rank 7), connected by
generic TensorRT-engine-build machinery (`Engine.build`/`build_engine`, ranks 3-6). Rank 1's
`Engine._build_fp8` score-spikes to blended_score 41.37 (Arm B's unbounded raw-fusion-score
artifact) but is itself topically correct.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:1030-1056:split_block:Engine._build_fp8` | split_block | 41.3699 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:539-555:split_block:EngineBuilder.build` | split_block | 1.3871 |
| 3 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/trt_base.py:452-468:split_block:SelfBuildingTRTPreprocessor._build_tensorrt_engine` | split_block | 1.2936 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:870-900:split_block:Engine.build` | split_block | 1.2298 |
| 5 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/trt_base.py:431-449:method:SelfBuildingTRTPreprocessor._ensure_engine` | method | 1.1952 |
| 6 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:1669-1688:split_block:build_engine` | split_block | 1.1583 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:2075-2106:split_block:quantize_onnx_fp8` | split_block | 0.9768 |

## E3 — ControlNet config uploaded via FastAPI route reaching pipeline runtime state

Known chain: `routes/controlnet.py` → `demo/realtime-img2img/config.py`/`connection_manager.py`
(breadcrumb possibly stale — see Arm A's E3 note)

**Note**: partial — the core answer is present and directly on-topic at ranks 1-3
(`upload_controlnet_config` → `AppState.populate_from_config` → `add_controlnet`, tracing
route-to-runtime-state), but ranks 4-7 are unrelated noise (a resizable-stream test fixture,
two unrelated `shmem_*` script copies' `DotChatUtil.__init__`, `TDReceiver`'s
`ReceiverConnection`) — heavier dilution than Arm A's version of this query.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:39-167:split_block:upload_controlnet_config` | split_block | 22.5544 |
| 2 | `StreamDiffusion/demo/realtime-img2img/main.py:121-208:method:AppState.populate_from_config` | method | 21.5952 |
| 3 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:308-384:decorated_definition:add_controlnet` | decorated_definition | 16.98 |
| 4 | `StreamDiffusion/tests/unit/test_live_t_index_resize_buffers.py:42-61:function:_make_resizable_stream` | function | 4.4778 |
| 5 | `Scripts/shmem_out_out_ip__Text__dot_chat_util__td.py:10-33:method:DotChatUtil.__init__` | method | 3.6924 |
| 6 | `Scripts/shmem_in_cn_processed__Text__dot_chat_util__td.py:10-33:method:DotChatUtil.__init__` | method | 3.5802 |
| 7 | `Scripts/td_exporter/TDReceiver.py:100-181:decorated_definition:ReceiverConnection` | decorated_definition | 3.55 |

## E4 — StreamDiffusionTD extension coordinating with model_utils to resolve compatible ControlNet model

Known chain: `StreamDiffusionExt__td.py` → `StreamDiffusionTD__Text__model_utils__td.py`

**Note**: strong/full coverage — both sides of the coordination are present: the resolution
logic (`resolve_controlnet_model_id` rank 1, `find_equivalent_cn_model` rank 2, both in
`model_utils__td.py`) and the extension-side consumers (`StreamDiffusionExt.update_cn_dynamic_parameters`
rank 4, `update_cn_id_menus` ranks 5-6). Rank 3 is a separate `StreamDiffusionTD-fork/` copy of
`model_utils.py` (duplicate-tree noise, same topic); rank 7 is unrelated.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/StreamDiffusionTD__Text__model_utils__td.py:376-402:function:resolve_controlnet_model_id` | function | 31.32 |
| 2 | `Scripts/StreamDiffusionTD__Text__model_utils__td.py:312-347:function:find_equivalent_cn_model` | function | 22.02 |
| 3 | `StreamDiffusionTD-fork/operator/model_utils.py:0-0:module:model_utils` | module | 13.3322 |
| 4 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:5711-5743:method:StreamDiffusionExt.update_cn_dynamic_parameters` | method | 12.288 |
| 5 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:166-188:method:StreamDiffusionExt.update_cn_id_menus` | method | 12.072 |
| 6 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:169-190:method:StreamDiffusionExt.update_cn_id_menus` | method | 11.952 |
| 7 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/base.py:26-40:method:BasePreprocessor.__init__` | method | 9.5814 |

## E5 — token stored by secure_storage used by tox_updater to authorize a TOX update download

Known chain: `secure_storage__td.py` → `tox_updater__Text__auth_manager__td.py`/`ToxUpdaterEXT__td.py`

**Note**: full coverage — top 3 cover the storage side (`store_token`/`delete_token`/`load_token`
across the cross-platform `secure_storage*` modules) and rank 4
(`ToxUpdaterEXT._async_download_tox`) is the actual download-authorization consumer, directly
connecting storage to the download action within top 5.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage__td.py:33-53:function:store_token` | function | 28.8576 |
| 2 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:189-193:function:delete_token` | function | 28.6992 |
| 3 | `Scripts/tox_updater__Text__secure_storage__td.py:56-72:function:load_token` | function | 27.648 |
| 4 | `Scripts/tox_updater__Text__ToxUpdaterEXT__td.py:700-723:method:ToxUpdaterEXT._async_download_tox` | method | 27.0144 |
| 5 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:25-28:function:get_storage_dir` | function | 26.8992 |
| 6 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:168-186:function:load_token` | function | 17.9712 |
| 7 | `Scripts/tox_updater__Text__secure_storage__td.py:75-86:function:delete_token` | function | 16.9488 |

## E6 — GPU profiling threaded through wrapper FP8 calibration path and pipeline per-step timing

Known chain: `tools/gpu_profiler.py` used from `wrapper.py` and `pipeline.py`

**Note**: full miss on the actual connection — all 7 rows are `gpu_profiler.py`/TensorRT-profiler
class-internal methods (`GPUProfiler.step/flush/reset`, `_NullProfiler.begin/nsys_start`,
`TRTProfiler.report_layer_time`, `Engine.dump_profile`). None of the top 7 shows the call sites
in `wrapper.py` (FP8 calibration path) or `pipeline.py` (per-step timing) that would demonstrate
how profiling actually threads through both — the query's connecting claim is unanswered within
the cut. Also notably low absolute blended_scores throughout (max 1.02), signaling weak match
overall.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:487-488:method:_NullProfiler.begin` | method | 1.02 |
| 2 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:329-335:method:GPUProfiler.step` | method | 0.9984 |
| 3 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:591-592:method:TRTProfiler.report_layer_time` | method | 0.996 |
| 4 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:493-494:method:_NullProfiler.nsys_start` | method | 0.996 |
| 5 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:379-396:method:GPUProfiler.flush` | method | 0.72 |
| 6 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:450-453:method:GPUProfiler.reset` | method | 0.708 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:1480-1486:method:Engine.dump_profile` | method | 0.684 |

## E7 — param_schema timestep-grid connecting wrapper calibration index building to pipeline sub-timestep scheduling

Known chain: `param_schema.py` used from `wrapper.py` and `pipeline.py`

**Note**: mostly miss — only rank 2 (`materialise_timestep_grid`) is the actual on-topic
`param_schema.py` function; the rest of top 7 is unit-test noise, largely generic `.to()` method
matches from unrelated fake-object test classes (`_FakeGrid.to`, `_FakeWrongTypePipe.to` x2,
`UNet2DConditionModelEngine.to`). The two functions that would actually demonstrate the
wrapper↔pipeline connection (`build_calibration_t_indices`, `compute_sub_timesteps`) rank well
outside top 7 (raw ranks ~20+, blended_score ≤0.57).

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/tests/unit/test_param_schema.py:286-299:method:TestMaterialiseTimestepGrid.test_unrecognised_spacing_falls_back_to_native_grid` | method | 17.7123 |
| 2 | `StreamDiffusion/src/streamdiffusion/param_schema.py:215-253:function:materialise_timestep_grid` | function | 15.7182 |
| 3 | `StreamDiffusion/tests/unit/test_param_schema.py:199-200:method:_FakeGrid.to` | method | 9.3781 |
| 4 | `StreamDiffusion/tests/unit/test_live_t_index_resize_buffers.py:42-61:function:_make_resizable_stream` | function | 6.8425 |
| 5 | `StreamDiffusion/tests/unit/test_load_model_network_error_reporting.py:50-51:method:_FakeWrongTypePipe.to` | method | 5.4516 |
| 6 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:72-73:method:_FakeWrongTypePipe.to` | method | 5.083 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/runtime_engines/unet_engine.py:428-429:method:UNet2DConditionModelEngine.to` | method | 4.6196 |

## E8 — OSC message handler in Scripts routing incoming control messages to StreamDiffusionTD extension's parameter updates

Known chain: `streamdiffusionTD__Text__td_osc_handler__td.py` → `StreamDiffusionExt__td.py`

**Note**: partial — strong coverage of the OSC-handler side itself (`_queue_parameter_update`,
`send_message` x3 duplicate-tree copies, `OSCParameterHandler` class x2, `start`), but no chunk
from `StreamDiffusionExt__td.py` (the routing target) appears in top 7 — the "routes to the
extension's parameter updates" half of the query is unanswered within the cut. Heavy duplicate-copy
noise: the same `OSCParameterHandler` methods appear near-identically across three parallel source
trees (`Scripts/`, `StreamDiffusion/StreamDiffusionTD/`, `StreamDiffusionTD-fork/`), consuming 6 of
7 slots on redundant copies of the same few methods.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/StreamDiffusionTD/td_osc_handler.py:168-171:method:OSCParameterHandler._queue_parameter_update` | method | 1.3068 |
| 2 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:130-135:method:OSCParameterHandler.send_message` | method | 1.224 |
| 3 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_osc_handler.py:103-108:method:OSCParameterHandler.send_message` | method | 1.2096 |
| 4 | `StreamDiffusion/StreamDiffusionTD/td_osc_handler.py:130-135:method:OSCParameterHandler.send_message` | method | 1.1952 |
| 5 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:56-599:class:OSCParameterHandler` | class | 1.1647 |
| 6 | `StreamDiffusion/StreamDiffusionTD/td_osc_handler.py:56-599:class:OSCParameterHandler` | class | 1.1167 |
| 7 | `StreamDiffusion/StreamDiffusionTD/td_osc_handler.py:88-109:method:OSCParameterHandler.start` | method | 1.092 |
