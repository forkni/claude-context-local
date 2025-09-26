# TOP glslmultiTOP

## Overview

The GLSL Multi TOP renders a GLSL shader into a TOP image.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `glslversion` | GLSL Version | Menu | Pick what version of GLSL to compile the shader with. |
| `mode` | Mode | Menu | Choose what type of shader you are writing, vertex/pixel shader, or a compute shader. |
| `predat` | Preprocess Directives | DAT |  |
| `vertexdat` | Vertex Shader | DAT | Points to the DAT holding the Vertex Shader. Drag & Drop a DAT here, or manually enter the path to the DAT. |
| `pixeldat` | Pixel Shader | DAT | Points to the DAT holding the Pixel Shader. Drag & Drop a DAT here, or manually enter the path to the DAT. |
| `computedat` | Compute Shader | DAT | Points to the DAT holding the Compute Shader. Drag & Drop a DAT here, or manually enter the path to the DAT. |
| `loaduniformnames` | Load Uniform Names | Pulse | When this button is pressed the node will try to pre-fill all it's uniform parameter with uniforms that are declare in the shader. Note that the shader compiler will likely not expose uniforms that... |
| `autodispatchsize` | Auto Dispatch Size | Toggle | Automatically set the dispatch size based on the compute shader's local size and the output texture resolution. Ensures at least one thread per pixel will execute. |
| `dispatchsize` | Dispatch Size | Int | The dispatch size to use when executing a compute shader. |
| `outputaccess` | Output Access | Menu | Controls how the output textures will be accessed. If the textures will be read from (such as using previous frame's values), then the access should be changed to Read-Write instead of Write Only. |
| `type` | Output Type | Menu | Specify what type of texture to create. When creating  a 3D texture the TOP will render once for every slice of the output. Refer to  3D Textures and 2D Texture Arrays for more info. |
| `depth` | Depth | Menu | Set the depth of the 3D texture from the Input or the Custom Depth parameter. |
| `customdepth` | Custom Depth | Int | Manually set the depth of the 3D texture, otherwise it will use the depth of the input. |
| `clearoutputs` | Clear Outputs | Toggle |  |
| `clearvalue` | Clear Value | RGBA |  |
| `inputmapping` | Input Mapping | Menu | Determines how the node's input(s) are passed into the shader for use when creating a 3D Texture. By default all of the inputs are passed to each slice. When using the N inputs per Slice mode, the ... |
| `nval` | N Value | Int | Determines how many inputs are passed to the shader per slice when using the N inputs per Slice mode for Input Mapping. If for example this is set to 2, then the first 2 inputs will be passed to th... |
| `inputextenduv` | Input Extend Mode UV | Menu | Controls what is returned from your texture sampling functions when the U and V texture coordinates (called S and T in the shader) are outside [0-1] range. |
| `inputextendw` | Input Extend Mode W | Menu | Controls what is returned from your texture sampling functions when the W texture coordinate (called W in the shader) are outside [0-1] range. Only useful for 3D Texture. |
| `numcolorbufs` | # of Color Buffers | Int | Any shader you write can output to more than one RGBA buffer at a time. Turn up this value to have more color buffers allocated for you, and refer to [Write_a_GLSL_TOP#Outputting_to_Multiple_Color_... |
| `vec` | Vector | Sequence | Sequence of vector uniforms |
| `array` | Array | Sequence | Sequence of array uniforms |
| `matrix` | Matrix | Sequence | Sequence of matrix uniforms |
| `ac` | Atomic Counter | Sequence | Sequence of atomic counter uniforms |
| `const` | Constant | Sequence | Sequence of constant uniforms |
| `outputresolution` | Output Resolution | Menu | quickly change the resolution of the TOP's data. |
| `resolution` | Resolution | Int | Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size. The drop down menu ... |
| `resmenu` | Resolution Menu | Pulse | A drop-down menu with some commonly used resolutions. |
| `resmult` | Use Global Res Multiplier | Toggle | Uses the Global Resolution Multiplier found in Edit>Preferences>TOPs. This multiplies all the TOPs resolutions by the set amount. This is handy when working on computers with different hardware spe... |
| `outputaspect` | Output Aspect | Menu | Sets the image aspect ratio allowing any textures to be viewed in any size. Watch for unexpected results when compositing TOPs with different aspect ratios. (You can define images with non-square p... |
| `aspect` | Aspect | Float | Use when Output Aspect parameter is set to Custom Aspect. |
| `armenu` | Aspect Menu | Pulse | A drop-down menu with some commonly used aspect ratios. |
| `inputfiltertype` | Input Smoothness | Menu | This controls pixel filtering on the input image of the TOP. |
| `fillmode` | Fill Viewer | Menu | Determine how the TOP image is displayed in the viewer. NOTE:To get an understanding of how TOPs work with images, you will want to set this to Native Resolution as you lay down TOPs when starting ... |
| `filtertype` | Viewer Smoothness | Menu | This controls pixel filtering in the viewers. |
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. Making this larger than 1 is essentially the same as taking the output from each pass, and passing it into the first input of the ... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP glslmultiTOP operator
glslmultitop_op = op('glslmultitop1')

# Get/set parameters
freq_value = glslmultitop_op.par.active.eval()
glslmultitop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
glslmultitop_op = op('glslmultitop1')
output_op = op('output1')

glslmultitop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(glslmultitop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **38** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
