# SOP attributecreateSOP

## Overview

The Attribute Create SOP allows you to add normals or tangents to geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `compnml` | Compute Normals | Toggle | Creates normals on the geometry. |
| `comptang` | Compute Tangents | Toggle | Creates tangents on the geometry. |
| `mikktspace` | Use MikkTSpace | Toggle | Uses MikkTSpace standard when creating tangents. Fixes seams when normal mapping in certain cases, slower than regular method. |

## Usage Examples

### Basic Usage

```python
# Access the SOP attributecreateSOP operator
attributecreatesop_op = op('attributecreatesop1')

# Get/set parameters
freq_value = attributecreatesop_op.par.active.eval()
attributecreatesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
attributecreatesop_op = op('attributecreatesop1')
output_op = op('output1')

attributecreatesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(attributecreatesop_op)
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
