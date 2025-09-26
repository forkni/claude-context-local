---
category: REF
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- Cache_TOP
- Info_CHOP
- Feedback_TOP
- Cache_SOP
- Timer_CHOP
concepts:
- gpu_memory_caching
- image_sequencing
- frame_delay
- frame_looping
- freezing_images
- pre-filling
- texture_buffering
prerequisites:
- TOP_basics
- gpu_memory_concepts
- rendering_fundamentals
workflows:
- video_delay_effects
- feedback_loops
- performance_optimization
- frame_scrubbing
- stutter_effects
- time_machine_effects
keywords:
- cache
- buffer
- delay
- frame buffer
- image sequence
- freeze
- loop
- VRAM
- GPU
- pre-fill
- time machine
- output index
- interpolation
- step size
tags:
- gpu
- real_time
- buffer
- delay
- cache
- vram
- performance
relationships:
  CLASS_Feedback_TOP: strong
  REF_PreFilling: strong
  CLASS_Cache_SOP: medium
  PERF_Optimize: medium
  REF_Pixel_Formats: weak
related_docs:
- REF_PreFilling
- CLASS_Feedback_TOP
- CLASS_Cache_SOP
- PERF_Optimize
- REF_Pixel_Formats
hierarchy:
  secondary: image_filters
  tertiary: cache
question_patterns: []
common_use_cases:
- video_delay_effects
- feedback_loops
- performance_optimization
- frame_scrubbing
---

# Cache TOP

<!-- TD-META
category: REF
document_type: reference
operators: [Cache_TOP, Info_CHOP, Feedback_TOP, Cache_SOP, Timer_CHOP]
concepts: [gpu_memory_caching, image_sequencing, frame_delay, frame_looping, freezing_images, pre-filling, texture_buffering]
prerequisites: [TOP_basics, gpu_memory_concepts, rendering_fundamentals]
workflows: [video_delay_effects, feedback_loops, performance_optimization, frame_scrubbing, stutter_effects, time_machine_effects]
related: [REF_PreFilling, CLASS_Feedback_TOP, CLASS_Cache_SOP, PERF_Optimize, REF_Pixel_Formats]
relationships: {
  "CLASS_Feedback_TOP": "strong",
  "REF_PreFilling": "strong",
  "CLASS_Cache_SOP": "medium",
  "PERF_Optimize": "medium",
  "REF_Pixel_Formats": "weak"
}
hierarchy:
  primary: "tops"
  secondary: "image_filters"
  tertiary: "cache"
keywords: [cache, buffer, delay, frame buffer, image sequence, freeze, loop, VRAM, GPU, pre-fill, time machine, output index, interpolation, step size]
tags: [gpu, real_time, buffer, delay, cache, vram, performance]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical reference for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: video_delay_effects, feedback_loops, performance_optimization

## 🔗 Learning Path

**Prerequisites**: [Top Basics] → [Gpu Memory Concepts] → [Rendering Fundamentals]
**This document**: REF reference/guide
**Next steps**: [REF PreFilling] → [CLASS Feedback TOP] → [CLASS Cache SOP]

**Related Topics**: video delay effects, feedback loops, performance optimization

## Summary

Reference documentation for Cache TOP operator, covering GPU memory caching, frame delay effects, and performance optimization through image sequence buffering.

## Relationship Justification

Forms performance trio with [PERF_Optimize] and [PERF_Performance_Monitor_Dialog]. Strong connection to [PY_Python_in_Touchdesigner] since it uses Python extensions. Links to [performance_fundamentals] for context.

## Content

