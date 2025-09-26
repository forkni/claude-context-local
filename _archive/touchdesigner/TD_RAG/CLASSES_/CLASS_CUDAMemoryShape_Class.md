---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Script_TOP
- GLSL_TOP
- Render_TOP
concepts:
- cuda_memory_management
- gpu_texture_processing
- color_component_ordering
- memory_layout
- data_type_conversion
- pixel_format_specification
- gpu_computing
prerequisites:
- CUDA_basics
- GPU_fundamentals
- numpy_data_types
- texture_concepts
- advanced_gpu_programming
workflows:
- gpu_texture_processing
- cuda_memory_operations
- custom_shader_development
- gpu_data_transfer
- texture_format_conversion
- high_performance_computing
keywords:
- cuda memory
- gpu memory
- texture format
- memory shape
- numpy dtype
- color components
- pixel format
- bgra rgba
- memory layout
- cuda texture
- gpu computing
tags:
- gpu
- cuda
- memory_management
- texture_format
- numpy_integration
- color_ordering
- advanced
- high_performance
relationships:
  GLSL_Advanced_GLSL_in_Touchdesigner: strong
  GLSL_Write_a_GLSL_TOP: medium
  MODULE_td_Module: medium
related_docs:
- GLSL_Advanced_GLSL_in_Touchdesigner
- GLSL_Write_a_GLSL_TOP
- MODULE_td_Module
hierarchy:
  secondary: gpu_programming
  tertiary: cuda_memory
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- gpu_texture_processing
- cuda_memory_operations
- custom_shader_development
- gpu_data_transfer
---

# CUDAMemoryShape Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_TOP, GLSL_TOP, Render_TOP]
concepts: [cuda_memory_management, gpu_texture_processing, color_component_ordering, memory_layout, data_type_conversion, pixel_format_specification, gpu_computing]
prerequisites: [CUDA_basics, GPU_fundamentals, numpy_data_types, texture_concepts, advanced_gpu_programming]
workflows: [gpu_texture_processing, cuda_memory_operations, custom_shader_development, gpu_data_transfer, texture_format_conversion, high_performance_computing]
related: [GLSL_Advanced_GLSL_in_Touchdesigner, GLSL_Write_a_GLSL_TOP, MODULE_td_Module]
relationships: {
  "GLSL_Advanced_GLSL_in_Touchdesigner": "strong",
  "GLSL_Write_a_GLSL_TOP": "medium",
  "MODULE_td_Module": "medium"
}
hierarchy:
  primary: "hardware"
  secondary: "gpu_programming"
  tertiary: "cuda_memory"
keywords: [cuda memory, gpu memory, texture format, memory shape, numpy dtype, color components, pixel format, bgra rgba, memory layout, cuda texture, gpu computing]
tags: [gpu, cuda, memory_management, texture_format, numpy_integration, color_ordering, advanced, high_performance]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: gpu_texture_processing, cuda_memory_operations, custom_shader_development

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Cuda Basics] → [Gpu Fundamentals] → [Numpy Data Types]
**This document**: CLASS reference/guide
**Next steps**: [GLSL Advanced GLSL in Touchdesigner] → [GLSL Write a GLSL TOP] → [MODULE td Module]

**Related Topics**: gpu texture processing, cuda memory operations, custom shader development

## Summary

Technical class for managing CUDA memory shapes and texture formats. Essential for advanced GPU programming and custom texture processing workflows. Provides interface between TouchDesigner and CUDA for high-performance computing applications.

## Relationship Justification

Connected to the [GLSL_TOP](GLSL_TOP.md) and [Render_TOP](Render_TOP.md) classes for GPU programming and rendering workflows. Links to the [numpy](numpy.md) module for data type handling and the [CUDA_basics](CUDA_basics.md) class for CUDA programming fundamentals.

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [width](#width)
  - [height](#height)
  - [numComps](#numcomps)
  - [dataType](#datatype)
- [Methods](#methods)

## Introduction

Describes the shape of a CUDA memory segment.

## Members

### width

width → int:

Get/Set the width in pixels of the memory.

### height

height → int:

Get/Set the height in pixels of the memory.

### numComps

numComps → int:

Get/Set the number of color components per pixel of the memory.

### dataType

dataType → numpy.dtype:

Get/Set the data type of each color component, as a numpy data type. E.g numpy.uint8, numpy.float32.

**Note**: For uint8 data types, the channel ordering will be BGRA for 4 component textures. It will be RGBA however for other data types.

## Methods

No operator specific methods.
