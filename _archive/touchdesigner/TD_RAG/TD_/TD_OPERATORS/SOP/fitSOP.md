# SOP fitSOP

## Overview

The Fit SOP fits a Spline curve to a sequence of points or a Spline surface to an m X n mesh of points.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `method` | Method | Menu | Specifies one of two fitting styles: approximation or interpolation. Each style has a number of parameters that are accessible from the respective folder. For more information see the Approximation... |
| `type` | Primitive Type | Menu | The output of the Fit SOP is a NURBS or Bzier primitive. All input faces are fitted to Spline curves, and all input surfaces are fitted to spline surfaces. The resulting shapes are identical whethe... |
| `surftype` | Connectivity | Menu | This option is used to select the type of surface, when using a Mesh Primitive Type. |
| `orderu` | U Order | Int | If the input is a face, this is the order of the Spline curve to be generated. If the input is a surface, this is the order of the fitted spline surface in the U parametric direction. |
| `orderv` | V Order | Int | If the input is a surface, this is the order of the fitted Spline surface in the V parametric direction. The V order is irrelevant if the input is a face. |
| `tol` | Tolerance | Float | This is the primary precision factor in approximation fitting. The smaller the tolerance, the closer the fit and the higher the number of generated vertices. If a small tolerance causes unwanted tw... |
| `smooth` | Smoothness | Float | For a set tolerance, the smoothness factor allows for more or less roundness in the generated shape. If this parameter is zero, it does not mean that the fit will be sharp. It simply indicates that... |
| `multipleu` | U Multiple Knots | Toggle | Sometimes the data set has sharp bends that must be preserved in the fitted shape. In this case, inserting multiple knots in the areas of sharp curvature will usually produce the right effect. Some... |
| `multiplev` | V Multiple Knots | Toggle | Sometimes the data set has sharp bends that must be preserved in the fitted shape. In this case, inserting multiple knots in the areas of sharp curvature will usually produce the right effect. Some... |
| `scope` | Scope | Menu | Scope establishes the interpolation method. |
| `dataparmu` | U Data Parameter | Menu | Specifies the parameterization of the data in the U direction (the only direction if the input is a curve). The data parameterization can be uniform, chord length, or centripetal.       Uniform Uni... |
| `dataparmv` | V Data Parameter | Menu | V data parameterization is identical to U data parameterization, but it affects the V direction when the input is a surface. It is not used when the input is a face. |
| `closeu` | U Wrap | Menu | This menu determines whether the fitted curve should be closed, or whether the fitted surface should be wrapped in the U parametric direction. The options are to open (Off), close (On), or inherit ... |
| `closev` | V Wrap | Menu | This menu determines whether the fitted surface should be wrapped in the V parametric direction. The options are to open (Off), close (On), or inherit the closure type from the input primitive. V W... |
| `corners` | Fit Corners | Toggle | Specifies whether corners in the data should be preserved when doing local curve interpolation. |

## Usage Examples

### Basic Usage

```python
# Access the SOP fitSOP operator
fitsop_op = op('fitsop1')

# Get/set parameters
freq_value = fitsop_op.par.active.eval()
fitsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fitsop_op = op('fitsop1')
output_op = op('output1')

fitsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fitsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
