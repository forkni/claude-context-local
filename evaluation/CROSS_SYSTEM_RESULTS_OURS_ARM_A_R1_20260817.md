# Our system, Arm A (full pipeline), Round 1 — raw results

Config: deployed defaults, `search_config.json` with `intent.enabled=false` pinned
(otherwise `search_code` was observed to silently redirect to a `find_similar_code`-shaped
response on query A1 — see note below). `search_mode="hybrid"` passed explicitly, `k=10`.
Index: `F2LLM-v2-0.6B`, 1024d, 6253 chunks / 422 files (`SDTD_040_Beta_8f1a0037`).

**Note — A1 re-run required**: the first attempt at A1 (before `intent.enabled=false` was
pinned) was redirected to an unrelated reference chunk (`TensorRTEngine` in
`temporal_net_tensorrt.py`) via the intent classifier's `find_similar_code` redirect
(`mcp_server/tools/search_orchestrator.py:144-210`). That result is discarded. The row
below is the corrected re-run with intent disabled.

Rows = top-10 requested, non-`.py` dropped (none this batch), first 7 kept per harness
parity rules.

## A1 — CUDA OOM detection/classification, incl. RuntimeErrors from TensorRT

Known candidate: `wrapper.py` `_is_oom_error`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:29-38:function:_is_oom_error` | function | 0.8521 |
| 2 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:42-61:class:TestIsOomError` | class | 0.2892 |
| 3 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:47-57:decorated_definition:test_string_heuristic_matches_known_oom_substrings` | decorated_definition | 0.0654 |
| 4 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:43-45:method:test_typed_cuda_oom_is_detected` | method | 0.0587 |
| 5 | `StreamDiffusion/src/streamdiffusion/wrapper.py:0-0:module:wrapper` | module | 0.017 |
| 6 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:0-0:module:test_wrapper_exception_hygiene` | module | 0.0 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:316-345:split_block:_apply_gpu_profile_to_config` | split_block | 0.0 |

## A2 — FP8 calibration per-image retry after batch encode failure

Known candidate: `wrapper.py` `_encode_fp8_calibration_images`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:41-95:function:_encode_fp8_calibration_images` | function | 0.9072 |
| 2 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:280-303:method:test_style_images_partial_encode_failure_keeps_survivors` | method | 0.2142 |
| 3 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:305-324:method:test_style_images_all_encode_failures_fall_through_to_surrogate` | method | 0.1224 |
| 4 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:116-129:method:_FakeIPA.get_image_embeds` | method | 0.1122 |
| 5 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:259-278:method:test_style_images_single_image_failure_falls_through_without_retry` | method | 0.0918 |
| 6 | `StreamDiffusion/examples/benchmark/single.py:39-105:split_block:run` | split_block | 0.0286 |
| 7 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:85-132:class:_FakeIPA` | class | 0.0 |

## A3 — feedback-loop blend formula (current input vs. previous frame's diffusion output)

Known candidate: `preprocessing/processors/feedback.py` `FeedbackPreprocessor`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:9-217:class:FeedbackPreprocessor` | class | 0.9678 |
| 2 | `StreamDiffusionTD-fork/operator/custom_processors/sdtd_fx/feedback_loop.py:8-224:class:FeedbackLoopPreprocessor` | class | 0.3857 |
| 3 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:85-134:method:FeedbackPreprocessor._process_core` | method | 0.372 |
| 4 | `StreamDiffusionTD-fork/operator/custom_processors/sdtd_fx/feedback_loop.py:169-189:method:FeedbackLoopPreprocessor._process_core` | method | 0.312 |
| 5 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:136-217:method:FeedbackPreprocessor._process_tensor_core` | method | 0.3 |
| 6 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:30-51:decorated_definition:FeedbackPreprocessor.get_preprocessor_metadata` | decorated_definition | 0.28 |
| 7 | `StreamDiffusion/custom_processors/sdtd_fx/feedback_loop.py:10-438:class:FeedbackLoopPreprocessor` | class | 0.2408 |

## A4 — IPAdapter embedding preprocessor avoids re-encoding unchanged style image

