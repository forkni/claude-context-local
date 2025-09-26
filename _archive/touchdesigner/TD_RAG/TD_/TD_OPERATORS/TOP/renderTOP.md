# TOP renderTOP

## Overview

The Render TOP is used to render all 3D scenes in TouchDesigner.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `camera` | Camera(s) | Object | Specifies which Cameras to look through when rendering the scene. You can specify multiple cameras and retrieve each camera image using the Render Select TOP. |
| `multicamerahint` | Multi-Camera Hint | Menu | Helps the Render TOP optimize rendering when multiple cameras are used. Controls the Multi-Camera Rendering behavior for this node. |
| `geometry` | Geometry | Object | Specifies which Geometry will be included in the rendered scene. You can use Pattern Matching to specify objects using patterns. Example: geo* ^geo7 will render all Geometry components whose names ... |
| `lights` | Lights | Object | Specifies which Lights will be used to render the scene. You can use Pattern Matching here as well. |
| `antialias` | Anti-Alias | Menu | Sets the level of anti-aliasing in the scene. Setting this to higher values uses more graphics memory. |
| `rendermode` | Render Mode | Menu | You can render different projections:  normal 2D, Cube Map, Fish Eye (180), or Dual Paraboloid. The Cube Map renders 6 views as needed for environment maps in the Phong MAT and Environment Light CO... |
| `posside` | Positive Sides | Toggle | When Render Mode is Cube Map, specify which sides if the cube map are rendered, +X, +Y, or +Z. |
| `negside` | Negative Sides | Toggle | When Render Mode is Cube Map, specify which sides if the cube map are rendered, -X, -Y, or -Z. |
| `uvunwrapcoord` | UV Unwrap Coord | Menu | When Render Mode is UV Unwrap Coord, select which Texture Layer the coordinates are rendered to, |
| `uvunwrapcoordattrib` | UV Unwrap Coord Attribute | Str |  |
| `transparency` | Transparency | Menu | Helps to render transparent geometry in proper depth order. More in-depth discussion available in the  Transparency article. |
| `depthpeel` | Depth Peel | Toggle | Depth peeling is a technique used as part of Order-Independent Transparency, but this parameter allows you to use it in a different way. This parameter enables rendering depth-peels, but without co... |
| `transpeellayers` | Transparency/Peel Layers | Int | Number of passes the renderer will use when Order Independant Transparency is turned on. |
| `render` | Render | Toggle | Enables rendering; 1 = on, 0 = off. |
| `dither` | Dither | Toggle | Dithers the rendering to help deal with banding and other artifacts created by precision limitations of 8-bit displays. |
| `coloroutputneeded` | Color Output Needed | Toggle | This is an optimization if you don't actually need the color result from this pass. Turning this off avoids a copy from the offscreen render buffer to the TOP's texture. When anti-aliasing is enabl... |
| `drawdepthonly` | Draw Depth Only | Toggle | This will cause the render to only draw depth values to the depth buffer. No color values will be created.  To make use of the depth buffer, use the Depth TOP. |
| `numcolorbufs` | # of Color Buffers | Int | Any shader you write can output to more than one RGBA buffer at a time. For GLSL 3.3+ you would use the layout(location = 1) specifier on an out variable in the pixel shader to write to the 2nd buf... |
| `allowbufblending` | Allow Blending for Extra Buffers | Toggle | Controls if blending (as enabled by the MAT common page setting) will be enabled for extra buffers beyond the first one. Often the extra buffers are used to write other types of information such as... |
| `depthformat` | Depth Buffer Format | Menu | Use either a 24-bit Fixed-Point or 32-bit Floating-Point depth buffer (single channel image). |
| `cullface` | Cull Face | Menu | Front Faces, Back Faces, Both Faces, Neither. Will cause the render to avoid rendering certain polygon faces depending on their orientation to the camera. Refer to Back-Face Culling for more inform... |
| `overridemat` | Override Material | MAT | This allows you to specify a material that will be applied to every Geometry that is rendered in the Render TOP. It is useful for pre-processing passes where we are outputting information about the... |
| `polygonoffset` | Polygon Depth Offset | Toggle | This feature pushes the polygons back into space a tiny fraction. This is useful when you are rendering two polygons directly ontop of each other and are experiencing Z-Fighting. Refer to Polygon D... |
| `polygonoffsetfactor` | Offset Factor | Float | Adds an offset to the Z value that depends on how sloped the surface is to the viewer. |
| `polygonoffsetunits` | Offset Units | Float | Adds a constant offset to the Z value. |
| `overdraw` | Display Overdraw | Toggle | This feature visually shows the overdraw in the scene. Refer to the Early Depth-Test article for more information. In particular the Analyzing Overdraw section. |
| `overdrawlimit` | Overdraw Limit | Int | This value quantizes the outputted color value to some # of overdraws. Refer to the Early Depth-Test for more information. |
| `cropleft` | Crop Left | Float | Positions the left edge of the rendered image. |
| `cropleftunit` | Crop Left Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `cropright` | Crop Right | Float | Positions the right edge of the rendered image. |
| `croprightunit` | Crop Right Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `cropbottom` | Crop Bottom | Float | Positions the bottom edge of the rendered image. |
| `cropbottomunit` | Crop Bottom Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `croptop` | Crop Top | Float | Positions the top edge of the rendered image. |
| `croptopunit` | Crop Top Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `vec` | Vector | Sequence | Sequence of uniform name and value pairs. |
| `uni0name` | Uniform Name | Str | The uniform name, as declared in the shader. |
| `sampler` | Sampler | Sequence | Sequence of sampler parmaeters, including uniform name, TOP reference, and sampling parameters. |
| `image` | Image | Sequence | A sequence of parameters to control image outputs available for the GLSL MATs. |
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
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. For every pass after the first it takes the result of the previous pass and replaces the node's first input with the result of the... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP renderTOP operator
rendertop_op = op('rendertop1')

# Get/set parameters
freq_value = rendertop_op.par.active.eval()
rendertop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
rendertop_op = op('rendertop1')
output_op = op('output1')

rendertop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(rendertop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **52** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
