---
title: "CUDA"
category: "REF_"
document_type: "reference"
difficulty: "intermediate"
time_estimate: "5 minutes"
user_personas: ["gpu_programmer", "c++_developer", "plugin_developer"]
completion_signals: ["knows_which_cuda_version_to_use"]
operators: ["CPlusPlusTOP"]
concepts: ["cuda", "gpu", "c++", "plugin"]
prerequisites: []
workflows: ["gpu_computing"]
keywords: ["cuda", "gpu", "nvidia", "version"]
tags: ["gpu", "cuda", "development", "reference"]
related_docs:
- "REF_WriteACUDADLL"
- "TOP_CUDATOP"
---

# CUDA

## Content
- [Overview](#overview)
- [CUDA Versions](#cuda-versions)
- [See Also](#see-also)

## Overview

CUDA is a programming language developed by NVIDIA to allow developers to exploit the power of GPUs for more general uses than only for graphics.

Writing CUDA code in TouchDesigner has many benefits, chief among them being the reduced amount of coding that needs to be done. For example, the typical procedure to port an existing CUDA application to run within TouchDesigner involves simply deleting all the code needed to initialize a window, allocate OpenGL resources and display the results in OpenGL.

Integrating CUDA code in TouchDesigner is done through the `CPlusPlus TOP`.

## CUDA Versions

CUDA versions for each TouchDesigner release:

- **2025.30000 series:** CUDA 12.8.0
- **2023.10000 series:** CUDA 11.8.0
- **2022.20000 series:** CUDA 11.8.0
- **2021.30000 series:** CUDA 11.2.0
- **2021.10000 series:** CUDA 11.2.0
- **2020.40000 series:** CUDA 10.1
- **2020.20000 series:** CUDA 10.0.130
- **2019.30000 series:** CUDA 10.1
- **2019.10000 series:** CUDA 9.2
- **2018.20000 series:** CUDA 8.0

## See Also

- [NVIDIA CUDA Homepage](https://developer.nvidia.com/cuda-zone)
- [REF_WriteACUDADLL]
- [TOP_CUDATOP]
