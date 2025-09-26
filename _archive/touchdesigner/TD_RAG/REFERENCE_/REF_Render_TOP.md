---
category: REF
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- Render_TOP
- Camera_COMP
- Geometry_COMP
- Light_COMP
- GLSL_MAT
- Render_Select_TOP
- Depth_TOP
- Render_Pass_TOP
concepts:
- 3d_rendering
- graphics_pipeline
- anti_aliasing
- transparency
- depth_peeling
- order_independent_transparency
- face_culling
- multiple_render_targets
- glsl_integration
- cubemap_rendering
- stereo_rendering
prerequisites:
- 3d_scene_setup
- camera_basics
- lighting_basics
- materials_basics
- GLSL_fundamentals
workflows:
- real_time_3d_graphics
- generative_visuals
- projection_mapping
- vr_content_creation
- deferred_shading
- g-buffer_passes
- performance_optimization
keywords:
- 3d render
- scene
- graphics pipeline
- anti-alias
- MSAA
- cube map
- transparency
- depth peel
- OIT
- face culling
- material override
- polygon offset
- z-fighting
- MRT
- GLSL
- stereo
- VR
- multiple render targets
- image outputs
tags:
- 3d
- gpu
- real_time
- shader
- lighting
- material
- camera
- glsl
- mrt
- oit
- reference
- rendering_pipeline
relationships:
  GLSL_Write_a_GLSL_Material: strong
  GLSL_TouchDesigner_Deferred_Lighting: strong
  PERF_Early_Depth_Test: strong
  PERF_Optimize: medium
related_docs:
- GLSL_Write_a_GLSL_Material
- GLSL_TouchDesigner_Deferred_Lighting
- PERF_Early_Depth_Test
- PERF_Optimize
hierarchy:
  secondary: 3d_graphics
  tertiary: render_top
question_patterns: []
common_use_cases:
- real_time_3d_graphics
- generative_visuals
- projection_mapping
- vr_content_creation
---

# Render TOP

<!-- TD-META
category: REF
document_type: reference
operators: [Render_TOP, Camera_COMP, Geometry_COMP, Light_COMP, GLSL_MAT, Render_Select_TOP, Depth_TOP, Render_Pass_TOP]
concepts: [3d_rendering, graphics_pipeline, anti_aliasing, transparency, depth_peeling, order_independent_transparency, face_culling, multiple_render_targets, glsl_integration, cubemap_rendering, stereo_rendering]
prerequisites: [3d_scene_setup, camera_basics, lighting_basics, materials_basics, GLSL_fundamentals]
workflows: [real_time_3d_graphics, generative_visuals, projection_mapping, vr_content_creation, deferred_shading, g-buffer_passes, performance_optimization]
related: [GLSL_Write_a_GLSL_Material, GLSL_TouchDesigner_Deferred_Lighting, PERF_Early_Depth_Test, PERF_Optimize]
relationships: {
  "GLSL_Write_a_GLSL_Material": "strong",
  "GLSL_TouchDesigner_Deferred_Lighting": "strong",
  "PERF_Early_Depth_Test": "strong",
  "PERF_Optimize": "medium"
}
hierarchy:
  primary: "rendering"
  secondary: "3d_graphics"
  tertiary: "render_top"
keywords: [3d render, scene, graphics pipeline, anti-alias, MSAA, cube map, transparency, depth peel, OIT, face culling, material override, polygon offset, z-fighting, MRT, GLSL, stereo, VR, multiple render targets, image outputs]
tags: [3d, gpu, real_time, shader, lighting, material, camera, glsl, mrt, oit, reference, rendering_pipeline]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical reference for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: real_time_3d_graphics, generative_visuals, projection_mapping

## 🔗 Learning Path

**Prerequisites**: [3D Scene Setup] → [Camera Basics] → [Lighting Basics]
**This document**: REF reference/guide
**Next steps**: [GLSL Write a GLSL Material] → [GLSL TouchDesigner Deferred Lighting] → [PERF Early Depth Test]

**Related Topics**: real time 3d graphics, generative visuals, projection mapping

