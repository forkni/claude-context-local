# SOP wireframeSOP

## Overview

The Wireframe SOP converts edges to tubes and points to spheres, creating the look of a wire frame structure in renderings.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `radius` | Wire Radius | Float | Radius of the individual wires used in the construction of the geometry. |
| `corners` | Round Corners | Toggle | When selected, rounds the corners by placing spheres at the point locations with the same radius as the wires. |
| `caps` | End Caps | Toggle | When selected, places end-caps on all wire geometry. |
| `remove` | Remove Polygons | Toggle | Removes the polygons from the output geometry, leaving only the converted line structures. |
| `fast` | Fast Wire | Toggle | Faster wire calculation at the expense of accuracy. |

## Usage Examples

### Basic Usage

```python
# Access the SOP wireframeSOP operator
wireframesop_op = op('wireframesop1')

# Get/set parameters
freq_value = wireframesop_op.par.active.eval()
wireframesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
wireframesop_op = op('wireframesop1')
output_op = op('output1')

wireframesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(wireframesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **6** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
