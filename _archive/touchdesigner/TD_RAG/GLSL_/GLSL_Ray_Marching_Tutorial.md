---
title: "Ray Marching Tutorial"
category: GLSL
document_type: tutorial
difficulty: intermediate
time_estimate: 30-45 minutes

# Enhanced metadata
user_personas: ["shader_programmer", "technical_artist", "intermediate_user", "visual_programmer"]
completion_signals: ["understands_raymarching_concepts", "can_implement_sdf_rendering", "writes_procedural_shaders", "debugs_raymarching_code"]

operators:
- GLSL_TOP
- GLSL_MAT
concepts:
- ray_marching
- signed_distance_fields
- procedural_rendering
- volume_rendering
- implicit_surfaces
- mathematical_rendering
- sphere_tracing
- surface_detection
prerequisites:
- GLSL_fundamentals
- 3d_math
- vector_operations
- GLSL_Distance_Functions
workflows:
- procedural_rendering
- generative_visuals
- mathematical_art
- volume_visualization
- real_time_rendering
- creative_coding
- advanced_graphics
keywords:
- ray marching tutorial
- ray casting
- signed distance field
- sdf
- procedural rendering
- volume rendering
- sphere tracing
- step size
- surface detection
- normal calculation
- lighting
- distance aided ray marching
- mathematical rendering
tags:
- glsl
- tutorial
- ray_marching
- sdf
- procedural
- rendering
- advanced
- mathematical
- learning
- step_by_step
relationships:
  GLSL_Distance_Functions: strong
  GLSL_Built_In_Functions_Reference: strong
  CLASS_glslTOP_Class: medium
related_docs:
- GLSL_Distance_Functions
- GLSL_Built_In_Functions_Reference
- CLASS_glslTOP_Class
# Enhanced search optimization
search_optimization:
  primary_keywords: ["raymarching", "sdf", "tutorial", "procedural"]
  semantic_clusters: ["procedural_rendering", "mathematical_graphics", "advanced_techniques"]
  user_intent_mapping:
    beginner: ["what is ray marching", "sdf basics", "procedural rendering intro"]
    intermediate: ["raymarching techniques", "distance functions", "volume rendering"]
    advanced: ["advanced raymarching", "optimization techniques", "complex sdf operations"]

hierarchy:
  secondary: advanced_techniques
  tertiary: ray_marching_tutorial
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- procedural_rendering
- generative_visuals
- mathematical_art
- volume_visualization
---

# Ray Marching Tutorial

<!-- TD-META
category: GLSL
document_type: tutorial
operators: [GLSL_TOP, GLSL_MAT]
concepts: [ray_marching, signed_distance_fields, procedural_rendering, volume_rendering, implicit_surfaces, mathematical_rendering, sphere_tracing, surface_detection]
prerequisites: [GLSL_fundamentals, 3d_math, vector_operations, GLSL_Distance_Functions]
workflows: [procedural_rendering, generative_visuals, mathematical_art, volume_visualization, real_time_rendering, creative_coding, advanced_graphics]
related: [GLSL_Distance_Functions, GLSL_Built_In_Functions_Reference, CLASS_glslTOP_Class]
relationships: {
  "GLSL_Distance_Functions": "strong",
  "GLSL_Built_In_Functions_Reference": "strong",
  "CLASS_glslTOP_Class": "medium"
}
hierarchy:
  primary: "shader_programming"
  secondary: "advanced_techniques"
  tertiary: "ray_marching_tutorial"
keywords: [ray marching tutorial, ray casting, signed distance field, sdf, procedural rendering, volume rendering, sphere tracing, step size, surface detection, normal calculation, lighting, distance aided ray marching, mathematical rendering]
tags: [glsl, tutorial, ray_marching, sdf, procedural, rendering, advanced, mathematical, learning, step_by_step]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming tutorial for GPU development
**Difficulty**: Intermediate
**Time to read**: 30-45 minutes
**Use for**: procedural_rendering, generative_visuals, mathematical_art

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Fundamentals] → [3D Math] → [Vector Operations]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Distance Functions] → [GLSL Built In Functions Reference] → [CLASS glslTOP Class]

**Related Topics**: procedural rendering, generative visuals, mathematical art

## Summary

Comprehensive step-by-step tutorial teaching ray marching techniques for procedural 3D rendering entirely in fragment shaders. Covers SDF concepts, ray generation, surface detection, and lighting calculations.

## Relationship Justification

Essential companion to Distance Functions reference, providing practical implementation of mathematical concepts. Demonstrates extensive use of built-in functions and provides foundation for advanced procedural graphics techniques.

## Content

