---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- GLSL_TOP
- Script_TOP
- Render_TOP
concepts:
- glsl_programming
- shader_development
- gpu_computing
- procedural_textures
- compute_shaders
- fragment_shaders
- vertex_shaders
- texture_processing
- compile_result_access
prerequisites:
- CLASS_TOP_Class
- GLSL_fundamentals
- shader_programming_basics
workflows:
- shader_development
- procedural_texture_generation
- gpu_computing
- real_time_graphics
- generative_visuals
- compute_shader_workflows
- shader_debugging
keywords:
- glsl top class
- shader programming
- fragment shader
- vertex shader
- compute shader
- glsl api
- gpu programming
- texture processing
- procedural shaders
- real time graphics
- compileResult
- shader compilation
tags:
- python
- api_reference
- glsl
- shader
- gpu
- procedural
- real_time
- graphics
- texture
- compute
- compilation
relationships:
  CLASS_TOP_Class: strong
  GLSL_Write_a_GLSL_TOP: strong
  GLSL_Compute_Shader_Reference: strong
  GLSL_Built_In_Functions_Reference: medium
related_docs:
- CLASS_TOP_Class
- GLSL_Write_a_GLSL_TOP
- GLSL_Compute_Shader_Reference
- GLSL_Built_In_Functions_Reference
hierarchy:
  secondary: shader_programming
  tertiary: glsl_top_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- shader_development
- procedural_texture_generation
- gpu_computing
- real_time_graphics
---

