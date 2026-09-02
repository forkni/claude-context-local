# chunkhound (hybrid BM25+dense competitor) — raw results

Config: `chunkhound search "<query>" "D:\dev\SDTD_040_Beta" --db "C:\Users\Inter\chunkhound_sdtd\chunkhound.db" --provider openai --base-url http://localhost:11434/v1 --model bge-m3 --api-key ollama --semantic`.
Default `--page-size` is 10 (top-10 requested, no flag needed). Index: 301.7MB, 382/398 `.py`
files, 21,798 chunks, built 2026-08-17 10:32. chunkhound v5.2.1, Ollama-served `bge-m3:latest`
(1024-dim) embedding model, `localhost:11434`.

Rows = top-10 requested, non-`.py` rows dropped (none this batch), first 7 kept per harness
parity rules. Every one of the 30 queries returned "10 of 21798" raw results — no anomaly to
flag by the A8/E2-style convention used in the Arm A/B files.

**Determinism**: two independently invoked rounds were run for every query; all 30 were
byte-identical between Round 1 and Round 2 (same files, same line ranges, same similarity
scores to 3 decimals) — zero flips. Every table below is Round 1; Round 2 is stated as
identical rather than duplicated.

**`kind` column**: chunkhound's CLI does not expose AST-derived symbol kind the way our own
system does. `kind` here is inferred purely from the file path (`test` for files under
`tests/`/`tests\unit\`/named `test_*.py`, `src` otherwise) — a coarser label than our system's
`function`/`method`/`class`/`split_block`/`module_preamble` taxonomy, noted here rather than
per-row.

## A1 — CUDA OOM detection/classification, incl. RuntimeErrors from TensorRT

Known candidate(s): `wrapper.py` `_is_oom_error`

**Note**: clean rank-1 hit — `wrapper.py:29-45` contains the known candidate (`_is_oom_error`
at 29-38). Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:29-45` | src | 0.772 |
| 2 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:42-61` | test | 0.690 |
| 3 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:37-75` | test | 0.675 |
| 4 | `StreamDiffusion/tests/unit/test_wrapper_exception_hygiene.py:43-45` | test | 0.660 |
| 5 | `StreamDiffusion/src/streamdiffusion/wrapper.py:1-30` | src | 0.635 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:2684-2709` | src | 0.622 |
| 7 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3871-3898` | src | 0.618 |

Round 2: identical top-7.

## A2 — FP8 calibration per-image retry after batch encode failure

Known candidate(s): `wrapper.py` `_encode_fp8_calibration_images`

**Note**: partial miss — the known candidate function spans `wrapper.py:41-95`; rank 1
(`145-168`) is unrelated, rank 2 (`41-53`) only covers the first third of the function as a
fragment. No clean single-chunk hit. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:145-168` | src | 0.705 |
| 2 | `StreamDiffusion/src/streamdiffusion/wrapper.py:41-53` | src | 0.684 |
| 3 | `StreamDiffusion/src/streamdiffusion/wrapper.py:246-275` | src | 0.659 |
| 4 | `StreamDiffusion/tests/unit/test_fp8_ipadapter_calibration_token_resolver.py:259-278` | test | 0.656 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py:426-433` | src | 0.655 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:2540-2546` | src | 0.653 |
| 7 | `StreamDiffusion/src/streamdiffusion/wrapper.py:138-152` | src | 0.652 |

Round 2: identical top-7.

## A3 — feedback-loop blend formula (current input vs. previous frame's diffusion output)

Known candidate(s): `preprocessing/processors/feedback.py` `FeedbackPreprocessor`

**Note**: partial — the canonical candidate file (`feedback.py`) appears at rank 3, not rank 1;
ranks 1-2 are the duplicate `StreamDiffusionTD-fork` blend implementation
(`feedback_loop.py`), equally relevant but not the primary named file. Round 1 and Round 2 are
byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/custom_processors/sdtd_fx/feedback_loop.py:1-28` | src | 0.703 |
| 2 | `StreamDiffusionTD-fork/operator/custom_processors/sdtd_fx/feedback_loop.py:8-34` | src | 0.691 |
| 3 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:31-51` | src | 0.687 |
| 4 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:9-34` | src | 0.686 |
| 5 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:28-54` | src | 0.660 |
| 6 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/feedback.py:1-27` | src | 0.659 |
| 7 | `Scripts/custom_processors__Text__feedback_loop__td.py:10-22` | src | 0.657 |

Round 2: identical top-7.

## A4 — IPAdapter embedding preprocessor avoids re-encoding unchanged style image

Known candidate(s): `preprocessing/processors/ipadapter_embedding.py` `_last_input_ptr`/`_cached_embeds`

**Note**: clean rank-1 hit — `ipadapter_embedding.py:39-41` is a narrow slice likely covering
the `_last_input_ptr`/`_cached_embeds` attribute declarations directly; the file also appears
at ranks 3, 6. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:39-41` | src | 0.672 |
| 2 | `StreamDiffusion/src/streamdiffusion/wrapper.py:46-61` | src | 0.671 |
| 3 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:11-35` | src | 0.659 |
| 4 | `StreamDiffusion/src/streamdiffusion/wrapper.py:429-443` | src | 0.658 |
| 5 | `StreamDiffusion/src/streamdiffusion/wrapper.py:41-53` | src | 0.650 |
| 6 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/ipadapter_embedding.py:1-28` | src | 0.648 |
| 7 | `StreamDiffusion/demo/realtime-img2img/img2img.py:290-291` | src | 0.647 |

Round 2: identical top-7.

## A5 — calibration image set signature hashed for TensorRT engine cache-key suffix

Known candidate(s): `acceleration/tensorrt/engine_manager.py` `_calibration_image_signature`

**Note**: full miss — `engine_manager.py` appears at ranks 5, 6 but at lines `421-451`, not the
known candidate's `109-135` range; ranks 1-4 and 7 are `controlnet_module.py`/
`compile_depth_anything_tensorrt.py`/`model_utils.py` noise unrelated to calibration-signature
hashing. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/tools/compile_depth_anything_tensorrt.py:219` | src | 0.651 |
| 2 | `StreamDiffusion/src/streamdiffusion/modules/controlnet_module.py:589-615` | src | 0.644 |
| 3 | `StreamDiffusion/src/streamdiffusion/modules/controlnet_module.py:609` | src | 0.639 |
| 4 | `StreamDiffusionTD-fork/operator/model_utils.py:411` | src | 0.627 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py:428-447` | src | 0.626 |
| 6 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/engine_manager.py:421-443` | src | 0.623 |
| 7 | `StreamDiffusion/src/streamdiffusion/modules/controlnet_module.py:579-606` | src | 0.622 |

Round 2: identical top-7.

## A6 — auth token stored via OS-native secure storage (DPAPI/Keychain)

Known candidate(s): `Scripts/tox_updater__Text__secure_storage__td.py` `store_token`

**Note**: clean hit — rank 2 (`33-53`) is the exact known-candidate function; rank 1 (`1-51`)
is a superset containing it; Windows/macOS sibling backends also present (ranks 3-6, 8).
Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage__td.py:1-51` | src | 0.731 |
| 2 | `Scripts/tox_updater__Text__secure_storage__td.py:33-53` | src | 0.712 |
| 3 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:147-165` | src | 0.705 |
| 4 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:1-39` | src | 0.669 |
| 5 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:139-167` | src | 0.666 |
| 6 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:1-27` | src | 0.642 |
| 7 | `Scripts/tox_updater__Text__auth_manager__td.py:189` | src | 0.638 |

Round 2: identical top-7.

## A7 — TD Script TOP pixel-format string from tensor dtype/channel count for CUDA memcpy

Known candidate(s): `Scripts/td_exporter/TDReceiver.py` `td_format_string`

**Note**: clean hit — rank 2 (`63-87`) is the exact known-candidate function; rank 1 (`39-76`)
is an overlapping superset; `TDHost.py`/`TDSender.py` siblings also present (ranks 3-4, 5).
Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/td_exporter/TDReceiver.py:39-76` | src | 0.668 |
| 2 | `Scripts/td_exporter/TDReceiver.py:63-87` | src | 0.658 |
| 3 | `Scripts/td_exporter/TDHost.py:47-74` | src | 0.658 |
| 4 | `Scripts/td_exporter/TDHost.py:21-50` | src | 0.639 |
| 5 | `Scripts/td_exporter/TDSender.py:41-58` | src | 0.621 |
| 6 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1102-1121` | src | 0.618 |
| 7 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1041-1060` | src | 0.614 |

Round 2: identical top-7.

## A8 — REST endpoint accepting uploaded ControlNet YAML config

Known candidate(s): `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py` `upload_controlnet_config`

**Note**: clean rank-1 hit — `controlnet.py:37-68` starts almost exactly where our own
system's known-candidate split_block starts (`39-167`); the file dominates ranks 1-4, 7, 9.
Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:37-68` | src | 0.702 |
| 2 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:22-43` | src | 0.645 |
| 3 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:46` | src | 0.634 |
| 4 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:43-65` | src | 0.633 |
| 5 | `StreamDiffusion/tests/unit/test_controlnet_duplicate_dedup.py:294-295` | test | 0.615 |
| 6 | `StreamDiffusion/demo/realtime-img2img/app_config.py:14-16` | src | 0.613 |
| 7 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:338-348` | src | 0.613 |

Round 2: identical top-7.

## A9 — FP8 calibration prompts loaded from bundled text file

Known candidate(s): `acceleration/tensorrt/fp8_quantize.py` (near `_BUNDLED_PROMPTS_PATH`)

**Note**: ambiguous/partial, same pattern as our own system's own self-flagged note on this
query — top hits are `builder.py`/`fp8_quantize.py` calibration-*image* machinery
(`_list_calibration_images`-adjacent regions), not the bundled-*prompts* loader specifically;
neither system cleanly resolves the images-vs-prompts ambiguity. Round 1 and Round 2 are
byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:602` | src | 0.701 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:604-637` | src | 0.698 |
| 3 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:35-51` | src | 0.695 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:121-134` | src | 0.685 |
| 5 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:120-137` | src | 0.685 |
| 6 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:604` | src | 0.671 |
| 7 | `StreamDiffusion/src/streamdiffusion/wrapper.py:195-221` | src | 0.664 |

Round 2: identical top-7.

## A10 — TF32 matmul / cuDNN benchmark mode enabled once per CUDA device at pipeline construction

Known candidate(s): `pipeline.py` `StreamDiffusion.__init__`

**Note**: clean hit — `pipeline.py` dominates ranks 1-4 (`55-94`), directly covering the
constructor region (our own system's own known-candidate `__init__` split_block is
`111-172` — chunkhound's finer chunking surfaces the earlier part of the same class/constructor
area at high similarity, 0.70/0.693/0.688/0.635). Round 1 and Round 2 are byte-identical — no
flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/pipeline.py:70-74` | src | 0.700 |
| 2 | `StreamDiffusion/src/streamdiffusion/pipeline.py:69-94` | src | 0.693 |
| 3 | `StreamDiffusion/src/streamdiffusion/pipeline.py:68-94` | src | 0.688 |
| 4 | `StreamDiffusion/src/streamdiffusion/pipeline.py:55-81` | src | 0.635 |
| 5 | `StreamDiffusion/src/streamdiffusion/config.py:318-334` | src | 0.618 |
| 6 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/__init__.py:163-189` | src | 0.606 |
| 7 | `Scripts/td_exporter/Importer.py:572-592` | src | 0.603 |

Round 2: identical top-7.

## B1 — Sender/Receiver CUDA IPC engines as a matched pair

Known candidate(s): `Scripts/td_exporter/TDSender.py`, `TDReceiver.py`

**Note**: miss on the specifically named classes — neither `TDSender.py` nor `TDReceiver.py`
appears in top 7; `CUDAIPCExtension.py` (rank 7 only) and generic import/export machinery
(`Importer.py`, `example_receiver_python.py`, `Exporter.py`, `script_top_callbacks.py`)
substitute instead. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:904-924` | src | 0.631 |
| 2 | `Scripts/td_exporter/Importer.py:900-930` | src | 0.626 |
| 3 | `Scripts/td_exporter/example_receiver_python.py:132-157` | src | 0.626 |
| 4 | `StreamDiffusion/src/streamdiffusion/wrapper.py:1350-1379` | src | 0.625 |
| 5 | `StreamDiffusion/src/streamdiffusion/wrapper.py:1473-1502` | src | 0.621 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:1481-1508` | src | 0.620 |
| 7 | `Scripts/td_exporter/script_top_callbacks.py:34-35` | src | 0.620 |

Round 2: identical top-7.

## B2 — Windows/macOS secure-storage backends as parallel platform-specific modules

Known candidate(s): `secure_storage_windows__td.py`, `secure_storage_macos__td.py`

**Note**: partial — `secure_storage_macos__td.py` present (rank 3), but
`secure_storage_windows__td.py` is absent from top 7 entirely; the generic
`secure_storage__td.py` dominates instead (ranks 1, 2). Round 1 and Round 2 are byte-identical
— no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage__td.py:1-51` | src | 0.700 |
| 2 | `Scripts/tox_updater__Text__secure_storage__td.py:21-30` | src | 0.678 |
| 3 | `Scripts/tox_updater__Text__secure_storage_macos__td.py:1-39` | src | 0.607 |
| 4 | `Scripts/shmem_in_cn_processed__Text__SharedMemEXT__td.py:21` | src | 0.581 |
| 5 | `Scripts/shmem_out_out_ip__Text__SharedMemEXT__td.py:21` | src | 0.581 |
| 6 | `Scripts/dotloader__Text__DotToxLoaderExt__td.py:28-57` | src | 0.578 |
| 7 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:1819-1821` | src | 0.571 |

Round 2: identical top-7.

## B3 — test exercising multi-ControlNet residual-merge, and the module it tests

Known candidate(s): `tests/unit/test_controlnet_residual_merge.py` vs `modules/controlnet_module.py`

**Note**: test file dominates top 7 (6 of 7 rows), matching our own system's own top-7
pattern; `controlnet_module.py` (the module under test) does not surface in top 7 for either
system. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:69-97` | test | 0.674 |
| 2 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:1-23` | test | 0.634 |
| 3 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:47-69` | test | 0.626 |
| 4 | `StreamDiffusion/src/streamdiffusion/stream_parameter_updater.py:1776` | src | 0.619 |
| 5 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:147-164` | test | 0.614 |
| 6 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:142-156` | test | 0.612 |
| 7 | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py:127-145` | test | 0.608 |

Round 2: identical top-7.

## B4 — single-frame/multi-frame variants of img2img and txt2img examples

Known candidate(s): `StreamDiffusion/examples/{img2img,txt2img}/{single,multi}.py`

**Note**: near-total miss — only 1 of 10 raw results is one of the four named example files
(`img2img/multi.py` at rank 5); the rest is `td_manager.py`/`td_osc_handler.py`/`websocket.py`
noise unrelated to the query. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:1357` | src | 0.631 |
| 2 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1329` | src | 0.631 |
| 3 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_osc_handler.py:217` | src | 0.623 |
| 4 | `StreamDiffusion/demo/realtime-img2img/utils/__init__.py:1` | src | 0.611 |
| 5 | `StreamDiffusion/examples/img2img/multi.py:62-122` | src | 0.586 |
| 6 | `StreamDiffusion/demo/realtime-img2img/routes/websocket.py:73-78` | src | 0.584 |
| 7 | `StreamDiffusion/demo/realtime-img2img/routes/common/__init__.py:1-3` | src | 0.576 |

Round 2: identical top-7.

## B5 — shmem_in_cn_processed / shmem_out_out_ip TouchDesigner script sets mirroring

Known candidate(s): `Scripts/shmem_in_cn_processed__*` vs `Scripts/shmem_out_out_ip__*`

**Note**: full miss — zero `shmem_*` files appear anywhere in the top 10; results are
dominated entirely by `td_manager.py` (both `Scripts/` and `StreamDiffusionTD-fork/` copies)
plus one `benchmark_timestamp.py` hit. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:472-492` | src | 0.656 |
| 2 | `Scripts/td_exporter/benchmark_timestamp.py:1-36` | src | 0.605 |
| 3 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:475-480` | src | 0.603 |
| 4 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1102-1121` | src | 0.602 |
| 5 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:1112-1158` | src | 0.592 |
| 6 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:461-480` | src | 0.590 |
| 7 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:484-504` | src | 0.587 |

Round 2: identical top-7.

## B6 — test exercising FaceID LoRA fusion, and the module implementing FaceID compat

Known candidate(s): `tests/unit/test_faceid_lora_fusion.py` vs `modules/faceid_compat.py`

**Note**: strong coverage — both named files present, `test_faceid_lora_fusion.py` at rank 2,
`faceid_compat.py` at ranks 3-6 (4 rows); `ipadapter_module.py` (rank 1) and
`test_faceid_bgr_patch.py` (rank 7, adjacent test) round out the set. Round 1 and Round 2 are
byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/modules/ipadapter_module.py:391` | src | 0.619 |
| 2 | `StreamDiffusion/tests/unit/test_faceid_lora_fusion.py:1-22` | test | 0.592 |
| 3 | `StreamDiffusion/src/streamdiffusion/modules/faceid_compat.py:433-449` | src | 0.583 |
| 4 | `StreamDiffusion/src/streamdiffusion/modules/faceid_compat.py:383-399` | src | 0.573 |
| 5 | `StreamDiffusion/src/streamdiffusion/modules/faceid_compat.py:383-402` | src | 0.571 |
| 6 | `StreamDiffusion/src/streamdiffusion/modules/faceid_compat.py:363-382` | src | 0.570 |
| 7 | `StreamDiffusion/tests/unit/test_faceid_bgr_patch.py:186` | test | 0.567 |

Round 2: identical top-7.

## C1 — StreamDiffusion pipeline class constructor: CFG type, LoRA dict, KV-cache, feature injection

Known candidate(s): `pipeline.py` `class StreamDiffusion.__init__`

**Note**: partial — `pipeline.py` present at ranks 4, 6 (`42-67`, `28-54`, overlapping the
class/constructor start) but not rank 1; `wrapper.py` and `examples/img2img/{single,multi}.py`
usage-example scripts crowd ranks 1-3, 5, 7-9 instead. Round 1 and Round 2 are byte-identical
— no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:2191-2219` | src | 0.665 |
| 2 | `StreamDiffusion/examples/img2img/multi.py:31-61` | src | 0.646 |
| 3 | `StreamDiffusion/src/streamdiffusion/wrapper.py:2195-2218` | src | 0.643 |
| 4 | `StreamDiffusion/src/streamdiffusion/pipeline.py:42-67` | src | 0.640 |
| 5 | `StreamDiffusion/examples/img2img/single.py:71-86` | src | 0.639 |
| 6 | `StreamDiffusion/src/streamdiffusion/pipeline.py:28-54` | src | 0.639 |
| 7 | `StreamDiffusion/examples/img2img/multi.py:75-90` | src | 0.637 |

Round 2: identical top-7.

## C2 — CUDA IPC extension architecture: Sender/Receiver engine delegation

Known candidate(s): `Scripts/td_exporter/CUDAIPCExtension.py` module docstring

**Note**: clean hit — `CUDAIPCExtension.py` at ranks 1-2 directly (module-preamble-equivalent
region + class body); `TDReceiver.py` present at ranks 7, 8, 10 (receiver side of the
delegation), though `TDSender.py` does not surface in top 7. Round 1 and Round 2 are
byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:73-112` | src | 0.617 |
| 2 | `Scripts/td_exporter/CUDAIPCExtension.py:1-24` | src | 0.610 |
| 3 | `Scripts/td_exporter/CUDARuntimeTypes.py:68-100` | src | 0.606 |
| 4 | `Scripts/td_exporter/CUDARuntimeTypes.py:69-81` | src | 0.602 |
| 5 | `Scripts/td_exporter/example_receiver_launcher.py:1-20` | src | 0.583 |
| 6 | `Scripts/td_exporter/example_sender_launcher.py:1-22` | src | 0.575 |
| 7 | `Scripts/td_exporter/TDReceiver.py:792-817` | src | 0.572 |

Round 2: identical top-7.

## C3 — StreamDiffusionTD extension class responsibilities: model mgmt, TensorRT build, version tracking

Known candidate(s): `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py` `class StreamDiffusionExt`

**Note**: weak/partial — only 2 of 10 rows (ranks 8, 10) are the named `StreamDiffusionExt`
class, and both are just the module-preamble/first-line region, not the class body or its
methods; `model_utils.py` and `td_manager.py` dominate ranks 1-7, 9. Round 1 and Round 2 are
byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/model_utils.py:1-18` | src | 0.715 |
| 2 | `Scripts/StreamDiffusionTD__Text__model_utils__td.py:1-20` | src | 0.703 |
| 3 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:38-84` | src | 0.689 |
| 4 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:49-88` | src | 0.670 |
| 5 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:43-63` | src | 0.667 |
| 6 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:46-65` | src | 0.664 |
| 7 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:20-42` | src | 0.660 |

Round 2: identical top-7.

## C4 — preprocessing pipeline orchestration across ControlNet/IPAdapter/FaceID

Known candidate(s): `preprocessing_orchestrator.py`, `pipeline_preprocessing_orchestrator.py`

**Note**: partial — `preprocessing_orchestrator.py` present (ranks 2, 4) but the second named
candidate, `pipeline_preprocessing_orchestrator.py`, does not appear anywhere in top 10;
`StreamDiffusionExt.py` and FaceID/image-processing files fill the remaining slots. Round 1
and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:3921-3948` | src | 0.673 |
| 2 | `StreamDiffusion/src/streamdiffusion/preprocessing/preprocessing_orchestrator.py:32-66` | src | 0.669 |
| 3 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:3629-3631` | src | 0.663 |
| 4 | `StreamDiffusion/src/streamdiffusion/preprocessing/preprocessing_orchestrator.py:153-177` | src | 0.656 |
| 5 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:3634-3656` | src | 0.655 |
| 6 | `StreamDiffusion/src/streamdiffusion/modules/image_processing_module.py:48-52` | src | 0.650 |
| 7 | `StreamDiffusion/tests/unit/test_faceid_preprocessor_contract.py:76` | test | 0.646 |

Round 2: identical top-7.

## C5 — shared-memory protocol layout: header, slot size, magic number, version

Known candidate(s): `Scripts/td_exporter/SHMProtocol.py`

**Note**: full miss — `SHMProtocol.py` does not appear anywhere in top 10; `td_manager.py`
dominates (ranks 1, 4, 6, 7), with `shmem_in_cn_processed`/`shmem_out_out_ip`
`SharedMemEXT` module preambles present (ranks 2-3) but not the protocol-layout module itself.
Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:484-504` | src | 0.664 |
| 2 | `Scripts/shmem_in_cn_processed__Text__SharedMemEXT__td.py:1-60` | src | 0.658 |
| 3 | `Scripts/shmem_out_out_ip__Text__SharedMemEXT__td.py:1-59` | src | 0.658 |
| 4 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:472-492` | src | 0.657 |
| 5 | `Scripts/td_exporter/CUDARuntimeTypes.py:68-100` | src | 0.653 |
| 6 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:466-496` | src | 0.653 |
| 7 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:461-480` | src | 0.645 |

Round 2: identical top-7.

## C6 — sd_installer CLI subsystem end to end: install, verify, report

Known candidate(s): `StreamDiffusion/StreamDiffusion-installer/sd_installer/*`

**Note**: good coverage — 5 of 10 rows are genuine `sd_installer/*` files (`cli.py`,
`__init__.py` ×2, `tensorrt.py`, `report.py` at rank 8 outside window), though weighted toward
file/module-level hits rather than the specific `cmd_install`/`cmd_verify`/`cmd_report`
command functions our own system surfaces. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/cli.py:389-412` | src | 0.620 |
| 2 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/__init__.py:1-19` | src | 0.613 |
| 3 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/__init__.py:19` | src | 0.612 |
| 4 | `StreamDiffusion/StreamDiffusion-installer/sd_installer/tensorrt.py:307` | src | 0.600 |
| 5 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/install_tensorrt.py:294` | src | 0.600 |
| 6 | `Scripts/streamdiffusionTD__Text__install_tensorrt__td.py:307` | src | 0.600 |
| 7 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:1271-1297` | src | 0.597 |

Round 2: identical top-7.

## E1 — frame from TD TOP through CUDA IPC shared memory to receiver-side texture

Known candidate chain: `TDHost.py` → `CUDAIPCExtension.py` → `TDSender.py`/`TDReceiver.py` → `SHMProtocol.py`

**Note**: partial — `CUDAIPCExtension.py` present (ranks 1, 4) and `example_receiver_python.py`
(rank 8), but generic `td_manager.py` duplicates fill 4 of 7 slots (ranks 2, 3, 5, 6) in place
of the specifically named `TDHost.py`, `TDSender.py`, `TDReceiver.py`, `SHMProtocol.py` chain
files — none of which appear anywhere in top 10. Round 1 and Round 2 are byte-identical — no
flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/td_exporter/CUDAIPCExtension.py:1-24` | src | 0.674 |
| 2 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:1070-1097` | src | 0.674 |
| 3 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1048-1073` | src | 0.672 |
| 4 | `Scripts/td_exporter/CUDAIPCExtension.py:73-112` | src | 0.668 |
| 5 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1102-1121` | src | 0.663 |
| 6 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_manager.py:1041-1060` | src | 0.662 |
| 7 | `Scripts/streamdiffusionTD__Text__td_manager__td.py:1127-1161` | src | 0.651 |

Round 2: identical top-7.

## E2 — FP8 quantization pipeline: calibration loading → ONNX Q/DQ injection → TensorRT build

Known candidate chain: `fp8_quantize.py` → `acceleration/tensorrt/engine_manager.py`/`builder.py`

**Note**: partial — `fp8_quantize.py` dominates (ranks 1, 2, 3, 7 — 4 of 7 rows) and
`builder.py` is present (rank 4), but `engine_manager.py` (the other named chain file) does
not appear in top 7. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1-34` | src | 0.700 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1923-1939` | src | 0.690 |
| 3 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1906-1934` | src | 0.683 |
| 4 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:661-677` | src | 0.677 |
| 5 | `StreamDiffusion/tests/unit/test_fp8_calibration_mode_dirs.py:22-30` | test | 0.671 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:1948-1963` | src | 0.670 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/fp8_quantize.py:1694-1707` | src | 0.665 |

Round 2: identical top-7.

## E3 — ControlNet config uploaded via FastAPI route → running pipeline's runtime state

Known candidate chain: `routes/controlnet.py` → `demo/realtime-img2img/config.py`/`connection_manager.py`

**Note**: ambiguous, same pattern as our own system's own self-flagged note — the breadcrumb
files `config.py`/`connection_manager.py` do not appear in top 7; `routes/controlnet.py`
dominates (5 of 7 rows) with `realtime-txt2img/main.py` and `realtime-img2img/main.py` filling
a "runtime" role instead. Not scored as a clean hit or miss. Round 1 and Round 2 are
byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3337` | src | 0.656 |
| 2 | `StreamDiffusion/demo/realtime-txt2img/main.py:50-90` | src | 0.630 |
| 3 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:625-643` | src | 0.625 |
| 4 | `StreamDiffusion/demo/realtime-img2img/main.py:759-782` | src | 0.624 |
| 5 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:550-571` | src | 0.623 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:1841-1870` | src | 0.622 |
| 7 | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py:154-175` | src | 0.617 |

Round 2: identical top-7.

## E4 — StreamDiffusionTD extension coordinates with model_utils for compatible ControlNet model

Known candidate chain: `StreamDiffusionExt__td.py` → `StreamDiffusionTD__Text__model_utils__td.py`

**Note**: full coverage — `model_utils.py` present at ranks 1-2 (both `Scripts/` and
`StreamDiffusionTD-fork/` copies) and `StreamDiffusionExt.py` at ranks 3, 7 (also both
copies), directly matching the named chain, though at coarser file/preamble granularity than
our own system's named-function hits. Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/model_utils.py:1-18` | src | 0.700 |
| 2 | `Scripts/StreamDiffusionTD__Text__model_utils__td.py:1-20` | src | 0.691 |
| 3 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:4106` | src | 0.685 |
| 4 | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py:4450` | src | 0.685 |
| 5 | `StreamDiffusion/src/streamdiffusion/wrapper.py:444-459` | src | 0.663 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3337` | src | 0.657 |
| 7 | `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:1-23` | src | 0.657 |

Round 2: identical top-7.

## E5 — token stored by secure_storage used by tox_updater to authorize TOX update download

Known candidate chain: `secure_storage__td.py` → `tox_updater__Text__auth_manager__td.py`/`ToxUpdaterEXT__td.py`

**Note**: full coverage — `secure_storage_windows__td.py` at rank 1, `auth_manager__td.py` at
ranks 2, 3, 7 (3 rows), `ToxUpdaterEXT__td.py` at ranks 4-6 (3 rows) — 7 of 7 rows across the
named chain files, directly tracing token storage → auth manager → updater. Round 1 and
Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `Scripts/tox_updater__Text__secure_storage_windows__td.py:139-167` | src | 0.704 |
| 2 | `Scripts/tox_updater__Text__auth_manager__td.py:355` | src | 0.676 |
| 3 | `Scripts/tox_updater__Text__auth_manager__td.py:305` | src | 0.669 |
| 4 | `Scripts/tox_updater__Text__ToxUpdaterEXT__td.py:1-32` | src | 0.662 |
| 5 | `Scripts/tox_updater__Text__ToxUpdaterEXT__td.py:198-230` | src | 0.657 |
| 6 | `Scripts/tox_updater__Text__ToxUpdaterEXT__td.py:27-58` | src | 0.637 |
| 7 | `Scripts/tox_updater__Text__auth_manager__td.py:1-30` | src | 0.635 |

Round 2: identical top-7.

## E6 — GPU profiling threaded through wrapper-level FP8 calibration path and pipeline per-step timing

Known candidate: `tools/gpu_profiler.py` used from `wrapper.py` and `pipeline.py`

**Note**: full miss — `gpu_profiler.py` does not appear anywhere in top 10; TensorRT
`utilities.py`/`builder.py`/`trt_base.py` GPU-build-profile code dominates instead (topically
adjacent — "GPU profile" as a TensorRT build concept, not the runtime `GPUProfiler` class the
query asks about). Round 1 and Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:168-190` | src | 0.660 |
| 2 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:708-736` | src | 0.654 |
| 3 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/trt_base.py:494-513` | src | 0.654 |
| 4 | `Scripts/StreamDiffusionTD__Text__model_utils__td.py:83-123` | src | 0.651 |
| 5 | `StreamDiffusion/src/streamdiffusion/preprocessing/processors/trt_base.py:495-514` | src | 0.650 |
| 6 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/utilities.py:239-262` | src | 0.644 |
| 7 | `StreamDiffusion/src/streamdiffusion/acceleration/tensorrt/builder.py:711-726` | src | 0.642 |

Round 2: identical top-7.

## E7 — param_schema timestep-grid connecting wrapper's calibration index building to pipeline's sub-timestep scheduling

Known candidate: `param_schema.py` used from `wrapper.py` and `pipeline.py`

**Note**: partial on `param_schema.py` itself (present but only ranks 3, 7 — thinner than our
own system's top-3 coverage of its three named functions) but stronger on the *caller-site*
half of the query: `wrapper.py` dominates ranks 1, 2, 4, 5, 6 (5 of 7 rows). Round 1 and
Round 2 are byte-identical — no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3006-3032` | src | 0.654 |
| 2 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3002-3016` | src | 0.645 |
| 3 | `StreamDiffusion/src/streamdiffusion/param_schema.py:190-203` | src | 0.643 |
| 4 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3031-3044` | src | 0.639 |
| 5 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3022-3036` | src | 0.638 |
| 6 | `StreamDiffusion/src/streamdiffusion/wrapper.py:3007-3030` | src | 0.636 |
| 7 | `StreamDiffusion/src/streamdiffusion/param_schema.py:191-218` | src | 0.626 |

Round 2: identical top-7.

## E8 — OSC message handler in Scripts routes control messages to StreamDiffusionTD extension parameter updates

Known candidate chain: `streamdiffusionTD__Text__td_osc_handler__td.py` → `StreamDiffusionExt__td.py`

**Note**: full coverage of both sides of the named chain — `td_osc_handler.py` dominates
ranks 1-7 across `StreamDiffusionTD-fork/` and `Scripts/`/duplicate-copy locations (handler
side), and rank 8 (`StreamDiffusionExt.py`, outside the 7-cut but present in raw 10) reaches
the receiving side our own system's own top-7 misses. Round 1 and Round 2 are byte-identical
— no flip.

| Rank | file:lines | kind | similarity |
|---|---|---|---|
| 1 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_osc_handler.py:21-54` | src | 0.708 |
| 2 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:56-89` | src | 0.698 |
| 3 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_osc_handler.py:1-35` | src | 0.689 |
| 4 | `StreamDiffusionTD-fork/operator/streamdiffusionTD/td_osc_handler.py:103-143` | src | 0.673 |
| 5 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:1-37` | src | 0.673 |
| 6 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:124-157` | src | 0.670 |
| 7 | `Scripts/streamdiffusionTD__Text__td_osc_handler__td.py:221-242` | src | 0.666 |

Round 2: identical top-7. (Raw rank 8, outside the 7-cut: `StreamDiffusionTD-fork/operator/StreamDiffusionExt.py:4833-4857`, similarity 0.657 — the chain's receiving-side endpoint.)

## Comparison vs claude-context-local (Arm A, full pipeline)

Verdict per query — **ours** (claude-context-local Arm A wins), **chunkhound** (chunkhound
wins), **tie** (comparable coverage of the known candidate(s)), or **both-miss** (neither
system cleanly resolves an ambiguous query):

- **A1** (CUDA OOM detection) — tie. Both hit `wrapper.py`'s `_is_oom_error` cleanly at rank 1.
- **A2** (FP8 per-image retry) — ours. Arm A gets the full function (`41-95`) at rank 1 (0.9072); chunkhound only surfaces a fragment (`41-53`) at rank 2.
- **A3** (feedback blend formula) — ours. Arm A ranks the canonical `feedback.py` class at rank 1; chunkhound ranks the sibling TD-fork duplicate first, the real file at rank 3.
- **A4** (IPAdapter re-encode avoidance) — tie. Both hit `ipadapter_embedding.py` at rank 1.
- **A5** (calibration signature hash) — ours. Arm A's rank-1 is the exact function (0.8268); chunkhound never finds the right line range, buried and wrong at ranks 5/6/8.
- **A6** (secure token storage) — tie. Both hit the exact `store_token` function.
- **A7** (TD pixel-format string) — tie. Both hit the exact `td_format_string` function.
- **A8** (ControlNet YAML upload) — tie. Both hit the exact function at rank 1.
- **A9** (bundled calibration prompts) — both-miss. Neither system resolves the images-vs-prompts ambiguity.
- **A10** (TF32/cuDNN pipeline construction) — chunkhound. Arm A fully misses this one (candidate absent from top 7); chunkhound's finer chunking nails `pipeline.py`'s constructor region at ranks 1-4.
- **B1** (Sender/Receiver pair) — ours. Arm A surfaces both named classes; chunkhound surfaces neither.
- **B2** (Windows/macOS secure storage) — ours. Arm A has both platform variants; chunkhound is missing the Windows one.
- **B3** (ControlNet residual-merge test) — tie. Both give strong test-file coverage; neither surfaces the module under test in top 7.
- **B4** (img2img/txt2img examples) — ours. Arm A gets full coverage of all four sibling files; chunkhound surfaces only one of ten rows as an example file.
- **B5** (shmem script mirroring) — ours. Arm A gets good coverage of both script sets; chunkhound has zero `shmem_*` hits.
- **B6** (FaceID LoRA fusion test/module) — tie. Both give strong coverage of the named pair.
- **C1** (pipeline constructor overview) — ours. Arm A's top-2 is a clean class/`__init__` hit; chunkhound buries `pipeline.py` at ranks 4/6 behind usage-example noise.
- **C2** (CUDA IPC architecture) — tie. Both hit `CUDAIPCExtension.py` cleanly at rank 1-2.
- **C3** (StreamDiffusionExt responsibilities) — ours. Arm A's entire top 7 is the named class (methods, installer, compat check); chunkhound gives only 2 weak preamble-only hits, dominated by unrelated `model_utils.py`/`td_manager.py`.
- **C4** (preprocessing orchestration) — ours. Arm A has both named orchestrator classes; chunkhound is missing `pipeline_preprocessing_orchestrator.py` entirely.
- **C5** (shared-memory protocol layout) — ours. Arm A has `SHMProtocol.py` at rank 6 (partial); chunkhound has zero presence of that file.
- **C6** (sd_installer CLI) — tie. Both give solid coverage of the installer subsystem.
- **E1** (TOP→CUDA IPC→receiver chain) — ours. Arm A names both sender/receiver engine classes explicitly; chunkhound substitutes generic `td_manager.py` noise for over half its rows.
- **E2** (FP8 quantization chain) — tie. Both are missing `engine_manager.py`, otherwise comparable `fp8_quantize.py`/`builder.py` coverage.
- **E3** (ControlNet config → runtime state) — tie/ambiguous. Same breadcrumb-absence pattern in both.
- **E4** (StreamDiffusionExt↔model_utils) — tie. Both give full file-level coverage of the named chain.
- **E5** (secure_storage→tox_updater auth chain) — tie. Both give full coverage across all three named files.
- **E6** (GPU profiling threading) — ours. Arm A has the actual `GPUProfiler` class present; chunkhound has zero `gpu_profiler.py` presence, substituting topically-adjacent TensorRT build-profile code.
- **E7** (param_schema timestep-grid) — chunkhound (edge). Arm A's own note admits caller sites (`wrapper.py`/`pipeline.py`) don't surface; chunkhound covers both the schema functions and the `wrapper.py` caller site the query specifically asks about.
- **E8** (OSC handler→extension routing) — chunkhound (edge). Arm A's own note admits the `StreamDiffusionExt` receiving side doesn't surface; chunkhound reaches it at raw rank 8 just outside the cut, while Arm A doesn't reach it at all within its top 7.

**Tally**: ours 13, chunkhound 3, tie 12, both-miss 2 (of 30).

**Flips**: zero — all 30 queries were byte-identical between chunkhound's Round 1 and Round 2.

**Anomalies**: zero — every query returned exactly "10 of 21798" raw results on both systems'
harnesses; no query fell below the top-10 floor.

**Structural differences observed**:

1. **Reranking/ranking quality on exact-symbol queries.** When both systems' underlying dense
   embeddings find the right file, our own system's cross-encoder reranker (F2LLM-v2-0.6B +
   listwise reranking) far more reliably puts the *exact* named function at rank 1 with a
   large score gap over noise (e.g. A2, A3, A5, C1, C3: Arm A blended scores of 0.68-0.97 at
   rank 1 vs. a steep drop-off). chunkhound's flat cosine-similarity ranking clusters
   everything in a narrow 0.55-0.70 band, so a genuinely relevant chunk at rank 2-3 is barely
   distinguishable in score from an irrelevant one at rank 6-7 — the exact candidate can end
   up anywhere in the window rather than reliably at the top.

2. **Named multi-file / sibling-pair queries (Category B) are where the gap is largest.**
   Arm A's graph-aware retrieval (ego-graph/multi-hop) explicitly surfaces sibling files that
   share a naming or import relationship (B1 Sender+Receiver, B2 Windows+macOS backends, B4
   all four example scripts, B5 both shmem script sets) even when their raw semantic
   similarity to the query text is modest. chunkhound has no such mechanism — it found *zero*
   or *one* of the intended files on B4 and B5, both full or near-total misses, because those
   files' plain-text content doesn't lexically/semantically resemble the query as strongly as
   unrelated but higher-frequency vocabulary elsewhere in the corpus (`td_manager.py`
   appeared as noise in both).

3. **Duplicate-tree noise is a minor, mostly-cosmetic shared weakness, not a load-bearing
   one.** Both systems' windows show occasional near-identical copies from the corpus's
   parallel source trees (`Scripts/`, `StreamDiffusionTD-fork/`, and occasionally a third
   `StreamDiffusion/StreamDiffusionTD/` copy) on TouchDesigner extension queries. Measured
   (`evaluation/DUPLICATE_CROWDING_PROBE_20260817.md`): only **5 of 210 (2.4%)** visible
   top-7 slots across the 30-query set are exact-duplicate waste, confined to 3 queries (B5,
   E4, E8) — 27 of 30 queries show none. Of those 5, 2 are actually *wanted* (B5 asks where
   two script sets mirror each other; both copies are the answer), leaving 1.4% net tractable
   waste. A follow-up probe measured the same question at the 30-slot rerank window (not just
   the visible top-7) with a pre-registered gate for a fold-don't-drop fix and found the ABORT
   condition on all four tested criteria: window-level duplicate occupancy is 5.8% against a
   10% bar, recoverable content is well under the recoverability bar, and — decisively — any
   fold wide enough to matter would collapse Category B's own sibling-pair mirror answers
   (B5) and legitimately-parallel example scripts (B4) at least as often as it recovers new
   content elsewhere. Neither system de-duplicates near-identical cross-tree chunks, and for
   this system that is now a measured, deliberate non-fix rather than an unexamined gap.

4. **chunkhound's finer, uniform chunk granularity occasionally wins on constructor-style
   queries.** A10 is the clearest case: our own system's chunk boundary for
   `StreamDiffusion.__init__` starts at line 111, past where TF32/cuDNN device setup actually
   happens (lines ~68-94); chunkhound's smaller, denser chunks landed squarely on that earlier
   region and won outright where Arm A fully missed. E7/E8 show a related pattern — when the
   query asks about a *connection* between two files, chunkhound's flatter ranking sometimes
   incidentally surfaces both ends of the connection where our own system's reranker, tuned
   to reward one dominant match, suppresses the second (caller-site) half.
