---
title: "Advanced GLSL in TouchDesigner - From Pixels to Parallel Power"
category: GLSL
document_type: guide
difficulty: advanced
time_estimate: 45-60 minutes

# Enhanced metadata
user_personas: ["shader_programmer", "advanced_user", "technical_artist", "performance_engineer"]
completion_signals: ["writes_advanced_shaders", "understands_complex_gpu_programming", "can_implement_raymarching", "optimizes_gpu_performance"]

operators:
- GLSL_TOP
- GLSL_MAT
- Compute_TOP
- Particle_GPU_TOP
concepts:
- advanced_gpu_programming
- raymarching
- signed_distance_fields
- volumetric_rendering
- particle_systems
- atomic_operations
- advanced_shading_techniques
prerequisites:
- GLSL_Write_a_GLSL_TOP
- GLSL_Write_a_GLSL_Material
- GPU_programming_experience
workflows:
- advanced_visual_effects
- procedural_geometry
- complex_simulations
- performance_optimization
related_docs:
- GLSL_Write_a_GLSL_TOP
- GLSL_Write_a_GLSL_Material
- GLSL_TouchDesigner_Deferred_Lighting
hierarchy:
  secondary: shaders
  tertiary: advanced_techniques
keywords:
- advanced glsl
- raymarching
- SDF
- signed distance fields
- volumetric rendering
- particle systems
- atomic operations
- compute shaders
- advanced gpu programming
tags:
- glsl
- gpu
- advanced
- raymarching
- volumetric
- particles
- compute
- performance
- sdf
question_patterns:
- How to do raymarching in TouchDesigner?
- Advanced GLSL techniques for visual effects?
- How to create particle systems with compute shaders?
- What are signed distance fields in GLSL?
- How to use atomic operations in TouchDesigner?
common_use_cases:
- Complex procedural visual effects
- High-performance particle simulations
- Volumetric rendering and raymarching
- GPU-accelerated geometry processing
# Enhanced search optimization
search_optimization:
  primary_keywords: ["advanced", "glsl", "raymarching", "gpu"]
  semantic_clusters: ["advanced_graphics", "gpu_computing", "procedural_rendering"]
  user_intent_mapping:
    beginner: ["what is advanced glsl", "complex shader techniques", "gpu programming basics"]
    intermediate: ["raymarching techniques", "advanced shaders", "compute programming"]
    advanced: ["complex gpu algorithms", "performance optimization", "advanced rendering techniques"]

relationships:
  GLSL_Write_a_GLSL_TOP: strong
  GLSL_Write_a_GLSL_Material: strong
  GLSL_TouchDesigner_Deferred_Lighting: medium
---


# Advanced GLSL in TouchDesigner - From Pixels to Parallel Power

<!-- TD-META
category: GLSL
document_type: guide
operators: [GLSL_TOP, GLSL_MAT, Compute_TOP, Particle_GPU_TOP]
concepts: [advanced_gpu_programming, raymarching, signed_distance_fields, volumetric_rendering, particle_systems, atomic_operations, advanced_shading_techniques]
prerequisites: [GLSL_Write_a_GLSL_TOP, GLSL_Write_a_GLSL_Material, GPU_programming_experience]
workflows: [advanced_visual_effects, procedural_geometry, complex_simulations, performance_optimization]
related: [GLSL_Write_a_GLSL_TOP, GLSL_Write_a_GLSL_Material, GLSL_TouchDesigner_Deferred_Lighting]
relationships: {
  "GLSL_Write_a_GLSL_TOP": "strong",
  "GLSL_Write_a_GLSL_Material": "strong",
  "GLSL_TouchDesigner_Deferred_Lighting": "medium"
}
hierarchy:
  primary: "rendering"
  secondary: "shaders"
  tertiary: "advanced_techniques"
keywords: [advanced glsl, raymarching, SDF, signed distance fields, volumetric rendering, particle systems, atomic operations, compute shaders, advanced gpu programming]
tags: [glsl, gpu, advanced, raymarching, volumetric, particles, compute, performance, sdf]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Advanced GLSL techniques for sophisticated GPU programming in TouchDesigner
**Difficulty**: Advanced (requires prior GLSL experience)
**Time to read**: 45-60 minutes
**Use for**: Complex visual effects, particle systems, volumetric rendering, GPU optimization

**Common Questions Answered**:

- "How to implement raymarching in TouchDesigner?" → Part 3: Raymarching techniques
- "How to create advanced particle systems?" → Part 4: GPU particle systems with shared memory
- "What are signed distance fields?" → Part 3: SDF-based raymarching
- "How to use atomic operations?" → Part 4: Stream compaction techniques

## 🔗 Learning Path

**Prerequisites**: [GLSL TOP basics] → [GLSL Material basics] → GPU programming experience
**This document**: Advanced GLSL techniques and compute shaders
**Next steps**: [Performance optimization] → [Custom shader libraries]

**Related Topics**: Deferred lighting, GPU optimization, procedural generation

## 🎯 Quick Reference

**Purpose**: GLSL shader programming guide for GPU development
**Difficulty**: Advanced
**Time to read**: 45-60 minutes
**Use for**: complex procedural visual effects, high-performance particle simulations, volumetric rendering and raymarching

**Common Questions Answered**:

- "How to do raymarching in TouchDesigner?" → [See relevant section]
- "Advanced GLSL techniques for visual effects?" → [See relevant section]
- "How to create particle systems with compute shaders?" → [See relevant section]
- "What are signed distance fields in GLSL?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Write A Glsl Top] → [Glsl Write A Glsl Material] → [Gpu Programming Experience]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Write a GLSL TOP] → [GLSL Write a GLSL Material] → [GLSL TouchDesigner Deferred Lighting]

**Related Topics**: advanced visual effects, procedural geometry, complex simulations

## Summary

Advanced GLSL topics including raymarching, complex particle systems, and atomic operations. Builds on foundational GLSL knowledge to cover sophisticated GPU programming techniques.

## Relationship Justification

Builds on foundational GLSL guides and connects to deferred lighting as another advanced technique. Represents the advanced tier of GLSL knowledge.