Known candidate: `preprocessing/processors/ipadapter_embedding.py` `_last_input_ptr`/`_cached_embeds`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:77-97:method:IPAdapterEmbeddingPreprocessor._process_tensor_core` | method | 0.684 |
| 2 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:26-43:method:IPAdapterEmbeddingPreprocessor.__init__` | method | 0.576 |
| 3 | `StreamDiffusion/demo/realtime-img2img/img2img.py:246-313:method:Pipeline._update_ipadapter_style_image` | method | 0.1872 |
| 4 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:45-75:method:IPAdapterEmbeddingPreprocessor._process_core` | method | 0.108 |
| 5 | `StreamDiffusion/src/streamdiffusion/modules/ipadapter_module.py:235-649:class:IPAdapterModule` | class | 0.0755 |
| 6 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:99-107:method:IPAdapterEmbeddingPreprocessor.process` | method | 0.072 |
| 7 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:38-86:method:StreamDiffusionExt.__init__` | method | 0.072 |

## A5 — calibration image set signature hashed for TensorRT engine cache-key suffix

Known candidate: `acceleration/tensorrt/engine_manager.py` `_calibration_image_signature`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py:109-135:method:EngineManager._calibration_image_signature` | method | 0.8268 |
| 2 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:37-44:function:_make_engine_manager` | function | 0.0898 |
| 3 | `StreamDiffusion/src/streamdiffusion/wrapper.py:195-221:function:_load_fp8_calibration_style_images` | function | 0.084 |
| 4 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:112-165:class:TestListLoadHashAgreement` | class | 0.0688 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:48-76:function:_list_calibration_images` | function | 0.0264 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:235-272:function:_resolve_fp8_calibration_dir` | function | -0.012 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py:166-183:method:EngineManager._trt_cc_tag` | method | -0.012 |

## A6 — auth token stored via OS-native secure storage (DPAPI/Keychain)

Known candidate: `Scripts/tox_updater__Text__secure_storage__td.py` `store_token`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage__td.py:33-53:function:store_token` | function | 0.504 |
| 2 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:152-165:function:store_token` | function | 0.4032 |
| 3 | `Scripts/tox_updater__Text__secure_storage__td.py:120-153:function:get_platform_info` | function | 0.336 |
| 4 | `Scripts/tox_updater__Text__secure_storage__td.py:1-18:module_preamble` | module_preamble | 0.29 |
| 5 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:147-149:function:get_storage_path` | function | 0.198 |
| 6 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:51-84:function:store_token` | function | 0.1728 |
| 7 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:1-22:module_preamble` | module_preamble | 0.08 |

## A7 — TD Script TOP pixel-format string from tensor dtype/channel count for CUDA memcpy

Known candidate: `Scripts/td_exporter/TDReceiver.py` `td_format_string`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/TDReceiver.py:63-87:function:td_format_string` | function | 0.7344 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:281-290:method:CUDAIPCExtension.update_receiver_format` | method | 0.2112 |
| 3 | `Scripts/td_exporter/TDHost.py:191-206:method:RealTOPHandle.cuda_memory` | method | 0.2028 |
| 4 | `Scripts/td_exporter/_td_fakes.py:94-106:method:FakeTOPHandle.cuda_memory` | method | 0.1248 |
| 5 | `Scripts/td_exporter/TDHost.py:46-102:decorated_definition:TOPHandle` | decorated_definition | 0.12 |
| 6 | `Scripts/td_exporter/SHMProtocol.py:261-269:decorated_definition:DtypeCodec.encode` | decorated_definition | 0.1 |
| 7 | `Scripts/td_exporter/TDHost.py:26-38:decorated_definition:CUDAMemoryRef` | decorated_definition | 0.084 |

## A8 — REST endpoint accepting uploaded ControlNet YAML config

Known candidate: `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py` `upload_controlnet_config`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:39-167:split_block:upload_controlnet_config` | split_block | 0.583 |
| 2 | `StreamDiffusion/demo/realtime-img2img/main.py:56-593:class:AppState` | class | 0.0614 |
| 3 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:0-0:module:controlnet` | module | 0.009 |
| 4 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/base.py:26-40:method:BasePreprocessor.__init__` | method | 0.0046 |
| 5 | `StreamDiffusion/demo/realtime-img2img/main.py:916-932:method:App._load_config_style_images` | method | 0.0 |
| 6 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:3512-3561:split_block:StreamDiffusionExt.generate_td_config_yaml` | split_block | 0.0 |
| 7 | `StreamDiffusion/src/streamdiffusion/modules/controlnet_module.py:21-29:decorated_definition:ControlNetConfig` | decorated_definition | -0.012 |

## A9 — FP8 calibration prompts loaded from bundled text file

Known candidate: `acceleration/tensorrt/fp8_quantize.py` (near `_BUNDLED_PROMPTS_PATH`)

