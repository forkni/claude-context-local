# Cross-system comparison — pre-registered queries, rubric, gate (frozen 2026-08-17)

Frozen before any competitor system is installed or run, per
`C:\Users\Inter\.claude\plans\c-users-inter-downloads-open-source-rag-spicy-harp.md`
Phase 0. Corpus: `evaluation/CROSS_SYSTEM_CORPUS_20260817.md` (398 `.py` files,
`D:\dev\SDTD_040_Beta`).

Queries were written from directly reading a sample of SDTD source files across every
top-level directory in the corpus (`StreamDiffusion/src/streamdiffusion/{wrapper,pipeline}.py`,
`.../preprocessing/processors/{feedback,ipadapter_embedding}.py`,
`.../acceleration/tensorrt/fp8_quantize.py`, `.../modules/controlnet_module.py` (via its
test), `Scripts/td_exporter/{TDHost,TDReceiver,CUDAIPCExtension}.py`,
`Scripts/tox_updater__Text__secure_storage__td.py`,
`Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py`,
`StreamDiffusion/demo/realtime-img2img/routes/controlnet.py`,
`StreamDiffusion/tests/unit/test_controlnet_residual_merge.py`) — never from watching
any system succeed or fail. No tool beyond `Read` was used to write these.

The "known candidate" column is a breadcrumb from that reading pass for my own Phase 8
seed-pass check — **not** a gold answer key. Pooled grading (Phase 8) is what actually
determines relevance; a candidate landing outside a system's top-7 is not automatically
counted against it, and other files may be equally or more relevant.

## Grading rubric (house scale, from `docs/BENCHMARKS.md`)

| Grade | Meaning |
|---|---|
| 3 | Directly answers the query — this is what the query is asking for |
| 2 | Relevant — meaningfully related, would help answer the query |
| 1 | Marginal — tangentially related only |
| 0 | Not relevant |

## Pre-registered gate

Our system is judged to have won on retrieval if, against the strongest competitor:

- **Upside**: mean nDCG@7 delta > 0, *and*
- **Guard-rail**: R@7 not lower by more than 0.05, *and*
- **Floor check**: we beat `probe` + `ripgrep` on nDCG@7 by a clear margin.

## The 30 queries

### Category A — small-function / symbol discovery (10)

| # | Query | Known candidate (breadcrumb only) |
|---|---|---|
| A1 | Where is a CUDA out-of-memory error detected and classified, including OOM errors that surface as generic RuntimeErrors from third-party code like TensorRT? | `StreamDiffusion/src/streamdiffusion/wrapper.py` `_is_oom_error` |
| A2 | Where does FP8 calibration retry encoding one image at a time after a batch encode fails, so one bad image doesn't zero out the whole calibration set? | `wrapper.py` `_encode_fp8_calibration_images` |
| A3 | Where is the feedback-loop blend formula between the current input image and the previous frame's diffusion output implemented? | `preprocessing/processors/feedback.py` `FeedbackPreprocessor` |
| A4 | Where does the IPAdapter embedding preprocessor avoid re-encoding a style image through CLIP when it hasn't changed across frames? | `preprocessing/processors/ipadapter_embedding.py` `_last_input_ptr`/`_cached_embeds` |
| A5 | Where is a calibration image set's signature hashed to build a cache-key suffix for a TensorRT engine build? | `acceleration/tensorrt/engine_manager.py` `_calibration_image_signature` |
| A6 | Where is an authentication token stored using OS-native secure storage (DPAPI on Windows, Keychain on macOS)? | `Scripts/tox_updater__Text__secure_storage__td.py` `store_token` |
| A7 | Where is the TouchDesigner Script TOP pixel-format string computed from a tensor's dtype and channel count for CUDA memory copy? | `Scripts/td_exporter/TDReceiver.py` `td_format_string` |
| A8 | Where does a REST endpoint accept an uploaded ControlNet YAML configuration file and parse it? | `StreamDiffusion/demo/realtime-img2img/routes/controlnet.py` `upload_controlnet_config` |
| A9 | Where are FP8 calibration prompts loaded from a bundled text file? | `acceleration/tensorrt/fp8_quantize.py` (near `_BUNDLED_PROMPTS_PATH`) |
| A10 | Where is TF32 matmul and cuDNN benchmark mode enabled once per CUDA device when the pipeline is constructed? | `pipeline.py` `StreamDiffusion.__init__` |

### Category B — sibling / paired operations (6)