- [Introduction](#introduction)
- [Signed Distance Functions](#signed-distance-functions)
  - [Understanding SDFs](#understanding-sdfs)
  - [Sphere Distance Function](#sphere-distance-function)
- [Setting Up the Ray Marching Loop](#setting-up-the-ray-marching-loop)
  - [Basic Stepping Approach](#basic-stepping-approach)
  - [Distance-Aided Ray Marching](#distance-aided-ray-marching)
  - [Complete Ray Marching Function](#complete-ray-marching-function)
- [Generating Rays](#generating-rays)
  - [Ray Components](#ray-components)
  - [UV Coordinate Mapping](#uv-coordinate-mapping)
  - [Camera and Image Plane Setup](#camera-and-image-plane-setup)
- [Putting It All Together](#putting-it-all-together)
  - [Complete Basic Shader](#complete-basic-shader)
- [Shading](#shading)
  - [Scene Mapping Function](#scene-mapping-function)
  - [Normal Calculation](#normal-calculation)
  - [Visualizing Normals](#visualizing-normals)
  - [Diffuse Lighting](#diffuse-lighting)
  - [Complete Shaded Shader](#complete-shaded-shader)
- [Distorting the Distance Function](#distorting-the-distance-function)
  - [Sinusoidal Displacement](#sinusoidal-displacement)
  - [Advanced Distortions](#advanced-distortions)
- [Conclusion](#conclusion)

## Introduction

Ray marching is a powerful rendering technique commonly seen on [REF_Shadertoy] that can generate fully procedural 3D environments entirely from a single fragment shader. Unlike traditional polygon-based rendering, ray marching uses mathematical functions to define surfaces, opening up possibilities for complex procedural geometry and effects.

This tutorial covers setting up a basic ray marching shader using [CLASS_TouchDesigner], though the techniques can be ported to any 3D environment. The concepts build a foundation for creating more complex procedural scenes.

**Setup Requirements:**

- [CLASS_GLSLTOP] in TouchDesigner
- Output Resolution set to "Custom Resolution" (e.g., 720 x 720)

## Signed Distance Functions

### Understanding SDFs

When using ray marching, traditional 3D elements like polygons, geometry, lights, and cameras are replaced with mathematical functions called **Signed Distance Functions** (SDFs). These functions take a point in 3D space and return the distance from that point to the nearest surface.

An SDF is "signed" because it returns:

- **Negative values:** Point is inside the object
- **Zero:** Point is on the surface
- **Positive values:** Point is outside the object

### Sphere Distance Function

Let's start with a basic sphere SDF. For a point `p` in 3D space and a sphere with center `c` and radius `r`, the distance is calculated as:

```glsl
// params:
// p: arbitrary point in 3D space
// c: the center of our sphere
// r: the radius of our sphere
float distance_from_sphere(in vec3 p, in vec3 c, float r)
{
    return length(p - c) - r;
}
```

**Understanding the Math:**

- `length(p - c)` gives the distance from point `p` to the sphere's center
- Subtracting `r` gives the distance to the sphere's surface

**Three Cases:**

1. **Inside:** `||p - c|| < r` → negative result
2. **On Surface:** `||p - c|| = r` → zero result  
3. **Outside:** `||p - c|| > r` → positive result

## Setting Up the Ray Marching Loop

### Basic Stepping Approach

A naive approach would use fixed-size steps along the ray:

```glsl
const float step_size = 0.1;

for (int i = 0; i < NUMBER_OF_STEPS; ++i)
{
    // Assume that `ro` and `rd` are defined elsewhere
    // and represent the ray's origin and direction, 
    // respectively
    vec3 current_position = ro + (i * step_size) * rd;

    // Some code to evaluate our SDF and determine whether or not 
    // we've hit a surface based on our current position...
}
```

This approach is inefficient and can miss small objects or overshoot surfaces.

### Distance-Aided Ray Marching

A better approach uses **distance-aided ray marching** (also called **sphere tracing**). At each position, we:

1. Evaluate the SDF to get distance to the nearest surface
2. Use this distance as a safe step size (we can move this far without missing anything)
3. Repeat until we're very close to a surface or exceed maximum distance

This creates "bounding spheres" around each sample point, ensuring we never overshoot surfaces while taking optimal step sizes.

### Complete Ray Marching Function

```glsl
vec3 ray_march(in vec3 ro, in vec3 rd)
{
    float total_distance_traveled = 0.0;
    const int NUMBER_OF_STEPS = 32;
    const float MINIMUM_HIT_DISTANCE = 0.001;
    const float MAXIMUM_TRACE_DISTANCE = 1000.0;

    for (int i = 0; i < NUMBER_OF_STEPS; ++i)
    {
        // Calculate our current position along the ray
        vec3 current_position = ro + total_distance_traveled * rd;

        // We wrote this function earlier in the tutorial -
        // assume that the sphere is centered at the origin
        // and has unit radius
        float distance_to_closest = distance_from_sphere(current_position, vec3(0.0), 1.0);

        if (distance_to_closest < MINIMUM_HIT_DISTANCE) // hit
        {
            // We hit something! Return red for now
            return vec3(1.0, 0.0, 0.0);
        }

        if (total_distance_traveled > MAXIMUM_TRACE_DISTANCE) // miss
        {
            break;
        }

        // accumulate the distance traveled thus far
        total_distance_traveled += distance_to_closest;
    }

    // If we get here, we didn't hit anything so just
    // return a background color (black)
    return vec3(0.0);
}
```

**Key Optimizations:**

- **Early termination:** Stop when very close to a surface (`MINIMUM_HIT_DISTANCE`)
- **Ray escape:** Stop rays that travel too far without hitting anything (`MAXIMUM_TRACE_DISTANCE`)

## Generating Rays

### Ray Components

Each ray needs two components:

- **Origin:** Starting point (camera position)
- **Direction:** Normalized vector pointing from camera through image plane

### UV Coordinate Mapping

Fragment shaders execute once per pixel. We need to convert 2D pixel coordinates to 3D ray directions:

```glsl
// TouchDesigner provides this variable for us
vec2 uv = vUV.st * 2.0 - 1.0;
```

This remaps UV coordinates from `[0.0, 1.0]` to `[-1.0, 1.0]`, centering the image at `(0.0, 0.0)`.

**Note:** For non-square images, aspect ratio correction is needed.

### Camera and Image Plane Setup

```glsl
vec3 camera_position = vec3(0.0, 0.0, -5.0);
vec3 ro = camera_position;
vec3 rd = vec3(uv, 1.0);
```

- `ro`: Ray origin (camera position)
- `rd`: Ray direction (through image plane)
- The Z-component of `rd` (1.0) acts like field-of-view control

## Putting It All Together

### Complete Basic Shader

```glsl
out vec4 o_color;

float distance_from_sphere(in vec3 p, in vec3 c, float r)
{
    return length(p - c) - r;
}

vec3 ray_march(in vec3 ro, in vec3 rd)
{
    float total_distance_traveled = 0.0;
    const int NUMBER_OF_STEPS = 32;
    const float MINIMUM_HIT_DISTANCE = 0.001;
    const float MAXIMUM_TRACE_DISTANCE = 1000.0;

    for (int i = 0; i < NUMBER_OF_STEPS; ++i)
    {
        vec3 current_position = ro + total_distance_traveled * rd;

        float distance_to_closest = distance_from_sphere(current_position, vec3(0.0), 1.0);

        if (distance_to_closest < MINIMUM_HIT_DISTANCE) 
        {
            return vec3(1.0, 0.0, 0.0);
        }

        if (total_distance_traveled > MAXIMUM_TRACE_DISTANCE)
        {
            break;
        }
        total_distance_traveled += distance_to_closest;
    }
    return vec3(0.0);
}

void main()
{
    vec2 uv = vUV.st * 2.0 - 1.0;

    vec3 camera_position = vec3(0.0, 0.0, -5.0);
    vec3 ro = camera_position;
    vec3 rd = vec3(uv, 1.0);

    vec3 shaded_color = ray_march(ro, rd);

    o_color = vec4(shaded_color, 1.0);
}
```

This basic shader renders a red sphere on a black background.

## Shading

To add realistic lighting, we need surface normals. Traditional mesh normals don't exist in ray marching, so we calculate them dynamically using the SDF gradient.

### Scene Mapping Function

First, create a function to accommodate multiple objects:

```glsl
float map_the_world(in vec3 p)
{
    float sphere_0 = distance_from_sphere(p, vec3(0.0), 1.0);

    // Later we might have sphere_1, sphere_2, cube_3, etc...

    return sphere_0;
}
```

Update the ray marching loop to use this function:

```glsl
float distance_to_closest = map_the_world(current_position);
```

### Normal Calculation

Calculate normals by sampling the SDF gradient - the rate of change in each direction:

```glsl
vec3 calculate_normal(in vec3 p)
{
    const vec3 small_step = vec3(0.001, 0.0, 0.0);

    float gradient_x = map_the_world(p + small_step.xyy) - map_the_world(p - small_step.xyy);
    float gradient_y = map_the_world(p + small_step.yxy) - map_the_world(p - small_step.yxy);
    float gradient_z = map_the_world(p + small_step.yyx) - map_the_world(p - small_step.yyx);

    vec3 normal = vec3(gradient_x, gradient_y, gradient_z);

    return normalize(normal);
}
```

**GLSL Swizzling Note:** `.xyy`, `.yxy`, `.yyx` are swizzle patterns that create vec3s by reordering components.

### Visualizing Normals

To verify normals are calculated correctly, visualize them as RGB colors:

```glsl
if (distance_to_closest < MINIMUM_HIT_DISTANCE) 
{
    vec3 normal = calculate_normal(current_position);

    // Remember, each component of the normal will be in 
    // the range -1..1, so for the purposes of visualizing
    // it as an RGB color, let's remap it to the range
    // 0..1
    return normal * 0.5 + 0.5;
}
```

### Diffuse Lighting

Implement basic diffuse lighting using the calculated normals:

```glsl
if (distance_to_closest < MINIMUM_HIT_DISTANCE) 
{
    vec3 normal = calculate_normal(current_position);

    // For now, hard-code the light's position in our scene
    vec3 light_position = vec3(2.0, -5.0, 3.0);

    // Calculate the unit direction vector that points from
    // the point of intersection to the light source
    vec3 direction_to_light = normalize(current_position - light_position);

    float diffuse_intensity = max(0.0, dot(normal, direction_to_light));

    return vec3(1.0, 0.0, 0.0) * diffuse_intensity;
}
```

### Complete Shaded Shader

```glsl
out vec4 o_color;

float distance_from_sphere(in vec3 p, in vec3 c, float r)
{
    return length(p - c) - r;
}

float map_the_world(in vec3 p)
{
    float sphere_0 = distance_from_sphere(p, vec3(0.0), 1.0);

    return sphere_0;
}

vec3 calculate_normal(in vec3 p)
{
    const vec3 small_step = vec3(0.001, 0.0, 0.0);

    float gradient_x = map_the_world(p + small_step.xyy) - map_the_world(p - small_step.xyy);
    float gradient_y = map_the_world(p + small_step.yxy) - map_the_world(p - small_step.yxy);
    float gradient_z = map_the_world(p + small_step.yyx) - map_the_world(p - small_step.yyx);

    vec3 normal = vec3(gradient_x, gradient_y, gradient_z);

    return normalize(normal);
}

vec3 ray_march(in vec3 ro, in vec3 rd)
{
    float total_distance_traveled = 0.0;
    const int NUMBER_OF_STEPS = 32;
    const float MINIMUM_HIT_DISTANCE = 0.001;
    const float MAXIMUM_TRACE_DISTANCE = 1000.0;

    for (int i = 0; i < NUMBER_OF_STEPS; ++i)
    {
        vec3 current_position = ro + total_distance_traveled * rd;

        float distance_to_closest = map_the_world(current_position);

        if (distance_to_closest < MINIMUM_HIT_DISTANCE) 
        {
            vec3 normal = calculate_normal(current_position);
            vec3 light_position = vec3(2.0, -5.0, 3.0);
            vec3 direction_to_light = normalize(current_position - light_position);

            float diffuse_intensity = max(0.0, dot(normal, direction_to_light));

            return vec3(1.0, 0.0, 0.0) * diffuse_intensity;
        }

        if (total_distance_traveled > MAXIMUM_TRACE_DISTANCE)
        {
            break;
        }
        total_distance_traveled += distance_to_closest;
    }
    return vec3(0.0);
}

void main()
{
    vec2 uv = vUV.st * 2.0 - 1.0;

    vec3 camera_position = vec3(0.0, 0.0, -5.0);
    vec3 ro = camera_position;
    vec3 rd = vec3(uv, 1.0);

    vec3 shaded_color = ray_march(ro, rd);

    o_color = vec4(shaded_color, 1.0);
}
```

## Distorting the Distance Function

### Sinusoidal Displacement

One of ray marching's most powerful features is the ability to distort SDFs for interesting procedural effects:

```glsl
float map_the_world(in vec3 p)
{
    float displacement = sin(5.0 * p.x) * sin(5.0 * p.y) * sin(5.0 * p.z) * 0.25;
    float sphere_0 = distance_from_sphere(p, vec3(0.0), 1.0);

    return sphere_0 + displacement;
}
```

This creates a bumpy, organic-looking surface by adding sinusoidal displacement to the sphere.

### Advanced Distortions

**Experimental Options:**

- Different combinations of `sin()` and `cos()` functions
- Noise functions (if available): `TDSimplexNoise()`, `TDPerlinNoise()`
- Time-based animation by adding uniform time parameters
- Domain distortion by modifying the input position `p`

**Important:** Since normals are calculated dynamically from the SDF gradient, lighting remains correct regardless of distortions!

## Conclusion

This tutorial establishes a solid foundation for ray marching. While the initial results may seem simple, this framework enables advanced techniques including:

- **Multiple shapes** and complex scene composition
- **CSG operations** (unions, intersections, subtractions)
- **Animated cameras** and dynamic viewpoints  
- **Shadows and ambient occlusion** for realistic lighting
- **Volumetric rendering** and atmospheric effects