## Content

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [Part 1: GLSL Fundamentals in TouchDesigner](#part-1-glsl-fundamentals-in-touchdesigner)
  - [What is GLSL?](#11-what-is-glsl)
  - [Why use GLSL in TouchDesigner?](#12-why-use-glsl-in-touchdesigner)
  - [Setting up your first GLSL TOP](#13-setting-up-your-first-glsl-top-pixel-shader)
  - [Coordinates and Sampling Textures](#14-coordinates-and-sampling-textures-pixel-shader)
  - [Uniforms: Passing Data from TouchDesigner](#15-uniforms-passing-data-from-touchdesigner)
  - [Basic GLSL Data Types](#16-basic-glsl-data-types)
  - [Basic Operators and Functions](#17-basic-operators-and-functions)
  - [GLSL MATs: Vertex and Pixel Shaders for 3D Objects](#18-glsl-mats-vertex-and-pixel-shaders-for-3d-objects)
- [Part 2: Introduction to Compute Shaders](#part-2-introduction-to-compute-shaders)
  - [What are Compute Shaders?](#21-what-are-compute-shaders)
  - [Setting up a Compute Shader in GLSL TOP](#22-setting-up-a-compute-shader-in-glsl-top)
  - [Workgroups and Invocations](#23-workgroups-and-invocations)
  - [Reading and Writing Data in Compute Shaders](#24-reading-and-writing-data-in-compute-shaders)
  - [First Compute Shader Example](#25-first-compute-shader-example-simple-image-processing)
  - [clearOutput and Feedback](#26-clearoutput-and-feedback-in-compute-shaders)
- [Part 3: Simulating and Visualizing 3D Textures](#part-3-simulating-and-visualizing-3d-textures)
  - [What are 3D Textures?](#31-what-are-3d-textures)
  - [Creating 3D Textures with Compute Shaders](#32-creating-3d-textures-with-compute-shaders)
  - [Visualizing 3D Textures: Raymarching](#33-visualizing-3d-textures-raymarching)
  - [Manipulating 3D Textures](#34-manipulating-3d-textures-eg-blur-feedback)
- [Part 4: Advanced Compute Shader Techniques](#part-4-advanced-compute-shader-techniques)
  - [Particle Systems with NxN Interactions & Shared Memory](#41-particle-systems-with-nxn-interactions--shared-memory)
  - [Stream Compaction with Atomic Counters](#42-stream-compaction-with-atomic-counters)
- [Part 5: Best Practices and Further Exploration](#part-5-best-practices-and-further-exploration)
  - [TouchDesigner GLSL Conventions & Helpers](#51-touchdesigner-glsl-conventions--helpers)
  - [Debugging GLSL in TouchDesigner](#52-debugging-glsl-in-touchdesigner)
  - [Performance Considerations](#53-performance-considerations)
  - [Further Exploration](#54-further-exploration-topics-from-workshop-outline)

## Introduction

**Goal:** This material aims to guide developers from the fundamentals of GLSL to leveraging its advanced capabilities, such as compute shaders for 3D texture manipulation, volumetric rendering via raymarching, and GPU-accelerated particle systems, all within the TouchDesigner environment.

## Prerequisites

- Basic familiarity with the TouchDesigner interface.
- General programming concepts are helpful. Prior GLSL knowledge is not strictly required for starting Part 1.

## Part 1: GLSL Fundamentals in TouchDesigner

This part introduces GLSL, why it's used in TouchDesigner, and how to write basic shaders for 2D image processing using the GLSL TOP.

### 1.1. What is GLSL?

- **GLSL** stands for **OpenGL Shading Language**.
- It's a high-level programming language based on C, used to create custom programs, called **shaders**, that run directly on the Graphics Processing Unit (GPU).
- GPUs are massively parallel processors, making them ideal for tasks that can be broken down into many independent operations (like processing every pixel of an image).
- Shaders are written for different **programmable stages** of the graphics pipeline. We'll initially focus on:
  - **Pixel Shaders (or Fragment Shaders):** Determine the color of each individual pixel being rendered.
  - Later, we'll explore **Vertex Shaders** (for 3D objects) and **Compute Shaders** (for general-purpose GPU computing).

### 1.2. Why use GLSL in TouchDesigner?

TouchDesigner provides a vast library of operators (TOPs, CHOPs, SOPs, MATs, etc.), but GLSL unlocks:

- **Custom Visual Effects:** Create unique looks and image processing effects not available through standard TOPs.
- **Performance:** Offload complex calculations to the GPU for real-time performance, especially for high-resolution imagery or demanding algorithms.
- **Procedural Generation:** Generate textures, patterns, and even geometry algorithmically.
- **Deeper Control:** Go beyond the limitations of pre-built operators when you need highly specific behavior.

### 1.3. Setting up your first GLSL TOP (Pixel Shader)

Let's create a simple shader that outputs a solid color.

1. **Create Operators:**
   - Right-click in your network and add a **GLSL TOP** (`TOPs -> GLSL`).
   - Add a **Text DAT** (`DATs -> Text`).
2. **Connect DAT to GLSL TOP:**
   - In the GLSL TOP's parameters, on the `GLSL` page, drag the Text DAT onto the `Pixel Shader` parameter.
3. **Write Shader Code in Text DAT:**
   Clear the default content of the Text DAT and type the following:

```glsl
// GLSL shaders in TouchDesigner don't need a #version directive here;
// TouchDesigner handles it based on the GLSL TOP's settings.
// We are writing a Pixel Shader.

// 'out vec4 fragColor;' declares the output variable for our pixel's color.
// 'vec4' means a 4-component vector (Red, Green, Blue, Alpha).
// 'layout(location = 0)' is often implicit for the first output.
layout(location = 0) out vec4 fragColor;

void main() {
    // main() is the entry point for the shader, executed for every pixel.
    vec4 color = vec4(1.0, 0.0, 0.5, 1.0); // R=1 (Red), G=0, B=0.5 (Purpleish), A=1 (Opaque)
    
    // TDOutputSwizzle is a TouchDesigner-specific function.
    // ::BEST_PRACTICE:: ALWAYS use it to ensure correct color channel
    // mapping across different texture formats and platforms.
    fragColor = TDOutputSwizzle(color);
}
```

Your GLSL TOP should now output a solid magenta-like color.

- **`TDOutputSwizzle(color)`:** This TouchDesigner function is crucial. It ensures that the RGBA channels you intend are correctly mapped to the output texture, especially with different pixel formats (e.g., monochrome textures storing alpha in the red channel).

### 1.4. Coordinates and Sampling Textures (Pixel Shader)

Shaders often need to know *which* pixel they are currently processing or read from input textures.

- **`vUV` Varying Input:**
  - When you have a GLSL TOP with only a Pixel Shader (no custom Vertex Shader), TouchDesigner provides a built-in input variable `vUV`.
  - `vUV` is a `vec3` containing texture coordinates. `vUV.st` (or `vUV.xy`) gives normalized coordinates from `(0,0)` (bottom-left) to `(1,1)` (top-right) of the texture being processed.
- **Sampling Input TOPs:**
  - Connect another TOP (e.g., a Movie File In TOP) to the first input of your GLSL TOP.
  - Input textures are accessible in GLSL as `sampler2D` (for 2D textures) through the `sTD2DInputs[]` array. `sTD2DInputs[0]` is the first input, `sTD2DInputs[1]` the second, and so on.
  - The `texture(sampler, coord)` function reads a color value from a sampler at given coordinates.

- **Example: Pass-through an input texture:**

```glsl
layout(location = 0) out vec4 fragColor;

// sTD2DInputs is an array of samplers for 2D texture inputs.
// We'll use the first input: sTD2DInputs.
// vUV is a vec3; vUV.st gives the 2D texture coordinates.
uniform sampler2D sTD2DInputs; // Declare we expect at least one 2D input

void main() {
    vec2 uv = vUV.st; // Get normalized 2D coordinates for the current pixel
    vec4 inputColor = texture(sTD2DInputs, uv); // Sample color from 1st input TOP
    
    fragColor = TDOutputSwizzle(inputColor);
}
```

This shader will simply output whatever is connected to its first input.

- **Example: Simple color manipulation based on UVs:**

```glsl
layout(location = 0) out vec4 fragColor;
// vUV is implicitly available

void main() {
    vec2 uv = vUV.st;
    // Use the u (horizontal) coordinate for Red, v (vertical) for Green.
    fragColor = TDOutputSwizzle(vec4(uv.x, uv.y, 0.5, 1.0));
}
```

This creates a gradient.

### 1.5. Uniforms: Passing Data from TouchDesigner

Uniforms are variables whose values are constant for all pixels processed in a single render pass. They are the primary way to send parameters from TouchDesigner's interface (or scripts) to your shader.

1. **Declare in GLSL:**

   ```glsl
   uniform float uTime;       // A float uniform, e.g., for animation
   uniform vec4 uTintColor;   // A vec4 for a color
   uniform int uMode;         // An integer for switching behavior
   ```

   The `u` prefix is a common naming convention for uniforms but not mandatory.
2. **Set in GLSL TOP Parameters:**
   - Go to your GLSL TOP's parameters, `Vectors 1` page (or `Vectors 2`, etc.).
   - You'll see fields for `Uniform Name`, `Value0`, `Value1`, etc.
   - For `uTime`, you might enter `uTime` as the name and use an expression like `absTime.seconds` for `Value0`.
   - For `uTintColor`, enter `uTintColor` and set the RGBA values.

- **Example: Animating a color with `uTime`:**

```glsl
layout(location = 0) out vec4 fragColor;

uniform float uTime; // Will be driven by absTime.seconds
uniform vec4 uBaseColor; // Set this on the Vectors page (e.g., R=0.2, G=0.5, B=0.8, A=1.0)

void main() {
    float sineWave = (sin(uTime) + 1.0) * 0.5; // Normalize sine to 0-1 range
    vec4 animatedColor = uBaseColor * sineWave;
    animatedColor.a = uBaseColor.a; // Keep original alpha

    fragColor = TDOutputSwizzle(animatedColor);
}
```

### 1.6. Basic GLSL Data Types

- **Scalar:**
  - `float`: Single-precision floating-point (e.g., `1.0`, `-3.14`).
  - `int`: Signed integer (e.g., `-5`, `0`, `100`).
  - `uint`: Unsigned integer (e.g., `0`, `100`).
  - `bool`: Boolean, `true` or `false`.
- **Vectors:** Collections of 2, 3, or 4 components of the same scalar type.
  - `vec2`, `vec3`, `vec4`: For floats (e.g., positions, colors, UVs).
  - `ivec2`, `ivec3`, `ivec4`: For integers.
  - `uvec2`, `uvec3`, `uvec4`: For unsigned integers.
  - `bvec2`, `bvec3`, `bvec4`: For booleans.
  - **Constructors:** `vec3 myPos = vec3(1.0, 0.0, -2.5);`
  - **Accessing Components (Swizzling):**
    - `myPos.x`, `myPos.y`, `myPos.z`
    - `myColor.r`, `myColor.g`, `myColor.b`, `myColor.a`
    - `myTexCoord.s`, `myTexCoord.t`, `myTexCoord.p` (p for 3rd tex coord)
    - You can combine and repeat: `vec2 newVec = myPos.xy;`, `vec4 weird = myColor.rgba;`, `float rVal = myColor.r;`, `vec3 rrr = myColor.rrr;`
- **Matrices:** 2x2, 3x3, 4x4 matrices of floats.
  - `mat2`, `mat3`, `mat4`.
  - Used for transformations in 3D graphics.
  - Example: `mat4 transformMatrix;`

### 1.7. Basic Operators and Functions

GLSL provides a rich set of C-like operators and built-in functions.

- **Arithmetic:** `+`, `-`, `*`, `/`, `%` (modulus for integers).
- **Relational:** `>`, `<`, `>=`, `<=`, `==`, `!=`.
- **Logical:** `&&` (AND), `||` (OR), `!` (NOT).
- **Control Flow:**
  - `if (condition) { ... } else { ... }`
- **Common Built-in Functions (operate component-wise on vectors):**
  - `sin(x)`, `cos(x)`, `tan(x)`
  - `pow(base, exp)`, `sqrt(x)`, `exp(x)` (e^x), `log(x)` (natural log)
  - `abs(x)`, `min(a,b)`, `max(a,b)`, `clamp(x, minVal, maxVal)`
  - `mix(x, y, a)`: Linear interpolation: `x*(1-a) + y*a`
  - `step(edge, x)`: `0.0` if `x < edge`, else `1.0`
  - `smoothstep(edge0, edge1, x)`: Smooth Hermite interpolation between 0 and 1.
  - `length(vec)`, `distance(p0, p1)`, `normalize(vec)`, `dot(vecA, vecB)`, `cross(vecA, vecB)` (for `vec3`).

- **Example: Creating a circular mask:**

```glsl
layout(location = 0) out vec4 fragColor;
uniform vec2 uCenter = vec2(0.5, 0.5);
uniform float uRadius = 0.3;
uniform float uSmoothness = 0.05; // For soft edges

void main() {
    vec2 uv = vUV.st;
    float dist = distance(uv, uCenter);
    
    // Hard circle:
    // float mask = (dist < uRadius) ? 1.0 : 0.0;

    // Soft circle using smoothstep:
    // Invert the distance check for smoothstep to create a filled circle
    // The range uRadius - uSmoothness to uRadius will be the soft edge
    float mask = smoothstep(uRadius, uRadius - uSmoothness, dist);

    fragColor = TDOutputSwizzle(vec4(vec3(mask), 1.0)); // Output mask as grayscale
}
```

### 1.8. GLSL MATs: Vertex and Pixel Shaders for 3D Objects

While GLSL TOPs are for 2D image processing, GLSL MATs allow you to write custom shaders for 3D objects (SOPs). A MAT typically involves two main shader programs:

- **Vertex Shader:**
  - Executed for each vertex of your 3D model.
  - Primary job: Calculate the final screen position (`gl_Position`) of the vertex.
  - Can also transform normals, texture coordinates, colors, and pass them to the pixel shader.
  - **TouchDesigner Built-ins:**
    - `P` (vec3): Input vertex position (model space).
    - `N` (vec3): Input vertex normal.
    - `Cd` (vec4): Input vertex color.
    - `uv[0]` (vec3): Input texture coordinates (uv[0].xy are common).
    - `TDDeform(vec3 p)`: Applies deformations from the MAT's Deform page.
    - `TDWorldToProj(vec4 worldSpacePos)`: Transforms world space position to clip space (for `gl_Position`).
- **Pixel (Fragment) Shader:**
  - Executed for each pixel covered by the rasterized geometry.
  - Receives interpolated values (varyings) from the vertex shader (e.g., interpolated normals, UVs, colors).
  - Determines the final color of the pixel (`fragColor`).

- **Example: Simple Vertex Displacement and Color Passthrough (GLSL MAT)**

1. Create a Sphere SOP, GLSL MAT, Text DATs for Vertex and Pixel shaders.
2. Assign the GLSL MAT to the Sphere SOP (e.g., via a Geometry COMP).
3. Connect Text DATs to the `Vertex Shader` and `Pixel Shader` parameters of the GLSL MAT.

**Vertex Shader (Text DAT 1):**

```glsl
// Vertex Shader for GLSL MAT
uniform float uTime;
uniform float uDisplaceAmount = 0.1;

// 'in' variables are attributes from the SOP
// 'out' variables (or interface blocks) pass data to the Pixel Shader

// TouchDesigner provides P, N, Cd, uv automatically
// We need to declare what we pass to the pixel shader
out vec3 vWorldPos; // Vertex position in world space
out vec3 vNormal;   // Vertex normal in world space
out vec4 vColor;    // Vertex color

void main() {
    vec3 deformedPos = P + N * sin(P.y * 10.0 + uTime) * uDisplaceAmount;
    vec4 worldSpacePos = TDDeform(deformedPos); // Apply TD Deform page
    
    vWorldPos = worldSpacePos.xyz;
    vNormal = normalize(TDDeformNorm(N)); // Transform normal & normalize
    vColor = Cd; // Pass through vertex color

    gl_Position = TDWorldToProj(worldSpacePos);
}
```

**Pixel Shader (Text DAT 2):**

```glsl
// Pixel Shader for GLSL MAT
layout(location = 0) out vec4 fragColor;

// 'in' variables receive interpolated data from the Vertex Shader
in vec3 vWorldPos;
in vec3 vNormal;
in vec4 vColor;

// Basic lighting (conceptual, not full TDLighting yet)
uniform vec3 uLightDir = normalize(vec3(0.5, 0.5, 1.0));

void main() {
    float diffuse = max(0.0, dot(vNormal, uLightDir));
    vec3 litColor = vColor.rgb * diffuse + vec3(0.1); // Add some ambient

    fragColor = TDOutputSwizzle(vec4(litColor, vColor.a));
}
```

This provides a basic introduction. The workshop dives much deeper into using GLSL MATs for raymarching with full `TDLighting` integration.

## Part 2: Introduction to Compute Shaders

This part introduces Compute Shaders, building directly on Section A of the workshop.

### 2.1. What are Compute Shaders?

- Compute Shaders are a type of GLSL program designed for **General-Purpose computing on the GPU (GPGPU)**.
- Unlike vertex or fragment shaders, they are not inherently tied to specific stages of the graphics rendering pipeline (like drawing triangles).
- They operate on a grid of "work items" or "invocations" and can read from and write to arbitrary memory locations (textures, buffers).
- **Ideal for:**
  - Complex simulations (physics, fluids).
  - Advanced image processing that doesn't fit the pixel-to-pixel model.
  - Parallel data manipulation (e.g., sorting, searching on the GPU).
  - Generating or processing 3D textures efficiently.

### 2.2. Setting up a Compute Shader in GLSL TOP

As covered in the workshop:

1. Add a **GLSL TOP**.
2. Set its `Mode` parameter (on the GLSL TOP's main page) to `Compute Shader`.
3. The GLSL Version (on the GLSL page of the GLSL TOP) must be **4.30 or higher**. TouchDesigner typically defaults to 4.60.
4. Write your compute shader code in a Text DAT and assign it to the `Compute Shader` parameter.

### 2.3. Workgroups and Invocations

This is fundamental to understanding compute shaders.

- **Dispatch:** When a compute shader runs, it's called a "dispatch."
- **Workgroups:** A dispatch is organized as a 1D, 2D, or 3D grid of **workgroups**.
- **Invocations (Threads):** Each workgroup consists of a 1D, 2D, or 3D array of **invocations**. An invocation is like a single thread of execution. All invocations within a workgroup execute the same shader code.
- **`layout(local_size_x = X, local_size_y = Y, local_size_z = Z) in;`**
  - This **input layout qualifier** at the beginning of your compute shader defines the number of invocations in *one* workgroup.
  - Example: `layout(local_size_x = 8, local_size_y = 8) in;` means each workgroup has 8x8 = 64 invocations (implicitly `local_size_z = 1`).
- **Built-in Variables:** These tell an invocation where it is:
  - `gl_WorkGroupSize` (const uvec3): The dimensions (X, Y, Z) of a single workgroup (e.g., `uvec3(8, 8, 1)`).
  - `gl_NumWorkGroups` (uvec3): The total number of workgroups in the current dispatch (set by the GLSL TOP's `Dispatch Size` parameters).
  - `gl_WorkGroupID` (uvec3): The 0-indexed (X,Y,Z) ID of the current workgroup this invocation belongs to.
  - `gl_LocalInvocationID` (uvec3): The 0-indexed (X,Y,Z) ID of this invocation *within* its workgroup. Ranges from `(0,0,0)` to `(gl_WorkGroupSize - 1)`.
  - `gl_GlobalInvocationID` (uvec3): The unique 0-indexed (X,Y,Z) ID of this invocation across the *entire dispatch*. It's calculated as:
    `gl_GlobalInvocationID = gl_WorkGroupID * gl_WorkGroupSize + gl_LocalInvocationID;`
    This is often used to determine which pixel or data element an invocation should process.
- **Dispatch Size (GLSL TOP Parameters):**
  - The `Dispatch Size X, Y, Z` parameters on the GLSL TOP specify how many workgroups to launch in each dimension (`gl_NumWorkGroups`).
  - To process every pixel of an output texture of `Width` x `Height` using workgroups of size `LSX` x `LSY`:
    - Dispatch Size X = `ceil(Width / LSX)`
    - Dispatch Size Y = `ceil(Height / LSY)`
    - (As shown in the workshop, use Math CHOPs: `me.par.resolutionw / LSX` then `ceil()`).

### 2.4. Reading and Writing Data in Compute Shaders

Compute shaders don't use `fragColor`. They read from and write to memory more generally.

- **Writing Output (`imageStore`):**
  - Outputs are typically `image2D`, `image3D`, or other `image*` types. In TouchDesigner, these are bound to the `mTDComputeOutputs[]` uniform array.
  - `imageStore(imageVariable, ivec_coord, dataToWrite);`
  - `imageVariable`: e.g., `mTDComputeOutputs[0]`.
  - `ivec_coord`: **Integer** pixel/voxel coordinates. For a 2D image, `ivec2(gl_GlobalInvocationID.xy)`.
  - `dataToWrite`: A `vec4`, `ivec4`, or `uvec4` matching the image format.
  - **Image Format Qualifiers:** When declaring image uniforms (which `mTDComputeOutputs` are, effectively), a format qualifier is often needed, e.g., `layout(rgba32f) uniform image2D outputImage;`. TouchDesigner usually manages the declaration of `mTDComputeOutputs` but understanding the underlying format is important.
- **Reading Inputs:**
  - **`texelFetch(sampler, ivec_coord, lod)`:**
    - Reads a single texel from an input `sampler` (e.g., `sTD2DInputs[0]`) at exact integer pixel coordinates `ivec_coord`.
    - `lod` is the level-of-detail (mipmap level), usually `0` for non-mipmapped inputs.
    - No interpolation. Fast for direct data lookup.
  - **`texture(sampler, vec_coord)`:**
    - Samples an input `sampler` using normalized `vec_coord` (0-1 range).
    - Applies texture filtering (linear, nearest) and wrap modes.
    - To use this, you must calculate normalized UVs from `gl_GlobalInvocationID`:

      ```glsl
      // For an input texture sTD2DInputs
      // uTD2DInfos.res.zw contains (width, height) of that input
      vec2 inputDims = uTD2DInfos.res.zw; 
      vec2 uv = (vec2(gl_GlobalInvocationID.xy) + 0.5) / inputDims;
      vec4 sampledColor = texture(sTD2DInputs, uv);
      ```

### 2.5. First Compute Shader Example: Simple Image Processing

Let's replicate a simple image inversion using a compute shader.

1. Connect a Movie File In TOP to a GLSL TOP (in Compute Shader mode).
2. Set GLSL TOP parameters:
   - `Local Size X`: 8, `Local Size Y`: 8
   - `Dispatch Size X`: `ceil(me.par.resolutionw / 8)`
   - `Dispatch Size Y`: `ceil(me.par.resolutionh / 8)`
   - (Ensure GLSL TOP `Output Resolution` is `Use Input` or set explicitly).

**Compute Shader Code (Text DAT):**

```glsl
layout (local_size_x = 8, local_size_y = 8) in; // Workgroup size

// Declare input sampler (TouchDesigner provides sTD2DInputs)
uniform sampler2D sTD2DInputs;
// Declare output image (TouchDesigner provides mTDComputeOutputs)
// Assuming rgba32f format for the output image, which TD handles
// layout(rgba32f, binding=0) uniform image2D mTDComputeOutputs; // More explicit

void main() {
    ivec2 pixelCoords = ivec2(gl_GlobalInvocationID.xy); // Integer coords for current invocation

    // Check bounds to avoid writing outside the texture (good practice)
    ivec2 outputSize = imageSize(mTDComputeOutputs); // Get output dimensions
    if (pixelCoords.x >= outputSize.x || pixelCoords.y >= outputSize.y) {
        return; // This invocation is outside the image, do nothing
    }

    vec4 color = texelFetch(sTD2DInputs, pixelCoords, 0);
    vec4 invertedColor = vec4(1.0 - color.rgb, color.a);
    
    imageStore(mTDComputeOutputs, pixelCoords, TDOutputSwizzle(invertedColor));
}
```

### 2.6. `clearOutput` and Feedback in Compute Shaders

- The GLSL TOP has a `Clear Output` toggle and a `Clear Value` parameter.
- **`Clear Output` ON (default):** The output texture(s) are cleared to `Clear Value` before each dispatch.
- **`Clear Output` OFF:** The output texture(s) retain their contents from the previous dispatch.
  - This allows for **feedback loops directly within a single compute shader**, as an invocation can read a value (e.g., using `texelFetch` from `mTDComputeOutputs[0]` if it's also an input, or by ping-ponging textures) that was written in a previous frame/dispatch.
  - **Workshop Caution:** This is powerful but requires care. If not all pixels are overwritten each frame, you'll see trails or accumulation. More complex feedback might involve reading from the output texture of the *previous frame* (which needs to be explicitly fed back in as an input). The lecture warns about potential race conditions if invocations within the *same dispatch* try to read values being written by other invocations without proper synchronization, especially across different workgroups (where `barrier()` doesn't apply).

## Part 3: Simulating and Visualizing 3D Textures

This part explores the creation, manipulation, and visualization of 3D textures, a key application of advanced GLSL in TouchDesigner, heavily leveraging compute shaders for performance and raymarching for rendering.

### 3.1. What are 3D Textures?

- Think of a standard 2D texture as a grid of pixels (Width x Height).
- A **3D Texture** is a volumetric grid of **voxels** (Volume Pixels) with dimensions Width x Height x Depth.
- Each voxel has a value (e.g., color, density, velocity vector).
- **Uses:**
  - Volumetric data representation (medical scans, scientific simulations).
  - Density fields for volumetric rendering (clouds, smoke, fog).
  - Storing 3D lookup tables (LUTs).
  - Simulation grids (e.g., 3D fluid dynamics, reaction-diffusion).

### 3.2. Creating 3D Textures with Compute Shaders

As the workshop highlights, compute shaders are significantly more efficient for generating and processing 3D textures than traditional fragment shaders (which would render slice by slice).

- **Setup in GLSL TOP:**
  1. Mode: `Compute Shader`.
  2. GLSL Version: `4.30` or higher (TD default `4.60`).
  3. **Common Page Parameters:**
     - Set `Output Resolution` to `Custom Resolution`.
     - Specify `Resolution W`, `Resolution H`.
     - Set `Output Texture` to `3D Texture`.
     - Specify `Resolution D` (for the depth).
     - Choose an appropriate `Pixel Format` (e.g., `32-bit float RGBA` for density or vector fields).
  4. **Shader `layout`:** Define a 3D workgroup size:
     `layout (local_size_x = LSX, local_size_y = LSY, local_size_z = LSZ) in;`
     (e.g., `layout (local_size_x = 4, local_size_y = 4, local_size_z = 4) in;` for 64 invocations per workgroup).
  5. **Dispatch Size Parameters:**
     - `Dispatch Size X`: `ceil(ResolutionW / LSX)`
     - `Dispatch Size Y`: `ceil(ResolutionH / LSY)`
     - `Dispatch Size Z`: `ceil(ResolutionD / LSZ)`

- **Writing to 3D Textures (`imageStore`):**
  - Output is to an `image3D` type, accessible via `mTDComputeOutputs[0]` in TouchDesigner.
  - `imageStore(mTDComputeOutputs[0], ivec3_voxelCoord, dataToWrite);`
  - `ivec3_voxelCoord`: Integer voxel coordinates, typically `ivec3(gl_GlobalInvocationID.xyz)`.

- **Example: Generating 3D Simplex Noise (from Workshop & previous guide)**

```glsl
// Compute Shader for 3D Simplex Noise
uniform vec3 uScale = vec3(1.0);
uniform float uTime = 0.0; // For 4D noise animation (animating the 3D field)
uniform float uAmplitude = 1.0;

// Define workgroup size for 3D processing
layout (local_size_x = 4, local_size_y = 4, local_size_z = 4) in;

// TDTexInfo struct (provided by TD):
// struct TDTexInfo { vec4 res; vec4 depth; };
// uTDOutputInfo.res.xy = vec2(1.0/width, 1.0/height)
// uTDOutputInfo.depth.x = 1.0/depth
// Helper to get normalized 0-1 coordinates for the center of a voxel
vec3 getNormalizedVoxelCenterPos3D(uvec3 globalID_xyz, TDTexInfo texInfo) {
    return (vec3(globalID_xyz) + 0.5) * vec3(texInfo.res.xy, texInfo.depth.x);
}

void main() {
    uvec3 voxelID = gl_GlobalInvocationID.xyz; // Current voxel this invocation is processing
    
    // Check bounds (good practice, though dispatch size should cover it)
    ivec3 outputDimensions = imageSize(mTDComputeOutputs); // Get output W, H, D
    if (voxelID.x >= outputDimensions.x || voxelID.y >= outputDimensions.y || voxelID.z >= outputDimensions.z) {
        return;
    }

    vec3 normalizedPos = getNormalizedVoxelCenterPos3D(voxelID, uTDOutputInfo);
    
    vec4 noiseDomainPos = vec4(normalizedPos * uScale, uTime);
    float density = TDSimplexNoise(noiseDomainPos) * uAmplitude; // TD built-in noise

    // Outputting density to all channels (e.g., for grayscale visualization)
    // Or just to one, e.g., vec4(density, 0.0, 0.0, 1.0) if density is just in red.
    vec4 voxelValue = vec4(density, density, density, 1.0); 
    
    // Write to the 3D image output at integer voxel coordinates
    imageStore(mTDComputeOutputs, ivec3(voxelID), TDOutputSwizzle(voxelValue));
}
```

- **Test:**
  - Set GLSL TOP to output a 3D Texture (e.g., 64x64x64, 32-bit float RGBA).
  - Use CHOPs to drive `uScale`, `uTime`, `uAmplitude`.
  - To visualize, you can use a **Texture 3D TOP** and view its slices, or proceed to raymarching.

### 3.3. Visualizing 3D Textures: Raymarching

Raymarching is a powerful technique to render volumetric data (like our 3D noise texture) or implicit surfaces. The workshop details a common method.

1. **The Concept:**
   - For each pixel on the screen, a ray is cast from the camera into the scene.
   - We are interested in where this ray intersects our 3D texture (which we can imagine as a unit cube in "texture space," where coordinates go from 0 to 1 in X, Y, and Z).
   - We "march" along the segment of the ray that is *inside* this texture space, taking small steps.
   - At each step, we sample the 3D texture to get a density value.
   - **Isosurface Rendering:** If the sampled density exceeds a certain `uThreshold`, we consider it a "hit" – we've found the surface. We then calculate its color based on lighting and normals.
   - **Volumetric Rendering (Density Accumulation):** Alternatively, we could accumulate color and opacity as we march through the volume (like rendering smoke). The workshop briefly touches on this.

2. **Setup for Ray Start/End Points (Texture Space - as in Part 2 of Workshop):**
   - **Proxy Geometry:** A Box SOP (size 1x1x1, centered at origin).
   - **Coloring for Texture Space:** In a Color SOP, set color to `($TX, $TY, $TZ) + 0.5`. This makes the Box's vertex colors represent their positions in 0-1 texture space.
   - **Render Back Faces:**
     - Render TOP (`render_back_faces`) viewing the colored Box SOP.
     - Use a Constant MAT with `Cull Face` set to `Front Faces`.
     - The output (e.g., `null_back_colors_texspace`) is a 2D texture where each pixel's color is the (X,Y,Z) texture-space coordinate of where the camera ray *exits* the back of the unit cube.
   - **Render Front Faces:**
     - Similar Render TOP (`render_front_faces`) viewing the same Box SOP.
     - Constant MAT with `Cull Face` set to `Back Faces` (or default).
     - The output (e.g., `null_front_colors_texspace`) is a 2D texture where each pixel's color is the texture-space coordinate of where the camera ray *enters* the front of the unit cube.

3. **The Raymarching Shader (GLSL MAT - as in Workshop):**
   This shader is applied to a screen-aligned quad (e.g., a Rectangle SOP scaled to fill the render view, or directly in a GLSL TOP if not using TD MAT lighting). The workshop uses a GLSL MAT for easy integration with TouchDesigner's lighting system.

   - **Inputs to the Pixel Shader:**
     - `sRayStartTex` (sampler2D): The `null_front_colors_texspace` texture.
     - `sRayStopTex` (sampler2D): The `null_back_colors_texspace` texture.
     - `sVolumeTex` (sampler3D): Our 3D density texture (e.g., the 3D noise).
     - Uniforms: `uResolution` (screen res), `uStepSize`, `uThreshold`, `uMaxSteps`, and TD lighting uniforms if using a MAT.
   - **Vertex Shader (for the GLSL MAT applied to a screen-filling quad):**
     Its main job is to pass through screen UVs (or calculate them from `gl_FragCoord` in the pixel shader) to sample `sRayStartTex` and `sRayStopTex`, and to provide necessary world-space info if integrating with TD lighting. The workshop's vertex shader for the MAT passes the front-face colors (ray start in texture space) via `oVert.color`.

**Pixel Shader Logic (Conceptual, see previous guide for full example):**

```glsl
// ... (uniforms, helper functions like calculateNormal_Volume) ...
// layout(location = 0) out vec4 oFragColor[TD_NUM_COLOR_BUFFERS]; // For MAT

void main() {
    // 1. Get Ray Start/End in Texture Space for current pixel
    vec2 screenUV = gl_FragCoord.xy / uResolution; // Or from vertex shader varying
    vec3 rayStart_texSpace = texture(sRayStartTex, screenUV).rgb; // .rgb as it stores XYZ
    vec3 rayEnd_texSpace = texture(sRayStopTex, screenUV).rgb;

    vec3 rayDir_texSpace = rayEnd_texSpace - rayStart_texSpace;
    float totalRayLength_texSpace = length(rayDir_texSpace);

    if (totalRayLength_texSpace < 0.001) { /* ... handle background ... */ return; }

    vec3 normalizedRayDir = normalize(rayDir_texSpace);
    vec3 currentRayPos_texSpace = rayStart_texSpace;
    vec4 finalColor = vec4(0.0); // Transparent black
    float hitDepthForGL = 1.0;   // Far plane

    // 2. Raymarching Loop
    for (int i = 0; i < uMaxSteps; ++i) {
        // Check if ray is still within the segment defined by start/end
        if (length(currentRayPos_texSpace - rayStart_texSpace) >= totalRayLength_texSpace) break;

        // ::BOUNDS_CHECKING:: Ensure currentRayPos_texSpace is within^3
        if (any(lessThan(currentRayPos_texSpace, vec3(0.0))) || any(greaterThan(currentRayPos_texSpace, vec3(1.0)))) break;

        // 3. Sample Density Volume
        float density = texture(sVolumeTex, currentRayPos_texSpace).r; // Assuming density in red channel

        // 4. Check for Isosurface Hit
        if (density > uThreshold) {
            // HIT!
            // a. Calculate Normal (using calculateNormal_Volume helper)
            vec3 normal_texSpace = -calculateNormal_Volume(currentRayPos_texSpace, sVolumeTex, uStepSize * 0.5);
            
            // b. Transform to World Space for Lighting (if using GLSL MAT)
            //    modelSpacePos = currentRayPos_texSpace - 0.5; (for unit cube centered at origin)
            //    worldSpacePos = (uTDMats[TDCameraIndex()].world * vec4(modelSpacePos, 1.0)).xyz;
            //    worldSpaceNorm = normalize(uTDMats[TDCameraIndex()].worldForNormals * normal_texSpace);

            // c. Apply Lighting (e.g., using TDLighting function or simple dot product)
            //    finalColor = ... calculated lit color ...
            finalColor = vec4(abs(normal_texSpace), 1.0); // Simple: visualize normals in texture space

            // d. Calculate gl_FragDepth for correct Z-ordering with other 3D objects
            //    Requires transforming hit point to clip space:
            //    vec4 clipSpacePos = uTDMats[TDCameraIndex()].camProj * worldSpacePos4;
            //    hitDepthForGL = (clipSpacePos.z / clipSpacePos.w) * 0.5 + 0.5;
            
            break; // Exit loop
        }
        // 5. Advance Ray
        currentRayPos_texSpace += normalizedRayDir * uStepSize;
    }
    
    // gl_FragDepth = hitDepthForGL; // Set depth
    oFragColor = TDOutputSwizzle(finalColor);
    // ... (handle other color buffers for MATs) ...
}
```

- **Workshop Note on `gl_FragDepth`:** Writing to `gl_FragDepth` allows the raymarched surface to correctly interact with other 3D geometry rendered by TouchDesigner via the depth buffer.
- **Workshop Note on TD Lighting:** The lecture shows integrating this with `TDLighting()` for Phong/PBR shading, requiring careful transformation of hit positions and normals into world space using `uTDMats` provided by TouchDesigner in a GLSL MAT context.

### 3.4. Manipulating 3D Textures (e.g., Blur, Feedback)

Since standard TOPs don't operate on 3D textures in TouchDesigner, you need custom GLSL (usually compute shaders) for operations like blurring, displacement, or feedback loops.

- **3D Blur (Compute Shader - Conceptual):**
  A compute shader would iterate for each output voxel (`gl_GlobalInvocationID.xyz`). For each, it would sample neighboring voxels from an input 3D texture (`sTD3DInputs[0]`) within a defined radius, average their values, and `imageStore` the result to `mTDComputeOutputs[0]`.
- **3D Feedback Systems (e.g., Reaction-Diffusion, Growth):**
  The workshop shows examples of 3D feedback processes. This typically involves:
  1. A 3D texture storing the current state (e.g., `state_t0`).
  2. A compute shader reads from `state_t0`, applies simulation rules (e.g., blur, gradient calculations, neighbor interactions, noise displacement), and writes the new state to another 3D texture (`state_t1`).
  3. In TouchDesigner, `state_t1` is then fed back as `state_t0` for the next frame using a Feedback TOP (or by ping-ponging textures if doing multiple iterations per frame within GLSL).
  4. The resulting 3D texture is visualized using raymarching.

## Part 4: Advanced Compute Shader Techniques

This section delves into more specialized compute shader features discussed in the workshop: optimizing particle systems with shared memory and using atomic counters for tasks like stream compaction.

### 4.1. Particle Systems with NxN Interactions & Shared Memory

- **The Challenge:** Simulating systems where every particle interacts with every other particle (e.g., N-body gravity, complex flocking) has a computational cost of O(N²), which becomes very slow for large N if all data is read from global GPU memory (textures) for each interaction.
- **`shared` Memory:**
  - Compute shaders allow declaration of `shared` variables. This memory is:
    - **Local to a workgroup:** Accessible by all invocations within that workgroup.
    - **Fast:** Typically on-chip, much faster than global texture/buffer memory.
    - **Limited in size:** `MAX_COMPUTE_SHARED_MEMORY_SIZE` (a GL constant).
    - **Uninitialized:** Contents are undefined at the start of workgroup execution and must be explicitly populated by the invocations.
  - Example: `shared vec3 shared_particle_data[64]; // For a workgroup of 64 invocations`
- **`barrier()` Synchronization:**
  - When invocations in a workgroup write to and then read from `shared` memory, synchronization is crucial.
  - `barrier();` acts as a synchronization point: no invocation in the workgroup can proceed past a `barrier()` until *all* invocations in that workgroup have reached it.
  - This ensures that all writes to `shared` memory are complete before any reads from it begin in a subsequent phase of the workgroup's logic.
  - **Memory Visibility:** `barrier()` synchronizes memory accesses to `shared` variables. For more complex scenarios involving other memory types (e.g., global image buffers) that need consistent ordering with shared memory operations across a barrier, an explicit `memoryBarrierShared()` or `groupMemoryBarrier()` might be needed.
- **Optimization Strategy (from Workshop):**
  1. **Load Phase:** Each invocation in a workgroup loads a subset of particle data (e.g., position, velocity) from global memory (e.g., a texture representing particle states) into a corresponding slot in a `shared` memory array.
     - `uint local_idx = gl_LocalInvocationIndex; // Flattened 0 to (TotalInvocationsInWorkgroup - 1)`
     - `uint global_particle_idx = gl_WorkGroupID.x * gl_WorkGroupSize.x * gl_WorkGroupSize.y + local_idx; // Example mapping`
     - `shared_particle_data[local_idx] = texelFetch(sParticlePosTex, ivec2(global_particle_idx % texWidth, global_particle_idx / texWidth), 0).xyz;`
  2. **Synchronize:** `barrier();`
  3. **Compute Phase:** Each invocation then iterates through all the particle data *now residing in the fast `shared` memory array* to calculate interactions (e.g., forces) with its own particle(s). This drastically reduces global memory reads.

     ```glsl
     vec3 my_force = vec3(0.0);
     vec3 my_pos = shared_particle_data[local_idx];
     for (uint i = 0; i < gl_WorkGroupSize.x * gl_WorkGroupSize.y; ++i) {
         if (i == local_idx) continue;
         vec3 other_pos = shared_particle_data[i];
         // ... calculate interaction between my_pos and other_pos, accumulate to my_force ...
     }
     ```

  4. **(Optional) Synchronize:** `barrier();` if results are written back to shared memory for another pass.
  5. **Store Phase:** Each invocation writes its computed results (e.g., updated velocity, new position) back to global memory (output textures).
     `imageStore(mNewParticlePosTex, ivec2(global_particle_idx % texWidth, global_particle_idx / texWidth), vec4(new_pos, 1.0));`
- **Workshop Performance Note:** This technique can yield significant speedups (e.g., "twice as fast" mentioned for a brute-force approach).
- **Important:** If the total number of particles (N) is larger than what can be processed by one workgroup or fit into shared memory, the overall algorithm might involve multiple dispatches or iterating through chunks of the global particle data, loading each chunk into shared memory.

### 4.2. Stream Compaction with Atomic Counters

- **Atomic Counters:**
  - Special GPU hardware feature allowing multiple shader invocations to perform thread-safe atomic operations (increment, decrement, add, etc.) on shared integer counter variables.
  - In GLSL, declared as `uniform atomic_uint uMyCounter;`.
  - In TouchDesigner, set up on the `Atomic Counters` page of the GLSL TOP. The `Binding` and `Offset` map the GLSL uniform to a physical counter. The counter itself is typically reset to 0 by TouchDesigner before the shader dispatch (or managed via CHOPs/scripts).
  - `uint index = atomicCounterIncrement(uMyCounter);`
    - This function atomically increments `uMyCounter` and returns its value *before* the increment. Each invocation calling this gets a unique, sequential index (0, 1, 2,...).
- **Use Case: Stream Compaction (Workshop Example - Emit from Active Pixels):**
  - **Goal:** Create a compact list (e.g., a new texture) containing only the "active" elements from a larger dataset (e.g., coordinates of white pixels in an image).
  - **Process:**
    1. A compute shader iterates over an input texture (e.g., `sMaskTexture`).
    2. An `atomic_uint uActivePixelCounter` is used.
    3. For each input pixel `gId = gl_GlobalInvocationID.xy`:
       - Read the mask value: `float mask_val = texelFetch(sMaskTexture, ivec2(gId), 0).r;`
       - If `mask_val > 0.5` (pixel is "active"):
         - `uint compact_idx = atomicCounterIncrement(uActivePixelCounter);` Get a unique index for this active pixel.
         - Calculate a 2D `writeLocation` in an output texture (`mCompactedDataTex`) based on `compact_idx` (e.g., `ivec2(compact_idx % outWidth, compact_idx / outWidth)`).
         - Store the original coordinate `gId` (or other data) of the active pixel into `mCompactedDataTex` at `writeLocation`:
           `imageStore(mCompactedDataTex, writeLocation, TDOutputSwizzle(vec4(vec2(gId), 0.0, 1.0)));`
- **Code Example (Stream Compaction - from previous guide, annotated):**

  ```glsl
  // Compute Shader for Stream Compaction
  // On GLSL TOP: Setup uCount on Atomic Counters page (e.g., Binding 0, Offset 0)
  // Ensure it's reset to 0 before dispatch if needed (e.g., via a Script CHOP).
  layout(binding = 0, offset = 0) uniform atomic_uint uCount; 
   
  layout (local_size_x = 8, local_size_y = 8) in;

  uniform sampler2D sInputMask; // Input texture to filter
  // Output texture for compacted data (e.g., coordinates)
  // layout(rg32f, binding = 0) uniform image2D mCompactedCoords; // Example explicit output
  // Output texture for debugging the counter value (optional)
  // layout(r32ui, binding = 1) uniform uimage2D mCounterDebug;

  void main() {
      ivec2 gId = ivec2(gl_GlobalInvocationID.xy); // Current input pixel coord

      ivec2 inputSize = textureSize(sInputMask, 0);
      if (gId.x >= inputSize.x || gId.y >= inputSize.y) return; // Bounds check for input

      float val = texelFetch(sInputMask, gId, 0).r; // Read from mask (e.g., red channel)
      
      if (val > 0.1) { // Condition for "active" pixel
          uint write_index = atomicCounterIncrement(uCount); 
      
          // Determine where to write in the output compacted texture
          ivec2 outputSize = imageSize(mTDComputeOutputs);
          int texWidth = outputSize.x;
          
          ivec2 writeLoc = ivec2(write_index % uint(texWidth), write_index / uint(texWidth));
          
          // Check bounds for output (important if max count could exceed output texture size)
          if (writeLoc.y < outputSize.y) {
               // Store original coordinate (gId) of the active pixel
              imageStore(mTDComputeOutputs, writeLoc, TDOutputSwizzle(vec4(float(gId.x), float(gId.y), 0.0, 1.0)));
          }
      }
      
      // Optional: Store the raw counter value for debugging total count
      // if (uTDNumComputeOutputs > 1) {
      //     uint current_total = atomicCounter(uCount); // Read current total (less reliable for *the* total)
      //     imageStore(mTDComputeOutputs, gId, uvec4(current_total,0,0,1));
      // }
  }
  ```

- **Using the Compacted Data & Count (Workshop Practicality):**
  - The `mTDComputeOutputs[0]` (or `mCompactedCoords`) now contains a dense list of active pixel coordinates.
  - To get the total number of active pixels written:
    1. The workshop mentions a technique: write the `write_index` itself to a *second* output image (`mTDComputeOutputs[1]`) for every *input* pixel.
    2. Then, use an Analyze TOP (Mode: Maximum) on this second output. The maximum value found will be `total_active_pixels - 1`.
    3. A TOP to CHOP on the Analyze TOP gives this count.
  - This count is then used in TouchDesigner to, for example, set the number of instances for a Geometry COMP that will use the compacted coordinate data for instancing.

## Part 5: Best Practices and Further Exploration

### 5.1. TouchDesigner GLSL Conventions & Helpers

- **`TDOutputSwizzle(vec4)`:** Always use when writing final colors (`fragColor` or via `imageStore`) to ensure correct channel mapping.
- **Built-in Uniforms:**
  - `sTD2DInputs[]`, `sTD3DInputs[]`, etc.: Sampler arrays for texture inputs.
  - `mTDComputeOutputs[]`: Image array for compute shader outputs.
  - `uTDOutputInfo` (TDTexInfo struct): Contains resolution (`.res.xy` = 1/w, 1/h; `.res.zw` = w,h) and depth info (`.depth.x` = 1/d, `.depth.y` = d) for the *output* texture of the GLSL TOP/MAT.
  - `uTD2DInfos[]`, `uTD3DInfos[]`: Arrays of TDTexInfo for *input* textures.
  - `uTDMats[cameraIndex]`: In GLSL MATs, provides matrices (`.world`, `.camProj`, `.worldForNormals`, `.camInverse`).
  - `uTDGeneral.ambientColor`: Scene ambient color in MATs.
- **Built-in Functions:**
  - `TDSimplexNoise(vecN)`, `TDPerlinNoise(vecN)`.
  - `TDDeform(P)`, `TDDeformNorm(N)` (in MAT vertex shaders).
  - `TDWorldToProj(worldPos)` (in MAT vertex shaders).
  - `TDLighting(...)` (in MAT pixel shaders for Phong/PBR).
  - `TDHSVToRGB()`, `TDRGBToHSV()`.
  - `TDDither(color)`.
- **Naming Conventions:**
  - `uUniformName`: Common for user uniforms.
  - `sSamplerName`: Common for samplers.
  - `vVaryingName`: Common for varyings passed from vertex to pixel shader.

### 5.2. Debugging GLSL in TouchDesigner

- **Info DAT/TOP:** Connect an Info DAT or Info TOP to your GLSL TOP/MAT. It will display compile errors and warnings. This is your first stop for debugging.
- **Output Intermediate Values:** If a shader is complex, output intermediate calculations as colors to debug. For example, `fragColor = TDOutputSwizzle(vec4(myVariable, 0.0, 0.0, 1.0));` to see the value of `myVariable` in the red channel.
- **Simplify:** Comment out sections of your shader to isolate where a problem might be.
- **Print to Textport (from Python):** While not direct GLSL debugging, you can use Python in Parameter Execute DATs to print uniform values being sent to the shader.
- **Save Frequently!** Especially with loops (raymarching) or complex compute shaders, an error can sometimes hang the GPU or TouchDesigner.

### 5.3. Performance Considerations

- **Compute Shaders for Bulk Data:** Use compute shaders for tasks that process large amounts of data in parallel (e.g., full texture processing, 3D texture generation, large particle systems).
- **`texelFetch` vs. `texture`:**
  - `texelFetch`: Integer coordinates, no interpolation, direct texel read. Faster if you don't need filtering.
  - `texture`: Normalized coordinates, uses filtering. Good for visual quality, but more computation.
- **Shared Memory:** Use for compute shader algorithms with data reuse within a workgroup (like the N-body particle example).
- **Minimize Loops / Divergence:**
  - In raymarching, `uMaxSteps` is a direct performance factor.
  - Conditional statements (`if`) within a workgroup can cause "divergence" if different invocations take different paths, potentially reducing parallelism.
- **Data Types and Precision:**
  - Using smaller data types (e.g., `mediump` or `lowp` precision qualifiers if appropriate, though GLSL 4.60 desktop often defaults to `highp`) can sometimes improve performance, but ensure it doesn't sacrifice necessary accuracy. TouchDesigner's GLSL TOPs/MATs often manage precision based on texture formats.
- **Texture Read/Write Patterns:** Cache coherency and memory bandwidth can be factors. Try to optimize for localized reads/writes where possible.

### 5.4. Further Exploration (Topics from Workshop Outline)

- **Integrating TD Lights, Materials, and Geometry (GLSL MAT):** The workshop showed how to use `TDLighting` and transform coordinates to make raymarched isosurfaces fit seamlessly into a standard TouchDesigner 3D scene.
- **2D History Visualization / 3D Growth Simulation:** These involve feedback loops where the output of a GLSL process from one frame becomes an input for the next, often using 3D textures as the state buffer.
- **Advanced Raymarching:**
  - Different step determination methods (e.g., sphere tracing for signed distance fields - SDFs).
  - Volumetric rendering (accumulating density and color).
  - Shadows and ambient occlusion for raymarched scenes.
- **More Complex Particle Logic:** Collision detection, flocking behaviors, vector fields for particle movement, all implemented in compute shaders.
- **Advanced Atomic Operations:** Beyond counters, GLSL supports atomic operations on buffer/shared memory (`atomicAdd`, `atomicMin`, `atomicExchange`, `atomicCompSwap`), useful for complex parallel algorithms.

## See Also

- [CLASS_glslTOP_Class] for TouchDesigner GLSL TOP documentation
- [CLASS_glslMAT_Class] for TouchDesigner GLSL MAT documentation
- [GLSL Language Specification](https://www.khronos.org/registry/OpenGL/specs/gl/GLSLangSpec.4.60.pdf) for detailed GLSL syntax and features
- [OpenGL Shading Language (GLSL) Wiki](https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language) for community resources and examples
