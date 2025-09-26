# SOP rasterSOP

## Overview

The Raster SOP converts a field of pixels into a field of colored geometry points suitable for laster devices.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `top` | TOP | TOP | The path to the TOP to rasterize into geometry. |
| `direction` | Direction | Menu | Determines the direction of rasterization. Depending on the image horizontal or vertical might work better. |
| `downloadtype` | Download Type | Menu | Gives the option for a delayed data download from the GPU, which is much faster and does not stall the render. |

## Usage Examples

### Basic Usage

```python
# Access the SOP rasterSOP operator
rastersop_op = op('rastersop1')

# Get/set parameters
freq_value = rastersop_op.par.active.eval()
rastersop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
rastersop_op = op('rastersop1')
output_op = op('output1')

rastersop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(rastersop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **3** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
