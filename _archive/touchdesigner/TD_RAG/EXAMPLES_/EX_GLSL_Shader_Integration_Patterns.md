---
category: EXAMPLES
document_type: examples
difficulty: advanced
time_estimate: 60-90 minutes
operators:
- GLSL_TOP
- GLSL_MAT
- GLSL_SOP
- GLSL_COMP
- Info_DAT
- Text_DAT
- Constant_TOP
- Render_TOP
- Geometry_COMP
- Camera_COMP
- Light_COMP
concepts:
- glsl_programming
- shader_integration
- gpu_computing
- real_time_rendering
- touchdesigner_specifics
- performance_optimization
- uniform_management
- texture_sampling
prerequisites:
- GLSL_fundamentals
- TouchDesigner_rendering_pipeline
- Python_scripting
workflows:
- shader_development
- gpu_effects_creation
- real_time_rendering
- performance_optimization
- shader_debugging
keywords:
- glsl
- shaders
- gpu computing
- uniforms
- textures
- vertex shader
- fragment shader
- compute shader
- touchdesigner functions
- TDOutputSwizzle
- texture sampling
- performance
tags:
- glsl
- shaders
- gpu
- rendering
- advanced
- examples
- patterns
relationships:
  GLSL_Advanced_GLSL_in_Touchdesigner: strong
  PY_Debugging_Error_Handling: medium
  REF_Troubleshooting_Guide: medium
  PERF_Optimize: medium
  PY_Working_with_OPs_in_Python: medium
related_docs:
- GLSL_Advanced_GLSL_in_Touchdesigner
- PY_Debugging_Error_Handling
- REF_Troubleshooting_Guide
- PERF_Optimize
- PY_Working_with_OPs_in_Python
hierarchy:
  secondary: advanced_examples
  tertiary: glsl_integration
question_patterns:
- GLSL shader integration in TouchDesigner?
- How to use TouchDesigner GLSL functions?
- Advanced shader programming patterns?
- GPU computing with GLSL in TouchDesigner?
- texelFetch vs texture in TouchDesigner?
common_use_cases:
- shader_development
- gpu_effects_creation
- real_time_rendering
- performance_optimization
---

# GLSL Shader Integration Patterns in TouchDesigner

## 🎯 Quick Reference

**Purpose**: Advanced GLSL shader integration with TouchDesigner-specific patterns and optimization
**Difficulty**: Advanced  
**Time to read**: 60-90 minutes
**Use for**: shader_development, gpu_effects_creation, real_time_rendering

## 🔗 Learning Path

**Prerequisites**: [GLSL Fundamentals] → [TouchDesigner Rendering Pipeline] → [TD GLSL Functions]  
**This document**: EXAMPLES advanced TouchDesigner GLSL patterns
**Next steps**: Production deployment and performance optimization

## TouchDesigner GLSL Fundamentals

### Built-in Uniforms and Variables

TouchDesigner provides a comprehensive set of built-in uniforms and variables that are automatically declared and populated. Understanding these is essential for effective shader development.

#### Texture Information Uniforms

```glsl
// Automatically declared texture info arrays - DO NOT declare these yourself
// uniform TDTexInfo uTD2DInfos[TD_NUM_2D_INPUTS];
// uniform TDTexInfo uTD3DInfos[TD_NUM_3D_INPUTS];
// uniform TDTexInfo uTDOutputInfo;

struct TDTexInfo {
    vec4 res;    // res.xy = 1.0/width, 1.0/height
                 // res.zw = width, height
    vec4 depth;  // depth.x = 1.0/depth
                 // depth.y = depth value
                 // depth.z = depthOffset (for 3D textures)
};
```

#### Input Samplers

```glsl
// Automatically declared input samplers - DO NOT declare these yourself
// uniform sampler2D sTD2DInputs[TD_NUM_2D_INPUTS];
// uniform sampler3D sTD3DInputs[TD_NUM_3D_INPUTS];
// uniform sampler2DArray sTD2DArrayInputs[TD_NUM_2D_ARRAY_INPUTS];
// uniform samplerCube sTDCubeInputs[TD_NUM_CUBE_INPUTS];

// Built-in convenience samplers
// uniform sampler2D sTDNoiseMap;       // 256x256 random noise texture
// uniform sampler1D sTDSineLookup;     // Sine wave lookup table
```