## Summary

Comprehensive reference documentation for TouchDesigner's core 3D rendering operator. Essential for understanding 3D graphics pipeline, rendering parameters, and integration with GLSL shaders. Critical for all 3D workflows and advanced rendering techniques.

## Relationship Justification

Connected to the [Camera_COMP](Camera_COMP.md) and [Geometry_COMP](Geometry_COMP.md) classes for 3D scene rendering workflows. Links to the [Light_COMP](Light_COMP.md) class for lighting setup and the [GLSL_MAT](GLSL_MAT.md) class for material rendering.

## Content

- [Summary](#summary)
- [Parameters - Render Page](#parameters---render-page)
  - [Camera(s)](#cameras)
  - [Multi-Camera Hint](#multi-camera-hint)
  - [Geometry](#geometry)
  - [Lights](#lights)
  - [Anti-Alias](#anti-alias)
  - [Render Mode](#render-mode)
  - [Positive/Negative Sides](#positivenegative-sides)
  - [UV Unwrap Options](#uv-unwrap-options)
  - [Transparency](#transparency)
  - [Depth Peel](#depth-peel)
- [Parameters - Advanced Page](#parameters---advanced-page)
  - [Render Controls](#render-controls)
  - [Color Buffers](#color-buffers)
  - [Depth Buffer](#depth-buffer)
  - [Face Culling](#face-culling)
  - [Material Override](#material-override)
  - [Polygon Depth Offset](#polygon-depth-offset)
  - [Overdraw Display](#overdraw-display)
- [Parameters - Crop Page](#parameters---crop-page)
- [Parameters - Vectors Page](#parameters---vectors-page)
- [Parameters - Samplers Page](#parameters---samplers-page)
- [Parameters - Images Page](#parameters---images-page)
- [Parameters - Common Page](#parameters---common-page)
- [Info CHOP Channels](#info-chop-channels)
  - [Common TOP Info Channels](#common-top-info-channels)
  - [Common Operator Info Channels](#common-operator-info-channels)
- [See Also](#see-also)

## Summary

The Render TOP is used to render all 3D scenes in TouchDesigner. You need to give it a Camera object and a Geometry object as a minimum.

The Geometry object needs to have a Material assigned to it. Materials can be pre-packaged ones like the [CLASS_PhongMAT], or they can be OpenGL GLSL shaders. All textures and bump maps in TouchDesigner materials are TOPs, i.e. files must be read in via [CLASS_MovieFileInTOP]s.

Rendering in TouchDesigner ties in nicely with compositing via the Render TOP and all other TOPs.

The Render TOP renders in many RGBA and single-channel formats, in 8-bit fixed-point up to to 32-bit floating point per pixel component.

It can render transparent surfaces correctly using Multi-Pass Depth Peeling. See below: [REF_OrderIndependentTransparency].

**Multiple Cameras**: The Render TOP is able to render multiple cameras (more quickly than separately) in a single node. You specify multiple cameras in one Camera parameter, and use [CLASS_RenderSelectTOP] to pull out those camera results. This feature is even faster on GPUs that support Multi-Camera Rendering.

**Multiple Images out**: The Render TOP, working with the [CLASS_GLSLMAT]s, can output multiple image at arbitrary formats, through the Images page.

**NOTE**: If you are doing non-realtime GPU-intensive renders (ones that take multiple seconds to render a single SOP), see the note in [REF_WindowsGPUDriverTimeouts] in the [CLASS_MovieFileOutTOP].

## Parameters - Render Page

### Camera(s)

**Camera(s)** `camera` - Specifies which Cameras to look through when rendering the scene. You can specify multiple cameras and retrieve each camera image using the [CLASS_RenderSelectTOP].

### Multi-Camera Hint

**Multi-Camera Hint** `multicamerahint` - Helps the Render TOP optimize rendering when multiple cameras are used. Controls the Multi-Camera Rendering behavior for this node.

- **Automatic** `automatic` - The node will decide based on the GPU and setup if Multi-Camera Rendering can be used and enable it if possible. Currently Multi-Camera rendering works for 2D and Cube Map renders on supported GPUs. For 2D renders multiple cameras can not be rendered in a single pass if their 'Camera Light Mask' parameters don't result in the same lights being used in the scene. Use of Depth Peeling or Order Independent Transparency will also disable Multi-Camera rendering.
- **Off (One Pass Per Camera)** `off` - Forces Multi-Camera Render to be disabled, so each camera is rendered one pass at a time.
- **X-Offset Stereo Cameras** `stereocameras` - Should be set only if the pair of cameras have transform/projection matrices that result in a difference only in the X-axis after being applied, as is the case for most VR headsets. Other differences between the cameras such as FOV, near/far plane etc will be ignored, and the values form the first camera will be used. This hint allows the TOP to run faster for this particular case, when appropriate hardware is available.

### Geometry

**Geometry** `geometry` - Specifies which Geometry will be included in the rendered scene. You can use [REF_PatternMatching] to specify objects using patterns. Example: `geo* ^geo7` will render all Geometry components whose names start with geo except geo7.

### Lights

**Lights** `lights` - Specifies which Lights will be used to render the scene. You can use [REF_PatternMatching] here as well.

### Anti-Alias

**Anti-Alias** `antialias` - Sets the level of anti-aliasing in the scene. Setting this to higher values uses more graphics memory.

- **1x (Off)** `aa1`
- **2x** `aa2`
- **4x** `aa4`
- **8x (Medium)** `aa8mid`
- **8x (High)** `aa8high`
- **16x (Low)** `aa16low`
- **16x (Medium)** `aa16mid`
- **16x (High)** `aa16high`
- **32x** `aa32`

### Render Mode

**Render Mode** `rendermode` - You can render different projections: normal 2D, Cube Map, Fish Eye (180), or Dual Paraboloid. The Cube Map renders 6 views as needed for environment maps in the [CLASS_PhongMAT] and [CLASS_EnvironmentLightCOMP].

See also the [CLASS_CubeMapTOP] and the [CLASS_ProjectionTOP].

- **2D** `render2d` - The standard 2D render mode.
- **Cube Map** `cubemap` - Does 6 renders, each with 90 degree FOV. The camera is automatically turned to face down each of the 6 axis, with the -Z axis being where the camera is facing to start.
- **Fish-Eye (180)** `fisheye180` - A single 2D render that warps the projection so it renders 180 degree FOV in all directions from where the camera is pointing (90 to each side). Since this render doesn't preserve straight lines, geometry that has large polygons that cover a lot of the viewport will suffer from artifacts. Well tesselated geometry is best for this mode.
- **Dual Paraboloid** `dualparaboloid` - Similar to Fisheye, but renders twice at 180 degrees, once forward and once backwards. The projection isn't the same as fisheye either. This is a legacy mode that isn't currently consumed by anything in TouchDesigner, but there are articles online that discuss how to sample from it.
- **UV Unwrap** `uvunwrap` - A 2D render that uses the UV coordinates of the geometry to unwrap it across the output image.
- **Cube Map (Omnidirectional Stereo)** `cubemapods` - This mode renders a stereo pair (two eyes) of cubemaps that can be used to record out stereo 360 videos. You can obtain the second eye's output by using a [CLASS_RenderSelectTOP] and selecting Camera Index=1. The [CLASS_CameraCOMP]'s IPD Shift parameter is used here to offset each eye viewport.

### Positive/Negative Sides

**Positive Sides** `posside` - When Render Mode is Cube Map, specify which sides if the cube map are rendered, +X, +Y, or +Z.

**Negative Sides** `negside` - When Render Mode is Cube Map, specify which sides if the cube map are rendered, -X, -Y, or -Z.

### UV Unwrap Options

**UV Unwrap Coord** `uvunwrapcoord` - When Render Mode is UV Unwrap Coord, select which Texture Layer the coordinates are rendered to.

- **Texture Layer 0 (uv[0-2])** `uv0`
- **Texture Layer 1 (uv[3-5])** `uv1`
- **Texture Layer 2 (uv[6-8])** `uv2`
- **Texture Layer 3 (uv[9-11])** `uv3`
- **Texture Layer 4 (uv[12-14])** `uv4`
- **Texture Layer 5 (uv[15-17])** `uv5`
- **Texture Layer 6 (uv[18-20])** `uv6`
- **Texture Layer 7 (uv[21-23])** `uv7`

**UV Unwrap Coord Attribute** `uvunwrapcoordattrib`

### Transparency

**Transparency** `transparency` - Helps to render transparent geometry in proper depth order. More in-depth discussion available in the [REF_Transparency] article.

- **Sorted Draw with Blending** `sortedblending` - See [REF_TransparencySortingGeometry]
- **Order Independent Transparency** `orderind` - See [REF_TransparencyOrderIndependent]
- **Alpha-to-Coverage** `alphatocoverage` - See [REF_TransparencyAlphaToCoverage]

### Depth Peel

**Depth Peel** `depthpeel` - Depth peeling is a technique used as part of Order-Independent Transparency, but this parameter allows you to use it in a different way. This parameter enables rendering depth-peels, but without combining all the layers using blending to create order independent transparency. Instead is keeps all the layers separate and they can be retrieved using a [CLASS_RenderSelectTOP]. Depth peeling is done by first rendering rendering geometry normally and saving that image and depth. Then another render is done but the closest pixels that were occluded by the previous pass are written to the color buffer instead. This can be done multiple times, each time peeling back farther into the scene. If you are rendering a sphere the first render will be the outside of the sphere, and the second peel layer will be the back-inside of the sphere.

**Transparency/Peel Layers** `transpeellayers` - Number of passes the renderer will use when Order Independant Transparency is turned on.

## Parameters - Advanced Page

### Render Controls

**Render** `render` - Enables rendering; 1 = on, 0 = off.

**Dither** `dither` - Dithers the rendering to help deal with banding and other artifacts created by precision limitations of 8-bit displays.

**Color Output Needed** `coloroutputneeded` - This is an optimization if you don't actually need the color result from this pass. Turning this off avoids a copy from the offscreen render buffer to the TOP's texture. When anti-aliasing is enabled, turning this off will also avoid 'resolving' the anti-aliasing.

**Draw Depth Only** `drawdepthonly` - This will cause the render to only draw depth values to the depth buffer. No color values will be created. To make use of the depth buffer, use the [CLASS_DepthTOP].

### Color Buffers

**# of Color Buffers** `numcolorbufs` - Any shader you write can output to more than one RGBA buffer at a time. For GLSL 3.3+ you would use the layout(location = 1) specifier on an out variable in the pixel shader to write to the 2nd buffer. In GLSL 1.2 instead of writing to gl_FragColor in your shader, you write to gl_FragData[i] where i is the color buffer index you want to write the value to.

**Allow Blending for Extra Buffers** `allowbufblending` - Controls if blending (as enabled by the MAT common page setting) will be enabled for extra buffers beyond the first one. Often the extra buffers are used to write other types of information such as normals or positions, where blending wouldn't be desirable.

### Depth Buffer

**Depth Buffer Format** `depthformat` - Use either a 24-bit Fixed-Point or 32-bit Floating-Point depth buffer (single channel image).

### Face Culling

**Cull Face** `cullface` - Front Faces, Back Faces, Both Faces, Neither. Will cause the render to avoid rendering certain polygon faces depending on their orientation to the camera. Refer to [REF_BackFaceCulling] for more information.

### Material Override

**Override Material** `overridemat` - This allows you to specify a material that will be applied to every Geometry that is rendered in the Render TOP. It is useful for pre-processing passes where we are outputting information about the geometry rather then lighting them and outputting RGB.

### Polygon Depth Offset

**Polygon Depth Offset** `polygonoffset` - This feature pushes the polygons back into space a tiny fraction. This is useful when you are rendering two polygons directly ontop of each other and are experiencing Z-Fighting. Refer to [REF_PolygonDepthOffset] for more information. This is also an important feature when doing shadows.

**Offset Factor** `polygonoffsetfactor` - Adds an offset to the Z value that depends on how sloped the surface is to the viewer.

**Offset Units** `polygonoffsetunits` - Adds a constant offset to the Z value.

### Overdraw Display

**Display Overdraw** `overdraw` - This feature visually shows the overdraw in the scene. Refer to the [REF_EarlyDepthTest] article for more information. In particular the Analyzing Overdraw section.

**Overdraw Limit** `overdrawlimit` - This value quantizes the outputted color value to some # of overdraws. Refer to the [REF_EarlyDepthTest] for more information.

## Parameters - Crop Page

Cropping here occurs using the projection matrix. It reduces the amount of the output render that is visible, without changing the resolution. It's particuarly useful to create sub-portion of an overall render in different buffers, such as for rendering across multiple instances of TouchDesigner. Be careful to set the aspect ratio of the Render TOP to match the 'real' aspect of the overall output image, not the aspect of this subsection. Otherwise the projection will be stretched incorrectly.

**Crop Left** `cropleft` - Positions the left edge of the rendered image.

**Crop Left Unit** `cropleftunit` - Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio).

**Crop Right** `cropright` - Positions the right edge of the rendered image.

**Crop Right Unit** `croprightunit` - Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio).

**Crop Bottom** `cropbottom` - Positions the bottom edge of the rendered image.

**Crop Bottom Unit** `cropbottomunit` - Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio).

**Crop Top** `croptop` - Positions the top edge of the rendered image.

**Crop Top Unit** `croptopunit` - Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio).

## Parameters - Vectors Page

These vectors will be passed to all [CLASS_GLSLMAT]s used in the render. They allow for global parameters to more easily be passed to many [CLASS_GLSLMAT]s from a single spot.

**Vector** `vec` - Sequence of uniform name and value pairs.

**Uniform Name** `vec0name` - The uniform name, as declared in the shader.

**Value** `vec0value` - The value to assign the vector uniform.

## Parameters - Samplers Page

These samplers will be passed to all [CLASS_GLSLMAT]s used in the render. They allow for global parameters to more easily be passed to many [CLASS_GLSLMAT]s from a single spot.

**Uniform Name** `uni0name` - The uniform name, as declared in the shader.

**Sampler** `sampler` - Sequence of sampler parameters, including uniform name, TOP reference, and sampling parameters.

**Sampler Name** `sampler0name` - This is the sampler name that the GLSL program will use to sample from this TOP. The samplers need to be declared as the same dimensions as the TOP (sampler2D for a 2D TOP, sampler3D for 3D TOP).

**TOP** `sampler0top` - This is the TOP that will be referenced by the above sampler name above it.

**Extend U/V/W** `sampler0extendu` / `sampler0extendv` / `sampler0extendw` - Texture coordinate wrapping options:

- **Hold** `hold`
- **Zero** `zero`
- **Repeat** `repeat`
- **Mirror** `mirror`

**Filter** `sampler0filter` - Texture filtering options:

- **Nearest** `nearest`
- **Linear** `linear`
- **Mipmap Linear** `mipmaplinear`

**Anisotropic Filter** `sampler0anisotropy` - Anisotropic filtering options:

- **Off** `off`
- **2x** `2x`
- **4x** `4x`
- **8x** `8x`
- **16x** `16x`

## Parameters - Images Page

Images are texture data that can be both read and written to at arbitrary pixels during a render operation, using a [CLASS_GLSLMAT], via the imageStore() and imageLoad(). You can obtain the results of the Image after the render is completed using a [CLASS_RenderSelectTOP]. The images will automatically be declared for you inside of the shader, you should not declare them yourself (as you do for other uniforms). This is because there is a lot of extra decoration required for the image uniforms. Currently when compiling in the [CLASS_GLSLMAT] itself your code will result in an error, since the images are not available there. However when you apply your MAT to a geometry and render it via the Render TOP, a new version of your shader will be included that has that image declared. Refer to [REF_WriteGLSLMaterialImageOutputs] for more information.

**Image** `image` - A sequence of parameters to control image outputs available for the [CLASS_GLSLMAT]s.

**Name** `image0name` - The uniform name for the image.

**Array Length** `image0arraylength` - If this value is 1 or greater, then the uniform is declared as an array and should be accessed using []. If this is 0 then it is not an array.

**Resolution** `image0res` - The resolution the image should be.

**Format** `image0format` - The pixel format the image should be allocated as. Options include various bit depths and channel configurations from 8-bit fixed to 32-bit float in RGBA, RGB, RG, Mono, and Alpha formats.

**Type** `image0type` - Specify what type of texture to create with the image output:

- **2D Texture** `texture2d`
- **2D Texture Array** `texture2darray`
- **3D Texture** `texture3d`
- **Cube Texture** `texturecube`

**Depth** `image0depth` - Set the depth when output Type is 2D Texture Array or 3D Texture.

**Access** `image0access` - Controls how the output textures will be accessed:

- **Write Only** `writeonly`
- **Read-Write** `readwrite`

## Parameters - Common Page

**Output Resolution** `outputresolution` - Quickly change the resolution of the TOP's data. Options include Use Input, fractional multipliers (Eighth, Quarter, Half, 2X, 4X, 8X), Fit Resolution, Limit Resolution, and Custom Resolution.

**Resolution** `resolution` - Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size.

**Use Global Res Multiplier** `resmult` - Uses the Global Resolution Multiplier found in Edit>[REF_Preferences]>TOPs. This multiplies all the TOPs resolutions by the set amount.

**Output Aspect** `outputaspect` - Sets the image aspect ratio allowing any textures to be viewed in any size. Options include Use Input, Resolution, and Custom Aspect.

**Input Smoothness** `inputfiltertype` - Controls pixel filtering on the input image of the TOP:

- **Nearest Pixel** `nearest` - Uses nearest pixel or accurate image representation.
- **Interpolate Pixels** `linear` - Uses linear filtering between pixels.
- **Mipmap Pixels** `mipmap` - Uses mipmap filtering when scaling images.

**Fill Viewer** `fillmode` - Determine how the TOP image is displayed in the viewer. Options include Use Input, Fill, Fit Horizontal, Fit Vertical, Fit Best, Fit Outside, and Native Resolution.

**Viewer Smoothness** `filtertype` - Controls pixel filtering in the viewers.

**Passes** `npasses` - Duplicates the operation of the TOP the specified number of times.

**Channel Mask** `chanmask` - Allows you to choose which channels (R, G, B, or A) the TOP will operate on.

**Pixel Format** `format` - Format used to store data for each channel in the image. Refer to [REF_PixelFormats] for more information.

## Info CHOP Channels

Extra Information for the Render TOP can be accessed via an [CLASS_InfoCHOP].

### Common TOP Info Channels

- `resx` - Horizontal resolution of the TOP in pixels.
- `resy` - Vertical resolution of the TOP in pixels.
- `aspectx` - Horizontal aspect of the TOP.
- `aspecty` - Vertical aspect of the TOP.
- `depth` - Depth of 2D or 3D array if this TOP contains a 2D or 3D texture array.
- `gpu_memory_used` - Total amount of texture memory used by this TOP.

### Common Operator Info Channels

- `total_cooks` - Number of times the operator has cooked since the process started.
- `cook_time` - Duration of the last cook in milliseconds.
- `cook_frame` - Frame number when this operator was last cooked relative to the component timeline.
- `cook_abs_frame` - Frame number when this operator was last cooked relative to the absolute time.
- `cook_start_time` - Time in milliseconds at which the operator started cooking in the frame it was cooked.
- `cook_end_time` - Time in milliseconds at which the operator finished cooking in the frame it was cooked.
- `cooked_this_frame` - 1 if operator was cooked this frame.
- `warnings` - Number of warnings in this operator if any.
- `errors` - Number of errors in this operator if any.

## See Also

[REF_Rendering], [REF_RenderingCategory], [CLASS_RenderPassTOP], [REF_WhyIsMyRenderBlack], [CLASS_renderTOP_Class]
