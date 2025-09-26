---
title: "Write a CPlusPlus TOP"
category: "REF_"
document_type: "guide"
difficulty: "advanced"
time_estimate: "5 minutes"
user_personas: ["c++_developer", "plugin_developer", "gpu_programmer"]
completion_signals: ["understands_top_plugin_specifics"]
operators: ["CPlusPlusTOP"]
concepts: ["c++", "plugin", "top", "cuda", "texture"]
prerequisites: ["REF_Write_a_CPlusPlus_Plugin"]
workflows: ["custom_top_development", "gpu_accelerated_processing"]
keywords: ["c++", "plugin", "top", "texture", "cuda"]
tags: ["c++", "sdk", "plugin", "development", "advanced", "top"]
related_docs:
- "REF_WriteACPlusPlusPlugin"
- "REF_WriteACPlusPlusCHOP"
- "REF_CPlusPlusTOPUpgrades"
- "TOP_CPlusPlusTOP"
- "CHOP_CPlusPlusCHOP"
---

# Write a CPlusPlus TOP

## Content
- [Overview](#overview)
- [CUDA](#cuda)
- [See Also](#see-also)

## Overview

Make sure you've read through [REF_WriteACPlusPlusPlugin] first for general information about writing a plugin for a `CPlusPlus TOP`.

The `CPlusPlus TOP` allows you to write C++ code to create a [TOP] that can output multiple textures. Currently you can create your output by filling a CPU memory buffer (`TOP_ExecuteMode::CPUMem`) or by filling a cudaArray buffer (`TOP_ExecuteMode::CUDA`).

Most of the documentation is held in the header files for the C++ API. The samples also contain a lot of comments about the workflow.

For upgrading your `CPlusPlus TOP` compiled using headers from TouchDesigner builds before and including 2021.10000 to work in builds 2022.20000 and after, refer to [REF_CPlusPlusTOPUpgrades].

## CUDA

The `CPlusPlus TOP` can be used with CUDA. See the `CudaTOP` example project included with the TouchDesigner installation for an example. Note that any CUDA operations that occur in your C++ code must occur on the main thread, between calls to `OP_Context::beginCUDAOperations()` and `OP_Context::endCUDAOperations()`.

## See Also

- [REF_WriteACPlusPlusPlugin]
- [REF_WriteACPlusPlusCHOP]
- [REF_CPlusPlusTOPUpgrades]
- [TOP_CPlusPlusTOP]
- [CHOP_CPlusPlusCHOP]
