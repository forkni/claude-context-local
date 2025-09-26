---
category: GLSL
document_type: guide
difficulty: intermediate
time_estimate: 20-30 minutes
operators:
- GLSL_TOP
- GLSL_MAT
concepts:
- texture_sampling
- texel_access
- texture_functions
- pixel_perfect_sampling
- texture_coordinates
- sampling_methods
- filtering_differences
- coordinate_systems
prerequisites:
- GLSL_fundamentals
- texture_concepts
- GLSL_Built_In_Functions_Reference
workflows:
- texture_processing
- pixel_perfect_operations
- image_analysis
- advanced_texture_techniques
- compute_shader_texture_access
- data_processing
keywords:
- texelFetch vs texture
- texture sampling
- pixel coordinates
- normalized coordinates
- texture access
- sampling differences
- pixel perfect
- filtering
- interpolation
- wrapping
- coordinate systems
- texel access
- mipmap levels
tags:
- glsl
- texture
- sampling
- texelFetch
- guide
- comparison
- techniques
- pixel_perfect
- filtering
relationships:
  GLSL_Built_In_Functions_Reference: strong
  GLSL_Compute_Shader_Reference: medium
  CLASS_glslTOP_Class: medium
related_docs:
- GLSL_Built_In_Functions_Reference
- GLSL_Compute_Shader_Reference
- CLASS_glslTOP_Class
hierarchy:
  secondary: texture_techniques
  tertiary: sampling_comparison
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- texture_processing
- pixel_perfect_operations
- image_analysis
- advanced_texture_techniques
---

# TexelFetch() vs texture() in GLSL

<!-- TD-META
category: GLSL
document_type: guide
operators: [GLSL_TOP, GLSL_MAT]
concepts: [texture_sampling, texel_access, texture_functions, pixel_perfect_sampling, texture_coordinates, sampling_methods, filtering_differences, coordinate_systems]
prerequisites: [GLSL_fundamentals, texture_concepts, GLSL_Built_In_Functions_Reference]
workflows: [texture_processing, pixel_perfect_operations, image_analysis, advanced_texture_techniques, compute_shader_texture_access, data_processing]
related: [GLSL_Built_In_Functions_Reference, GLSL_Compute_Shader_Reference, CLASS_glslTOP_Class]
relationships: {
  "GLSL_Built_In_Functions_Reference": "strong",
  "GLSL_Compute_Shader_Reference": "medium",
  "CLASS_glslTOP_Class": "medium"
}
hierarchy:
  primary: "shader_programming"
  secondary: "texture_techniques"
  tertiary: "sampling_comparison"
keywords: [texelFetch vs texture, texture sampling, pixel coordinates, normalized coordinates, texture access, sampling differences, pixel perfect, filtering, interpolation, wrapping, coordinate systems, texel access, mipmap levels]
tags: [glsl, texture, sampling, texelFetch, guide, comparison, techniques, pixel_perfect, filtering]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming guide for GPU development
**Difficulty**: Intermediate
**Time to read**: 20-30 minutes
**Use for**: texture_processing, pixel_perfect_operations, image_analysis

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Fundamentals] → [Texture Concepts] → [Glsl Built In Functions Reference]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Built In Functions Reference] → [GLSL Compute Shader Reference] → [CLASS glslTOP Class]

**Related Topics**: texture processing, pixel perfect operations, image analysis

## Summary

Technical guide comparing texelFetch() and texture() functions in GLSL, explaining coordinate systems, filtering differences, and appropriate use cases for each sampling method. Essential for optimal texture access patterns.

## Relationship Justification

Core texture technique that builds on built-in functions reference. Important for compute shader workflows where precise texel access is often required. Practical application through GLSL TOP development.

## Content

