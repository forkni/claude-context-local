---
category: REF
document_type: troubleshooting
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- Render_TOP
- Camera_COMP
- Geometry_COMP
- Light_COMP
- Constant_MAT
- SOP_to_DAT
- Sphere_SOP
- Constant_TOP
- Base_COMP
concepts:
- rendering_troubleshooting
- scene_visibility
- lighting_setup
- camera_setup
- geometry_flags
- material_properties
- operator_flags
- debugging_techniques
prerequisites:
- rendering_basics
- 3d_scene_setup
workflows:
- debugging_3d_scenes
- project_troubleshooting
keywords:
- render black
- nothing rendering
- black screen
- 3d scene not showing
- troubleshoot render
- debug rendering
- visibility
- lighting
- camera
- geometry
- material
- alpha
- checkerboard
- no output
tags:
- 3d
- rendering
- debug
- troubleshooting
- visibility
- lighting
- camera
- alpha
relationships:
  REF_Render_TOP: strong
  Camera_COMP: strong
  Light_COMP: strong
  Geometry_COMP: strong
  REF_Transparency: medium
related_docs:
- REF_Render_TOP
- REF_Transparency
- REF_BackFaceCulling
hierarchy:
  secondary: troubleshooting
  tertiary: black_screen
question_patterns: []
common_use_cases:
- debugging_3d_scenes
- project_troubleshooting
---

# Why is My Render Black

<!-- TD-META
category: REF
document_type: troubleshooting
operators: [Render_TOP, Camera_COMP, Geometry_COMP, Light_COMP, Constant_MAT, SOP_to_DAT, Sphere_SOP, Constant_TOP, Base_COMP]
concepts: [rendering_troubleshooting, scene_visibility, lighting_setup, camera_setup, geometry_flags, material_properties, operator_flags, debugging_techniques]
prerequisites: [rendering_basics, 3d_scene_setup]
workflows: [debugging_3d_scenes, project_troubleshooting]
related: [REF_Render_TOP, REF_Transparency, REF_BackFaceCulling]
relationships: {
"REF_Render_TOP": "strong", 
"Camera_COMP": "strong", 
"Light_COMP": "strong", 
"Geometry_COMP": "strong", 
"REF_Transparency": "medium"
}
hierarchy:
  "primary": "rendering"
  "secondary": "troubleshooting"
  "tertiary": "black_screen"
keywords: [render black, nothing rendering, black screen, 3d scene not showing, troubleshoot render, debug rendering, visibility, lighting, camera, geometry, material, alpha, checkerboard, no output]
tags: [3d, rendering, debug, troubleshooting, visibility, lighting, camera, alpha]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical troubleshooting for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: debugging_3d_scenes, project_troubleshooting

## 🔗 Learning Path

**Prerequisites**: [Rendering Basics] → [3D Scene Setup]
**This document**: REF reference/guide
**Next steps**: [REF Render TOP] → [REF Transparency] → [REF BackFaceCulling]

**Related Topics**: debugging 3d scenes, project troubleshooting

## Summary

Troubleshooting guide for debugging black screen issues in 3D rendering, covering common visibility, lighting, and camera problems.

## Relationship Justification

Strong connection to Render TOP and lighting concepts as core troubleshooting areas. Strong connection to lighting fundamentals as many black screen issues are lighting-related.

## Content

- [Introduction](#introduction)
- [Basic Visibility Check](#basic-visibility-check)
- [Lighting Issues](#lighting-issues)
- [Camera and View Problems](#camera-and-view-problems)
- [Geometry Rendering Settings](#geometry-rendering-settings)
- [SOP-Level Troubleshooting](#sop-level-troubleshooting)
- [Material and Texture Issues](#material-and-texture-issues)
- [Component Hierarchy Issues](#component-hierarchy-issues)
- [Advanced Troubleshooting](#advanced-troubleshooting)
- [Other Common Issues](#other-common-issues)

## Introduction

Often, your [CLASS_RenderTOP] is all black, though you expect to see something there. Here's are things to try to find out why you don't see what you expect.

## Basic Visibility Check

Check to see if anything is being rendered: Go to Edit -> [REF_Preferences] on the TOPs page, the Viewer Background is set to show Checker Board as the background (vs Black).

Then in your [CLASS_RenderTOP], if you see all-checkerboard, then there is indeed nothing rendering there. If it has black, there there is something rendering but isn't getting lit.

## Lighting Issues

If you see black instead of checkerboard, there's something rendering but it's not properly lit:

- Add a light, and make sure it is in front of the geometry.
- Change the material of the object to have Emit color, or Ambient color. Or change the Material to a Constant MAT with a default white color.
- For lights to have an effect, the display flag in the lights needs to be on.

## Camera and View Problems

Maybe the geometry is outside the field of view of the camera:

- Change the [CLASS_RenderTOP]'s Render Mode parameter to Cube Map. Here you see in all directions. If you see nothing in the Cube Map render...
- Check the Near and Far clipping planes of the camera. In your [CLASS_CameraCOMP], is your Near and Far parameter set to reasonable values that bound your 3D geometry? For large scenes with cameras at distances over 1000, your geometry may be outside the near/far clipping planes.
- You may want to replace the Camera that the [CLASS_RenderTOP] is using with a default [CLASS_CameraCOMP].

## Geometry Rendering Settings

Next it's time to check what's rendering:

- Check the Geometry parameter of the [CLASS_RenderTOP]. It should have a pattern to all your expected objects to render. To make sure you catch everything, put "*" into the Geometry parameter. If you still see nothing...
- Check that you are rendering Geometry components. On the Geometry components you expect to see, make sure their Render flag is on (purple).
- That's not enough. The Geometry components also have a Render parameter. Make sure the Render parameter is on.
- And that is not enough. For each [CLASS_GeometryCOMP], inside the component, make sure, for all the SOPs in your network that you expecting to render, that the Render flag is on at the bottom of the node.

## SOP-Level Troubleshooting

If you have done all that and you still see nothing, check the SOP that you expect to see:

- Middle mouse click to see the info on the SOP. Is the bounding box what you expect?
- Check to see if there is point or vertex color, in particular, make sure alpha is not set to 0. Or it's all black.
- One way to see the numbers in your SOP is to attach the SOP to a "[CLASS_SOPtoDAT]" operator and look at the different columns. Sometimes Normals that are 0 will give black results.
- If you still see nothing, put a [CLASS_SphereSOP] in your network and turn on its Render flag (and Display flag, so you can see it in a camera viewer).

## Material and Texture Issues

- Make sure Materials of your objects have a non-0 Alpha parameter setting.
- Make sure Materials that have texture maps contain textures with non-0 alpha. Replace your textures with white [CLASS_ConstantTOP]s.

## Component Hierarchy Issues

- Lights/cameras cannot be nested in [CLASS_BaseCOMP]s, as a base will exclude them from the Geometry Viewer.
- It might also be the case that the network path of the geometry viewer is not at a level from where all lights are visible.

## Advanced Troubleshooting

- Try creating a new empty [CLASS_RenderTOP], then adding in the objects / cameras that you expect to see. Try creating a default [CLASS_GeometryCOMP], default [CLASS_LightCOMP].

## Other Common Issues

Other things to check:

- Back-Face Culling settings
- Blend Modes on [CLASS_RenderTOP] (though unlikely)
