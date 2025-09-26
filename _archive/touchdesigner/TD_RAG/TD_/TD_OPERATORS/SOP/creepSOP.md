# SOP creepSOP

## Overview

The Creep SOP lets you deform and animate Source Input geometry along the surface of the Path Input geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `reset` | Reset | Pulse | Reset's the creep state based on Reset Method parameter below. |
| `resetmethod` | Reset Method | Menu | The Source Input is Translated, Rotated and Scaled so as to complete the given options listed below. |
| `t` | Translate | XYZ | Translate the Source Input Creep geometry on the surface of the Path Input. |
| `r` | Rotate | XYZ | Rotate the Source Input creep geometry on the surface of the Path Input. |
| `s` | Scale | XYZ | Scale the Source Input creep geometry on the surface of the Path Input. |

## Usage Examples

### Basic Usage

```python
# Access the SOP creepSOP operator
creepsop_op = op('creepsop1')

# Get/set parameters
freq_value = creepsop_op.par.active.eval()
creepsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
creepsop_op = op('creepsop1')
output_op = op('output1')

creepsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(creepsop_op)
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
