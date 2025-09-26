---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Script_TOP
- Render_TOP
- GLSL_TOP
concepts:
- cuda_interoperability
- gpu_memory_management
- raw_data_access
- texture_processing
- high_performance_computing
- memory_pointers
prerequisites:
- Python_fundamentals
- TOP_basics
- CUDA_programming_concepts
- advanced_gpu_programming
workflows:
- gpu_accelerated_computing
- custom_glsl_operations
- real_time_data_processing
- external_library_integration
- cuda_texture_processing
- high_performance_computing
keywords:
- cuda memory
- gpu memory
- raw pointer
- memory address
- cuda interop
- gpu data
- texture to cuda
- cuda buffer
- memory management
- high performance computing
tags:
- gpu
- cuda
- memory_management
- pointer
- real_time
- python
- api
- high_performance
- advanced
- interoperability
relationships:
  CLASS_CUDAMemoryShape_Class: strong
  CLASS_renderTOP_Class: strong
  GLSL_Write_a_GLSL_TOP: medium
  MODULE_td_Module: medium
related_docs:
- CLASS_CUDAMemoryShape_Class
- CLASS_renderTOP_Class
- GLSL_Write_a_GLSL_TOP
- MODULE_td_Module
hierarchy:
  secondary: gpu_computing
  tertiary: cuda_memory_management
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- gpu_accelerated_computing
- custom_glsl_operations
- real_time_data_processing
- external_library_integration
---

# CUDAMemory Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_TOP, Render_TOP, GLSL_TOP]
concepts: [cuda_interoperability, gpu_memory_management, raw_data_access, texture_processing, high_performance_computing, memory_pointers]
prerequisites: [Python_fundamentals, TOP_basics, CUDA_programming_concepts, advanced_gpu_programming]
workflows: [gpu_accelerated_computing, custom_glsl_operations, real_time_data_processing, external_library_integration, cuda_texture_processing, high_performance_computing]
related: [CLASS_CUDAMemoryShape_Class, CLASS_renderTOP_Class, GLSL_Write_a_GLSL_TOP, MODULE_td_Module]
relationships: {
  "CLASS_CUDAMemoryShape_Class": "strong",
  "CLASS_renderTOP_Class": "strong",
  "GLSL_Write_a_GLSL_TOP": "medium",
  "MODULE_td_Module": "medium"
}
hierarchy:
  primary: "hardware"
  secondary: "gpu_computing"
  tertiary: "cuda_memory_management"
keywords: [cuda memory, gpu memory, raw pointer, memory address, cuda interop, gpu data, texture to cuda, cuda buffer, memory management, high performance computing]
tags: [gpu, cuda, memory_management, pointer, real_time, python, api, high_performance, advanced, interoperability]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: gpu_accelerated_computing, custom_glsl_operations, real_time_data_processing

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Top Basics] → [Cuda Programming Concepts]
**This document**: CLASS reference/guide
**Next steps**: [CLASS CUDAMemoryShape Class] → [CLASS renderTOP Class] → [GLSL Write a GLSL TOP]

**Related Topics**: gpu accelerated computing, custom glsl operations, real time data processing

## Summary

Low-level class for CUDA memory management and GPU interoperability. Essential for advanced GPU computing workflows and custom texture processing operations.

## Relationship Justification

Strong bidirectional connection to CUDAMemoryShape_Class as they work together for memory operations. Connected to renderTOP_Class since many CUDA operations involve render targets. Links to GLSL TOP guide and td module for complete GPU programming workflows.

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [ptr](#ptr)
  - [size](#size)
  - [shape](#shape)
- [Methods](#methods)

## Introduction

Holds a reference to CUDA memory. The CUDA memory will be deallocated when this class is destructed.

## Members

### ptr

ptr → int (Read Only):

Returns the raw memory pointer address for the CUDA memory.

### size

size → int (Read Only):

Returns the size of the CUDA Memory, in bytes.

### shape

shape → [CLASS_CUDAMemoryShape] (Read Only):

Returns the [CLASS_CUDAMemoryShape] describing this CUDA memory. See the help for that class for notes about channel order for different data types.

## Methods

No operator specific methods.
