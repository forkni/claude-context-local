# SOP basisSOP

## Overview

The Basis SOP provides a set of operations applicable to the parametric space of spline curves and surfaces.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `ubasis` | Edit the U Basis | Toggle | Enable editing of the U Basis. |
| `uparmtype` | Parameterization | Menu | Select the method of parameterization in u from the options below. |
| `uknots` | Knot Sequence | Str | The basis of the first spline primitive in the input loads its knot sequence with the data specified in this field when the Parameterization is set to Manual. The values must be in ascending order,... |
| `uread` | Read Basis | Pulse | Loads the original knots of the basis into the Knot Sequence field when the Parameterization type is Manual. |
| `urange` | Range | Float | Range specifies the domain interval to be shifted. All the knots captured in this range are shifted by the same amount as far as the closest neighbouring knot on either side. |
| `ubias` | Bias | Float | Bias indicates the direction and the amount of translation. A Bias of 0.5 does not displace the knots at all. As the Bias decreases, the knot cluster migrates closer to its left-neighbouring knot. ... |
| `uconcat` | Concatenate | Toggle | Indicates whether the bases of the input spline primitives should be concatenated such that the last knot of the first primitive coincides with the first knot of the second primitive, and so on. Th... |
| `udoorigin` | Origin | Toggle | Enables the Origin parameter. |
| `uorigin` | Origin | Float | The new origin of the basis, or the origin of the cummulated bases if Concatenation is On. |
| `udolength` | Length | Toggle | Enables the Length parameter. |
| `ulength` | Length | Float | The new length of the basis, or the total length of the cummulated bases if Concatenation is On. The Length, which represents the distance between the first and last knot, must be greater than zero. |
| `udoscale` | Scale | Toggle | Enables the Scale parameter. |
| `uscale` | Scale | Float | The multiplier applied to the basis starting at the basis origin. The Scale must be greater than zero. |
| `uraise` | Raise to | Toggle | Enables the Raise to parameter. |
| `orderu` | Raise U to | Int | The only operation here is raising the order (or degree) of the spline basis. Valid orders range from 2 to 11. Orders lower than the current spline order are ignored. The operation preserves the sh... |
| `vbasis` | Edit the V Basis | Toggle | Enable editing of the V Basis. |
| `vparmtype` | Parameterization | Menu | Select the method of parameterization in v from the options below. |
| `vknots` | Knot Sequence | Str | The basis of the first spline primitive in the input loads its knot sequence with the data specified in this field when the Parameterization is set to Manual. The values must be in ascending order,... |
| `vread` | Read Basis | Pulse | Loads the original knots of the basis into the Knot Sequence field when the Parameterization type is Manual |
| `vrange` | Range | Float | Range specifies the domain interval to be shifted. All the knots captured in this range are shifted by the same amount as far as the closest neighbouring knot on either side. |
| `vbias` | Bias | Float | Bias indicates the direction and the amount of translation. A Bias of 0.5 does not displace the knots at all. As the Bias decreases, the knot cluster migrates closer to its left-neighbouring knot. ... |
| `vconcat` | Concatenate | Toggle | Indicates whether the bases of the input spline primitives should be concatenated such that the last knot of the first primitive coincides with the first knot of the second primitive, and so on. Th... |
| `vdoorigin` | Origin | Toggle | Enables the Origin parameter. |
| `vorigin` | Origin | Float | The new origin of the basis, or the origin of the cummulated bases if Concatenation is On. |
| `vdolength` | Length | Toggle | Enables the Length parameter. |
| `vlength` | Length | Float | The new length of the basis, or the total length of the cummulated bases if Concatenation is On. The Length, which represents the distance between the first and last knot, must be greater than zero. |
| `vdoscale` | Scale | Toggle | Enables the Scale parameter. |
| `vscale` | Scale | Float | The multiplier applied to the basis starting at the basis origin. The Scale must be greater than zero. |
| `vraise` | Raise to | Toggle | Enables the Raise to parameter. |
| `orderv` | Raise V to | Int | The only operation here is raising the order (or degree) of the spline basis. Valid orders range from 2 to 11. Orders lower than the current spline order are ignored. The operation preserves the sh... |

## Usage Examples

### Basic Usage

```python
# Access the SOP basisSOP operator
basissop_op = op('basissop1')

# Get/set parameters
freq_value = basissop_op.par.active.eval()
basissop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
basissop_op = op('basissop1')
output_op = op('output1')

basissop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(basissop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **30** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