#### Key TouchDesigner Functions

```glsl
// Color channel management - ALWAYS use for final output
vec4 TDOutputSwizzle(vec4 color);

// Noise generation
float TDPerlinNoise(vec2 coord);
float TDPerlinNoise(vec3 coord);
float TDPerlinNoise(vec4 coord);
float TDSimplexNoise(vec2 coord);
float TDSimplexNoise(vec3 coord);
float TDSimplexNoise(vec4 coord);

// Color space conversion
vec3 TDHSVToRGB(vec3 hsvColor);
vec3 TDRGBToHSV(vec3 rgbColor);

// Dithering
vec4 TDDither(vec4 color);
```

#### Texture Sampling Methods

TouchDesigner supports two primary texture sampling methods with distinct use cases:

```glsl
// texture() - Normalized coordinates with filtering/interpolation
vec4 color = texture(sTD2DInputs[0], vUV.st);

// texelFetch() - Direct pixel access without filtering
ivec2 pixelCoord = ivec2(gl_GlobalInvocationID.xy);
vec4 color = texelFetch(sTD2DInputs[0], pixelCoord, 0);
```

**Use texture() for:**
- Traditional UV-based sampling (0.0 to 1.0 coordinates)
- When filtering and interpolation are desired
- Standard fragment shader rendering
- Wrapping and repeat behavior

**Use texelFetch() for:**
- Pixel-perfect operations requiring exact texel values
- Compute shaders with integer coordinates
- Data processing where interpolation would corrupt results
- Advanced algorithms requiring precise pixel access

```glsl
// Example: Compare filtered vs unfiltered sampling
layout(location = 0) out vec4 fragColor;

void main() {
    // Filtered sampling - smooth interpolation
    vec4 filteredColor = texture(sTD2DInputs[0], vUV.st);
    
    // Unfiltered sampling - exact pixel values
    ivec2 texSize = textureSize(sTD2DInputs[0], 0);
    ivec2 pixelCoord = ivec2(vUV.st * vec2(texSize));
    vec4 exactColor = texelFetch(sTD2DInputs[0], pixelCoord, 0);
    
    // Output comparison or blend
    fragColor = TDOutputSwizzle(mix(filteredColor, exactColor, 0.5));
}
```

## GLSL TOP Shader Patterns

### Basic Pixel Shader Structure

All GLSL TOP pixel shaders in TouchDesigner follow this basic structure:

```glsl
// TouchDesigner automatically adds #version - don't include it
// Built-in input: vec2 vUV; (texture coordinates 0.0-1.0)
// Built-in samplers: sTD2DInputs[], sTD3DInputs[], etc.

layout(location = 0) out vec4 fragColor;

void main() {
    // Sample input texture
    vec4 inputColor = texture(sTD2DInputs[0], vUV.st);
    
    // Process the color
    vec4 outputColor = inputColor;
    
    // ALWAYS use TDOutputSwizzle for final output
    fragColor = TDOutputSwizzle(outputColor);
}
```

### Procedural Pattern Examples

#### 1. TouchDesigner Noise Pattern

```glsl
layout(location = 0) out vec4 fragColor;
uniform float uNoiseScale;
uniform float uNoiseSpeed;

void main() {
    vec2 coord = vUV.st * uNoiseScale;
    coord += absTime.seconds * uNoiseSpeed;
    
    // Use TouchDesigner's built-in noise functions
    float noise = TDSimplexNoise(coord);
    
    // Convert from -1,1 range to 0,1 range
    noise = noise * 0.5 + 0.5;
    
    // Create color gradient
    vec3 color = mix(vec3(0.2, 0.4, 0.8), vec3(0.8, 0.6, 0.2), noise);
    
    fragColor = TDOutputSwizzle(vec4(color, 1.0));
}
```

#### 2. Audio-Reactive Visualizer