| # | Query | Known candidate (breadcrumb only) |
|---|---|---|
| B1 | Where are the Sender and Receiver engines for CUDA IPC frame export and import implemented as a matched pair? | `Scripts/td_exporter/TDSender.py`, `TDReceiver.py` |
| B2 | Where are the Windows and macOS secure-storage backends implemented as parallel platform-specific modules? | `Scripts/tox_updater__Text__secure_storage_windows__td.py`, `secure_storage_macos__td.py` |
| B3 | Which test file exercises the multi-ControlNet residual-merge logic, and which module implements the merge it's testing? | `StreamDiffusion/tests/unit/test_controlnet_residual_merge.py` vs `modules/controlnet_module.py` |
| B4 | Where are the single-frame and multi-frame variants of the img2img and txt2img example scripts? | `StreamDiffusion/examples/{img2img,txt2img}/{single,multi}.py` |
| B5 | Where do the shmem_in_cn_processed and shmem_out_out_ip TouchDesigner script sets mirror each other's callback structure? | `Scripts/shmem_in_cn_processed__*` vs `Scripts/shmem_out_out_ip__*` |
| B6 | Which test exercises FaceID LoRA fusion, and which module implements FaceID compatibility handling? | `tests/unit/test_faceid_lora_fusion.py` vs `modules/faceid_compat.py` |

### Category C — class / subsystem overview (6)

| # | Query | Known candidate (breadcrumb only) |
|---|---|---|
| C1 | What does the StreamDiffusion pipeline class's constructor configure — CFG type, LoRA dict, KV-cache, feature injection? | `pipeline.py` `class StreamDiffusion.__init__` |
| C2 | What is the architecture of the CUDA IPC extension that delegates sender and receiver work to separate engines? | `Scripts/td_exporter/CUDAIPCExtension.py` module docstring |
| C3 | What responsibilities does the StreamDiffusionTD TouchDesigner extension class own — model management, TensorRT engine building, version tracking? | `Scripts/StreamDiffusionTD__Text__StreamDiffusionExt__td.py` `class StreamDiffusionExt` |
| C4 | How is the preprocessing pipeline orchestrated across ControlNet, IPAdapter, and FaceID processors? | `preprocessing/preprocessing_orchestrator.py`, `pipeline_preprocessing_orchestrator.py` |
| C5 | What is the shared-memory protocol layout — header, slot size, magic number, version — used for TouchDesigner/CUDA IPC transport? | `Scripts/td_exporter/SHMProtocol.py` |
| C6 | What does the sd_installer CLI subsystem do end to end — install, verify, report? | `StreamDiffusion/StreamDiffusion-installer/sd_installer/*` |

### Category E — cross-file / architectural (8)

| # | Query | Known candidate (breadcrumb only) |
|---|---|---|
| E1 | How does a frame captured from a TouchDesigner TOP travel through CUDA IPC shared memory to become a texture on the receiver side? | `TDHost.py` → `CUDAIPCExtension.py` → `TDSender.py`/`TDReceiver.py` → `SHMProtocol.py` |
| E2 | How does the FP8 quantization pipeline connect calibration image loading, ONNX Q/DQ node injection, and the TensorRT engine build? | `fp8_quantize.py` → `acceleration/tensorrt/engine_manager.py`/`builder.py` |
| E3 | How does a ControlNet config uploaded through the FastAPI route reach the running diffusion pipeline's runtime state? | `routes/controlnet.py` → `demo/realtime-img2img/config.py`/`connection_manager.py` |
| E4 | How does the StreamDiffusionTD extension coordinate with model_utils to resolve a compatible ControlNet model for the currently loaded base model? | `StreamDiffusionExt__td.py` → `StreamDiffusionTD__Text__model_utils__td.py` |
| E5 | How does the token stored by secure_storage get used by the tox_updater extension to authorize a TOX update download? | `secure_storage__td.py` → `tox_updater__Text__auth_manager__td.py`/`ToxUpdaterEXT__td.py` |
| E6 | How is GPU profiling threaded through both the wrapper-level FP8 calibration path and the core pipeline's per-step timing? | `tools/gpu_profiler.py` used from `wrapper.py` and `pipeline.py` |
| E7 | How does the param_schema module's timestep-grid computation connect the wrapper's calibration index building to the pipeline's sub-timestep scheduling? | `param_schema.py` used from `wrapper.py` and `pipeline.py` |
| E8 | How does the OSC message handler in Scripts route incoming control messages to the StreamDiffusionTD extension's parameter updates? | `streamdiffusionTD__Text__td_osc_handler__td.py` → `StreamDiffusionExt__td.py` |

## Harness parity rules (reproduced from the plan, binding for every phase)

- Request top-10 from every system; drop non-`.py` rows; score the first 7 survivors.
- Identical file set for every system (see corpus doc).
- One query, one shot — no rewriting, no retries.
- Record exact command, config, latency, index build time verbatim.
- Two rounds per competitor system (not deterministic-pinned); flag any flipped query,
  don't average it away.
