# MAT depthMAT

## Overview

The Depth Only MAT can be used to prevent objects from being drawn by making an invisible barrier in Z.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `dodeform` | Deform | Toggle | Enables deforms on this material. |
| `deformdata` | Get Bone Data: | Menu | Specifies where the deform bone data will be obtained. |
| `targetsop` | SOP with Capture Data | OP | Specifies the SOP that contains the deform capture attributes. |
| `pcaptpath` | pCaptPath Attrib | Str | Specifies the name of the pCaptPath attribute to use. When your geometry has been put through a Bone Group SOP, the attributes will be split into names like pCaptPath0, pCaptPath1. You can only ren... |
| `pcaptdata` | pCaptData Attrib | Str | Much like pCaptPath Attrib. |
| `skelrootpath` | Skeleton Root Path | Object | Specifies the path to the COMP where the root of the skeleton is located. |
| `mat` | MAT | MAT | When obtaining deform data from a MAT or a Deform In MAT, this is where that MAT is specified. |
| `blending` | Blending (Transparency) | Toggle | This toggle enables and disables blending. However see the wiki article Transparency. |
| `blendop` | Blend Operation | Menu |  |
| `srcblend` | Source Color * | Menu | This value is multiplied by the color value of the pixel that is being written to the Color-Buffer (also know as the Source Color). |
| `destblend` | Destination Color * | Menu | This value is multiplied by the color value of the pixel currently in the Color-Buffer (also known as the Destination Color). |
| `separatealphafunc` | Separate Alpha Function | Toggle | This toggle enables and disables separate blending options for the alpha values. |
| `blendopa` | Alpha Blend Operation | Menu |  |
| `srcblenda` | Source Alpha * | Menu | This value is multiplied by the alpha value of the pixel that is being written to the Color-Buffer (also know as the Source Alpha). |
| `destblenda` | Destination Alpha * | Menu | This value is multiplied by the alpha value of the pixel currently in the Color-Buffer (also known as the Destination Alpha). |
| `blendconstant` | Blend Constant Color | RGB |  |
| `blendconstanta` | Blend Constant Alpha | Float |  |
| `legacyalphabehavior` | Legacy Alpha Behavior | Toggle |  |
| `postmultalpha` | Post-Mult Color by Alpha | Toggle | Multiplies the color by alpha after all other operations have taken place. |
| `pointcolorpremult` | Point Color Pre-Multiply | Menu |  |
| `depthtest` | Depth Test | Toggle | Enables and disables the Depth-Test. If the depth-test is disabled, depths values aren't written to the Depth-Buffer. |
| `depthfunc` | Depth Test Function | Menu | The depth value of the pixel being drawn is compared to the depth value currently in the depth-buffer using this function. If the test passes then the pixel is drawn to the Frame-Buffer. If the tes... |
| `depthwriting` | Write Depth Values | Toggle | If Write Depth Values is on, pixels that pass the depth-test will write their depth value to the Depth-Buffer. If this isn't on then no changes will be made to the Depth-Buffer, regardless of if th... |
| `alphatest` | Discard Pixels Based on Alpha | Toggle | This enables or disables the pixel alpha test. |
| `alphafunc` | Keep Pixels with Alpha | Menu | This menu works in conjunction with the Alpha Threshold parameter below in determining which pixels to keep based on their alpha value. |
| `alphathreshold` | Alpha Threshold | Float | This value is what the pixel's alpha is compared to to determine if the pixel should be drawn. Pixels with alpha greater than the Alpha Threshold will be drawn. Pixels with alpha less than or equal... |
| `wireframe` | Wire Frame | Menu | Enables and disables wire-frame rendering with the option of OpenGL Tesselated or Topology based wireframes. |
| `wirewidth` | Line Width | Float | This value is the width that the wires will be. This value is in pixels. |
| `cullface` | Cull Face | Menu | Selects which faces to render. |
| `polygonoffset` | Polygon Depth Offset | Toggle | Turns on the polygon offset feature. |
| `polygonoffsetfactor` | Offset Factor | Float |  |
| `polygonoffsetunits` | Offset Units | Float |  |

## Usage Examples

### Basic Usage

```python
# Access the MAT depthMAT operator
depthmat_op = op('depthmat1')

# Get/set parameters
freq_value = depthmat_op.par.active.eval()
depthmat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
depthmat_op = op('depthmat1')
output_op = op('output1')

depthmat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(depthmat_op)
```

## Technical Details

### Operator Family

**MAT** - Material Operators - Shading and material definitions

### Parameter Count

This operator has **32** documented parameters.

## Navigation

- [Back to MAT Index](../MAT/MAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
