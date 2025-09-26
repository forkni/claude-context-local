---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Render_TOP
- Camera_COMP
- Geometry_COMP
- Light_COMP
- Render_Pass_TOP
- Depth_TOP
concepts:
- 3d_rendering
- texture_operations
- gpu_rendering
- scene_rendering
- render_pipeline
- lighting_systems
- camera_systems
- geometry_rendering
- texture_sampling
- image_processing
- cuda_memory_integration
prerequisites:
- CLASS_TOP
- 3d_rendering_concepts
- GPU_fundamentals
- camera_systems
- lighting_basics
- geometry_concepts
workflows:
- 3d_scene_rendering
- render_pipeline_setup
- texture_generation
- real_time_rendering
- render_optimization
- lighting_setup
- camera_control
- geometry_rendering
- procedural_texturing
keywords:
- renderTOP class
- 3d rendering api
- texture rendering
- gpu rendering
- geometry rendering
- camera rendering
- lighting systems
- 3d scene rendering
- render pipeline
- texture operations
- numpy integration
- cuda memory
- pixel sampling
- image export
- render passes
- python api
tags:
- python
- api_reference
- 3d_rendering
- gpu_accelerated
- real_time
- texture_output
- camera_rendering
- lighting
- geometry
- cuda_compatible
- numpy_integration
- class_documentation
relationships:
  CLASS_TOP: strong
  REF_Render_TOP: strong
  CLASS_CUDAMemory_Class: strong
  CLASS_CUDAMemoryShape_Class: medium
  GLSL_Write_a_GLSL_Material: medium
related_docs:
- CLASS_TOP
- REF_Render_TOP
- CLASS_CUDAMemory_Class
- CLASS_CUDAMemoryShape_Class
- GLSL_Write_a_GLSL_Material
hierarchy:
  secondary: 3d_rendering
  tertiary: render_top_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- 3d_scene_rendering
- render_pipeline_setup
- texture_generation
- real_time_rendering
---

