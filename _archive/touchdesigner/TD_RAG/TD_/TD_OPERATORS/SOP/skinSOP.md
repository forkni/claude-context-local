# SOP skinSOP

## Overview

The Skin SOP takes any number of faces and builds a skin surface over them.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `uprims` | U Cross Sections | StrMenu | Empty by default, this field provides a way to specify a subset of the first input's faces and surfaces. Do so by selecting one or more primitive groups from this field's pop-up menu. |
| `vprims` | V Cross Sections | StrMenu | Empty by default, this field provides a way to specify a subset of V faces. If a second input exists, the primitive groups available for selection are taken from the second input. If only the first... |
| `surftype` | Connectivity | Menu | (Results only viewable for polygons and meshes). |
| `keepshape` | Preserve Shape | Toggle | This parameter determines the precision of a linear skin (case c in the diagram). If enabled, it ensures that the generated surface goes through each cross-section. Here, a cross-section can be a f... |
| `closev` | V Wrap | Menu | This menu (menu: Off, On, If primitive does) setting determines whether the surface should be wrapped in the V parametric direction. The options are to open (Off), close (On), or inherit the closur... |
| `force` | Use V Order | Toggle | Enables or disables the use of the V Order parameter. If the flag is OFF, the skinned surface is built as a cubic (order 4) in V, unless fewer than four cross-sections for an open V or 3 cross-sect... |
| `orderv` | V Order | Int | Specifies the order of the skinned surface when the V Order flag is enabled. A NURB surface of order "n" can be constructed with at least n or n-1 cross-sections, depending on whether the surface i... |
| `skinops` | Skin | Menu | Can optionally skin subgroups of n primitives or every nth primitive in a cyclical manner.     For example; assume there are six primitives numbered for 0 - 5, and N = 2. Then,       Groups will ge... |
| `inc` | N | Int | Determines the number of primitives to be either grouped or skipped. N2. |
| `prim` | Keep Primitives | Toggle | Determines whether the input primitives will be preserved (On) or deleted from the output (Off). |
| `polys` | Output Polygons | Toggle | If set, this flag instructs the program to convert the skinned surface(s) to polygons if the surface type is Mesh. |

## Usage Examples

### Basic Usage

```python
# Access the SOP skinSOP operator
skinsop_op = op('skinsop1')

# Get/set parameters
freq_value = skinsop_op.par.active.eval()
skinsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
skinsop_op = op('skinsop1')
output_op = op('output1')

skinsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(skinsop_op)
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
