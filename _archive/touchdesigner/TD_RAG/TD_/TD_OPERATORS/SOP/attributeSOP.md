# SOP attributeSOP

## Overview

The Attribute SOP allows you to manually rename and delete point, vertex, and primitive attributes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `ptdel` | Delete Attributes | StrMenu | Use the field to specify the point attributes to delete. Simply enter a list of the attributes (separated by spaces) to delete, for example entering:Cd Alpha. You can also use the dropdown menu on ... |
| `pt` | Point Rename | Sequence | Sequence of point renames |
| `vertdel` | Delete Attributes | StrMenu | Use the field to specify the vertex attributes to delete. Simply enter a list of the attributes (separated by spaces) to delete, for example entering:uv N. You can also use the dropdown menu on the... |
| `vert` | Vertex Rename | Sequence | Sequence of vertex renames |
| `primdel` | Delete Attributes | StrMenu | Use the field to specify the primitive attributes to delete. Simply enter a list of the attributes (separated by spaces) to delete, for example entering:Cd creaseweight. You can also use the dropdo... |
| `prim` | Prim Rename | Sequence | Sequence of primitive renames |
| `attrdel` | Delete Attributes | StrMenu | Use the field to specify the detail attributes to delete. Simply enter a list of the attributes (separated by spaces) to delete. You can also use the dropdown menu on the right to select them. |
| `attr` | Detail Rename | Sequence | Sequence of detail renames |

## Usage Examples

### Basic Usage

```python
# Access the SOP attributeSOP operator
attributesop_op = op('attributesop1')

# Get/set parameters
freq_value = attributesop_op.par.active.eval()
attributesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
attributesop_op = op('attributesop1')
output_op = op('output1')

attributesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(attributesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **8** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