- [Introduction](#introduction)
- [Parameters - Cache Page](#parameters---cache-page)
  - [Active](#active)
  - [Active Pulse](#active-pulse)
  - [Get One Image on Startup](#get-one-image-on-startup)
  - [Replace Single](#replace-single)
  - [Replace Pulse](#replace-pulse)
  - [Replace Index](#replace-index)
  - [Pre-Fill](#pre-fill)
  - [Pre-Fill Pulse](#pre-fill-pulse)
  - [Cache Size](#cache-size)
  - [Step Size](#step-size)
  - [Output Index](#output-index)
  - [Output Index Unit](#output-index-unit)
  - [Interpolate Frames](#interpolate-frames)
  - [Always Cook](#always-cook)
  - [Reset](#reset)
- [Parameters - Common Page](#parameters---common-page)
  - [Output Resolution](#output-resolution)
  - [Resolution](#resolution)
  - [Resolution Menu](#resolution-menu)
  - [Use Global Res Multiplier](#use-global-res-multiplier)
  - [Output Aspect](#output-aspect)
  - [Aspect](#aspect)
  - [Aspect Menu](#aspect-menu)
  - [Input Smoothness](#input-smoothness)
  - [Fill Viewer](#fill-viewer)
  - [Viewer Smoothness](#viewer-smoothness)
  - [Passes](#passes)
  - [Channel Mask](#channel-mask)
  - [Pixel Format](#pixel-format)
- [Operator Inputs](#operator-inputs)
- [Info CHOP Channels](#info-chop-channels)
  - [Common TOP Info Channels](#common-top-info-channels)
  - [Common Operator Info Channels](#common-operator-info-channels)

## Introduction

The Cache TOP stores a sequence of images into GPU memory. These cached images can be read by the graphics card much faster than an image cache in main memory or reading images off disk.

The Cache TOP can be used to freeze images in the TOP by turning the `Active` parameter Off. (You can set the cache size too 1.)

The Cache TOP acts as a delay if you set `Output Index` to negative numbers and leave the `Active` parameter On.

Once a sequence of images has been captured by turning the `Active` parameter On or toggling the `Active Pulse` parameter, they can be looped by animating the `Output Index` parameter.

## Parameters - Cache Page

### Active

`active` - While this is On, the Cache TOP will capture images into its memory.

### Active Pulse

`activepulse` - Captures an image for the single frame this was pulsed.

### Get One Image on Startup

`cacheonce` - Checking this On will cook the TOP once after startup to load an initial image.

### Replace Single

`replace` - While this is On, the Cache TOP will replace the image at 'Replace Index' with the input image. This allows you to replace specific images in the cache at will.

### Replace Pulse

`replacespulse` - Replace an image for the single frame this was pulsed.

### Replace Index

`replaceindex` - Select the image index that will be replaced by the input, when 'Replace Single' is turned on.

### Pre-Fill

`prefill` - Cooks 'Cache Size' number of times to fill the Cache TOP with images. When set to 1, it will fill the cache. If set to 1 during playback, it will fill immediately. If set to 1 and saved out, then next time the file is opened the cache will pre-fill. While this is > 0, the node behaves as if the `Active` parameter is Off. If set to 0, then back > 0, it will clear the previous data, and pre-fill again. For more information refer to the [REF_PreFilling] article.

### Pre-Fill Pulse

`prefillpulse` - Pre-fills a single image during the frame this was pulsed.

### Cache Size

`cachesize` - Determines the number of images that can be stored in this Cache TOP.

### Step Size

`step` - The number of cooks that go by before the Cache TOP grabs an image. A Step Size of 2 will cache an image every 2nd cook, a Step Size of 3 will cache every 3rd cook, and so on.

### Output Index

`outputindex` - Determines which image in cache the TOP outputs. 0 is the most recent image, negative integers output image further back in time.

### Output Index Unit

`outputindexunit` - Sets the units used in the `Output Index` parameter.

### Interpolate Frames

`interp` - When On (On = 1), the Cache TOP will interpolate between frames when non-integer values are used in the `Output Index` parameter. For example, a value of -0.5 in `Output Index` will output a blended image of the most recent frame (0.0) and the second most recent frame (-1.0).

### Always Cook

`alwayscook` - Forces the operator to cook every frame.

### Reset

`reset` - While On this will empty the cache of stored images and release the memory held by the TOP.

`resetpulse` - Instantly empty the cache.

## Parameters - Common Page

### Output Resolution

`outputresolution` - Quickly change the resolution of the TOP's data.

- `Use Input` `useinput` - Uses the input's resolution.
- `Eighth` `eighth` - Multiply the input's resolution by that amount.
- `Quarter` `quarter` - Multiply the input's resolution by that amount.
- `Half` `half` - Multiply the input's resolution by that amount.
- `2X` `2x` - Multiply the input's resolution by that amount.
- `4X` `4x` - Multiply the input's resolution by that amount.
- `8X` `8x` - Multiply the input's resolution by that amount.
- `Fit Resolution` `fit` - Fits the width and height to the resolution given below, while maintaining the aspect ratio.
- `Limit Resolution` `limit` - The width and height are limited to the resolution given below. If one of the dimensions exceeds the given resolution, the width and height will be reduced to fit inside the given limits while maintaining the aspect ratio.
- `Custom Resolution` `custom` - Enables the Resolution parameter below, giving direct control over width and height.

### Resolution

`resolution` - Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size. The drop down menu on the right provides some commonly used resolutions.

- `W` `resolutionw`
- `H` `resolutionh`

### Resolution Menu

`resmenu` - A drop-down menu with some commonly used resolutions.

### Use Global Res Multiplier

`resmult` - Uses the Global Resolution Multiplier found in Edit>Preferences>TOPs. This multiplies all the TOPs resolutions by the set amount. This is handy when working on computers with different hardware specifications. If a project is designed on a desktop workstation with lots of graphics memory, a user on a laptop with only 64MB VRAM can set the Global Resolution Multiplier to a value of half or quarter so it runs at an acceptable speed. By checking this checkbox on, this TOP is affected by the global multiplier.

### Output Aspect

`outputaspect` - Sets the image aspect ratio allowing any textures to be viewed in any size. Watch for unexpected results when compositing TOPs with different aspect ratios. (You can define images with non-square pixels using xres, yres, aspectx, aspecty where xres/yres != aspectx/aspecty.)

- `Use Input` `useinput` - Uses the input's aspect ratio.
- `Resolution` `resolution` - Uses the aspect of the image's defined resolution (ie 512x256 would be 2:1), whereby each pixel is square.
- `Custom Aspect` `custom` - Lets you explicitly define a custom aspect ratio in the Aspect parameter below.

### Aspect

`aspect` - Use when Output Aspect parameter is set to Custom Aspect.

- `Aspect1` `aspect1`
- `Aspect2` `aspect2`

### Aspect Menu

`armenu` - A drop-down menu with some commonly used aspect ratios.

### Input Smoothness

`inputfiltertype` - This controls pixel filtering on the input image of the TOP.

### Fill Viewer

`fillmode` - Determine how the TOP image is displayed in the viewer.

**NOTE:** To get an understanding of how TOPs work with images, you will want to set this to Native Resolution as you lay down TOPs when starting out. This will let you see what is actually happening without any automatic viewer resizing.

### Viewer Smoothness

`filtertype` - This controls pixel filtering in the viewers.

### Passes

`npasses` - Duplicates the operation of the TOP the specified number of times. Making this larger than 1 is essentially the same as taking the output from each pass, and passing it into the first input of the node and repeating the process. Other inputs and parameters remain the same for each pass.

### Channel Mask

`chanmask` - Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default.

### Pixel Format

`format` - Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to [REF_PixelFormats] for more information.

- `Use Input` `useinput` - Uses the input's pixel format.
- `8-bit fixed (RGBA)` `rgba8fixed` - Uses 8-bit integer values for each channel.
- `sRGB 8-bit fixed (RGBA)` `srgba8fixed` - Uses 8-bit integer values for each channel and stores color in sRGB colorspace.
- `16-bit float (RGBA)` `rgba16float` - Uses 16-bits per color channel, 64-bits per pixel.
- `32-bit float (RGBA)` `rgba32float` - Uses 32-bits per color channel, 128-bits per pixels.
- `10-bit RGB, 2-bit Alpha, fixed (RGBA)` `rgb10a2fixed` - Uses 10-bits per color channel and 2-bits for alpha, 32-bits total per pixel.
- `16-bit fixed (RGBA)` `rgba16fixed` - Uses 16-bits per color channel, 64-bits total per pixel.
- `11-bit float (RGB), Positive Values Only` `rgba11float` - A RGB floating point format that has 11 bits for the Red and Green channels, and 10-bits for the Blue Channel, 32-bits total per pixel (therefore the same memory usage as 8-bit RGBA). The Alpha channel in this format will always be 1. Values can go above one, but can't be negative. ie. the range is [0, infinite).
- `16-bit float (RGB)` `rgb16float`
- `32-bit float (RGB)` `rgb32float`
- `8-bit fixed (Mono)` `mono8fixed` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 8-bits per pixel.
- `16-bit fixed (Mono)` `mono16fixed` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 16-bits per pixel.
- `16-bit float (Mono)` `mono16float` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 16-bits per pixel.
- `32-bit float (Mono)` `mono32float` - Single channel, where RGB will all have the same value, and Alpha will be 1.0. 32-bits per pixel.
- `8-bit fixed (RG)` `rg8fixed` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 8-bits per channel, 16-bits total per pixel.
- `16-bit fixed (RG)` `rg16fixed` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 16-bits per channel, 32-bits total per pixel.
- `16-bit float (RG)` `rg16float` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 16-bits per channel, 32-bits total per pixel.
- `32-bit float (RG)` `rg32float` - A 2 channel format, R and G have values, while B is 0 always and Alpha is 1.0. 32-bits per channel, 64-bits total per pixel.
- `8-bit fixed (A)` `a8fixed` - An Alpha only format that has 8-bits per channel, 8-bits per pixel.
- `16-bit fixed (A)` `a16fixed` - An Alpha only format that has 16-bits per channel, 16-bits per pixel.
- `16-bit float (A)` `a16float` - An Alpha only format that has 16-bits per channel, 16-bits per pixel.
- `32-bit float (A)` `a32float` - An Alpha only format that has 32-bits per channel, 32-bits per pixel.
- `8-bit fixed (Mono+Alpha)` `monoalpha8fixed` - A 2 channel format, one value for RGB and one value for Alpha. 8-bits per channel, 16-bits per pixel.
- `16-bit fixed (Mono+Alpha)` `monoalpha16fixed` - A 2 channel format, one value for RGB and one value for Alpha. 16-bits per channel, 32-bits per pixel.
- `16-bit float (Mono+Alpha)` `monoalpha16float` - A 2 channel format, one value for RGB and one value for Alpha. 16-bits per channel, 32-bits per pixel.
- `32-bit float (Mono+Alpha)` `monoalpha32float` - A 2 channel format, one value for RGB and one value for Alpha. 32-bits per channel, 64-bits per pixel.

## Operator Inputs

**Input 0:** -

## Info CHOP Channels

Extra Information for the Cache TOP can be accessed via an Info CHOP.

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