# glslTOP Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [GLSL_TOP, Script_TOP, Render_TOP]
concepts: [glsl_programming, shader_development, gpu_computing, procedural_textures, compute_shaders, fragment_shaders, vertex_shaders, texture_processing, compile_result_access]
prerequisites: [CLASS_TOP_Class, GLSL_fundamentals, shader_programming_basics]
workflows: [shader_development, procedural_texture_generation, gpu_computing, real_time_graphics, generative_visuals, compute_shader_workflows, shader_debugging]
related: [CLASS_TOP_Class, GLSL_Write_a_GLSL_TOP, GLSL_Compute_Shader_Reference, GLSL_Built_In_Functions_Reference]
relationships: {
  "CLASS_TOP_Class": "strong",
  "GLSL_Write_a_GLSL_TOP": "strong",
  "GLSL_Compute_Shader_Reference": "strong",
  "GLSL_Built_In_Functions_Reference": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "shader_programming"
  tertiary: "glsl_top_class"
keywords: [glsl top class, shader programming, fragment shader, vertex shader, compute shader, glsl api, gpu programming, texture processing, procedural shaders, real time graphics, compileResult, shader compilation]
tags: [python, api_reference, glsl, shader, gpu, procedural, real_time, graphics, texture, compute, compilation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: shader_development, procedural_texture_generation, gpu_computing

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Class Top Class] → [Glsl Fundamentals] → [Shader Programming Basics]
**This document**: CLASS reference/guide
**Next steps**: [CLASS TOP Class] → [GLSL Write a GLSL TOP] → [GLSL Compute Shader Reference]

**Related Topics**: shader development, procedural texture generation, gpu computing

## Summary

Python class interface for GLSL TOP operations providing access to shader compilation results and texture properties. Essential for shader programming workflows and procedural texture generation using GLSL.

## Relationship Justification

Inherits from TOP class and provides practical implementation of GLSL concepts. Strongly connected to GLSL guides and compute shader reference for complete shader development workflows.

## Content

- [Introduction](#introduction)
- [glslTOP Class](#glsltop-class-1)
  - [Members](#members)
  - [Methods](#methods)
- [TOP Class](#top-class)
  - [Members](#members-1)
  - [Methods](#methods-1)
    - [sample()](#sample)
    - [numpyArray()](#numpyarray)
    - [save()](#save)
    - [saveByteArray()](#savebytearray)
    - [cudaMemory()](#cudamemory)

## Introduction

This class inherits from the [CLASS_TOP] class. It references a specific GLSL TOP.

## glslTOP Class

### Members

#### compileResult → str (Read Only)

The latest compile result.

### Methods

No operator specific methods.

## TOP Class

### Members

#### width → int (Read Only)

Texture width, measured in pixels.

#### height → int (Read Only)

Texture height, measured in pixels.

#### aspect → float (Read Only)

Texture aspect ratio, width divided by height.

#### aspectWidth → float (Read Only)

Texture aspect ratio, width.

#### aspectHeight → float (Read Only)

Texture aspect ratio, height.

#### depth → int (Read Only)

Texture depth, when using a 3 dimensional texture.

#### gpuMemory → int (Read Only)

The amount of GPU memory this TOP is using, in bytes.

#### curPass → int (Read Only)

The current cooking pass iteration, beginning at 0. The total can be set with the 'Passes' parameter on the operator's common page.

#### isTOP → bool (Read Only)

True if the operators is a TOP.

#### newestSliceWOffset → int (Read Only)

When a Texture3D TOP fills it's contents, it keeps track of the newest slice it's filled so texturing can be offset this so a '0' coordinate results in the first slice. This member give you access to this value.

#### pixelFormat → str (Read Only)

Returns the pixel Format of the TOP. The returned string format resembles the pixel format on the operator's common page.

### Methods

#### sample()

sample(x=None, y=None, z=None, u=None, v=None, w=None)→ Tuple[float, float, float, float]:

Returns a 4-tuple representing the color value at the specified texture location. One horizontal and one vertical component must be specified. **Note:** This is a very expensive operation currently. It will always stall the graphics pipeline if the TOP is currently queued to get updated, and then downloads the entire texture (not just the requested pixel). Use this for debugging and non-realtime workflows only.

- `x` - (Keyword, Optional) The horizontal pixel coordinate to be sampled.
- `y` - (Keyword, Optional) The vertical pixel coordinate to be sampled.
- `z` - (Keyword, Optional) The depth pixel coordinate to be sampled. Available in builds 2022.23800 and later.
- `u` - (Keyword, Optional) The normalized horizontal coordinate to be sampled.
- `v` - (Keyword, Optional) The normalized vertical coordinate to be sampled.
- `w` - (Keyword, Optional) The normalized depth pixel coordinate to be sampled. Available in builds 2022.23800 and later.

```python
r = n.sample(x=25,y=100)[0]   #The red component at pixel 25,100.
g = n.sample(u=0.5,v=0.5)[1]  #The green component at the central location.
b = n.sample(x=25,v=0.5)[2]  #The blue 25 pixels across, and half way down.
```

#### numpyArray()

numpyArray(delayed=False, writable=False)→ numpy.ndarray:

Returns the TOP image as a Python NumPy array. **Note:** Since NumPy arrays are referenced by line first, pixels are addressed as [h, w]. Currently data will always be in floating point, regardless of what the texture data format is on the GPU.

- `delayed` - (Keyword, Optional) If set to True, the download results will be delayed until the next call to `numpyArray()`, avoiding stalling the GPU waiting for the result immediately. This is useful to avoid long stalls that occur if immediately asking for the result. Each call with return the image that was 'current' on the previous call to `numpyArray()`. None will be returned if there isn't a result available. You should always check the return value against None to make sure you have a result. Call `numpyArray()` again, ideally on the next frame or later, to get the result. If you always need a result, you can call `numpyArray()` a second time in the event None is returned on the first call.
- `writable` - (Keyword, Optional) If set to True, the memory in the numpy array will be allocated in such a way that writes to it arn't slow. By default the memory the numpy array holds can be allocated in such a way that is very slow to write to. **Note:** In either case, writing to the numpy array will *not* change the data in the TOP.

#### save()

save(filepath, asynchronous=False, createFolders=False, quality=1.0, metadata=[])→ str:

Saves the image to the file system. Support file formats are: .tif, .tiff, .jpg, .jpeg, .bmp, .png, .exr and .dds. Returns the filename and path used.

- `filepath` - (Optional) The path and filename to save to. If not given then a default filename will be used, and the file will be saved in the `project.folder` folder.
- `asynchronous` - (Keyword, Optional) If True, the save will occur in another thread. The file may not be done writing at the time this function returns.
- `createFolders` - (Keyword, Optional) If True, folders listed in the path that don't exist will be created.
- `quality` - (Keyword, Optional) Specify the compression quality used. Values range from 0 (lowest quality, small size) to 1 (best quality, largest size).
- `metadata` - (Keyword, Optional) A list of string pairs that will be inserted into the file's metadata section. Any type of list structure is supported (dictionary, tuple, etc) as long as each metadata item has two entries (key & value). **Note:** Only supported on EXR files.

```python
name = n.save()   #save in default format with default name.
n.save('picture.jpg')
n.save('image.exr', metadata=[ ("my_key", "my_value"), ("author_name", "derivative") ] ); # save as .exr with custom metadata
```

#### saveByteArray()

saveByteArray(filetype, quality=1.0, metadata=[])→ bytearray:

Saves the image to a bytearray object in the requested file format. Support file formats are: .tif, .tiff, .jpg, .jpeg, .bmp, .png, .exr and .dds. Returns the bytearray object. To get the raw image data use `numpyArray()` or `cudaArray()` instead.

- `filetype` - (Optional) A string specifying the file type to save as. If not given the default file type '.tiff' will be used. Just the suffix of the string is used to determine the file type. E.g '.tiff', 'file.tiff', 'C:/Files/file.tiff' will all work. Suffix must include the period.
- `quality` - (Keyword, Optional) Specify the compression quality used. Values range from 0 (lowest quality, small size) to 1 (best quality, largest size).
- `metadata` - (Keyword, Optional) A list of string pairs that will be inserted into the file's metadata section. Any type of list structure is supported (dictionary, tuple, etc) as long as each metadata item has two entries (key & value). **Note:** Only supported on EXR files.

```python
arr = n.saveByteArray() # save in default format.
arr = n.saveByteArray('.jpg') # save as .jpg
arr = n.saveByteArray('.exr', metadata=[ ("my_key", "my_value"), ("author_name", "derivative") ] ); # save as .exr with custom metadata
```

#### cudaMemory()

cudaMemory()→ CUDAMemory:

Copies the contents of the TOP to a newly allocated block of raw CUDA memory. The CUDA memory will be deallocated when the returned [CLASS_CUDAMemory] object is deallocated. Ensure you keep a reference to the returned object around as long as you are using it.
