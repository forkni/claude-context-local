# SOP subdivideSOP

## Overview

The Subdivide SOP takes an input polygon surface (which can be piped into one or both inputs), and divides each face to create a smoothed polygon surface using a Catmull-Clark subdivision algorithm.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `subdivide` | Group | StrMenu | Subset of input to use as a polygonal mesh to subdivide. Accepts patterns, as described in Pattern Matching. |
| `creases` | Creases | StrMenu | This field allows you to specify a subset of the second input to use as creases. The elements of the second input specified by the Creases field are used as creases. Each edge in a crease polygon c... |
| `iterations` | Depth | Int | How many iterations to subdivide. Higher numbers give a smoother surface. |
| `overridecrease` | Override Crease Weight Attribute | Toggle | Determine if the crease sharpness should be determined by the primitive or vertex creaseweight attribute or by overridden by this SOP. |
| `creaseweight` | Crease Weight | Float | If the crease weight is overriden, this is the weight used.     Tip: The default is to have the Override Crease Weight Attribute enabled. So you can simply set a value which applies to all the crea... |
| `outputcrease` | Generate Resulting Creases | Toggle | If any creases are sharper than the Depth, they will be left over in the resulting geometry. With this parameter enabled, these left over creases are created with the appropriate primitive attribut... |
| `outcreasegroup` | New Group | Str | Name of the group to place the generated creases into. |
| `closeholes` | Close Cracks | Menu | Choose how gaps are handled in the output geometry. |
| `surroundpoly` | Surrounding Faces | Menu | Choose how to handle the polygons on either side of a crack when pulling or stitching it closed. |
| `bias` | Bias | Float | Determines which points are moved when pulling crack closed.      0 means move points on subdivided area to meet boundary.    1 means move points on boundary to meet subdivided area. |

## Usage Examples

### Basic Usage

```python
# Access the SOP subdivideSOP operator
subdividesop_op = op('subdividesop1')

# Get/set parameters
freq_value = subdividesop_op.par.active.eval()
subdividesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
subdividesop_op = op('subdividesop1')
output_op = op('output1')

subdividesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(subdividesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
