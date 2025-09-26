---
title: "Compute Shader Introduction - GPU Parallel Processing Fundamentals"
description: "Introduction to GPU compute shaders and parallel processing concepts in TouchDesigner with working examples"
category: GLSL
difficulty: intermediate
concepts: ["compute_shaders", "work_groups", "global_invocation_id", "texture_sampling", "parallel_processing", "coordinate_systems"]
operators: ["glslTOP", "textDAT", "infoDAT", "moviefileinTOP", "mathCHOP"]
user_personas: ["shader_programmer", "technical_artist", "gpu_developer"]
techniques: ["basic_compute_patterns", "coordinate_visualization", "texture_processing", "performance_optimization"]
masterclass: true
source: "TouchDesigner Advanced GLSL Masterclass 2019"
---

# COMPUTE_INTRO - GPU Parallel Processing Fundamentals Reference

## Module Overview

**Educational Objective**: Introduction to GPU compute shaders and parallel processing concepts in TouchDesigner  
**Skill Level**: Beginner to Intermediate  
**Key Concepts**: Work groups, global/local invocation IDs, texture sampling vs compute processing  
**TouchDesigner Integration**: Basic GLSL_TOP usage, compute vs pixel shader comparison  

## Network Architecture Analysis

**Total Operators**: 21 operators in optimized, lightweight network  
**Performance Profile**: 0.000ms active cost (inactive when not processing)  
**Potential Cost**: 69.967ms (4 active nodes when processing)  

### Key Network Components

```
compute_intro [baseCOMP]
├── glsl1 [glslTOP] - Basic compute shader introduction
│   ├── glsl1_compute [textDAT] - First compute shader example  
│   ├── glsl1_pixel [textDAT] - Companion pixel shader
│   └── glsl1_info [infoDAT] - GLSL operator configuration
├── glsl2 [glslTOP] - Coordinate visualization compute shader
│   ├── glsl2_compute [textDAT] - Clean compute pattern
│   ├── glsl2_pixel [textDAT] - Fragment coordinate visualization
│   └── glsl2_info [infoDAT] - Configuration data
├── glsl3 [glslTOP] - Pure compute shader example  
│   ├── glsl3_compute [textDAT] - Compute coordinate visualization
│   └── glsl3_info [infoDAT] - Configuration data
├── moviefilein1 [moviefileinTOP] - Input data source
├── math1 [mathCHOP] - Parameter control
└── Data flow: moviefilein1 → glsl1, constants → math1
```

### Performance Characteristics

- **Network Efficiency**: Designed for learning, not performance
- **Memory Usage**: Minimal - basic texture operations only
- **GPU Load**: Light compute operations suitable for real-time learning

## GLSL Techniques Deep Dive

### 1. Basic Compute Shader (glsl1_compute)

**Purpose**: Introduction to compute shader fundamentals

```glsl
// Essential compute shader structure
layout (local_size_x = 8, local_size_y = 8) in;
void main()
{
    // Get thread position
    vec2 uv = gl_GlobalInvocationID.xy*uTDOutputInfo.res.xy;
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Sample input texture
    vec4 color = texelFetch(sTD2DInputs[0], gId, 0);
    
    // Write to output with offset
    imageStore(mTDComputeOutputs[0], 
               ivec2(gl_GlobalInvocationID.xy)+ivec2(100), 
               TDOutputSwizzle(color));
}
```

**Key Concepts Demonstrated**:

- **Work Group Size**: 8×8 = 64 threads per work group
- **Global Invocation ID**: Thread's unique position in entire compute dispatch
- **Texture Sampling**: `texelFetch()` for precise pixel access vs `texture()` for normalized UVs
- **Image Store**: Writing to compute output buffers
- **Coordinate Offset**: Demonstrates coordinate manipulation (+100 pixel shift)

**Educational Value**: Shows fundamental compute shader structure and coordinate systems

### 2. Clean Compute Pattern (glsl2_compute)

**Purpose**: Simplified compute shader pattern without complexity

```glsl
layout (local_size_x = 8, local_size_y = 8) in;
void main()
{
    vec4 color = vec4(1.0);  // White output
    imageStore(mTDComputeOutputs[0], 
               ivec2(gl_GlobalInvocationID.xy), 
               TDOutputSwizzle(color));
}
```

**Key Concepts**:

- **Direct 1:1 Mapping**: No coordinate transformation
- **Simplified Pattern**: Focus on core compute shader structure
- **TouchDesigner Integration**: Proper use of `TDOutputSwizzle()`

### 3. Coordinate Visualization Shaders

#### Pixel Shader Approach (glsl2_pixel)

```glsl
out vec4 fragColor;
void main()
{
    vec4 color = vec4(gl_FragCoord.xy,0,1);
    fragColor = TDOutputSwizzle(color);
}
```

#### Compute Shader Approach (glsl3_compute)  

```glsl
layout (local_size_x = 8, local_size_y = 8) in;
void main()
{
    vec4 color = vec4(gl_GlobalInvocationID.xy,0,1);
    imageStore(mTDComputeOutputs[0], 
               ivec2(gl_GlobalInvocationID.xy), 
               TDOutputSwizzle(color));
}
```

**Educational Comparison**:

- **gl_FragCoord.xy**: Fragment shader screen coordinates  
- **gl_GlobalInvocationID.xy**: Compute shader thread coordinates
- **Visual Result**: Both create similar gradients, demonstrating coordinate system equivalence
- **Performance**: Compute shader has potential for more complex parallel operations

## TouchDesigner Integration Patterns

### 1. GLSL_TOP Configuration

- **Pixel Shader**: Use `.par.pixeldat` to link pixel shader text DAT
- **Compute Shader**: Use `.par.computedat` to link compute shader text DAT  
- **Resolution**: Controlled by GLSL_TOP resolution settings
- **Input Textures**: Connected via TOP inputs to GLSL_TOP

### 2. Parameter Binding Fundamentals

```python
# Basic parameter synchronization pattern
def setup_glsl_parameters(glsl_op):
    # Resolution info automatically available as uTDOutputInfo
    # Input textures automatically available as sTD2DInputs[]
    # Compute outputs automatically available as mTDComputeOutputs[]
    pass
```

### 3. Data Flow Patterns

```
Input Data → GLSL_TOP (Compute) → Output TOP → Analysis/Visualization
```

## Reusable Code Templates

### Basic Compute Shader Template

```glsl
// TouchDesigner Compute Shader Template
layout (local_size_x = 8, local_size_y = 8) in;
void main()
{
    // Get thread position
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Sample input (if needed)
    vec4 inputColor = texelFetch(sTD2DInputs[0], gId, 0);
    
    // Process data
    vec4 outputColor = processData(inputColor);
    
    // Write result
    imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(outputColor));
}
```

### Basic Pixel Shader Template

```glsl
// TouchDesigner Pixel Shader Template  
out vec4 fragColor;
void main()
{
    // Sample input texture
    vec4 inputColor = texture(sTD2DInputs[0], vUV.st);
    
    // Process data
    vec4 outputColor = processData(inputColor);
    
    // Write result  
    fragColor = TDOutputSwizzle(outputColor);
}
```

## Advanced Concepts Explained

### Work Group Architecture

- **Local Size**: `local_size_x = 8, local_size_y = 8` creates 64-thread work groups
- **Hardware Alignment**: Powers of 2 are optimal for GPU architecture
- **Memory Coalescing**: Sequential threads access sequential memory for best performance

### Coordinate System Fundamentals

- **Compute Threads**: Discrete thread IDs (0, 1, 2, 3...)
- **Fragment Pixels**: Screen space coordinates with sub-pixel precision
- **Texture UVs**: Normalized coordinates (0.0 to 1.0)

### TouchDesigner GLSL Specifics

- **No #version**: TouchDesigner automatically handles GLSL version
- **TDOutputSwizzle()**: MANDATORY for all color outputs
- **Built-in Uniforms**: `uTDOutputInfo`, `sTD2DInputs[]`, `mTDComputeOutputs[]`

## Performance Considerations

### When to Use Compute vs Pixel Shaders

**Use Compute Shaders For**:

- Arbitrary read/write patterns  
- Complex data structures
- Multi-pass algorithms
- Non-graphics computations

**Use Pixel Shaders For**:

- Simple per-pixel effects
- Standard image processing
- Real-time visual effects
- GPU-accelerated rendering pipeline

### Optimization Guidelines

- **Work Group Size**: Use multiples of 32 (warp size) for optimal GPU utilization
- **Memory Access**: Prefer sequential memory access patterns
- **Branching**: Minimize conditional statements in shaders
- **Texture Access**: Use `texelFetch()` for precise pixel access, `texture()` for filtered sampling

## Future Development Guidance

### Progressive Learning Path

1. **Master Basic Patterns**: Start with simple compute shader structures
2. **Understand Coordinates**: Practice with coordinate visualization techniques
3. **Explore Data Flow**: Experiment with input/output texture patterns
4. **Add Interactivity**: Connect CHOP parameters to shader uniforms

### Extension Possibilities

- **Real-time Parameters**: Connect CHOP operators for dynamic control
- **Multi-pass Processing**: Chain multiple GLSL_TOPs for complex effects
- **Data Analysis**: Use compute shaders for image analysis and processing
- **Creative Effects**: Build upon coordinate manipulation for artistic applications

### Next Level Techniques

After mastering these fundamentals, progress to:

- **3D Texture Processing** (3DTex module)
- **Particle Simulations** (particles module)  
- **Memory Optimization** (atomic_compaction module)

## Common Patterns for Future Projects

### 1. Image Processing Pipeline

```glsl
// Read → Process → Write pattern
vec4 input = texelFetch(sTD2DInputs[0], gId, 0);
vec4 processed = applyFilter(input);
imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(processed));
```

### 2. Coordinate-Based Generation

```glsl  
// Generate patterns based on thread position
vec2 uv = vec2(gl_GlobalInvocationID.xy) / uTDOutputInfo.res.xy;
vec4 pattern = generatePattern(uv);
imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(pattern));
```

### 3. Multi-Input Processing

```glsl
// Combine multiple texture inputs
vec4 input1 = texelFetch(sTD2DInputs[0], gId, 0);
vec4 input2 = texelFetch(sTD2DInputs[1], gId, 0);  
vec4 result = combineInputs(input1, input2);
imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(result));
```

This foundational knowledge provides the essential building blocks for all advanced GPU computing techniques in TouchDesigner.