```glsl
layout(location = 0) out vec4 fragColor;
uniform float uAudioScale;

void main() {
    // Assume sTD2DInputs[0] is background, sTD2DInputs[1] is audio spectrum
    vec4 background = texture(sTD2DInputs[0], vUV.st);
    
    // Sample audio spectrum based on horizontal position
    vec4 audioSample = texture(sTD2DInputs[1], vec2(vUV.s, 0.5));
    float audioLevel = audioSample.r * uAudioScale;
    
    // Create audio-reactive pattern
    float distFromCenter = length(vUV.st - 0.5);
    float audioInfluence = smoothstep(0.3, 0.3 + audioLevel * 0.2, distFromCenter);
    
    // Mix background with audio-reactive color
    vec3 audioColor = vec3(audioLevel, audioLevel * 0.5, audioLevel * 0.2);
    vec3 finalColor = mix(background.rgb, audioColor, audioInfluence * 0.7);
    
    fragColor = TDOutputSwizzle(vec4(finalColor, 1.0));
}
```

#### 3. Multi-Input Compositing

```glsl
layout(location = 0) out vec4 fragColor;
uniform float uBlendFactor;
uniform float uEffectStrength;

void main() {
    // TouchDesigner automatically handles different numbers of inputs
    vec4 layer1 = texture(sTD2DInputs[0], vUV.st);
    vec4 layer2 = vec4(0.0);
    
    // Check if second input exists using TD_NUM_2D_INPUTS
    if (TD_NUM_2D_INPUTS > 1) {
        layer2 = texture(sTD2DInputs[1], vUV.st);
    }
    
    // Custom blend operation
    vec4 blended = mix(layer1, layer2, uBlendFactor);
    
    // Apply effect using texture info
    float aspectRatio = uTD2DInfos[0].res.z / uTD2DInfos[0].res.w;
    vec2 centeredUV = (vUV.st - 0.5) * vec2(aspectRatio, 1.0);
    float vignette = 1.0 - smoothstep(0.3, 0.8, length(centeredUV));
    
    blended.rgb *= mix(1.0, vignette, uEffectStrength);
    
    fragColor = TDOutputSwizzle(blended);
}
```

### Compute Shader Patterns

Compute shaders in TouchDesigner use different syntax and provide direct pixel manipulation capabilities:

```glsl
// Compute shader basic structure
// TouchDesigner provides: uniform image2D sTDComputeOutputs[TD_NUM_COLOR_BUFFERS];

layout(local_size_x = 8, local_size_y = 8) in;

void main() {
    ivec2 storePos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 workGroup = ivec2(gl_WorkGroupID.xy);
    ivec2 localPos = ivec2(gl_LocalInvocationID.xy);
    
    // Get texture dimensions
    ivec2 imgSize = imageSize(sTDComputeOutputs[0]);
    
    // Bounds checking
    if (storePos.x >= imgSize.x || storePos.y >= imgSize.y) return;
    
    // Compute color based on position
    vec2 uv = vec2(storePos) / vec2(imgSize);
    vec4 color = vec4(uv, 0.5, 1.0);
    
    // Store result
    imageStore(sTDComputeOutputs[0], storePos, TDOutputSwizzle(color));
}
```

#### Compute Shader with Input Sampling

```glsl
layout(local_size_x = 16, local_size_y = 16) in;
uniform float uEffectStrength;

void main() {
    ivec2 storePos = ivec2(gl_GlobalInvocationID.xy);
    ivec2 imgSize = imageSize(sTDComputeOutputs[0]);
    
    if (storePos.x >= imgSize.x || storePos.y >= imgSize.y) return;
    
    // Sample input using texelFetch for pixel-perfect access
    vec4 inputColor = texelFetch(sTD2DInputs[0], storePos, 0);
    
    // Or use texture() with normalized coordinates
    vec2 uv = (vec2(storePos) + 0.5) / vec2(imgSize);
    vec4 inputColorFiltered = texture(sTD2DInputs[0], uv);
    
    // Apply processing
    vec4 processed = inputColor * uEffectStrength;
    
    imageStore(sTDComputeOutputs[0], storePos, TDOutputSwizzle(processed));
}
```

## GLSL MAT Shader Patterns

GLSL Materials in TouchDesigner use vertex and fragment shaders to customize 3D object rendering:

### Basic Vertex Shader

