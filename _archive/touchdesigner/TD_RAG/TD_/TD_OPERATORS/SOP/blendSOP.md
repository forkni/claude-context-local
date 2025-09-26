# SOP blendSOP

## Overview

The Blend SOP provides 3D metamorphosis between shapes with the same topology. It can blend

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Specifies a point or primitive group in the first input. If, for example, a group is specified containing the first and third points, then the first and third point of every input will be blended w... |
| `diff` | Differencing | Toggle | Generates exaggerated blends between objects where values above 1 or less than 0 will result in over-scaled blends.     When this option is checked, the above channel values are not summed and scal... |
| `dopos` | Blend Position | Toggle | When checked, the point positions of the inputs will be blended based on the weights of the blend channels. If not checked, the input geometry will not change, only allowing Blending of Colors, Nor... |
| `doclr` | Blend Colors | Toggle | When checked, the point colors of the geometry inputs will be blended based on the weights of the blend channels. |
| `donml` | Blend Normals | Toggle | When checked, the point normals of the geometry inputs will be blended based on the weights of the blend channels. |
| `douvw` | Blend Texture | Toggle | When checked, the point texture co-ordinates of the geometry inputs will be blended based on the weights of the blend channels. |
| `doup` | Blend Up | Toggle | When checked, the Up Vector of the geometry inputs will be blended based on the weights of the blend channels. |
| `input` | Input | Sequence | Sequence of input weights |

## Usage Examples

### Basic Usage

```python
# Access the SOP blendSOP operator
blendsop_op = op('blendsop1')

# Get/set parameters
freq_value = blendsop_op.par.active.eval()
blendsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
blendsop_op = op('blendsop1')
output_op = op('output1')

blendsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(blendsop_op)
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
