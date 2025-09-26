# SOP clipSOP

## Overview

The Clip SOP cuts and creases source geometry with a plane.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching in the Scripting Guide. |
| `clipop` | Keep | Menu | Options controlling what part of the clip to keep: |
| `dist` | Distance | Float | Allows you to move the cutting plane along the Direction vector. If the Direction (plane's normal) is 0 1 0, putting a positive number in the Distance field moves the plane up in Y. |
| `dir` | Direction | XYZ | The default values of 0 1 0 creates a Normal vector straight up in Y, which is perpendicular to the XZ plane, which becomes the clipping plane. 1 0 0 points the normal in positive X, giving a clipp... |
| `newg` | Create Groups | Toggle | When checked, allows you to generate specific groups for the geometry above and below the cutting plane. See the two group option fields below. This option is only available when All Primitives are... |
| `above` | Above Plane | Str | When Create Groups is checked, you can assign the geometry below the cutting plane to the Group name typed in this field. |
| `below` | Below Plane | Str | When Create Groups is checked, you can assign the geometry above the cutting plane to the Group name typed in this field. |

## Usage Examples

### Basic Usage

```python
# Access the SOP clipSOP operator
clipsop_op = op('clipsop1')

# Get/set parameters
freq_value = clipsop_op.par.active.eval()
clipsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
clipsop_op = op('clipsop1')
output_op = op('output1')

clipsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(clipsop_op)
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