**Note**: top hit is image-calibration loading (`_load_fp8_calibration_style_images`), not
prompt loading. The actual `_load_calibration_prompts` function only surfaces indirectly via
the `fp8_quantize` module docstring summary at rank 4 — partial miss, query is ambiguous
between "calibration images" and "calibration prompts" and the system favored the former.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:195-221:function:_load_fp8_calibration_style_images` | function | 0.5016 |
| 2 | `StreamDiffusion/src/streamdiffusion/wrapper.py:235-272:function:_resolve_fp8_calibration_dir` | function | 0.144 |
| 3 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:119-144:method:TestListLoadHashAgreement.test_loader_lister_and_hasher_agree_on_which_files_count` | method | 0.1428 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:0-0:module:fp8_quantize` | module | 0.0864 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:48-76:function:_list_calibration_images` | function | 0.0396 |
| 6 | `StreamDiffusion/tests/unit/test_fp8_calib_provenance.py:159-227:class:TestWriteCalibProvenanceSidecar` | class | 0.0229 |
| 7 | `STREAMDIFFUSION_COURSE/course_v3/appendices/assets/test_lora_gating_measure.py:90-106:function:load_prompts` | function | 0.0122 |

## A10 — TF32 matmul / cuDNN benchmark mode enabled once per CUDA device at pipeline construction

Known candidate: `pipeline.py` `StreamDiffusion.__init__`

**Note**: known candidate does NOT appear in top 7 — full miss. Top hits are TensorRT
model/engine-build GPU-profile code, adjacent but not the pipeline constructor itself.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/models/models.py:165-301:class:BaseModel` | class | 0.0898 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:430-458:split_block:_apply_gpu_profile_to_config` | split_block | 0.088 |
| 3 | `StreamDiffusion/demo/realtime-img2img/img2img.py:88-130:method:Pipeline.__init__` | method | 0.0782 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:140-165:decorated_definition:GPUBuildProfile` | decorated_definition | 0.055 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:1136-1148:method:Engine.activate` | method | 0.0 |
| 6 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:465-487:split_block:EngineBuilder.build` | split_block | 0.0 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:168-262:function:detect_gpu_profile` | function | -0.0115 |

## B1 — Sender/Receiver CUDA IPC engines as a matched pair

Known candidates: `Scripts/td_exporter/TDSender.py`, `TDReceiver.py`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:1-70:module_preamble` | module_preamble | 0.47 |
| 2 | `Scripts/td_exporter/TDSender.py:171-851:class:TDSenderEngine` | class | 0.2116 |
| 3 | `Scripts/td_exporter/CUDAIPCExtension.py:266-270:method:CUDAIPCExtension.import_frame` | method | 0.2028 |
| 4 | `Scripts/td_exporter/CUDAIPCExtension.py:73-396:class:CUDAIPCExtension` | class | 0.1932 |
| 5 | `Scripts/td_exporter/CUDAIPCExtension.py:216-238:method:CUDAIPCExtension._make_engine` | method | 0.192 |
| 6 | `Scripts/td_exporter/CUDAIPCExtension.py:261-264:method:CUDAIPCExtension.export_frame` | method | 0.1716 |
| 7 | `Scripts/td_exporter/TDReceiver.py:220-1220:class:TDReceiverEngine` | class | 0.1663 |

## B2 — Windows/macOS secure-storage backends as parallel platform-specific modules

Known candidates: `secure_storage_windows__td.py`, `secure_storage_macos__td.py`

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage__td.py:21-30:function:_get_backend` | function | 0.4255 |
| 2 | `Scripts/tox_updater__Text__secure_storage__td.py:1-18:module_preamble` | module_preamble | 0.15 |
| 3 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:25-40:module_preamble` | module_preamble | 0.11 |
| 4 | `Scripts/tox_updater__Text__secure_storage__td.py:120-153:function:get_platform_info` | function | 0.0633 |
| 5 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:38-86:method:StreamDiffusionExt.__init__` | method | 0.0293 |
| 6 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:0-0:module:tox_updater__Text__secure_storage_macos__td` | module | 0.0255 |
| 7 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:0-0:module:tox_updater__Text__secure_storage_windows__td` | module | 0.0 |

## B3 — test exercising multi-ControlNet residual-merge, and the module it tests

Known candidates: `tests/unit/test_controlnet_residual_merge.py` vs `modules/controlnet_module.py`

