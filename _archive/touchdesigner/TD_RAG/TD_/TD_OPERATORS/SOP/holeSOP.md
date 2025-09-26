# SOP holeSOP

## Overview

The Hole SOP is for making holes where faces are enclosed, even if they are not in the same plane. It can also remove existing holes from the input geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `unbridge` | Unbridge Holes | Toggle | This function checks for bridges to holes in the input and removes the bridges, leaving the interior freestanding. At times you may need to unhole faces so that you can connect them in some other way. |
| `dist` | Distance Tolerance | Float | Interior polygons that are not in exactly the same plane as the exteriors can still become holes. The Distance Tolerance value tells the Hole SOP how far away potential holes can be from the exteri... |
| `angle` | Angle Tolerance | Float | Interior faces that are rotated in relation to the exterior faces can become holes. The Angle value sets the maximum rotation of the potential holes from the exteriors. Faces beyond this rotation w... |
| `snap` | Snap Holes to Outlines | Toggle | Points of any holes that are rotated or translated away from the exterior (or outline) plane will be moved so that they lie on the surface of the outline plane, thus avoiding twisted faces. |

## Usage Examples

### Basic Usage

```python
# Access the SOP holeSOP operator
holesop_op = op('holesop1')

# Get/set parameters
freq_value = holesop_op.par.active.eval()
holesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
holesop_op = op('holesop1')
output_op = op('output1')

holesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(holesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **5** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
