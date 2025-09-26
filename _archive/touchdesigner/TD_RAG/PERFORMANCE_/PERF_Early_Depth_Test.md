---
title: "Early Depth Test"
category: PERF
document_type: guide
difficulty: intermediate
time_estimate: 20-30 minutes

# Enhanced metadata
user_personas: ["performance_engineer", "shader_programmer", "technical_artist", "advanced_user"]
completion_signals: ["understands_depth_testing", "optimizes_gpu_performance", "can_reduce_overdraw", "manages_rendering_optimization"]

operators:
- Render_TOP
- Render_Pass_TOP
- GLSL_MAT
- Phong_MAT
- Light_COMP
concepts:
- rendering_optimization
- gpu_performance
- depth_testing
- overdraw_reduction
- pixel_shading
- occlusion_culling
- gpu_bottleneck_analysis
prerequisites:
- rendering_basics
- 3d_scene_setup
- GLSL_fundamentals
workflows:
- performance_tuning
- complex_scene_optimization
- real-time_rendering
- gpu_optimization_workflows
keywords:
- overdraw
- depth buffer
- pixel shader
- fill rate
- occlusion
- culling
- gpu optimization
- draw order
- z-buffer
- gl_FragDepth
- early depth test
- rendering performance
tags:
- gpu
- real_time
- rendering
- optimization
- 3d
- glsl
- depth
- performance
- overdraw
relationships:
  PERF_Optimize: strong
  GLSL_Write_a_GLSL_Material: medium
  GLSL_TouchDesigner_Deferred_Lighting: medium
related_docs:
- PERF_Optimize
- GLSL_Write_a_GLSL_Material
- GLSL_TouchDesigner_Deferred_Lighting
# Enhanced search optimization
search_optimization:
  primary_keywords: ["depth", "optimization", "gpu", "overdraw"]
  semantic_clusters: ["gpu_optimization", "rendering_techniques", "performance_optimization"]
  user_intent_mapping:
    beginner: ["what is depth testing", "basic gpu optimization", "rendering basics"]
    intermediate: ["depth optimization", "overdraw reduction", "gpu performance"]
    advanced: ["advanced rendering optimization", "complex scene optimization", "shader optimization"]

hierarchy:
  secondary: gpu_optimization
  tertiary: depth_optimization
question_patterns:
- How to optimize performance?
- TouchDesigner performance tips?
- Bottleneck identification?
- Real-time optimization?
common_use_cases:
- performance_tuning
- complex_scene_optimization
- real-time_rendering
- gpu_optimization_workflows
---

# Early Depth-Test

<!-- TD-META
category: PERF
document_type: guide
operators: [Render_TOP, Render_Pass_TOP, GLSL_MAT, Phong_MAT, Light_COMP]
concepts: [rendering_optimization, gpu_performance, depth_testing, overdraw_reduction, pixel_shading, occlusion_culling, gpu_bottleneck_analysis]
prerequisites: [rendering_basics, 3d_scene_setup, GLSL_fundamentals]
workflows: [performance_tuning, complex_scene_optimization, real-time_rendering, gpu_optimization_workflows]
related: [PERF_Optimize, GLSL_Write_a_GLSL_Material, GLSL_TouchDesigner_Deferred_Lighting]
relationships: {
  "PERF_Optimize": "strong", 
  "GLSL_Write_a_GLSL_Material": "medium",
  "GLSL_TouchDesigner_Deferred_Lighting": "medium"
}
hierarchy:
  primary: "optimization"
  secondary: "gpu_optimization"
  tertiary: "depth_optimization"
keywords: [overdraw, depth buffer, pixel shader, fill rate, occlusion, culling, gpu optimization, draw order, z-buffer, gl_FragDepth, early depth test, rendering performance]
tags: [gpu, real_time, rendering, optimization, 3d, glsl, depth, performance, overdraw]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Performance optimization guide for real-time systems
**Difficulty**: Intermediate
**Time to read**: 20-30 minutes
**Use for**: performance_tuning, complex_scene_optimization, real-time_rendering

**Common Questions Answered**:

- "How to optimize performance?" → [See relevant section]
- "TouchDesigner performance tips?" → [See relevant section]
- "Bottleneck identification?" → [See relevant section]
- "Real-time optimization?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Rendering Basics] → [3D Scene Setup] → [Glsl Fundamentals]
**This document**: PERF reference/guide
**Next steps**: [PERF Optimize] → [GLSL Write a GLSL Material] → [GLSL TouchDesigner Deferred Lighting]

**Related Topics**: performance tuning, complex scene optimization, real-time rendering

## Summary

Specialized rendering optimization technique focusing on GPU performance through depth testing optimization. Essential for complex 3D scenes with heavy overdraw.

## Relationship Justification

Strong connection to general optimization guide. Links to GLSL material and deferred lighting guides since depth optimization is crucial for advanced rendering techniques.

## Content