Good coverage — test file dominates top 7 (class + 5 of its test methods), and
`controlnet_module.py`'s `ControlNetModule` class/`build_unet_hook` appear via ego_graph
at rank 12-13 (outside top-7 window but present in the raw 30).

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:69-186:class:TestControlNetResidualMerge` | class | 0.5045 |
| 2 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:44-56:function:_make_module_with_two_controlnets` | function | 0.2645 |
| 3 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:0-0:module:test_controlnet_residual_merge` | module | 0.2346 |
| 4 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:127-145:method:TestControlNetResidualMerge.test_merge_does_not_alias_engine_output_buffer` | method | 0.1455 |
| 5 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:147-164:method:TestControlNetResidualMerge.test_single_controlnet_bypasses_merge_buffers` | method | 0.1455 |
| 6 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:70-81:method:TestControlNetResidualMerge.test_merge_is_numerically_correct` | method | 0.1309 |
| 7 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:20-36:class:_FakeCN` | class | 0.1087 |

## B4 — single-frame/multi-frame variants of img2img and txt2img examples

Known candidates: `StreamDiffusion/examples/{img2img,txt2img}/{single,multi}.py`

All four target files present in top 7 (txt2img/multi ×2 rows, img2img/single, txt2img/single,
img2img/multi ×2 rows) — full coverage of the sibling set.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/examples/txt2img/multi.py:0-0:module:multi` | module | 0.1989 |
| 2 | `StreamDiffusion/examples/txt2img/multi.py:14-82:function:main` | function | 0.192 |
| 3 | `StreamDiffusion/examples/img2img/single.py:14-102:function:main` | function | 0.144 |
| 4 | `StreamDiffusion/examples/txt2img/single.py:0-0:module:single` | module | 0.1287 |
| 5 | `StreamDiffusion/examples/img2img/multi.py:0-0:module:multi` | module | 0.0936 |
| 6 | `StreamDiffusion/examples/txt2img/multi.py:1-11:module_preamble` | module_preamble | 0.07 |
| 7 | `StreamDiffusion/examples/img2img/single.py:0-0:module:single` | module | 0.0644 |

## B5 — shmem_in_cn_processed / shmem_out_out_ip TouchDesigner script sets mirroring

Known candidates: `Scripts/shmem_in_cn_processed__*` vs `Scripts/shmem_out_out_ip__*`

Good coverage of the pairing intent — both `shmem_out_out_ip` and `shmem_in_cn_processed`
`output_callbacks` modules present (ranks 1, 3-5), plus `CUDAIPCExtension._sibling_mirrors_available`
(rank 9) which names the mirroring relationship directly. `SharedMemEXT` class internals for
one side only otherwise crowd the tail.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/shmem_out_out_ip__Text__output_callbacks__td.py:0-0:module:shmem_out_out_ip__Text__output_callbacks__td` | module | 0.2244 |
| 2 | `Scripts/shmem_out_out_ip__ParExecute__extensionParExec__td.py:1-4:module_preamble` | module_preamble | 0.15 |
| 3 | `Scripts/shmem_out_out_ip__Text__output_callbacks__td.py:9-10:function:onPulse` | function | 0.138 |
| 4 | `Scripts/shmem_in_cn_processed__ParExecute__extensionParExec__td.py:1-4:module_preamble` | module_preamble | 0.12 |
| 5 | `Scripts/shmem_in_cn_processed__Text__output_callbacks__td.py:0-0:module:shmem_in_cn_processed__Text__output_callbacks__td` | module | 0.1174 |
| 6 | `Scripts/shmem_in_cn_processed__Text__output_callbacks__td.py:9-10:function:onPulse` | function | 0.092 |
| 7 | `Scripts/shmem_out_out_ip__Text__SharedMemEXT__td.py:412-420:method:SharedMemEXT._trigger_change_callback` | method | 0.0886 |

## B6 — test exercising FaceID LoRA fusion, and the module implementing FaceID compat

Known candidates: `tests/unit/test_faceid_lora_fusion.py` vs `modules/faceid_compat.py`

Full coverage — both known-candidate files present at ranks 1-2, with test class and
module docstring for `faceid_compat` also in top 7.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:1-28:module_preamble` | module_preamble | 0.437 |
| 2 | `StreamDiffusion/src/streamdiffusion/modules/faceid_compat.py:363-443:function:fuse_faceid_lora` | function | 0.2415 |
| 3 | `StreamDiffusion/src/streamdiffusion/modules/faceid_compat.py:339-352:module_preamble` | module_preamble | 0.16 |
| 4 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:0-0:module:test_faceid_lora_fusion` | module | 0.1584 |
| 5 | `StreamDiffusion/src/streamdiffusion/modules/faceid_compat.py:0-0:module:faceid_compat` | module | 0.1487 |
| 6 | `StreamDiffusion/tests/unit/test_faceid_bgr_patch.py:75-157:function:_install_fake_diffusers_ipadapter` | function | 0.1455 |
| 7 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:46-59:class:_FakeUNet` | class | 0.0776 |

## C1 — StreamDiffusion pipeline class constructor: CFG type, LoRA dict, KV-cache, feature injection

Known candidate: `pipeline.py` `class StreamDiffusion.__init__`

