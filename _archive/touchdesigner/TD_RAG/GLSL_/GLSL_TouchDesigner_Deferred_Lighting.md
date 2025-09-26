---
category: GLSL
document_type: tutorial
difficulty: intermediate
time_estimate: 30-45 minutes
operators:
- GLSL_MAT
- GLSL_TOP
- Render_TOP
- Render_Select_TOP
- Light_COMP
concepts:
- deferred_lighting
- g_buffer
- multi_pass_rendering
- lighting_optimization
- data_packing
- multiple_render_targets
- many_lights
- performance_optimization
prerequisites:
- GLSL_Write_a_GLSL_Material
- GLSL_Write_a_GLSL_TOP
- advanced_rendering_concepts
workflows:
- rendering_with_many_lights
- real_time_3d_graphics
- performance_optimization
- advanced_rendering_techniques
- large_scale_lighting
keywords:
- deferred shading
- g-buffer
- many lights
- point lights
- lighting pass
- data packing
- multi-pass
- mrt
- texelFetchBuffer
- performance optimization
- advanced lighting
tags:
- glsl
- gpu
- real_time
- multi_pass
- g_buffer
- mrt
- lighting
- optimization
- tutorial
- advanced
relationships:
  GLSL_Write_a_GLSL_Material: strong
  GLSL_Write_a_GLSL_TOP: strong
  GLSL_Advanced_GLSL_in_Touchdesigner: medium
  PERF_Optimize: medium
related_docs:
- GLSL_Write_a_GLSL_Material
- GLSL_Write_a_GLSL_TOP
- GLSL_Advanced_GLSL_in_Touchdesigner
- PERF_Optimize
hierarchy:
  secondary: rendering
  tertiary: advanced_lighting
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- rendering_with_many_lights
- real_time_3d_graphics
- performance_optimization
- advanced_rendering_techniques
---

# TouchDesigner Deferred Lighting – Point Lights

<!-- TD-META
category: GLSL
document_type: tutorial
operators: [GLSL_MAT, GLSL_TOP, Render_TOP, Render_Select_TOP, Light_COMP]
concepts: [deferred_lighting, g_buffer, multi_pass_rendering, lighting_optimization, data_packing, multiple_render_targets, many_lights, performance_optimization]
prerequisites: [GLSL_Write_a_GLSL_Material, GLSL_Write_a_GLSL_TOP, advanced_rendering_concepts]
workflows: [rendering_with_many_lights, real_time_3d_graphics, performance_optimization, advanced_rendering_techniques, large_scale_lighting]
related: [GLSL_Write_a_GLSL_Material, GLSL_Write_a_GLSL_TOP, GLSL_Advanced_GLSL_in_Touchdesigner, PERF_Optimize]
relationships: {
  "GLSL_Write_a_GLSL_Material": "strong", 
  "GLSL_Write_a_GLSL_TOP": "strong", 
  "GLSL_Advanced_GLSL_in_Touchdesigner": "medium",
  "PERF_Optimize": "medium"
}
hierarchy:
  primary: "tutorials"
  secondary: "rendering"
  tertiary: "advanced_lighting"
keywords: [deferred shading, g-buffer, many lights, point lights, lighting pass, data packing, multi-pass, mrt, texelFetchBuffer, performance optimization, advanced lighting]
tags: [glsl, gpu, real_time, multi_pass, g_buffer, mrt, lighting, optimization, tutorial, advanced]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming tutorial for GPU development
**Difficulty**: Intermediate
**Time to read**: 30-45 minutes
**Use for**: rendering_with_many_lights, real_time_3d_graphics, performance_optimization

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Write A Glsl Material] → [Glsl Write A Glsl Top] → [Advanced Rendering Concepts]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Write a GLSL Material] → [GLSL Write a GLSL TOP] → [GLSL Advanced GLSL in Touchdesigner]

**Related Topics**: rendering with many lights, real time 3d graphics, performance optimization

## Summary

Specialized tutorial on implementing deferred lighting for handling many lights efficiently. Advanced rendering technique that builds on foundational GLSL knowledge.

## Relationship Justification

Connected to foundational GLSL guides and advanced techniques. Links to performance optimization since deferred lighting is a performance-oriented technique.

## Content

