# SOP sweepSOP

## Overview

The Sweep SOP sweeps primitives in the Cross-section input along Backbone Source primitive(s), creating ribbon and tube-like shapes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `xgrp` | X-Section Group | StrMenu | You can use only a subset of primitives from the Cross-section inputs by specifying a group here. |
| `pathgrp` | Path Group | StrMenu | You can use only a subset of primitives from the Backbone inputs by specifying a group here. |
| `refgrp` | Reference Group | StrMenu | You can use only a subset of primitives from the Reference inputs by specifying a group here. |
| `cycle` | Cycle Type | Menu | Determines the Cycle Type based on these menu options. |
| `angle` | Angle Fix | Toggle | Attempts to fix buckling twists that may occur when sweeping. |
| `noflip` | Fix Flipping | Toggle | Attempts to fix buckling twists that may occur when sweeping by fixing flipped normals. |
| `skipcoin` | Remove Coincident Points on Path | Toggle | When selected, any points right on top of one another will be ignored. |
| `aimatref` | Aim at Reference Points | Toggle | Reference Points are used in conjunction with the backbone to control the orientation of the elements along the sweep. This is done by drawing a line between the reference point and corresponding b... |
| `usevtx` | Use Vertex | Toggle | Use vertex number of the incoming cross-section to place the cross-section on the backbone. |
| `vertex` | Connection Vertex | Int | Specify a specific vertex to connect to the backbone. |
| `scale` | Scale | Float | Scales the cross sections globally. |
| `twist` | Twist | Float | Cumulative rotation of the cross sections around the backbone. If a value of five is specified, the cross section at the first point of the backbone is rotated five degrees, the next ten degrees, t... |
| `roll` | Roll | Float | Non-cumulative rotation of the cross sections around the backbone. All cross sections get the same rotation.      Note: The Scale, Twist and Roll parameters can now be controlled directly by points... |
| `newg` | Create Groups | Toggle | Selecting this option enables the creation of groups. A group is created for each backbone that is incoming. This allows for easy skinning in the Skin SOP. |
| `sweepgrp` | Sweep Groups | Str | Specify the name of your output groups in this field. |
| `skin` | Skin Output | Menu | Determines the output based on these menu options. |
| `fast` | Fast Sweep | Toggle | Enables an optimized skinning technique which speeds up output from 2 - 4 times in many cases at the expense of accuracy. In order for it to work correctly, the input topologies must remain consist... |

## Usage Examples

### Basic Usage

```python
# Access the SOP sweepSOP operator
sweepsop_op = op('sweepsop1')

# Get/set parameters
freq_value = sweepsop_op.par.active.eval()
sweepsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sweepsop_op = op('sweepsop1')
output_op = op('output1')

sweepsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sweepsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
