# TOP noiseTOP

## Overview

The Noise TOP generates a variety of noise patterns including perlin, simplex, sparse, alligator and random.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | The noise function used to generate noise. The functions available are: |
| `seed` | Seed | Float | Any number, integer or non-integer, which starts the random number generator. Each number gives completely different noise patterns, but with similar characteristics. |
| `period` | Period | Float | The approximate separation between peaks of a noise cycle. It is expressed in Units. Increasing the period stretches the noise pattern out.      Period is the opposite of frequency. If the period i... |
| `harmon` | Harmonics | Int | The number of higher frequency components to layer on top of the base frequency. The higher this number, the bumpier the noise will be (as long as roughness is not set to zero). 0 harmonics give th... |
| `spread` | Harmonic Spread | Float | The factor by which the frequency of the harmonics are increased. It is normally 2. A spread of 3 and a base frequency of 0.1Hz will produce harmonics at 0.3Hz, 0.9Hz, 2.7Hz, etc.. This parameter i... |
| `gain` | Harmonic Gain | Float | Amount of the Harmonic Gain layered on top of the base frequency. |
| `rough` | Roughness | Float | Controls the effect of the higher frequency noise. When roughness is zero, all harmonics above the base frequency have no effect. At one, all harmonics are equal in amplitude to the base frequency.... |
| `exp` | Exponent | Float | Pushes the noise values toward 0, or +1 and -1. (It raises the value to the power of the exponent.) Exponents greater than one will pull the channel toward zero, and powers less than one will pull ... |
| `amp` | Amplitude | Float | Defines the noise value's amplitude (a scale on the values output). |
| `offset` | Offset | Float | Defines the midpoint color of the noise pattern, the default is 0.5 grey. |
| `mono` | Monochrome | Toggle | Toggle color or monochrome noise. |
| `aspectcorrect` | Aspect Correct | Toggle | Controls if the noise takes aspect ratio into account when calculating it's noise coordinates. When this is off, the noise will stretch to fit a non-square aspect ratio texture. |
| `xord` | Transform Order | Menu | The menu attached to this parameter allows you to specify the order in which the transforms will take place. Changing the Transform order will change where things go much the same way as going a bl... |
| `rord` | Rotate Order | Menu | The rotational matrix presented when you click on this option allows you to set the transform order for the rotations. As with transform order (above), changing the order in which the rotations tak... |
| `t` | Translate | XYZ | Translate the sampling plane through the noise space. |
| `r` | Rotate | XYZ | Rotate the sampling plane in the noise space. |
| `s` | Scale | XYZ | Scale the sampling plane. |
| `p` | Pivot | XYZ | Control the pivot for the transform of the sampling plane. |
| `t4d` | Translate 4D | Float | When doing 4D noise, this applies a translation to the 4th coordinate. The previous transformation parameters do not affect the 4th coordinate. |
| `s4d` | Scale 4D | Float | When doing 4D noise, this applies a scale to the 4th coordinate. |
| `rgb` | RGB | Menu | When an input is connected to the Noise TOP, the noise pattern is placed over the input image using UV coordinates and the settings from this menu. |
| `inputscale` | Input Scale | Float | Adjusts how much of the input image is added to the output. |
| `noisescale` | Noise Scale | Float | Adjusts how much of the noise is added to the output. |
| `alpha` | Alpha | Menu | Sets the alpha channel for the output image. |
| `dither` | Dither | Toggle | Dithers the output to help deal with banding and other artifacts created by precision limitations of 8-bit displays. |
| `derivative` | Derivative (Slope) | Toggle | Turn this on to output the derivative (also known as slope) of the noise function. Currently, only supported for Simplex2D, Simplex3D, Perlin2D and Perlin3D noise types. For 2D noise derivatives, t... |
| `mode` | Mode | Menu | Pick between Performance vs Quality noise. Performance noise is the existing TD noise. Quality noise reduces certain artifacts and axis alignment issues with the existing noise at the cost of speed... |
| `outputresolution` | Output Resolution | Menu | quickly change the resolution of the TOP's data. |
| `resolution` | Resolution | Int | Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size. The drop down menu ... |
| `resmenu` | Resolution Menu | Pulse | A drop-down menu with some commonly used resolutions. |
| `resmult` | Use Global Res Multiplier | Toggle | Uses the Global Resolution Multiplier found in Edit>Preferences>TOPs. This multiplies all the TOPs resolutions by the set amount. This is handy when working on computers with different hardware spe... |
| `outputaspect` | Output Aspect | Menu | Sets the image aspect ratio allowing any textures to be viewed in any size. Watch for unexpected results when compositing TOPs with different aspect ratios. (You can define images with non-square p... |
| `aspect` | Aspect | Float | Use when Output Aspect parameter is set to Custom Aspect. |
| `armenu` | Aspect Menu | Pulse | A drop-down menu with some commonly used aspect ratios. |
| `inputfiltertype` | Input Smoothness | Menu | This controls pixel filtering on the input image of the TOP. |
| `fillmode` | Fill Viewer | Menu | Determine how the TOP image is displayed in the viewer. NOTE:To get an understanding of how TOPs work with images, you will want to set this to Native Resolution as you lay down TOPs when starting ... |
| `filtertype` | Viewer Smoothness | Menu | This controls pixel filtering in the viewers. |
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. For every pass after the first it takes the result of the previous pass and replaces the node's first input with the result of the... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP noiseTOP operator
noisetop_op = op('noisetop1')

# Get/set parameters
freq_value = noisetop_op.par.active.eval()
noisetop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
noisetop_op = op('noisetop1')
output_op = op('output1')

noisetop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(noisetop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **40** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