- [Introduction](#introduction)
- [Color Buffers](#color-buffers)
- [Light Attributes](#light-attributes)
- [Combining Buffers](#combining-buffers)
- [Representing Lights](#representing-lights)
- [Post Processing for Final Output](#post-processing-for-final-output)
- [Examples](#examples)

## Introduction

A comprehensive guide to implementing real-time rendering with multiple lights using deferred lighting (also referred to as deferred shading) in TouchDesigner. The typical [GLSL_OpenGL] pipeline has limitations when working with numerous lights, but deferred lighting provides interesting potential for handling LOTS of lights efficiently.

This approach differs from the standard lighting pipeline by encoding scene information in color buffers for later combination, allowing lighting calculations to be performed based on actual output pixels rather than on geometry that may not be visible to the camera.

## Color Buffers

The deferred lighting pipeline begins by creating four color buffers that contain all the information needed for lighting calculations in subsequent passes. At this stage, no lighting calculations have been performed yet – this is purely data setup.

The four buffers represent:

- `position` – renderselect_postition
- `normals` – renderselect_normal  
- `color` – renderselect_color
- `uvs` – renderselect_uv

### Vertex Shader Implementation

```glsl
// TouchDesigner vertex shader

// struct and data to fragment shader
out VS_OUT{
    vec4 position;
    vec3 normal;
    vec4 color;
    vec2 uv;
    } vs_out;

void main(){
    
    // packing data for passthrough to fragment shader
    vs_out.position     = TDDeform(P);
    vs_out.normal       = TDDeformNorm(N);
    vs_out.color        = Cd;
    vs_out.uv           = uv[0].st;

    gl_Position         = TDWorldToProj(vs_out.position); 
}
```

### Fragment Shader Implementation

```glsl
// TouchDesigner frag shader

// struct and data from our vertex shader
in VS_OUT{
    vec4 position;
    vec3 normal;
    vec4 color;
    vec2 uv;
    } fs_in;

// color buffer assignments
layout (location = 0) out vec4 o_position;
layout (location = 1) out vec4 o_normal;
layout (location = 2) out vec4 o_color;
layout (location = 3) out vec4 o_uv;

void main(){
    o_position  = fs_in.position;
    o_normal    = vec4( fs_in.normal, 1.0 );
    o_color     = fs_in.color;
    o_uv        = vec4( fs_in.uv, 0.0, 1.0 );
}
```

The concept involves encoding scene information in color buffers for later combination. To properly implement this approach, you need point position, normal, color, and UV data – information normally handled automatically but requiring specific organization when working with multiple lights.

## Light Attributes

The next stage involves computing and packing data for position, color, and falloff properties of point lights.

### Light Position Setup

For simplicity, geometry is used to represent point light positions, similar to instancing approaches. In the network, this is represented by a Circle SOP (`circle1`). CHOP data is converted and attributes from the circle (number of points) ensure that the remaining CHOP data matches the correct number of samples/lights in the scene.

### Light Color and Properties

Light colors can be generated using noise or ramp TOPs. While these values are ultimately CHOP data, visual representation makes them easier to conceptualize. Light attributes are packed into CHOPs where each sample represents attributes for a different light, accessed via `texelFetchBuffer()` calls in the next stage.

Light attributes are packed in the following CHOPs:

- `position` – null_light_pos
- `color` – null_light_color  
- `falloff` – null_light_falloff

**Note:** Sample 0 from each of these three CHOPs relates to the same light. Data is packed in sequences of three channels for easy translation to `vec3` in fragment processing.

## Combining Buffers

This stage combines color buffers with CHOPs containing light location and property information. The process loops through each light to determine its contribution to scene lighting, accumulates values, and combines them with existing scene data.

This assemblage is "deferred" because calculations are performed only on actual output pixels rather than on potentially invisible geometry. While for loops are generally discouraged in [GLSL_OpenGL], this case allows advantageous use with less overhead than traditional light components.

### Combination Shader Implementation

```glsl
uniform int numLights;

uniform vec3 viewDirection;
uniform vec3 specularColor;

uniform float shininess;

uniform sampler2D samplerPos;
uniform sampler2D samplerNorm;
uniform sampler2D samplerColor;
uniform sampler2D samplerUv;

uniform samplerBuffer lightPos;
uniform samplerBuffer lightColor;
uniform samplerBuffer lightFalloff;

out vec4 fragColor;

void main()
{
    vec2 screenSpaceUV  = vUV.st;
    vec2 resolution   = uTD2DInfos[0].res.zw;

    // parse data from g-buffer
    vec3 position   = texture( sTD2DInputs[0], screenSpaceUV ).rgb;
    vec3 normal   = texture( sTD2DInputs[1], screenSpaceUV ).rgb;
    vec4 color    = texture( sTD2DInputs[2], screenSpaceUV );
    vec2 uv    = texture( sTD2DInputs[3], screenSpaceUV ).rg;

    // set up placeholder for final color
    vec3 finalColor  = vec3(0.0);

    // loop through all lights
    for ( int light = 0; light < numLights; ++light ){

     // parse lighting data based on the current light index
     vec3 currentLightPos  = texelFetchBuffer( lightPos, light ).xyz;
     vec3 currentLightColor  = texelFetchBuffer( lightColor, light ).xyz;
     vec3 currentLightFalloff = texelFetchBuffer( lightFalloff, light ).xyz;

     // calculate the distance between the current fragment and the light source
     float lightDist    = length( currentLightPos – position );

     // diffuse contribution
     vec3 toLight      = normalize( currentLightPos – position );
     vec3 diffuse     = max( dot( normal, toLight ), 0.0 ) * color.rgb * currentLightColor;

     // specular contribution
     vec3 toViewer     = normalize( position – viewDirection );
     vec3 h       = normalize( toLight – toViewer );
     float spec      = pow( max( dot( normal, h ), 0.0 ), shininess );
     vec3 specular     = currentLightColor * spec * specularColor;

     // attenuation
     float attenuation    = 1.0 / ( 1.0 + currentLightFalloff.y * lightDist + currentLightFalloff.z * lightDist * lightDist );
     diffuse      *= attenuation;
     specular      *= attenuation;

     // accumulate lighting
     finalColor      += diffuse + specular;

    }

    // final color out 
    fragColor = TDOutputSwizzle( vec4( finalColor, color.a ) );
}
```

## Representing Lights

After completing lighting calculations and accumulation, visual representation of lights may be desired for verification that calculations and data packing work correctly.

Instances and a render pass can represent lights as spheres, providing visual confirmation of light locations in the scene. This approach should be familiar to those who have used [REF_SimpleInstancing] in TouchDesigner.

## Post Processing for Final Output

The final stage assembles the scene and applies post-processing for clean, finished output.

Up to this point, no anti-aliasing has been applied, and instances exist in a separate render pass. To combine all elements and remove sharp edges, several final steps are required:

1. Composite scene elements
2. Apply anti-aliasing pass
3. Optional additional post-process treatments (glow, bloom, etc.)

This stage provides opportunity for additional visual enhancements and final output optimization.

## Examples

Complete example files and experimentation materials are available in the [REF_TouchDesignerDeferredLighting] repository.

**Note:** TouchDesigner networks can be difficult to read, and this documentation helps illuminate concepts explored in the sample `.tox` file.