Top-1/2 clean hit — `class:StreamDiffusion` then `StreamDiffusion.__init__` split_block.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/pipeline.py:42-1754:class:StreamDiffusion` | class | 0.838 |
| 2 | `StreamDiffusion/src/streamdiffusion/pipeline.py:111-172:split_block:StreamDiffusion.__init__` | split_block | 0.3272 |
| 3 | `StreamDiffusion/tests/unit/test_unet_call_backend_gate.py:104-139:function:_make_pipeline` | function | 0.0938 |
| 4 | `StreamDiffusion/src/streamdiffusion/wrapper.py:2371-3334:split_block:StreamDiffusionWrapper._load_model` | split_block | 0.0475 |
| 5 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:5302-5311:method:StreamDiffusionExt.Fienable` | method | 0.046 |
| 6 | `StreamDiffusion/demo/realtime-img2img/img2img.py:88-130:method:Pipeline.__init__` | method | 0.0293 |
| 7 | `StreamDiffusion/demo/realtime-txt2img/config.py:10-49:decorated_definition:Config` | decorated_definition | 0.022 |

## C2 — CUDA IPC extension architecture: Sender/Receiver engine delegation

Known candidate: `Scripts/td_exporter/CUDAIPCExtension.py` module docstring

Full coverage — module preamble at rank 1, `CUDAIPCExtension` class at rank 2, plus
`_make_engine` (the actual delegation point) at rank 3 and both sibling engine classes
(`TDSenderEngine`, `TDReceiverEngine`) at ranks 4 and 7.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:1-70:module_preamble` | module_preamble | 0.5 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:73-396:class:CUDAIPCExtension` | class | 0.4946 |
| 3 | `Scripts/td_exporter/CUDAIPCExtension.py:216-238:method:CUDAIPCExtension._make_engine` | method | 0.192 |
| 4 | `Scripts/td_exporter/TDSender.py:171-851:class:TDSenderEngine` | class | 0.1059 |
| 5 | `Scripts/td_exporter/CUDAIPCExtension.py:257-259:method:CUDAIPCExtension.initialize` | method | 0.084 |
| 6 | `Scripts/td_exporter/CUDAIPCWrapper.py:169-257:method:CUDARuntimeAPI._load_cuda_runtime` | method | 0.066 |
| 7 | `Scripts/td_exporter/TDReceiver.py:220-1220:class:TDReceiverEngine` | class | 0.0383 |

## C3 — StreamDiffusionTD extension class responsibilities: model mgmt, TensorRT build, version tracking

Known candidate: `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py` `class StreamDiffusionExt`

Good coverage — both the `Scripts/` deployed copy and the `StreamDiffusionTD-fork/`
source copy of `StreamDiffusionExt` surface (constructor, class body, `Installtensorrt`,
compatibility check), reflecting the dual-copy repo layout rather than a retrieval gap.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:38-86:method:StreamDiffusionExt.__init__` | method | 0.414 |
| 2 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:39-89:method:StreamDiffusionExt.__init__` | method | 0.414 |
| 3 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:2605-2634:method:StreamDiffusionExt.Installtensorrt` | method | 0.345 |
| 4 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:32-6686:class:StreamDiffusionExt` | class | 0.3359 |
| 5 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:31-6252:class:StreamDiffusionExt` | class | 0.2893 |
| 6 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:2434-2460:method:StreamDiffusionExt.Installtensorrt` | method | 0.2645 |
| 7 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:1412-1444:method:StreamDiffusionExt.check_tensorrt_engine_compatibility` | method | 0.2415 |

## C4 — preprocessing pipeline orchestration across ControlNet/IPAdapter/FaceID

Known candidates: `preprocessing_orchestrator.py`, `pipeline_preprocessing_orchestrator.py`

Full coverage — both known-candidate orchestrator classes present (ranks 1, 3), plus
their per-modality dispatch methods (`_process_multiple_ipadapters_sync`,
`_process_ipadapter_preprocessors_parallel`).

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/preprocessing/preprocessing_orchestrator.py:18-814:class:PreprocessingOrchestrator` | class | 0.74 |
| 2 | `StreamDiffusion/src/streamdiffusion/preprocessing/preprocessing_orchestrator.py:47-88:method:PreprocessingOrchestrator.process_sync` | method | 0.348 |
| 3 | `StreamDiffusion/src/streamdiffusion/preprocessing/pipeline_preprocessing_orchestrator.py:11-177:class:PipelinePreprocessingOrchestrator` | class | 0.3078 |
| 4 | `StreamDiffusion/src/streamdiffusion/preprocessing/preprocessing_orchestrator.py:381-403:method:PreprocessingOrchestrator._process_multiple_ipadapters_sync` | method | 0.264 |
| 5 | `StreamDiffusion/src/streamdiffusion/preprocessing/preprocessing_orchestrator.py:405-429:method:PreprocessingOrchestrator._process_ipadapter_preprocessors_parallel` | method | 0.216 |
| 6 | `StreamDiffusion/src/streamdiffusion/preprocessing/preprocessing_orchestrator.py:0-0:module:preprocessing_orchestrator` | module | 0.1566 |
| 7 | `StreamDiffusion/src/streamdiffusion/modules/controlnet_module.py:760-770:method:ControlNetModule._prepare_control_image` | method | 0.132 |

