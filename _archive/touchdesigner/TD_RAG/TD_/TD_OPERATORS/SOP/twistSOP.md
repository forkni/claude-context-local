# SOP twistSOP

## Overview

The Twist SOP performs non-linear deformations such as bend, linear taper, shear, squash and stretch, taper and twist.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `op` | Operation | Menu | This menu allows you to select a type of non-linear deformation. Select from the following options: |
| `paxis` | Primary Axis | Menu | These menus allows you to select the primary and secondary axes for the deformation. The selected deformation will first occur in the Primary Axis and then the Secondary Axis. |
| `saxis` | Secondary Axis | Menu | These menus allows you to select the primary and secondary axes for the deformation. The selected deformation will first occur in the Primary Axis and then the Secondary Axis. |
| `p` | Pivot | XYZ | This field allows you to choose the origin of the deformation. |
| `strength` | Strength | Float | The Strength of the effect being applied. The Rolloff determines an accentuation of the effect being applied. When you are using different types of transformations this Strength / Roll will have di... |
| `roll` | Rolloff | Float | The Strength of the effect being applied. The Rolloff determines an accentuation of the effect being applied. When you are using different types of transformations this Strength / Roll will have di... |

## Usage Examples

### Basic Usage

```python
# Access the SOP twistSOP operator
twistsop_op = op('twistsop1')

# Get/set parameters
freq_value = twistsop_op.par.active.eval()
twistsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
twistsop_op = op('twistsop1')
output_op = op('output1')

twistsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(twistsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **7** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
