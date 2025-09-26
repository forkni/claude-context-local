# SOP joinSOP

## Overview

The Join SOP connects a sequence of faces or surfaces into a single primitive that inherits their attributes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `blend` | Blend | Toggle | Determines the way the primitives are joined. A blended face or surface will typically reposition the ends to be joined and convert them into a single, common point, row or column respectively. The... |
| `tolerance` | Tolerance | Float | The meaning of the tolerance varies with the type of join. The shapes of blended primitives will change less if the tolerance is low. If the tolerance is < 1, a new point, knot, row or column is in... |
| `bias` | Bias | Float | Affects only blended primitives by varying the position of the common point, row or column linearly between the two original ends. If the bias is zero, the common part will coincide with the end of... |
| `knotmult` | Multiplicity | Toggle | Affects the number of knots inserted at the blend point and thus allows for smooth or pointed connections. The connection will be pointed when the Multiplicity is on. When Blend is not on, an activ... |
| `proximity` | Connect Closest Ends | Toggle | The Join SOP connects the tail of the first primitive with the head on the next primitive, and so on unless this toggle is on, in which case the closest ends are chosen instead. For surfaces, this ... |
| `dir` | Direction | Menu | This menu determines the parametric direction of the joining operation, which can be in U or in V, and is meaningful only when the inputs are surfaces. The U direction is associated with columns; t... |
| `joinop` | Join | Menu | Can optionally join subgroups of n primitives or every nth primitive in a cyclical manner.     For Example; assume there are six primitives numbered for 0 - 5, and N = 2. Then,        Groups will g... |
| `inc` | N | Int | Determines the number of primitives to be either grouped or skipped. N2. |
| `loop` | Wrap Last to First | Toggle | If enabled, it connects the beginning of the first primitive to the end of the last primitive, thus forming a single, closed face or hull. If a single, open primitive exists in the input, it will b... |
| `prim` | Keep Primitives | Toggle | If this button is not checked, the input primitives will be deleted after being joined. If checked, they will be preserved. |

## Usage Examples

### Basic Usage

```python
# Access the SOP joinSOP operator
joinsop_op = op('joinsop1')

# Get/set parameters
freq_value = joinsop_op.par.active.eval()
joinsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
joinsop_op = op('joinsop1')
output_op = op('output1')

joinsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(joinsop_op)
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
