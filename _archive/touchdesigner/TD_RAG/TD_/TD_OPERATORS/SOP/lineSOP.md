# SOP lineSOP

## Overview

The Line SOP creates straight lines.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `pa` | Point A | XYZ | These X,Y, and Z values set the position of the beginning of the line. |
| `pb` | Point B | XYZ | These X,Y, and Z values set the position of the end of the line. |
| `points` | Number of Points | Int | The number of points the line is made of. Minimum is 2 points. |
| `texture` | Texture Coordinates | Menu | Texture adds (0,1) coordinates to the vertices when set to Unit. Creates a rectangle without uv attributes when set to Off. |

## Usage Examples

### Basic Usage

```python
# Access the SOP lineSOP operator
linesop_op = op('linesop1')

# Get/set parameters
freq_value = linesop_op.par.active.eval()
linesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
linesop_op = op('linesop1')
output_op = op('output1')

linesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(linesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **4** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
