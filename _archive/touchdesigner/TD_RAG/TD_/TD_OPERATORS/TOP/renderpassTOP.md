# TOP renderpassTOP

## Overview

The Render Pass TOP is used along with a Render TOP to achieve multipass rendering.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `renderinput` | Render/RenderPass TOP | TOP | The network path to the Render TOP used as input. This parameter can be used as an alternate to connecting a Render or Render Pass TOP to the Render Pass's input connector. Makes it easier to selec... |
| `camera` | Camera | Object | Specifies which Cameras to look through when rendering the scene. |
| `geometry` | Geometry | Object | Specifies which Geometry will be included in the rendered scene. You can use Pattern Matching to specify objects using patterns. Example: geo* ^geo7 will render all Geometry components whose names ... |
| `lights` | Lights | Object | Specifies which Lights will be used to render the scene. You can use Pattern Matching here as well. |
| `cleartocamcolor` | Clear to Camera Color | Toggle | Clears the values that are currently in the color buffer (coming from the TOP that is wired to the input of this node). |
| `cleardepth` | Clear Depth Buffer | Toggle | Clears the values that are currently in the depth buffer (coming from the TOP that is wired to the input of this node). |
| `posside` | Positive Sides | Toggle | When Render Mode is Cube Map, specify which sides if the cube map are rendered, +X, +Y, or +Z. |
| `negside` | Negative Sides | Toggle | When Render Mode is Cube Map, specify which sides if the cube map are rendered, -X, -Y, or -Z. |
| `transparency` | Transparency | Menu | Refer to to the same parameter in the Render TOPs help page. |
| `depthpeel` | Depth Peel | Toggle | Refer to to the same parameter in the Render TOPs help page. |
| `transpeellayers` | Transparency/Peel Layers | Int | Refer to to the same parameter in the Render TOPs help page. |
| `render` | Render | Toggle | Enables rendering; 1 = on, 0 = off. |
| `dither` | Dither | Toggle | Dithers the rendering to help deal with banding and other artifacts created by precision limitations of 8-bit displays. |
| `coloroutputneeded` | Color Output Needed | Toggle | This is an optimization if you don't actually need the color result from this pass. Turning this off avoids a copy from the offscreen render buffer to the TOP's texture. When anti-aliasing is enabl... |
| `drawdepthonly` | Draw Depth Only | Toggle | This will cause the render to only draw depth values to the depth buffer. No color values will be created. To make use of the depth buffer, use the Depth TOP. |
| `allowbufblending` | Allow Blending for Extra Buffers | Menu | Controls if blending (as enabled by the MAT common page setting) will be enabled for extra buffers beyond the first one. Often the extra buffers are used to write other types of information such as... |
| `cullface` | Cull Face | Menu | Front Faces, Back Faces, Both Faces, Neither. Will cause the render to avoid rendering certain polygon faces depending on their orientation to the camera. Refer to Back-Face Culling for more inform... |
| `overridemat` | Override Material | MAT | This allows you to specific a material that will be applied to every Geometry that is rendered in the Render TOP. It is useful for pre-processing passes where we are outputting infoformation about ... |
| `polygonoffset` | Polygon Depth Offset | Toggle | This feature pushes the polygons back into space a tiny fraction. This is useful when you are rendering two polygons directly ontop of each other and are experiencing Z-Fighting. Refer to Polygon D... |
| `polygonoffsetfactor` | Offset Factor | Float | Refer to to the same parameter in the Render TOPs help page. |
| `polygonoffsetunits` | Offset Units | Float | Refer to to the same parameter in the Render TOPs help page. |
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
| `sampler` | Sampler | Sequence |  |
| `vec` | Vector | Sequence |  |
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
# Access the TOP renderpassTOP operator
renderpasstop_op = op('renderpasstop1')

# Get/set parameters
freq_value = renderpasstop_op.par.active.eval()
renderpasstop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
renderpasstop_op = op('renderpasstop1')
output_op = op('output1')

renderpasstop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(renderpasstop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **46** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
