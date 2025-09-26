# SOP choptoSOP

## Overview

The CHOP to SOP takes CHOP channels and generates 3D polygons in a SOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Modify only the points within this point group. If blank, all points are modified. Accepts patterns, as described in: Pattern Matching. |
| `chop` | CHOP | CHOP | Specifies which CHOP Network / CHOP contains the sample data to fetch. |
| `startpos` | Start Position | XYZ | Sets the bounds for positions that are not defined by a channel, ie. a channel is not set to one of the P attributes. |
| `endpos` | End Position | XYZ | Sets the bounds for positions that are not defined by a channel, ie. a channel is not set to one of the P attributes. |
| `method` | Method |  | The sample data fetch method: |
| `chanscope` | Channel Scope | StrMenu | The names to use to modify the attributes. |
| `attscope` | Attribute Scope | StrMenu | A string list of attributes to modify in the SOP. List of Common Attributes:      P - Point position (X, Y, Z) - 3 values    Pw - Point weight - 1 value    Cd - Point color (red, green, blue, alpha... |
| `organize` | Organize by Attribute |  | Instead of using the point index, use the value of this attribute as the index to use when looking up into the CHOP. |
| `mapping` | Mapping | Menu | Determines how the CHOP samples are mapped to the geometry points. |
| `compnml` | Compute Normals | Toggle | Creates normals on the geometry. |
| `comptang` | Compute Tangents | Toggle | Creates tangents on the geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP choptoSOP operator
choptosop_op = op('choptosop1')

# Get/set parameters
freq_value = choptosop_op.par.active.eval()
choptosop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
choptosop_op = op('choptosop1')
output_op = op('output1')

choptosop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(choptosop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