```glsl
// Vertex shader for GLSL MAT
// Built-in inputs: P (position), N (normal), Cd (color)
// Built-in functions: TDDeform(), TDWorldToProj()

out vec3 worldPos;
out vec3 worldNormal;
out vec2 texCoord;
out vec4 vertexColor;

void main() {
    // Apply deformations (handles instancing, bone deforms automatically)
    vec4 worldPosition = TDDeform(P);
    worldPos = worldPosition.xyz;
    
    // Transform normal to world space
    worldNormal = normalize(TDDeformNorm(N));
    
    // Pass through texture coordinates and color
    texCoord = uv[0].st;
    vertexColor = TDPointColor();
    
    // Transform to projection space - TouchDesigner handles special cases
    gl_Position = TDWorldToProj(worldPosition);
}
```

### Basic Fragment Shader with TouchDesigner Lighting

```glsl
// Fragment shader for GLSL MAT
in vec3 worldPos;
in vec3 worldNormal;
in vec2 texCoord;
in vec4 vertexColor;

layout(location = 0) out vec4 fragColor;
uniform float uRoughness;
uniform vec3 uBaseColor;

void main() {
    vec3 normal = normalize(worldNormal);
    vec3 viewDir = normalize(uTDMats[0].camInverse[3].xyz - worldPos);
    
    // Initialize lighting accumulation
    vec3 diffuseLight = vec3(0.0);
    vec3 specularLight = vec3(0.0);
    
    // TouchDesigner PBR lighting loop
    for (int i = 0; i < TD_NUM_LIGHTS; i++) {
        TDPBRResult lightResult = TDLightingPBR(
            i,                    // light index
            uBaseColor,           // diffuse color
            vec3(0.04),          // specular color (dielectric)
            worldPos,            // world position
            normal,              // world normal
            1.0,                 // shadow strength
            vec3(0.0),           // shadow color
            viewDir,             // view direction
            uRoughness           // roughness
        );
        
        diffuseLight += lightResult.diffuse;
        specularLight += lightResult.specular;
    }
    
    // Environment lighting
    for (int i = 0; i < TD_NUM_ENV_LIGHTS; i++) {
        TDEnvLightingPBR(
            diffuseLight, specularLight,  // inout parameters
            i,                            // environment light index
            uBaseColor,                   // diffuse color
            vec3(0.04),                  // specular color
            normal,                      // world normal
            viewDir,                     // view direction
            uRoughness,                  // roughness
            1.0                          // ambient occlusion
        );
    }
    
    vec3 finalColor = diffuseLight + specularLight;
    fragColor = TDOutputSwizzle(vec4(finalColor, 1.0));
}
```

### Custom Material with Texture Sampling

```glsl
// Fragment shader with texture and custom effects
in vec3 worldPos;
in vec3 worldNormal;
in vec2 texCoord;

layout(location = 0) out vec4 fragColor;
uniform float uMetallic;
uniform float uRoughness;
uniform float uDisplacement;

void main() {
    // Sample base texture if available
    vec3 baseColor = vec3(0.8);
    if (TD_NUM_2D_INPUTS > 0) {
        baseColor = texture(sTD2DInputs[0], texCoord).rgb;
    }
    
    // Displace normal using noise
    vec3 normal = normalize(worldNormal);
    if (uDisplacement > 0.0) {
        vec2 noiseCoord = texCoord * 10.0 + absTime.seconds * 0.1;
        float noise = TDSimplexNoise(noiseCoord);
        
        // Create tangent space displacement
        vec3 tangent = normalize(cross(normal, vec3(0.0, 1.0, 0.0)));
        vec3 bitangent = cross(normal, tangent);
        normal += (tangent * noise * uDisplacement);
        normal = normalize(normal);
    }
    
    // PBR material setup
    vec3 viewDir = normalize(uTDMats[0].camInverse[3].xyz - worldPos);
    vec3 specularColor = mix(vec3(0.04), baseColor, uMetallic);
    vec3 diffuseColor = baseColor * (1.0 - uMetallic);
    
    // Lighting calculation
    vec3 finalColor = vec3(0.0);
    for (int i = 0; i < TD_NUM_LIGHTS; i++) {
        TDPBRResult lightResult = TDLightingPBR(
            i, diffuseColor, specularColor,
            worldPos, normal, 1.0, vec3(0.0),
            viewDir, uRoughness
        );
        finalColor += lightResult.diffuse + lightResult.specular;
    }
    
    fragColor = TDOutputSwizzle(vec4(finalColor, 1.0));
}
```

## Advanced Integration Patterns

