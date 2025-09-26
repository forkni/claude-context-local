---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Movie_File_Out_TOP
- Info_CHOP
- Audio_File_In_CHOP
concepts:
- video_encoding
- file_export_operations
- image_sequence_rendering
- movie_production
- audio_video_sync
- multi_channel_export
- file_format_conversion
- compression_workflows
- non_realtime_rendering
prerequisites:
- CLASS_TOP
- video_encoding_concepts
- file_operations
- audio_basics
workflows:
- video_recording
- movie_production
- image_sequence_export
- stop_frame_animation
- non_realtime_rendering
- audio_video_recording
- multi_channel_exr_export
- automated_rendering
keywords:
- movie file out class
- video recording api
- movie export
- image sequences
- file output
- video codecs
- h264 h265
- stop frame animation
- audio sync
- exr export
- write progress
- writeCount
- curSeqIndex
- fileSuffix
- python api
tags:
- python
- api_reference
- video_export
- real_time
- gpu_accelerated
- multi_format
- audio_support
- commercial_license_required
- automation
relationships:
  CLASS_TOP: strong
  REF_MovieFileOut_TOP: strong
  CLASS_Project_Class: medium
  REF_Cook: medium
related_docs:
- CLASS_TOP
- REF_MovieFileOut_TOP
- CLASS_Project_Class
- REF_Cook
hierarchy:
  secondary: file_export
  tertiary: movie_output_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- video_recording
- movie_production
- image_sequence_export
- stop_frame_animation
---

