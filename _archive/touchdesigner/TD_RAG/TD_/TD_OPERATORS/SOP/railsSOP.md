# SOP railsSOP

## Overview

The Rails SOP generates surfaces by stretching cross-sections between two rails.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `xsectgrp` | X-Section Groups | StrMenu | You can use a subset of primitives from the Cross-section input by specifying a group here. Accepts patterns, as described in Pattern Matching. |
| `railgrp` | Rail Groups | StrMenu | You can use a subset of primitives from the Rails input by specifying a group here. Accepts patterns, as described in Pattern Matching. |
| `cycle` | Cycle Type | Menu | Select how the cross=section is applied along the rails. |
| `pairs` | Sweep along Pairs of Rails | Toggle | Sweeps along rail 1 & 2, 3 & 4, 5 & 6 etc. instead of 1 & 2, 2 & 3, 3 & 4 etc. |
| `firstl` | Sweep along First and Last Rail | Toggle | Connects the cross-section between the first and last rails. |
| `stretch` | Stretch to Rails | Toggle | Stretches the cross-section geometry to the rail geometry. |
| `usevtx` | Use Vertex | Toggle | Specifies two vertices of the cross section polygon to be placed on rail1 and rail2 respectively. Very useful, for instance, to keep the first vertex on rail1 and the seventh vertex on rail2. |
| `vertex` | Connection Vertices | Int | The vertices at which the cross-section is connected to the rails. |
| `scale` | Scale | Float | Global scaling of the cross-sections. |
| `roll` | Roll | Float | Non-cumulative rotation of the cross sections around the backbone. All cross sections get the same rotation. |
| `noflip` | Fix Flipping | Toggle | Option to correct the flipping when no direction vector is used and the two rails happen to cross each other causing the normal to flip upside down. |
| `usedir` | Use Direction | Toggle | Uses the direction vector specified in the X, Y and Z coordinates. Otherwise it will use the normals of the geometry. |
| `dir` | Direction | XYZ | The direction vector to use. |
| `newg` | Create Output Groups | Toggle | Selecting this option enables the creation of groups. A group is created for each backbone that is incoming. This allows for easy skinning in the Skin SOP. |
| `railname` | Group Name | Str | Specify the name of your output groups in this field. Accepts patterns, as described in Pattern Matching. |

## Usage Examples

### Basic Usage

```python
# Access the SOP railsSOP operator
railssop_op = op('railssop1')

# Get/set parameters
freq_value = railssop_op.par.active.eval()
railssop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
railssop_op = op('railssop1')
output_op = op('output1')

railssop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(railssop_op)
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