- [Overview](#overview)
- [Early Depth-Test Example](#early-depth-test-example)
- [Taking Advantage of Early Depth-Test](#taking-advantage-of-early-depth-test)
- [Analyzing Overdraw](#analyzing-overdraw)
- [Conflicts with Transparency](#conflicts-with-transparency)

## Overview

On modern GPUs with high quality shaders, the majority of work is done shading pixels. This means for every pixel drawn the GPU must do X amount of work. Consequently the more pixels that are drawn, the more work the GPU needs to do. It is very common that a synth will become pixel-shader bottlenecked due to the amount of pixels that are getting drawn and complexity of the shader. To find out if your synth is pixel shader bottlenecked, simply turn down the resolution of the Renders or reduce the anti-alias level. If the frame-rate improves that usually means the synth is pixel-shader bottlenecked. If the frame-rate doesn't change then the synth isn't pixel shader bottlenecked, so time should be spent elsewhere speeding up the synth rather then worrying about the pixel-shader load.

The Early Depth-Test is a feature present on most GPUs designed to reduce the amount of pixels that need to be shaded. It is a test that is done after the vertex shader (so after the geometry is transformed into its final render position), but before the pixel shader does it's work on that polygon. The Early Depth-Test then compares the z-value of each pixel that is about to be drawn with the ones that have already been drawn. If it determines the pixel would fail the Depth-Test and get discarded, it just discards it right then, before the pixel shader does any work on it. If the Early Depth-Test didn't exist the pixel would have been shaded, and then the normal Depth-Test would have discarded it anyway, making the all of the work done shading the pixel pointless. When a pixel is shaded but ends up getting overwritten by another pixel, it's known as Overdraw.

## Early Depth-Test Example

Here is a .toe file that illustrates how Early Depth-Test works.

Media:earlydepthtest.toe

Open up the file and make the synth play forward. Take note of the frame-rate displayed in the Perform CHOP. If you go into /geo1 you'll notice the geometry that is being rendered is a large stack of simple grids. This is very simple geometry, just a bunch of polygons. Despite the low polygon count, the synth is running a little slow. Now rotate the /geo1 180 in the X direction. The scene shouldn't change much as you've simply flipped the stack of grids, but take note of the frame-rate now, it should be significantly faster. It's still rendering the same number of polygons, and using the same shader, and the scene looks about the same, but there is a huge speed difference, why? Well, originally the farthest grid was getting rendered first, followed by the next farthest and so on. So, the GPU draws and shades the farthest grid, but then the next grid is drawn and it ends up completely occluding the previous grid. So all of the work done shading the previous grid was a waste. In this example every grid gets drawn, shaded and then occluded by a closer grid (except for the closest one). In fact in this case, only the closest grid matters as that is the only one we see. When we rotate the geometry 180 degrees, the grid that's closest gets drawn first. Every grid that gets drawn afterward ends up getting discarded by the Early Depth-Test because the GPU determines that they won't be visible anyway.

## Taking Advantage of Early Depth-Test

Early Depth-Test is enabled by default on GPUs. There is no toggle to turn it on and off. Instead the GPU will automatically turn it off if features that aren't compatible with Early Depth-Test are enabled. Unfortunately which features will cause Early Depth-Test to be disabled changes from vendor to vendor and from card model to card model (also different drivers can behave differently). This makes the use of this feature somewhat black-magic when doing complex custom shader. If you are just using the Phong MAT and not doing anything too tricky though, Early Depth-Test will be on. Unfortunately, there is no way for Touch or the user to query the GPU to find out if Early Depth-Test is enabled or not.

One thing that is guaranteed to disable the Early Depth-Test is writing to the gl_FragDepth value in a GLSL MAT. This is not to say that you shouldn't do this, but avoid it unless needed.

On some cards enabling the Alpha-Test, Transparency or using a non-default Depth-Test function in the Depth-Test may disable the Early Depth-Test.

If Early Depth-Test is on, the only thing you need to do is draw your geometry in closest to farthest order. If done perfectly (which is nearly impossible though), the only pixels the GPU will shade are the ones that are visible in the final image.

## Analyzing Overdraw

In a complex scene it may be difficult to know how much overdraw is occurring and which objects are drawing in a less than optimal order. To aid with this there is a feature in the Render and Render Pass TOPs on their 'Advanced' page that displays the amount of overdraw that is occurring on a per-pixel basis.

Re-Open up the earlydepthtest.toe example that was given earlier in this article. On the 'Advanced' page turn on the 'Display Overdraw' option. What the Render TOP is now displaying is a representation of how much overdraw has occurred on each pixel. The brighter the pixel color is, the more overdraw has occurred on that pixel. Because its possible for a pixel to be draw to any number of times, the 'Overdraw Limit' parameter quantizes the number of overdraws within a range. If the 'Overdraw Limit' is set to 10, and a pixel is 100% white then that pixel has been drawn to 10 or more times. If the pixel is 70% white, than the pixel has been drawn to 7 times. Try turning up 'Overdraw Limit' parameter, notice how some pixels remain 100% white, even with a 'Overdraw Limit' of 100. That means those pixels have been drawn to 100 or more times. Now rotate the geometry 180 around the X axis as we did before. You'll notice that the overdraw display is now a solid grey. In fact you will only get pixels 100% white if you turn the 'Overdraw Limit' to 1. The most ideal situation would be the entire scene be 50% white (medium grey) when the 'Overdraw Limit' is set to 2. That means that every pixel has only been drawn to once (or possibly not at all, if they are 0% white), which is the best possible setup.

Note: This feature is currently not compatible with GPU based deforms (the Deform page on MATs). If you turn on this feature any object that is using deforms will be drawn without deforms (return to its default position).

## Conflicts with Transparency

A big catch with a scene optimized to take advantage of Early Depth-Test is that the process is completely opposite of how the scene needs to be rendered to take advantage of Transparency. Transparency requires that objects be drawn in farthest to closest order. In the end its a trade-off between speed and visual quality that the user must decide on. A good compromise is to draw all of your opaque objects first in closest to farthest order. Then draw your transparency objects in farthest to closest order. You can use a Render Pass TOP to split up the work to make it easier to deal with.
