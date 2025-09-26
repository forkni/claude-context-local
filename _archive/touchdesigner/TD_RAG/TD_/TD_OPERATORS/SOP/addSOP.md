# SOP addSOP

## Overview

The Add SOP can both create new Points and Polygons on its own, or it can be used to add Points and Polygons to an existing input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `pointdat` | Points DAT | DAT | Path to a Table DAT containing point data. By default, x, y, z, and w can be defined in the first 4 columns of the table using un-named columns.         If the Named Attributes parameter below is t... |
| `namedattribs` | Named Attributes | Toggle | Allows extra attributes to be defined in the Point Table DAT above. |
| `keep` | Delete Geometry, Keep Points | Toggle | Use this option to remove any unused points. When checked, existing geometry in the input are discarded, but the polygons created by this SOP are kept, as well as any points in the input. |
| `addpts` | Add Points | Toggle | When On you can add individual points with position and weight of your choosing by using the parameters below. |
| `point` | Point | Sequence | Sequence of points to add |
| `method` | Method | Menu | Specify to create polygons from the points by using a Group method or Pattern Method. |
| `group` | Group | StrMenu | Subset of points to be connected. |
| `add` | Add | Menu | Optionally join subgroups of points. |
| `inc` | N | Int | Increment / skip amount to use for adding points. |
| `closedall` | Closed | Toggle | Closes the generated polygons. |
| `polydat` | Polygons Table | DAT | Path to a Table DAT containing polygon data. Accepts rows of polygons specified by point number in the first column. The second column indicates if the polygons are closed (1) or open (0). |
| `poly` | Polygon | Sequence | Sequence of polygon patterns |
| `remove` | Remove Unused Points | Toggle | Keep only the connected points, and discard unused points. |
| `normals` | Compute Normals | Toggle | Creates normals on the geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP addSOP operator
addsop_op = op('addsop1')

# Get/set parameters
freq_value = addsop_op.par.active.eval()
addsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
addsop_op = op('addsop1')
output_op = op('output1')

addsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(addsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