## C5 — shared-memory protocol layout: header, slot size, magic number, version

Known candidate: `Scripts/td_exporter/SHMProtocol.py`

**Note**: `SHMProtocol` module surfaces at rank 6, not top-3 — `Importer.py`'s
`IPCConnection`/`_open_and_validate_shm` and module preambles of the SharedMemEXT
scripts crowd the top ranks instead. Partial coverage — the known candidate is present
in the top 7 but not prioritized as the primary hit despite naming the exact protocol
concepts (header, magic number, version) in its own docstring per the summary field.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/Importer.py:268-323:decorated_definition:IPCConnection` | decorated_definition | 0.372 |
| 2 | `Scripts/td_exporter/Importer.py:1151-1193:method:Importer._open_and_validate_shm` | method | 0.192 |
| 3 | `Scripts/shmem_out_out_ip__Text__SharedMemEXT__td.py:1-36:module_preamble` | module_preamble | 0.19 |
| 4 | `Scripts/td_exporter/CUDAIPCExtension.py:1-70:module_preamble` | module_preamble | 0.16 |
| 5 | `Scripts/td_exporter/ActivationBarrier.py:1-50:module_preamble` | module_preamble | 0.13 |
| 6 | `Scripts/td_exporter/SHMProtocol.py:0-0:module:SHMProtocol` | module | 0.1242 |
| 7 | `Scripts/td_exporter/Importer.py:1008-1040:decorated_definition:Importer.open` | decorated_definition | 0.08 |

## C6 — sd_installer CLI subsystem end to end: install, verify, report

Known candidate: `StreamDiffusion/StreamDiffusion-installer/sd_installer/*`

Full coverage — module docstring at rank 3 (with `cmd_check`/`cmd_install`/`cmd_verify`/
`cmd_report` all named in the summary), plus individual `cmd_report`, `cmd_verify`,
`Installer.install`, `report.py` preamble, `cmd_install`, and `main` all in top 7.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/cli.py:206-247:function:cmd_report` | function | 0.288 |
| 2 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/cli.py:130-158:function:cmd_verify` | function | 0.2304 |
| 3 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/cli.py:0-0:module:cli` | module | 0.193 |
| 4 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/installer.py:477-533:method:Installer.install` | method | 0.1872 |
| 5 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/report.py:1-27:module_preamble` | module_preamble | 0.18 |
| 6 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/cli.py:107-127:function:cmd_install` | function | 0.1728 |
| 7 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/cli.py:389-486:function:main` | function | 0.168 |

## E1 — frame from TD TOP through CUDA IPC shared memory to receiver-side texture

Known candidate chain: `TDHost.py` → `CUDAIPCExtension.py` → `TDSender.py`/`TDReceiver.py` → `SHMProtocol.py`

**Note**: strong middle-of-chain coverage (`CUDAIPCExtension` module/class/`import_frame`/
`export_frame`, `TDSenderEngine.export_frame`, `TDReceiverEngine.import_frame`) but both
named chain *endpoints* — `TDHost.py` and `SHMProtocol.py` — are absent from top 7. Partial
coverage of the named chain.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:1-70:module_preamble` | module_preamble | 0.41 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:266-270:method:CUDAIPCExtension.import_frame` | method | 0.3744 |
| 3 | `Scripts/td_exporter/TDSender.py:591-818:split_block:TDSenderEngine.export_frame` | split_block | 0.2736 |
| 4 | `Scripts/td_exporter/TDReceiver.py:387-403:split_block:TDReceiverEngine.import_frame` | split_block | 0.198 |
| 5 | `Scripts/td_exporter/CUDAIPCExtension.py:261-264:method:CUDAIPCExtension.export_frame` | method | 0.1872 |
| 6 | `Scripts/td_exporter/CUDAIPCExtension.py:73-396:class:CUDAIPCExtension` | class | 0.1804 |
| 7 | `Scripts/td_exporter/TDReceiver.py:1-60:module_preamble` | module_preamble | 0.17 |

## E2 — FP8 quantization pipeline: calibration loading → ONNX Q/DQ injection → TensorRT build

Known candidate chain: `fp8_quantize.py` → `acceleration/tensorrt/engine_manager.py`/`builder.py`

**Note**: `builder.py` present (rank 5, `EngineBuilder.build`) but `engine_manager.py` does
NOT appear in top 7 — partial coverage of the named chain. Calibration-image-loading side
(`capture_calibration_data`, blended_score 0.0968 in the raw 30) falls just outside the cut.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1920-1955:split_block:quantize_onnx_fp8` | split_block | 0.6336 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1-45:module_preamble` | module_preamble | 0.32 |
| 3 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:998-1029:split_block:Engine._build_fp8` | split_block | 0.3003 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:2144-2192:function:_main` | function | 0.24 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:465-487:split_block:EngineBuilder.build` | split_block | 0.143 |
| 6 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/trt_base.py:469-503:split_block:SelfBuildingTRTPreprocessor._build_tensorrt_engine` | split_block | 0.132 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/__init__.py:122-186:function:compile_unet` | function | 0.108 |

## E3 — ControlNet config uploaded via FastAPI route → running pipeline's runtime state

Known candidate chain: `routes/controlnet.py` → `demo/realtime-img2img/config.py`/`connection_manager.py`

**Note**: the query's named breadcrumb files `config.py`/`connection_manager.py` do not
appear in top 7; instead `main.py`'s `AppState` class (constructor, `populate_from_config`,
`_sync_appstate_to_pipeline`) fills the "runtime state" role. Plausibly a stale/imprecise
breadcrumb rather than a genuine miss — flagged ambiguous, not scored as a clean hit or miss.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:39-167:split_block:upload_controlnet_config` | split_block | 0.5808 |
| 2 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:21-33:function:_ensure_runtime_controlnet_config` | function | 0.576 |
| 3 | `StreamDiffusion/demo/realtime-img2img/main.py:56-593:class:AppState` | class | 0.3244 |
| 4 | `StreamDiffusion/demo/realtime-img2img/main.py:121-208:method:AppState.populate_from_config` | method | 0.2772 |
| 5 | `StreamDiffusion/demo/realtime-img2img/main.py:59-119:method:AppState.__init__` | method | 0.2448 |
| 6 | `StreamDiffusion/demo/realtime-img2img/main.py:734-776:method:App._sync_appstate_to_pipeline` | method | 0.132 |
| 7 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:646-703:decorated_definition:get_current_preprocessor_params` | decorated_definition | 0.12 |

## E4 — StreamDiffusionTD extension coordinates with model_utils for compatible ControlNet model

Known candidate chain: `StreamDiffusionExt__td.py` → `StreamDiffusionTD__Text__model_utils__td.py`

Full coverage — `StreamDiffusionExt`'s coordination method (`auto_update_cn_values_for_model`,
rank 5) present alongside `model_utils`'s resolution functions (`resolve_controlnet_model_id`,
`find_compatible_cn_model`, `find_equivalent_cn_model`, `get_compatible_cn_menus`) across both
the `Scripts/` and `StreamDiffusionTD-fork/` copies, directly matching the known chain.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/StreamDiffusionTD__Text__model_utils__td.py:376-402:function:resolve_controlnet_model_id` | function | 0.6768 |
| 2 | `StreamDiffusionTD-fork/operator/model_utils.py:339-365:function:resolve_controlnet_model_id` | function | 0.6624 |
| 3 | `Scripts/StreamDiffusionTD__Text__model_utils__td.py:350-373:function:find_compatible_cn_model` | function | 0.5328 |
| 4 | `StreamDiffusionTD-fork/operator/model_utils.py:313-336:function:find_compatible_cn_model` | function | 0.4752 |
| 5 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:190-208:method:StreamDiffusionExt.auto_update_cn_values_for_model` | method | 0.4092 |
| 6 | `StreamDiffusionTD-fork/operator/model_utils.py:276-310:function:find_equivalent_cn_model` | function | 0.3 |
| 7 | `StreamDiffusionTD-fork/operator/model_utils.py:228-254:function:get_compatible_cn_menus` | function | 0.288 |

## E5 — token stored by secure_storage used by tox_updater to authorize TOX update download

Known candidate chain: `secure_storage__td.py` → `tox_updater__Text__auth_manager__td.py`/`ToxUpdaterEXT__td.py`

Full coverage — both named chain files present: `secure_storage__td.py`'s `store_token`/
`load_token`/`get_valid_token` alongside `auth_manager.py`'s `download_tox`/`get_token`/
`get_token_data` and `ToxUpdaterEXT`'s `_async_download_tox`/`_async_fetch_registry`, directly
tracing token → auth manager → download.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__ToxUpdaterEXT__td.py:700-723:method:ToxUpdaterEXT._async_download_tox` | method | 0.6336 |
| 2 | `Scripts/tox_updater__Text__auth_manager__td.py:442-484:method:AuthManager.download_tox` | method | 0.4056 |
| 3 | `Scripts/tox_updater__Text__ToxUpdaterEXT__td.py:675-698:method:ToxUpdaterEXT._async_fetch_registry` | method | 0.264 |
| 4 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:152-165:function:store_token` | function | 0.2592 |
| 5 | `Scripts/tox_updater__Text__ToxUpdaterEXT__td.py:1-24:module_preamble` | module_preamble | 0.25 |
| 6 | `Scripts/tox_updater__Text__auth_manager__td.py:320-327:method:AuthManager.get_token_data` | method | 0.2304 |
| 7 | `Scripts/tox_updater__Text__auth_manager__td.py:308-318:method:AuthManager.get_token` | method | 0.2028 |

## E6 — GPU profiling threaded through wrapper-level FP8 calibration path and pipeline per-step timing

Known candidate: `tools/gpu_profiler.py` used from `wrapper.py` and `pipeline.py`

**Note**: `GPUProfiler` class/`step` method and the FP8 calibration side (`fp8_quantize.py`
module preamble, `_build_fp8`) are present, but `pipeline.py`'s per-step timing usage only
surfaces indirectly via `unet_step` (rank 4, ego_graph) rather than a direct profiler call
site — partial coverage of the "both sides" framing.

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:329-335:method:GPUProfiler.step` | method | 0.2808 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:79-118:module_preamble` | module_preamble | 0.26 |
| 3 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:172-453:class:GPUProfiler` | class | 0.235 |
| 4 | `StreamDiffusion/src/streamdiffusion/pipeline.py:1075-1077:split_block:StreamDiffusion.unet_step` | split_block | 0.1188 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:1030-1056:split_block:Engine._build_fp8` | split_block | 0.0396 |
| 6 | `StreamDiffusion/scripts/fp8/probe_calib_pool_diversity.py:182-264:function:main` | function | 0.036 |
| 7 | `StreamDiffusion/src/streamdiffusion/tools/gpu_profiler.py:134-142:method:_RegionCtx.__enter__` | method | 0.0204 |

## E7 — param_schema timestep-grid connecting wrapper's calibration index building to pipeline's sub-timestep scheduling

Known candidate: `param_schema.py` used from `wrapper.py` and `pipeline.py`

Full coverage of `param_schema.py`'s own machinery — `materialise_timestep_grid`,
`compute_sub_timesteps`, `build_calibration_t_indices` (the exact three functions the query
names) all in top 3 — though the caller sites in `wrapper.py`/`pipeline.py` themselves don't
surface in top 7 (only `stream_parameter_updater.py`'s `_update_timestep_calculations` does,
rank 9 in raw results, outside window).

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/param_schema.py:215-253:function:materialise_timestep_grid` | function | 0.7038 |
| 2 | `StreamDiffusion/src/streamdiffusion/param_schema.py:189-204:function:compute_sub_timesteps` | function | 0.4175 |
| 3 | `StreamDiffusion/src/streamdiffusion/param_schema.py:341-436:function:build_calibration_t_indices` | function | 0.3795 |
| 4 | `StreamDiffusion/tests/unit/test_param_schema.py:324-329:method:TestBuildCalibrationTIndices.test_generalises_to_five_step_schedule` | method | 0.1662 |
| 5 | `StreamDiffusion/src/streamdiffusion/param_schema.py:207-212:module_preamble` | module_preamble | 0.15 |
| 6 | `StreamDiffusion/src/streamdiffusion/param_schema.py:0-0:module:param_schema` | module | 0.0774 |
| 7 | `StreamDiffusion/tests/unit/test_param_schema.py:408-426:method:TestBuildCalibrationTIndices.test_every_configured_value_lands_in_its_own_band` | method | 0.0391 |

## E8 — OSC message handler in Scripts routes control messages to StreamDiffusionTD extension parameter updates

Known candidate chain: `streamdiffusionTD__Text__td_osc_handler__td.py` → `StreamDiffusionExt__td.py`

Good coverage of the OSC-handler side — `_setup_osc_handlers`, `_queue_parameter_update`,
and per-parameter dispatch methods (`_handle_controlnet_config`, `_handle_controlnet_enable`)
dominate top 7 across both `Scripts/` and duplicate-copy locations; the `StreamDiffusionExt`
receiving side of the chain does not itself surface in top 7 (query is answered from the
handler side only).

| Rank | chunk_id | kind | blended_score |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_osc_handler.py:146-243:method:OSCParameterHandler._setup_osc_handlers` | method | 0.5412 |
| 2 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:173-261:method:OSCParameterHandler._setup_osc_handlers` | method | 0.5412 |
| 3 | `StreamDiffusion/StreamDiffusionTD/td_osc_handler.py:173-261:method:OSCParameterHandler._setup_osc_handlers` | method | 0.528 |
| 4 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:168-171:method:OSCParameterHandler._queue_parameter_update` | method | 0.4884 |
| 5 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:56-599:class:OSCParameterHandler` | class | 0.4785 |
| 6 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_osc_handler.py:21-574:class:OSCParameterHandler` | class | 0.4619 |
| 7 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:130-135:method:OSCParameterHandler.send_message` | method | 0.4464 |