# moviefileoutTOP Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Movie_File_Out_TOP, Info_CHOP, Audio_File_In_CHOP]
concepts: [video_encoding, file_export_operations, image_sequence_rendering, movie_production, audio_video_sync, multi_channel_export, file_format_conversion, compression_workflows, non_realtime_rendering]
prerequisites: [CLASS_TOP, video_encoding_concepts, file_operations, audio_basics]
workflows: [video_recording, movie_production, image_sequence_export, stop_frame_animation, non_realtime_rendering, audio_video_recording, multi_channel_exr_export, automated_rendering]
related: [CLASS_TOP, REF_MovieFileOut_TOP, CLASS_Project_Class, REF_Cook]
relationships: {
  "CLASS_TOP": "strong",
  "REF_MovieFileOut_TOP": "strong",
  "CLASS_Project_Class": "medium",
  "REF_Cook": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "file_export"
  tertiary: "movie_output_class"
keywords: [movie file out class, video recording api, movie export, image sequences, file output, video codecs, h264 h265, stop frame animation, audio sync, exr export, write progress, writeCount, curSeqIndex, fileSuffix, python api]
tags: [python, api_reference, video_export, real_time, gpu_accelerated, multi_format, audio_support, commercial_license_required, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: video_recording, movie_production, image_sequence_export

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Class Top] → [Video Encoding Concepts] → [File Operations]
**This document**: CLASS reference/guide
**Next steps**: [CLASS TOP] → [REF MovieFileOut TOP] → [CLASS Project Class]

**Related Topics**: video recording, movie production, image sequence export

## Summary

MovieFileOutTOP class provides access to Movie File Out TOP, which allows video recording and image sequence export. It can be accessed with the `moviefileout` object, found in the automatically imported [PY_td] module. Alternatively, one can use the regular python statement: `import`. Use of the `import` statement is limited to modules in the search path, where as the `mod` format allows complete statements in one line, which is more useful for entering expressions. Also note that [CLASS_DAT] modules cannot be organized into packages as regular file system based python modules can be.

## Relationship Justification

Strong connection to TOP base class and operator reference documentation. Links to Project class for non-realtime rendering configuration and Cook reference for understanding rendering workflow timing.

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [writeCount](#writecount)
  - [curSeqIndex](#curseqindex)
  - [fileSuffix](#filesuffix)
- [Methods](#methods)
- [TOP Class](#top-class)
  - [Members](#members-1)
    - [width](#width)
    - [height](#height)
    - [aspect](#aspect)
    - [aspectWidth](#aspectwidth)
    - [aspectHeight](#aspectheight)
    - [depth](#depth)
    - [gpuMemory](#gpumemory)
    - [curPass](#curpass)
    - [isTOP](#istop)
    - [newestSliceWOffset](#newestslicewoffset)
    - [pixelFormat](#pixelformat)
  - [Methods](#methods-1)
    - [sample()](#sample)
    - [numpyArray()](#numpyarray)
    - [save()](#save)
    - [saveByteArray()](#savebytearray)
    - [cudaMemory()](#cudamemory)

## Introduction

This class inherits from the [CLASS_TOP] class. It references a specific Movie File Out TOP.

## Members

### writeCount

`writeCount` → (Read Only):

The number of files that have been written. This can be used to create an incrementing file name.

### curSeqIndex

`curSeqIndex` → (Read Only):

The current index of the last written image on disk.

### fileSuffix

`fileSuffix` → str (Read Only):

Returns the generated file suffix. It will be generated based on the values of the parameters Unique Suffix and N, plus the file extension. It will take one of two forms: N.ext or N.i.ext where N is the suffix index (uniquely generated if Unique Suffix is enabled), i is the image sequence index (used only for the image sequence type), and ext is the image/movie extension.

## Methods

No operator specific methods.

## TOP Class

### Members

#### width

`width` → int (Read Only):

Texture width, measured in pixels.

#### height

`height` → int (Read Only):

Texture height, measured in pixels.

#### aspect

`aspect` → float (Read Only):

Texture aspect ratio, width divided by height.

#### aspectWidth

`aspectWidth` → float (Read Only):

Texture aspect ratio, width.

#### aspectHeight

`aspectHeight` → float (Read Only):

Texture aspect ratio, height.

#### depth

`depth` → int (Read Only):

Texture depth, when using a 3 dimensional texture.

#### gpuMemory

`gpuMemory` → int (Read Only):

The amount of GPU memory this TOP is using, in bytes.

#### curPass

`curPass` → int (Read Only):

The current cooking pass iteration, beginning at 0. The total can be set with the 'Passes' parameter on the operator's common page.

#### isTOP

`isTOP` → bool (Read Only):

True if the operators is a TOP.

#### newestSliceWOffset

`newestSliceWOffset` → int (Read Only):

When a Texture3D TOP fills it's contents, it keeps track of the newest slice it's filled so texturing can be offset this so a '0' coordinate results in the first slice. This member give you access to this value.

#### pixelFormat

`pixelFormat` → str (Read Only):

Returns the pixel Format of the TOP. The returned string format resembles the pixel format on the operator's common page.

### Methods

#### sample()

sample(x=None, y=None, z=None, u=None, v=None, w=None)→ Tuple[float, float, float, float]:

Returns a 4-tuple representing the color value at the specified texture location. One horizontal and one vertical component must be specified. Note that this is a very expensive operation currently. It will always stall the graphics pipeline if the TOP is currently queued to get updated, and then downloads the entire texture (not just the requested pixel). Use this for debugging and non-realtime workflows only.

- `x` - (Keyword, Optional) The horizontal pixel coordinate to be sampled.
- `y` - (Keyword, Optional) The vertical pixel coordinate to be sampled.
- `z` - (Keyword, Optional) The depth pixel coordinate to be sampled. Available in builds 2022.23800 and later.
- `u` - (Keyword, Optional) The normalized horizontal coordinate to be sampled.
- `v` - (Keyword, Optional) The normalized vertical coordinate to be sampled.
- `w` - (Keyword, Optional) The normalized depth pixel coordinate to be sampled. Available in builds 2022.23800 and later.

```python
r = n.sample(x=25,y=100)[0]   # The red component at pixel 25,100.
g = n.sample(u=0.5,v=0.5)[1]  # The green component at the central location.
b = n.sample(x=25,v=0.5)[2]   # The blue 25 pixels across, and half way down.
```

#### numpyArray()

numpyArray(delayed=False, writable=False)→ numpy.ndarray:

Returns the TOP image as a Python NumPy array. Note that since NumPy arrays are referenced by line first, pixels are addressed as [h, w]. Currently data will always be in floating point, regardless of what the texture data format is on the GPU.

- `delayed` - (Keyword, Optional) If set to True, the download results will be delayed until the next call to `numpyArray()`, avoiding stalling the GPU waiting for the result immediately. This is useful to avoid long stalls that occur if immediately asking for the result. Each call with return the image that was 'current' on the previous call to `numpyArray()`. None will be returned if there isn't a result available. You should always check the return value against None to make sure you have a result. Call `numpyArray()` again, ideally on the next frame or later, to get the result. If you always need a result, you can call `numpyArray()` a second time in the event None is returned on the first call.
- `writable` - (Keyword, Optional) If set to True, the memory in the numpy array will be allocated in such a way that writes to it aren't slow. By default the memory the numpy array holds can be allocated in such a way that is very slow to write to. Note that in either case, writing to the numpy array will *not* change the data in the TOP.

#### save()

save(filepath, asynchronous=False, createFolders=False, quality=1.0, metadata=[])→ str:

Saves the image to the file system. Support file formats are: .tif, .tiff, .jpg, .jpeg, .bmp, .png, .exr and .dds. Returns the filename and path used.

- `filepath` - (Optional) The path and filename to save to. If not given then a default filename will be used, and the file will be saved in the `project.folder` folder.
- `asynchronous` - (Keyword, Optional) If True, the save will occur in another thread. The file may not be done writing at the time this function returns.
- `createFolders` - (Keyword, Optional) If True, folders listed in the path that don't exist will be created.
- `quality` - (Keyword, Optional) Specify the compression quality used. Values range from 0 (lowest quality, small size) to 1 (best quality, largest size).
- `metadata` - (Keyword, Optional) A list of string pairs that will be inserted into the file's metadata section. Any type of list structure is supported (dictionary, tuple, etc) as long as each metadata item has two entries (key & value). **Note:** Only supported on EXR files.

```python
name = n.save()   # save in default format with default name.
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

cudaMemory(stream=None)→ CUDAMemory:

Copies the contents of the TOP to a newly allocated block of raw CUDA memory. The CUDA memory will be deallocated when the returned [CLASS_CUDAMemory] object is deallocated. Ensure you keep a reference to the returned object around as long as you are using it.

- `stream` - (Optional) A CUDA stream handle to synchronize the operation with. Any CUDA subsequent operations occurring on this stream will wait for this CUDA memory to be filled before executing their operation. If this is left as None, then the default CUDA stream will be used (which results in poor performance).
