---
title: "Write a CUDA DLL"
category: "REF_"
document_type: "guide"
difficulty: "advanced"
time_estimate: "5 minutes"
user_personas: ["c++_developer", "gpu_programmer", "plugin_developer"]
completion_signals: ["understands_how_to_approach_cuda_in_td"]
operators: ["CPlusPlusTOP"]
concepts: ["cuda", "c++", "gpu", "dll", "plugin"]
prerequisites: ["c++_programming"]
workflows: ["gpu_computing", "high_performance_computing"]
keywords: ["cuda", "dll", "gpu", "c++", "nvidia"]
tags: ["c++", "sdk", "plugin", "development", "advanced", "gpu", "cuda"]
related_docs:
- "REF_WriteACPlusPlusTOP"
---

# Write a CUDA DLL

## Content
- [Overview](#overview)

## Overview

CUDA is a programming language developed by NVIDIA to allow developers to use the power of GPUs in a way much more general than using them only for graphics. More details about CUDA can be found at the CUDA Homepage.

Using TouchDesigner as a tool to program CUDA has many benefits. It allows you to use all the tools TouchDesigner already has to create, load, manipulate, save and visualize data that you are passing to and sending out of your CUDA program. For example if you want to write a CUDA program that does something with audio data, instead of having to write your own code that loads audio using an external API, you can simply load the audio into a [CHOP], and pass that data into the CUDA program. Similarly instead of having to write your own OpenGL code to visualize the output of a CUDA program, it can be visualized using the tools TouchDesigner already has.

If you are interested in programming CUDA, a good starting place is the CUDA Programming Guide included in the CUDA SDK.

> **Important:** The official 2020.20000 series release of TouchDesigner currently uses version 10.0 of the CUDA toolkit, make sure you download that version, even if a newer one is available. See here for CUDA versions supported by different releases of TouchDesigner.

CUDA is now fully supported using the `CPlusPlus TOP`. The `CUDA TOP` is no longer supported. For more information see the articles in [CATEGORY_CPlusPlus].