# renderTOP Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Render_TOP, Camera_COMP, Geometry_COMP, Light_COMP, Render_Pass_TOP, Depth_TOP]
concepts: [3d_rendering, texture_operations, gpu_rendering, scene_rendering, render_pipeline, lighting_systems, camera_systems, geometry_rendering, texture_sampling, image_processing, cuda_memory_integration]
prerequisites: [CLASS_TOP, 3d_rendering_concepts, GPU_fundamentals, camera_systems, lighting_basics, geometry_concepts]
workflows: [3d_scene_rendering, render_pipeline_setup, texture_generation, real_time_rendering, render_optimization, lighting_setup, camera_control, geometry_rendering, procedural_texturing]
related: [CLASS_TOP, REF_Render_TOP, CLASS_CUDAMemory_Class, CLASS_CUDAMemoryShape_Class, GLSL_Write_a_GLSL_Material]
relationships: {
  "CLASS_TOP": "strong",
  "REF_Render_TOP": "strong", 
  "CLASS_CUDAMemory_Class": "strong",
  "CLASS_CUDAMemoryShape_Class": "medium",
  "GLSL_Write_a_GLSL_Material": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "3d_rendering"
  tertiary: "render_top_class"
keywords: [renderTOP class, 3d rendering api, texture rendering, gpu rendering, geometry rendering, camera rendering, lighting systems, 3d scene rendering, render pipeline, texture operations, numpy integration, cuda memory, pixel sampling, image export, render passes, python api]
tags: [python, api_reference, 3d_rendering, gpu_accelerated, real_time, texture_output, camera_rendering, lighting, geometry, cuda_compatible, numpy_integration, class_documentation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: 3d_scene_rendering, render_pipeline_setup, texture_generation

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Class Top] → [3D Rendering Concepts] → [Gpu Fundamentals]
**This document**: CLASS reference/guide
**Next steps**: [CLASS TOP] → [REF Render TOP] → [CLASS CUDAMemory Class]

**Related Topics**: 3d scene rendering, render pipeline setup, texture generation

## Summary

Class documentation for the renderTOP class, providing Python API access to 3D rendering operations. Critical for procedural rendering workflows and advanced texture generation.

## Relationship Justification

Strong connection to CLASS_TOP as base class and REF_Render_TOP as operator reference. Connected to CUDA memory classes since renderTOP provides CUDA interoperability for advanced GPU computing workflows. Links to GLSL material guide for shader integration.

## Content

- [Introduction](#introduction)
- [renderTOP Specific](#rendertop-specific)
- [TOP Class](#top-class)
  - [Members](#top-members)
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
  - [Methods](#top-methods)
    - [sample()](#sample)
    - [numpyArray()](#numpyarray)
    - [save()](#save)
    - [saveByteArray()](#savebytearray)
    - [cudaMemory()](#cudamemory)
- [OP Class](#op-class)
  - [Members](#op-members)
    - [General](#general)
    - [Common Flags](#common-flags)
    - [Appearance](#appearance)
    - [Connection](#connection)
    - [Cook Information](#cook-information)
    - [Type](#type)
  - [Methods](#op-methods)
    - [General](#op-general)
    - [Errors](#errors)
    - [Appearance](#op-appearance)
    - [Viewers](#viewers)
    - [Storage](#storage)
    - [Miscellaneous](#miscellaneous)

## Introduction

This class inherits from the [CLASS_TOP] class. It references a specific [CLASS_RenderTOP].

## renderTOP Specific

### Members

No operator specific members.

### Methods

No operator specific methods.

## TOP Class

### Members

#### width

width → int (Read Only):

Texture width, measured in pixels.

#### height

height → int (Read Only):

Texture height, measured in pixels.

#### aspect

aspect → float (Read Only):

Texture aspect ratio, width divided by height.

#### aspectWidth

aspectWidth → float (Read Only):

Texture aspect ratio, width.

#### aspectHeight

aspectHeight → float (Read Only):

Texture aspect ratio, height.

#### depth

depth → int (Read Only):

Texture depth, when using a 3 dimensional texture.

#### gpuMemory

gpuMemory → int (Read Only):

The amount of GPU memory this TOP is using, in bytes.

#### curPass

curPass → int (Read Only):

The current cooking pass iteration, beginning at 0. The total can be set with the 'Passes' parameter on the operator's common page.

#### isTOP

isTOP → bool (Read Only):

True if the operators is a TOP.

#### newestSliceWOffset

newestSliceWOffset → int (Read Only):

When a [CLASS_Texture3DTOP] fills it's contents, it keeps track of the newest slice it's filled so texturing can be offset this so a '0' coordinate results in the first slice. This member give you access to this value.

#### pixelFormat

pixelFormat → str (Read Only):

Returns the pixel Format of the TOP. The returned string format resembles the pixel format on the operator's common page.

### Methods

#### sample()

sample(x=None,y=None,z=None,u=None,v=None,w=None)→ Tuple[float, float, float, float]:

Returns a 4-tuple representing the color value at the specified texture location. One horizontal and one vertical component must be specified. Note that this is a very expensive operation currently. It will always stall the graphics pipeline if the TOP is currently queued to get updated, and then downloads the entire texture (not just the requested pixel). Use this for debugging and non-realtime workflows only.

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

Returns the TOP image as a Python NumPy array. Note that since NumPy arrays are referenced by line first, pixels are addressed as [h, w]. Currently data will always be in floating point, regardless of what the texture data format is on the GPU.

- `delayed` - (Keyword, Optional) If set to True, the download results will be delayed until the next call to numpyArray(), avoiding stalling the GPU waiting for the result immediately. This is useful to avoid long stalls that occur if immediately asking for the result. Each call with return the image that was 'current' on the previous call to numpyArray(). None will be returned if there isn't a result available. You should always check the return value against None to make sure you have a result. Call numpyArray() again, ideally on the next frame or later, to get the result. If you always need a result, you can call numpyArray() a second time in the event None is returned on the first call.
- `writable` - (Keyword, Optional) If set to True, the memory in the numpy array will be allocated in such a way that writes to it arn't slow. By default the memory the numpy array holds can be allocated in such a way that is very slow to write to. Note that in either case, writing to the numpy array will *not* change the data in the TOP.

#### save()

save(filepath, asynchronous=False, createFolders=False, quality=1.0, metadata=[])→ str:

Saves the image to the file system. Support file formats are: .tif, .tiff, .jpg, .jpeg, .bmp, .png, .exr and .dds. Returns the filename and path used.

- `filepath` - (Optional) The path and filename to save to. If not given then a default filename will be used, and the file will be saved in the project.folder folder.
- `asynchronous` - (Keyword, Optional) If True, the save will occur in another thread. The file may not be done writing at the time this function returns.
- `createFolders` - (Keyword, Optional) If True, folders listed in the path that don't exist will be created.
- `quality` - (Keyword, Optional) Specify the compression quality used. Values range from 0 (lowest quality, small size) to 1 (best quality, largest size).
- `metadata` - (Keyword, Optional) A list of string pairs that will be inserted into the file's metadata section. Any type of list structure is supported (dictionary, tuple, etc) as long as each metadata item has two entries (key & value). Note: Only supported on EXR files.

```python
name = n.save()   #save in default format with default name.
n.save('picture.jpg')
n.save('image.exr', metadata=[ ("my_key", "my_value"), ("author_name", "derivative") ] ); # save as .exr with custom metadata
```

#### saveByteArray()

saveByteArray(filetype, quality=1.0, metadata=[])→ bytearray:

Saves the image to a bytearray object in the requested file format. Support file formats are: .tif, .tiff, .jpg, .jpeg, .bmp, .png, .exr and .dds. Returns the bytearray object. To get the raw image data use numpyArray() or cudaArray() instead.

- `filetype` - (Optional) A string specifying the file type to save as. If not given the default file type '.tiff' will be used. Just the suffix of the string is used to determine the file type. E.g '.tiff', 'file.tiff', 'C:/Files/file.tiff' will all work. Suffix must include the period.
- `quality` - (Keyword, Optional) Specify the compression quality used. Values range from 0 (lowest quality, small size) to 1 (best quality, largest size).
- `metadata` - (Keyword, Optional) A list of string pairs that will be inserted into the file's metadata section. Any type of list structure is supported (dictionary, tuple, etc) as long as each metadata item has two entries (key & value). Note: Only supported on EXR files.

```python
arr = n.saveByteArray() # save in default format.
arr = n.saveByteArray('.jpg') # save as .jpg
arr = n.saveByteArray('.exr', metadata=[ ("my_key", "my_value"), ("author_name", "derivative") ] ); # save as .exr with custom metadata
```

#### cudaMemory()

cudaMemory(stream=None)→ [CLASS_CUDAMemory]:

Copies the contents of the TOP to a newly allocated block of raw CUDA memory. The CUDA memory will be deallocated when the returned [CLASS_CUDAMemory] object is deallocated. Ensure you keep a reference to the returned object around as long as you are using it.

- `stream` - (Optional) A CUDA stream handle to synchronize the operation with. Any CUDA subsequent operations occurring on this stream will wait for this CUDA memory to be filled before executing their operation. If this is left as None, then the default CUDA stream will be used (which results in poor performance).

## OP Class

### Members

#### General

**valid** → bool (Read Only): True if the referenced operator currently exists, False if it has been deleted.

**id** → int (Read Only): Unique id for the operator. This id can also be passed to the op() and ops() methods. Id's are not consistent when a file is re-opened, and will change if the OP is copied/pasted, changes OP types, deleted/undone. The id will not change if the OP is renamed though. Its data type is integer.

**name** → str: Get or set the operator name.

**path** → str (Read Only): Full path to the operator.

**digits** → int (Read Only): Returns the numeric value of the last consecutive group of digits in the name, or None if not found. The digits can be in the middle of the name if there are none at the end of the name.

**base** → str (Read Only): Returns the beginning portion of the name occurring before any digits.

**passive** → bool (Read Only): If true, operator will not cook before its access methods are called. To use a passive version of an operator n, use passive(n).

**curPar** → [CLASS_Par] (Read Only): The parameter currently being evaluated. Can be used in a parameter expression to reference itself. An easy way to see this is to put the expression curPar.name in any string parameter.

**curBlock** → (Read Only): The SequenceBlock of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

**curSeq** → [CLASS_Sequence] (Read Only): The Sequence of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

**time** → [CLASS_OP] (Read Only): Time Component that defines the operator's time reference.

**ext** → class (Read Only): The object to search for parent extensions. Example: `me.ext.MyClass`

**fileFolder** → str (Read Only): Returns the folder where this node is saved.

**filePath** → str (Read Only): Returns the file location of this node.

**mod** → mod (Read Only): Get a module on demand object that searches for DAT modules relative to this operator.

**pages** → list (Read Only): A list of all built-in pages.

**parGroup** → tuple (Read Only): An intermediate parameter collection object, from which a specific parameter group can be found. Example: `n.parGroup.t` or `n.parGroup['t']`

**par** → [CLASS_Par] (Read Only): An intermediate parameter collection object, from which a specific parameter can be found. Example: `n.par.tx` or `n.par['tx']`

**builtinPars** → list or par (Read Only): A list of all built-in parameters.

**customParGroups** → list of parGroups (Read Only): A list of all ParGroups, where a ParGroup is a set of parameters all drawn on the same line of a dialog, sharing the same label.

**customPars** → list of par (Read Only): A list of all custom parameters.

**customPages** → list (Read Only): A list of all custom pages.

**replicator** → [CLASS_OP] or None (Read Only): The replicatorCOMP that created this operator, if any.

**storage** → dict (Read Only): Storage is dictionary associated with this operator. Values stored in this dictionary are persistent, and saved with the operator. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with methods such as [CLASS_OP].fetch() or [CLASS_OP].store() described below, or examined with an Examine DAT.

**tags** → list: Get or set a set of user defined strings. Tags can be searched using [CLASS_OP].findChildren() and the OP Find DAT.

**children** → list (Read Only): A list of operators contained within this operator. Only component operators have children, otherwise an empty list is returned.

**numChildren** → int (Read Only): Returns the number of children contained within the operator. Only component operators have children.

**numChildrenRecursive** → int (Read Only): Returns the number of operators contained recursively within this operator. Only component operators have children.

**op** → [CLASS_OP] or None (Read Only): The operator finder object, for accessing operators through paths or shortcuts.

**opex** → [CLASS_OP] (Read Only): An operator finder object, for accessing operators through paths or shortcuts. Works like the op() shortcut method, except it will raise an exception if it fails to find the node instead of returning None as op() does.

**parent** → Shortcut (Read Only): The Parent Shortcut object, for accessing parent components through indices or shortcuts.

**iop** → [CLASS_OP] (Read Only): The Internal Operator Shortcut object, for accessing internal shortcuts. See also [REF_InternalOperators].

**ipar** → ParCollection (Read Only): The Internal Operator Parameter Shortcut object, for accessing internal shortcuts. See also [REF_InternalParameters].

**currentPage** → [CLASS_Page]: Get or set the currently displayed parameter page. It can be set by setting it to another page or a string label.

#### Common Flags

**activeViewer** → bool: Get or set Viewer Active Flag.

**allowCooking** → bool: Get or set Cooking Flag. Only COMPs can disable this flag.

**bypass** → bool: Get or set Bypass Flag.

**cloneImmune** → bool: Get or set Clone Immune Flag.

**current** → bool: Get or set Current Flag.

**display** → bool: Get or set Display Flag.

**expose** → bool: Get or set the Expose Flag which hides a node from view in a network.

**lock** → bool: Get or set Lock Flag.

**selected** → bool: Get or set Selected Flag. This controls if the node is part of the network selection. (yellow box around it).

**seq** → (Read Only): An intermediate sequence collection object, from which a specific sequence group can be found.

**python** → bool: Get or set parameter expression language as python.

**render** → bool: Get or set Render Flag.

**showCustomOnly** → bool: Get or set the Show Custom Only Flag which controls whether or not non custom parameters are display inparameter dialogs.

**showDocked** → bool: Get or set Show Docked Flag. This controls whether this node is visible or hidden when it is docked to another node.

**viewer** → bool: Get or set Viewer Flag.

#### Appearance

**color** → tuple(r, g, b): Get or set color value, expressed as a 3-tuple, representing its red, green, blue values. To convert between color spaces, use the built in colorsys module.

**comment** → str: Get or set comment string.

**nodeHeight** → int: Get or set node height, expressed in network editor units.

**nodeWidth** → int: Get or set node width, expressed in network editor units.

**nodeX** → int: Get or set node X value, expressed in network editor units, measured from its left edge.

**nodeY** → int: Get or set node Y value, expressed in network editor units, measured from its bottom edge.

**nodeCenterX** → int: Get or set node X value, expressed in network editor units, measured from its center.

**nodeCenterY** → int: Get or set node Y value, expressed in network editor units, measured from its center.

**dock** → [CLASS_OP]: Get or set the operator this operator is docked to. To clear docking, set this member to None.

**docked** → list (Read Only): The (possibly empty) list of operators docked to this node.

#### Connection

**inputs** → list (Read Only): List of input operators (via left side connectors) to this operator. To get the number of inputs, use len(OP.inputs).

**outputs** → list (Read Only): List of output operators (via right side connectors) from this operator.

**inputConnectors** → list (Read Only): List of input connectors (on the left side) associated with this operator.

**outputConnectors** → list (Read Only): List of output connectors (on the right side) associated with this operator.

#### Cook Information

**cookFrame** → float (Read Only): Last frame at which this operator cooked.

**cookTime** → float (Read Only): Deprecated Duration of the last measured cook (in milliseconds).

**cpuCookTime** → float (Read Only): Duration of the last measured cook in CPU time (in milliseconds).

**cookAbsFrame** → float (Read Only): Last absolute frame at which this operator cooked.

**cookStartTime** → float (Read Only): Last offset from frame start at which this operator cook began, expressed in milliseconds.

**cookEndTime** → float (Read Only): Last offset from frame start at which this operator cook ended, expressed in milliseconds. Other operators may have cooked between the start and end time. See the cookTime member for this operator's specific cook duration.

**cookedThisFrame** → bool (Read Only): True when this operator has cooked this frame.

**cookedPreviousFrame** → bool (Read Only): True when this operator has cooked the previous frame.

**childrenCookTime** → float (Read Only): Deprecated The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenCPUCookTime** → float (Read Only): The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenCookAbsFrame** → float (Read Only): Deprecated The absolute frame on which childrenCookTime is based.

**childrenCPUCookAbsFrame** → float (Read Only): The absolute frame on which childrenCPUCookTime is based.

**gpuCookTime** → float (Read Only): Duration of GPU operations during the last measured cook (in milliseconds).

**childrenGPUCookTime** → float (Read Only): The total accumulated GPU cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenGPUCookAbsFrame** → float (Read Only): The absolute frame on which childrenGPUCookTime is based.

**totalCooks** → int (Read Only): Number of times the operator has cooked.

**cpuMemory** → int (Read Only): The approximate amount of CPU memory this Operator is using, in bytes.

**gpuMemory** → int (Read Only): The amount of GPU memory this OP is using, in bytes.

#### Type

**type** → str (Read Only): Operator type as a string. Example: 'oscin'.

**subType** → str (Read Only): Operator subtype. Currently only implemented for components. May be one of: 'panel', 'object', or empty string in the case of base components.

**OPType** → str (Read Only): Python operator class type, as a string. Example: 'oscinCHOP'. Can be used with COMP.create() method.

**label** → str (Read Only): Operator type label. Example: 'OSC In'.

**icon** → str (Read Only): Get the letters used to create the operator's icon.

**family** → str (Read Only): Operator family. Example: CHOP. Use the global dictionary families for a list of each operator type.

**isFilter** → bool (Read Only): True if operator is a filter, false if it is a generator.

**minInputs** → int (Read Only): Minimum number of inputs to the operator.

**maxInputs** → int (Read Only): Maximum number of inputs to the operator.

**isMultiInputs** → bool (Read Only): True if inputs are ordered, false otherwise. Operators with an arbitrary number of inputs have unordered inputs, example Merge CHOP.

**visibleLevel** → int (Read Only): Visibility level of the operator. For example, expert operators have visibility level 1, regular operators have visibility level 0.

**isBase** → bool (Read Only): True if the operator is a Base (miscellaneous) component.

**isCHOP** → bool (Read Only): True if the operator is a CHOP.

**isCOMP** → bool (Read Only): True if the operator is a component.

**isDAT** → bool (Read Only): True if the operator is a DAT.

**isMAT** → bool (Read Only): True if the operator is a Material.

**isObject** → bool (Read Only): True if the operator is an object.

**isPanel** → bool (Read Only): True if the operator is a Panel.

**isSOP** → bool (Read Only): True if the operator is a SOP.

**isTOP** → bool (Read Only): True if the operators is a TOP.

**licenseType** → str (Read Only): Type of License required for the operator.

### Methods

#### General

**NOTE**: create(), copy() and copyOPs() is done by the parent operator (a component). For more information see [CLASS_COMP].create, [CLASS_COMP].copy and [CLASS_COMP].copyOPs methods.

**pars(pattern)→ list**: Returns a (possibly empty) list of parameter objects that match the pattern.

**cook(force=False, recurse=False, includeUtility=False)→ None**: Cook the contents of the operator if required.

**copyParameters(OP, custom=True, builtin=True)→ None**: Copy all of the parameters from the specified operator. Both operators should be the same type.

**changeType(OPtype)→ OP**: Change referenced operator to a new operator type. After this call, this OP object should no longer be referenced. Instead use the returned OP object.

**dependenciesTo(OP)→ list**: Returns a (possibly empty) list of operator dependency paths between this operator and the specified operator. Multiple paths may be found.

**evalExpression(str)→ value**: Evaluate the expression from the context of this OP. Can be used to evaluate arbitrary snippets of code from arbitrary locations.

**destroy()→ None**: Destroy the operator referenced by this OP. An exception will be raised if the OP's operator has already been destroyed.

**var(name, search=True)→ str**: Evaluate avariable. This will return the empty string, if not found. Most information obtained from variables (except for Root and Component variables) are accessible through other means in Python, usually in the global td module.

**openMenu(x=None, y=None)→ None**: Open a node menu for the operator at x, y. Opens at mouse if x & y are not specified.

**relativePath(OP)→ str**: Returns the relative path from this operator to the OP that is passed as the argument. See [CLASS_OP].shortcutPath for a version using expressions.

**setInputs(listOfOPs)→ None**: Set all the operator inputs to the specified list.

**shortcutPath(OP, toParName=None)→ str**: Returns an expression from this operator to the OP that is passed as the argument. See [CLASS_OP].relativePath for a version using relative path constants.

**ops(pattern1, pattern2.., includeUtility=False)→ list of OPs**: Returns a (possibly empty) list of OPs that match the patterns, relative to the inside of this OP.

**resetPars(parNames='*', parGroupNames='*', pageNames='*', includeBuiltin=True, includeCustom=True)→ bool**: Resets the specified parameters in the operator.

#### Errors

**addScriptError(msg)→ None**: Adds a script error to a node.

**addError(msg)→ None**: Adds an error to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

**addWarning(msg)→ None**: Adds a warning to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

**errors(recurse=False)→ str**: Get error messages associated with this OP.

**warnings(recurse=False)→ str**: Get warning messages associated with this OP.

**scriptErrors(recurse=False)→ str**: Get script error messages associated with this OP.

**clearScriptErrors(recurse=False, error='*')→ None**: Clear any errors generated during script execution. These may be generated during execution of DATs, Script Nodes, Replicator COMP callbacks, etc.

**childrenCPUMemory()→ int**: Returns the total CPU memory usage for all the children from this COMP.

**childrenGPUMemory()→ int**: Returns the total GPU memory usage for all the children from this COMP.

#### Appearance

**resetNodeSize()→ None**: Reset the node tile size to its default width and height.

#### Viewers

**closeViewer(topMost=False)→ None**: Close the floating content viewers of the OP.

**openViewer(unique=False, borders=True)→ None**: Open a floating content viewer for the OP.

**resetViewer(recurse=False)→ None**: Reset the OP content viewer to default view settings.

**openParameters()→ None**: Open a floating dialog containing the operator parameters.

#### Storage

Storage can be used to keep data within components. Storage is implemented as one python dictionary per node.

When an element of storage is changed by using n.store() as explained below, expressions and operators that depend on it will automatically re-cook. It is retrieved with the n.fetch() function.

Storage is saved in .toe and .tox files and restored on startup.

Storage can hold any python object type (not just strings as in Tscript variables). Storage elements can also have optional startup values, specified separately. Use these startup values for example, to avoid saving and loading some session specific object, and instead save or load a well defined object like None.

See the Examine DAT for procedurally viewing the contents of storage.

**fetch(key, default, search=True, storeDefault=False)→ value**: Return an object from the OP storage dictionary. If the item is not found, and a default it supplied, it will be returned instead.

**fetchOwner(key)→ OP**: Return the operator which contains the stored key, or None if not found.

**store(key, value)→ value**: Add the key/value pair to the OP's storage dictionary, or replace it if it already exists. If this value is not intended to be saved and loaded in the toe file, it can be be given an alternate value for saving and loading, by using the method storeStartupValue described below.

**unstore(keys1, keys2..)→ None**: For key, remove it from the OP's storage dictionary. Pattern Matching is supported as well.

**storeStartupValue(key, value)→ None**: Add the key/value pair to the OP's storage startup dictionary. The storage element will take on this value when the file starts up.

**unstoreStartupValue(keys1, keys2..)→ None**: For key, remove it from the OP's storage startup dictionary. Pattern Matching is supported as well. This does not affect the stored value, just its startup value.

#### Miscellaneous

****getstate**()→ dict**: Returns a dictionary with persistent data about the object suitable for pickling and deep copies.

****setstate**()→ dict**: Reads the dictionary to update persistent details about the object, suitable for unpickling and deep copies.
