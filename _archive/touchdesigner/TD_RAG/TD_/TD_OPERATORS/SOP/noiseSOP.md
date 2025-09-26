# SOP noiseSOP

## Overview

The Noise SOP displaces geometry points using noise patterns.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `attribute` | Attribute | Menu | This menu sets which attribute of the geometry the Noise SOP acts on. |
| `type` | Type | Menu | The noise function used to generate noise. The functions available are: |
| `seed` | Seed | Float | Any number, integer or non-integer, which starts the random number generator. Each number gives completely different noise patterns, but with similar characteristics. |
| `period` | Period | Float | The approximate separation between peaks of a noise cycle. It is expressed in Units. Increasing the period stretches the noise pattern out.      Period is the opposite of frequency. If the period i... |
| `harmon` | Harmonics | Int | The number of higher frequency components to layer on top of the base frequency. The higher this number, the bumpier the noise will be (as long as roughness is not set to zero). 0 Harmonics give th... |
| `spread` | Harmonic Spread | Float | The factor by which the frequency of the harmonics are increased. It is normally 2. A spread of 3 and a base frequency of 0.1Hz will produce harmonics at 0.3Hz, 0.9Hz, 2.7Hz, etc.. This parameter i... |
| `rough` | Roughness | Float | Controls the effect of the higher frequency noise. When Roughness is zero, all harmonics above the base frequency have no effect. At one, all harmonics are equal in amplitude to the base frequency.... |
| `exp` | Exponent | Float | Pushes the noise values toward 0, or +1 and -1. (It raises the value to the power of the exponent.) Exponents greater than one will pull the channel toward zero, and powers less than one will pull ... |
| `numint` | Number of Integrals | Int | Defines the number of times to integrate (see the Speed CHOP) the Brownian noise. Higher values produce smoother curves with fewer features. Values beyond 4 produce somewhat identical curves. This ... |
| `amp` | Amplitude | Float | Defines the noise value's amplitude (a scale on the values output). |
| `keepnormals` | Keep Computed Normals | Toggle |  |
| `xord` | Transform Order | Menu | The menu attached to this parameter allows you to specify the order in which the transforms will take place. Changing the Transform order will change where things go much the same way as going a bl... |
| `rord` | Rotate Order | Menu | The rotational matrix presented when you click on this option allows you to set the transform order for the rotations. As with transform order (above), changing the order in which the rotations tak... |
| `t` | Translate | XYZ | Translate the sampling plane through the noise space. |
| `r` | Rotate | XYZ | Rotate the sampling plane in the noise space. |
| `s` | Scale | XYZ | Scale the sampling plane. |
| `p` | Pivot | XYZ | Control the pivot for the transform of the sampling plane. |

## Usage Examples

### Basic Usage

```python
# Access the SOP noiseSOP operator
noisesop_op = op('noisesop1')

# Get/set parameters
freq_value = noisesop_op.par.active.eval()
noisesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
noisesop_op = op('noisesop1')
output_op = op('output1')

noisesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(noisesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **18** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