### Multi-Buffer Rendering

TouchDesigner supports multiple render targets for advanced effects:

```glsl
// Fragment shader outputting to multiple buffers
layout(location = 0) out vec4 colorBuffer;
layout(location = 1) out vec4 normalBuffer;
layout(location = 2) out vec4 materialBuffer;

in vec3 worldPos;
in vec3 worldNormal;
in vec2 texCoord;

uniform float uMetallic;
uniform float uRoughness;

void main() {
    // Sample base texture if available
    vec3 baseColor = vec3(0.8);
    if (TD_NUM_2D_INPUTS > 0) {
        baseColor = texture(sTD2DInputs[0], texCoord).rgb;
    }
    
    vec3 normal = normalize(worldNormal);
    
    // Output to multiple buffers
    colorBuffer = TDOutputSwizzle(vec4(baseColor, 1.0));
    normalBuffer = TDOutputSwizzle(vec4(normal * 0.5 + 0.5, 1.0));
    materialBuffer = TDOutputSwizzle(vec4(uMetallic, uRoughness, 0.0, 1.0));
}
```

### Performance Optimization Tips

**1. Minimize texture lookups:**
```glsl
// Good - single lookup
vec4 tex = texture(sTD2DInputs[0], vUV.st);
vec3 color = tex.rgb;
float alpha = tex.a;

// Avoid - multiple lookups
vec3 color = texture(sTD2DInputs[0], vUV.st).rgb;
float alpha = texture(sTD2DInputs[0], vUV.st).a;
```

**2. Use appropriate precision:**
```glsl
// Use mediump for colors and normals
mediump vec3 color;
mediump vec3 normal;

// Use highp only when needed for positions
highp vec3 worldPos;
```

**3. Optimize branching:**
```glsl
// Good - use mix() instead of if/else when possible
vec3 result = mix(colorA, colorB, condition ? 1.0 : 0.0);

// Avoid complex branching in pixel shaders
// if (complexCondition) { ... }
```

## Best Practices Summary

### TouchDesigner GLSL Development Guidelines

1. **Always use `TDOutputSwizzle()` for final color output**
2. **Use TD-specific functions**: `TDDeform()`, `TDWorldToProj()`, `TDSimplexNoise()`
3. **Leverage built-in uniforms**: `uTD2DInfos[]`, `absTime`, texture info structs
4. **Choose appropriate sampling method**: `texture()` vs `texelFetch()`
5. **Optimize for real-time performance**: minimize texture lookups, avoid complex branching
6. **Use compute shaders for parallel processing**: particle systems, image processing
7. **Test with multiple input configurations**: handle varying `TD_NUM_*_INPUTS` counts
8. **Follow TouchDesigner naming conventions**: `uCustomName` for uniforms

### Common Patterns

- **Image processing**: GLSL TOP with pixel or compute shaders
- **3D material effects**: GLSL MAT with vertex/fragment shaders
- **Procedural generation**: Built-in noise functions with time-based animation
- **Audio visualization**: Texture sampling of audio spectrum data
- **Multi-pass effects**: Multiple color buffers with Render Select TOP

## Cross-References

**Related Documentation:**
- [GLSL_Write_a_GLSL_TOP](../GLSL_/GLSL_Write_a_GLSL_TOP.md) - GLSL TOP fundamentals
- [GLSL_Write_a_GLSL_Material](../GLSL_/GLSL_Write_a_GLSL_Material.md) - GLSL MAT development
- [GLSL_Advanced_GLSL_in_Touchdesigner](../GLSL_/GLSL_Advanced_GLSL_in_Touchdesigner.md) - Advanced GLSL techniques
- [GLSL_Built-In_Function_Reference](../GLSL_/GLSL_Built-In_Function_Reference.md) - TouchDesigner GLSL functions
- [PERF_Optimize](../PERFORMANCE_/PERF_Optimize.md) - Performance optimization

**External Resources:**
- [TouchDesigner GLSL Documentation](https://docs.derivative.ca/Write_a_GLSL_TOP)
- [OpenGL Shading Language Specification](https://www.khronos.org/opengl/wiki/OpenGL_Shading_Language)

---

*This comprehensive GLSL integration guide provides TouchDesigner-specific patterns, built-in functions, and performance optimization techniques for shader development.*