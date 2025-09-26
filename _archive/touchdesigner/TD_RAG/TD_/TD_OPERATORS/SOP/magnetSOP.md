# SOP magnetSOP

## Overview

The Magnet SOP allows you to affect deformations of the input geometry with another object using a "magnetic field" of influence, defined by a metaball field.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `deformgrp` | Deform Group | StrMenu | Allows you to specify a group of geometry to be deformed, and a group that will act as the magnet respectively. Accepts patterns, as described in Pattern Matching. |
| `magnetgrp` | Magnet Group | StrMenu | Allows you to specify a group of geometry to be deformed, and a group that will act as the magnet respectively. Accepts patterns, as described in Pattern Matching. |
| `xord` | Transform Order | Menu | Sets the overall transform order for the transformations. The transform order determines the order in which transformations take place. Depending on the order, you can achieve different results usi... |
| `rord` | Rotate Order | Menu | Sets the order of the rotations within the overall transform order. |
| `t` | Translate | XYZ | These three fields move the Source geometry in the three axes. The Translates of the metaball only affect the position of the area of influence. The influence itself is provided by an imaginary mag... |
| `r` | Rotate | XYZ | These three fields rotate the Source geometry in the three axes. |
| `s` | Scale | XYZ | These three fields scale the input geometry in the three axes. |
| `p` | Pivot | XYZ | The pivot point for the transformations. Not the same as the pivot point in the pivot channels. |
| `position` | Affect Position | Toggle | Allow the magnet to affect the position of the input geometry. This is enabled by default. |
| `color` | Affect Point Color | Toggle | Allow the magnet to affect the point color of the input geometry.      Tip: To control the contribution of each magnet on the surface's Point Color when the Affect Point Color option is enabled, se... |
| `nml` | Affect Point Normal | Toggle | Allow the magnet to affect the point normals of the input geometry. |
| `velocity` | Affect Point Velocity | Toggle | Allow the magnet to affect the velocity of the input geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP magnetSOP operator
magnetsop_op = op('magnetsop1')

# Get/set parameters
freq_value = magnetsop_op.par.active.eval()
magnetsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
magnetsop_op = op('magnetsop1')
output_op = op('output1')

magnetsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(magnetsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
