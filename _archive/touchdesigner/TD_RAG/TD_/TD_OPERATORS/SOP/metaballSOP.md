# SOP metaballSOP

## Overview

The Metaball SOP creates metaballs and meta-superquadric surfaces.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `modifybounds` | Modify Bounds | Toggle | Available only when an input is connected to the Metaball SOP to set bounds for the metaball. When Modify Bounds = On the transform parameters below will further modify the position and radius of t... |
| `rad` | Radius | XYZ | Controls the radius of the metaball field. |
| `t` | Center | XYZ | Metaball center in X, Y and Z. |
| `metaweight` | Weight | Float | Defines the weight of the Metaball iso-surface within metaball field. An increase in weight makes the density of the metaball greater, and thus the defined implicit surface of it and surrounding me... |
| `kernel` | Kernel Function | StrMenu | There are four different metaball interpretations: Wyvill, Elendt, Blinn and Links. See the Geometry articles for illustrations of the differences between these. |
| `expxy` | XY Exponent | Float | The XY Exponent determines inflation / contraction in the X and Y axes. |
| `expz` | Z Exponent | Float | The Z Exponent determines inflation / contraction in the Z axis. |
| `normals` | Compute Normals | Toggle | Creates normals on the geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP metaballSOP operator
metaballsop_op = op('metaballsop1')

# Get/set parameters
freq_value = metaballsop_op.par.active.eval()
metaballsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
metaballsop_op = op('metaballsop1')
output_op = op('output1')

metaballsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(metaballsop_op)
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
