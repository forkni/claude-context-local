# SOP filletSOP

## Overview

The Fillet SOP is used to create smooth bridging geometry between two curves / polygons or two surfaces / meshes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Which primitives to fillet. If blank, it fillets the entire input. Accepts patterns, as described in Pattern Matching. |
| `fillet` | Fillet | Menu | Can optionally fillet subgroups of N primitives or every nth primitive in a cyclical manner.     Example: Assume there are six primitives numbered for 0 - 5, and N = 2. Then:        Groups will fil... |
| `inc` | N | Int | Determines the number of primitives to be either grouped or skipped. |
| `loop` | Wrap Last to First | Toggle | Connects the beginning of the first primitive to the end of the last primitive filleted, or, if only one primitive exists, it creates a fillet between its ends. |
| `dir` | Direction | Menu | This menu determines the parametric direction of the filleting operation, which can be in U or in V, and is meaningful only when the inputs are surfaces. The U direction is associated with columns;... |
| `fillettype` | Fillet Type | Menu | Select which type of fillet to use in this menu. |
| `primtype` | Primitive Type | Menu | Select what type of primitive will be created by the fillet in this menu. |
| `order` | Order | Int | Order at which to build the spline fillets. |
| `leftuv` | Left UV | Float | Parametric point on each left primitive at which to begin the fillet. |
| `rightuv` | Right UV | Float | Parametric point on each right primitive at which to begin the fillet. |
| `lrwidth` | LR Width | Float | The first value represents the proportion of the left primitive that the left end of the fillet spans. The second value represents the proportion of the right primitive that the right end of the fi... |
| `lrscale` | LR Scale | Float | Use to control the direction and scale of the first and last segments of the fillet. |
| `lroffset` | LR Offset | Float | Controls the position of the first and last segments of the fillet. |
| `seamless` | Match Input to Fillets | Toggle | If selected, then the inputs are modified in such a way that the isoparms appear continuous from one primitive, through the fillet to the other primitive. Also, the primitives are promoted to the s... |
| `cut` | Cut Primitives | Toggle | If selected, the primitives are trimmed at the point the fillet begins. |

## Usage Examples

### Basic Usage

```python
# Access the SOP filletSOP operator
filletsop_op = op('filletsop1')

# Get/set parameters
freq_value = filletsop_op.par.active.eval()
filletsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
filletsop_op = op('filletsop1')
output_op = op('output1')

filletsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(filletsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
