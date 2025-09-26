# SOP sequenceblendSOP

## Overview

The Sequence Blend SOP allows you do 3D Metamorphosis between shapes and Interpolate point position, colors, point normals, and texture coordinates between shapes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `blend` | Blend Factor | Float | This value determines the blend transition between consecutive geometry inputs. Values between 0 and 1 will control the metamorphosis between geometry input 1 and 2, values between 1 and 2 will con... |
| `dopos` | Blend Position | Toggle | If checked, only point xyz positions are blended. |
| `doclr` | Blend Colors | Toggle | Point Colors are blended. |
| `donml` | Blend Normals | Toggle | Point normals are blended. |
| `douvw` | Blend Texture | Toggle | Point texture coordinates are blended. |
| `doup` | Blend Up | Toggle | When checked, the Up Vector of the geometry inputs will be blended based on the weights of the blend channels. |

## Usage Examples

### Basic Usage

```python
# Access the SOP sequenceblendSOP operator
sequenceblendsop_op = op('sequenceblendsop1')

# Get/set parameters
freq_value = sequenceblendsop_op.par.active.eval()
sequenceblendsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sequenceblendsop_op = op('sequenceblendsop1')
output_op = op('output1')

sequenceblendsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sequenceblendsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **6** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
