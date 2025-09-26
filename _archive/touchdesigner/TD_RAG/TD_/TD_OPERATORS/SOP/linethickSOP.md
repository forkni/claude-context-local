# SOP linethickSOP

## Overview

The Line Thick SOP extrudes a surface from a curved line.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns. |
| `startwidth` | Start Width | Float | Controls the width of the surface created at the start of the line. Startwidth1 adjusts the width on the inside of the curve, Startwidth2 adjusts the width on the outside of the curve. |
| `endwidth` | End Width | Float | Controls the width of the surface created at the end of the line. Endwidth1 adjusts the width on the inside of the curve, Endwidth2 adjusts the width on the outside of the curve. |
| `divisions` | Divisions | Int | Number of Divisions (Columns) in the surface geometry created. |
| `rows` | Rows | Int | Number of Rows in the surface geometry created. |
| `domain` | Domain | Float | Fraction of the input curve that is used to create the new surface geometry. Domain1 sets position on the curve for Startwidth, Domain2 sets position on the curve for Endwidth. |
| `shape` | Shape | Menu | This menu selects the type of interpolation used between Startwidth and Endwidth. |
| `symmetric` | Symmetric | Toggle | When this is selected, the Endwidth is positioned at the middlepoint on the curve between Domain1 and Domain2. Startwidth is placed at Domain1 and Domain2. The result is a symmetric surface. |

## Usage Examples

### Basic Usage

```python
# Access the SOP linethickSOP operator
linethicksop_op = op('linethicksop1')

# Get/set parameters
freq_value = linethicksop_op.par.active.eval()
linethicksop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
linethicksop_op = op('linethicksop1')
output_op = op('output1')

linethicksop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(linethicksop_op)
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