- [Introduction](#introduction)
- [The texture() Function](#the-texture-function)
  - [Characteristics](#characteristics)
  - [Usage Example](#usage-example)
- [The texelFetch() Function](#the-texelfetch-function)
  - [Key Differences](#key-differences)
  - [Usage Example](#usage-example-1)
- [Comparison: texture() vs texelFetch()](#comparison-texture-vs-texelfetch)
  - [Coordinate Systems](#coordinate-systems)
  - [Filtering and Interpolation](#filtering-and-interpolation)
  - [Use Cases](#use-cases)
- [When to Use Each Function](#when-to-use-each-function)
- [Conclusion](#conclusion)

## Introduction

Texturing in GLSL can be performed in different ways. This article explores the differences between the `texelFetch()` and `texture()` functions in GLSL (OpenGL Shading Language).

GLSL is one of the most powerful tools for visual development. It is a C-style language that performs high-level operations on shaders - functions that calculate position and color of pixels. In TouchDesigner, we can leverage GLSL through the dedicated [CLASS_GLSLTOP] operator.

## The texture() Function

### Characteristics

`texture()` is the most commonly used function for texturing in GLSL. It allows us to handle filtered and normalized textures in the 0-1 domain.

Key features of `texture()`:

- Works with normalized floating point texture coordinates between 0 and 1
- Coordinates range from left to bottom and right to top
- Can perform wrapping - coordinates can exceed the 0-1 range
- Performs filtering and interpolation
- Infinitely interpolating

### Usage Example

The `texture()` function requires two arguments: the texture (sampler2D) and the UV coordinate to sample.

```glsl
in vec2 TexCoords; //uv coordinates
out vec4 FragColor;
uniform sampler2D myTexture; //the texture

void main() {
    vec4 texColor = texture(myTexture, TexCoords);
    FragColor = texColor;
}
```

`texture()` is the traditional approach to texturing in GLSL. However, sometimes we need to perform operations in the integer domain, which is where `texelFetch()` becomes useful.

## The texelFetch() Function

### Key Differences

`texelFetch()` has several important differences from `texture()`:

- Accesses a texel (texture element) directly
- Does not perform filtering or wrapping
- Works with non-normalized coordinates
- Operates in texture integer coordinates rather than the 0-1 domain

### Usage Example

For example, to access a texel in the middle of a 512×512 texture:

- `texture()` coordinates: (0.5, 0.5)
- `texelFetch()` coordinates: (256, 256)

The `texelFetch()` function takes three arguments:

1. The texture (sampler2D)
2. The UV coordinate in integer pixels
3. The LOD (Level of Detail) - the mipmap level (use 0 for original size)

```glsl
in vec2 TexCoords; //uv coordinates
out vec4 FragColor;
uniform sampler2D myTexture; //the texture
uniform ivec2 textureSize; //the texture size

void main() {
    ivec2 texelCoord = ivec2(TexCoords * vec2(textureSize)); //convert uv coordinates to integer pixels
    vec4 texColor = texelFetch(myTexture, texelCoord, 0);
    FragColor = texColor;
}
```

## Comparison: texture() vs texelFetch()

### Coordinate Systems

| Function | Coordinate System | Range |
|----------|-------------------|-------|
| `texture()` | Normalized floating point | 0.0 to 1.0 |
| `texelFetch()` | Integer pixels | 0 to texture size |

### Filtering and Interpolation

| Function | Filtering | Interpolation | Wrapping |
|----------|-----------|---------------|----------|
| `texture()` | Yes | Yes | Yes |
| `texelFetch()` | No | No | No |

### Use Cases

**Use `texture()` when:**

- Working with normalized UV coordinates
- Filtering and interpolation are desired
- Wrapping behavior is needed
- Working with mipmaps

**Use `texelFetch()` when:**

- Precise texel access is required
- No interpolation is wanted
- Working with integer pixel coordinates
- Implementing algorithms that require exact pixel values

## When to Use Each Function

`texelFetch()` is particularly advantageous in several scenarios:

- **Precise Texel Access**: When you need to access a specific texel or array of texels without interpolation
- **No Mipmaps**: When you don't need mipmaps and want to access the texture layer without changes
- **Advanced Techniques**: When working with techniques that require access to specific pixels, such as:
  - Path tracing
  - Advanced simulations
  - Data processing applications
  - Computer vision algorithms

## Conclusion

Texturing is the foundation of working with GLSL in TouchDesigner. Understanding the differences between `texture()` and `texelFetch()` is crucial for maximizing project efficiency. Each function serves different purposes:

- `texture()` provides the traditional, interpolated approach suitable for most rendering scenarios
- `texelFetch()` offers precise, unfiltered access ideal for computational and data-processing tasks

By choosing the appropriate function for your specific needs, you can optimize both performance and visual quality in your [CLASS_GLSLTOP] implementations.
