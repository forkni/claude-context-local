# SOP polypatchSOP

## Overview

The Polypatch SOP creates a smooth polygonal patch from a mesh primitive or a set of faces (polygons, NURBS or Bezier curves).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Subset of input to use. Accepts patterns, as described in Pattern Matching. |
| `basis` | Basis | Menu | Select spline type: Cardinal or BSpline. |
| `connecttype` | Connectivity | Menu | This option is used to select how the points of the created surface are connected. |
| `closeu` | U Wrap | Menu | Settings for wrapping in U direction. |
| `closev` | V Wrap | Menu | Settings for wrapping in V direction. |
| `firstuclamp` | U Clamp (First) | Menu | Settings for clamping first end in U. |
| `lastuclamp` | U Clamp (Last) | Menu | Settings for clamping last end in U. |
| `firstvclamp` | V Clamp (First) | Menu | Settings for clamping first end in V. |
| `lastvclamp` | V Clamp (Last) | Menu | Settings for clamping last end in V. |
| `divisions` | Output Divisions | Int | The number of divisions in the output surface. Use more divisions for a smoother surface. |
| `polys` | Output Polygons | Toggle | Force polygonal rather than mesh output. |

## Usage Examples

### Basic Usage

```python
# Access the SOP polypatchSOP operator
polypatchsop_op = op('polypatchsop1')

# Get/set parameters
freq_value = polypatchsop_op.par.active.eval()
polypatchsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
polypatchsop_op = op('polypatchsop1')
output_op = op('output1')

polypatchsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(polypatchsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
