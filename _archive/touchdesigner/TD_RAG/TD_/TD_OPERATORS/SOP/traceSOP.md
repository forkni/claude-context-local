# SOP traceSOP

## Overview

The Trace SOP reads an image file and automatically traces it, generating a set of faces around areas exceeding a certain brightness threshold.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `top` | TOP Name | TOP | Specify the TOP image to trace. |
| `thresh` | Threshold | Float | Brightness level value adjusts where trace outline in image occurs. |
| `addtexture` | Add Point Texture | Toggle | This option allows the generation of point texture coordinates (UVs). This may occasionally be necessary when the Convert to Poly option is enabled. |
| `delborder` | Remove Borders | Toggle | When enabled, this option eliminates extraneous data along the edges of the original image so it isn't traced. This is useful for when "dirty" edges exist in the original image that you don't want ... |
| `normals` | Compute Normals | Toggle | Creates normals on the geometry. |
| `bordwidth` | Border Width | Int | The number of pixels the removal border should be. |
| `doresample` | Resample Shapes | Toggle | Determines level of refinement (number of points) for generating trace outlines. |
| `step` | Step Size | Float | Value controlling trace outline refinement when Resample Shapes is checked. |
| `dosmooth` | Smooth Shapes | Toggle | When this option is checked, the geometry is filtered to remove sharp corners. |
| `corner` | Corner Delta | Float | Value controlling corner smoothing when Smooth Shapes is checked. |
| `fitcurve` | Fit to Curves | Toggle | If selected, the geometry at this point is converted to two-dimensional Bzier curves. Flat edges are preserved in polygons. |
| `error` | Fitting Error | Float | Value controlling accuracy of the above curve fitting process. For best results, the input should retain as many points as possible, i.e. do not select Smooth Shapes or Resample Shapes. |
| `convpoly` | Convert to Poly | Toggle | This option will convert the above curves back into polygons. |
| `lod` | Level of Detail | Float | This value controls the accuracy of the conversion back into polygons. |
| `hole` | Hole Faces | Toggle | This will bridge all holes in the output so that they may be rendered properly. Bzier curves and polygons can be holed, but polygonal holing sometimes produces better results. You may want to use t... |

## Usage Examples

### Basic Usage

```python
# Access the SOP traceSOP operator
tracesop_op = op('tracesop1')

# Get/set parameters
freq_value = tracesop_op.par.active.eval()
tracesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tracesop_op = op('tracesop1')
output_op = op('output1')

tracesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tracesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
