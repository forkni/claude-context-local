# CHOP noiseCHOP

## Overview

The Noise CHOP makes an irregular wave that never repeats, with values approximately in the range -1 to +1.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | The noise function used to generate noise. The functions available are: |
| `seed` | Seed | Float | Any number, integer or non-integer, which starts the random number generator. Each number gives completely different noise patterns, but with similar characteristics. |
| `period` | Period | Float | The approximate separation between peaks of a noise cycle. It is expressed in Units. Increasing the period stretches the noise pattern out.      Period is the opposite of frequency. If the period i... |
| `periodunit` | Period Unit | Menu | Select the units to use for this parameter, Samples, Frames, Seconds, or Fraction. |
| `harmon` | Harmonics | Int | The number of higher frequency components to layer on top of the base frequency. The higher this number, the bumpier the noise will be (as long as roughness is not set to zero). 0 harmonics give th... |
| `spread` | Harmonic Spread | Float | The factor by which the frequency of the harmonics are increased. It is normally 2. A spread of 3 and a base frequency of 0.1Hz will produce harmonics at 0.3Hz, 0.9Hz, 2.7Hz, etc. This parameter is... |
| `rough` | Roughness | Float | Controls the effect of the higher frequency noise. When roughness is zero, all harmonics above the base frequency have no effect. At one, all harmonics are equal in amplitude to the base frequency.... |
| `exp` | Exponent | Float | Pushes the noise values toward 0, or +1 and -1. (It raises the value to the power of the exponent.) Exponents greater than one will pull the channel toward zero, and powers less than one will pull ... |
| `numint` | Num of Integrals | Int | Defines the number of times to integrate (see the Area CHOP p. 114) the Brownian noise. Higher values produce smoother curves with fewer features. Values beyond 4 produce somewhat identical curves.... |
| `amp` | Amplitude | Float | Defines the noise value's amplitude (a scale on the values output). |
| `reset` | Reset | Toggle | Only available if operator's Time Slice Parameter is on. Toggling this parameter will reset the noise calculation and hold the value until the parameter is released again. |
| `resetpulse` | Reset Pulse | Pulse | Only available if operator's Time Slice Parameter is on. Pulsing this parameter will reset the noise calculation. |
| `xord` | Transform Order | Menu | Changing the Transform Order will change where things go much the same way as going a block and turning east gets you to a different place than turning east and then going a block. In matrix math t... |
| `rord` | Rotate Order | Menu | As with transform order (above), changing the order in which the rotations take place will alter the final position and orientation. A Rotation order of Rx Ry Rz would create the final rotation mat... |
| `t` | Translate | XYZ | XYZ translation values. |
| `r` | Rotate | XYZ | XYZ rotation, in degrees. |
| `s` | Scale | XYZ | XYZ scale to shrink or enlarge the transform. |
| `p` | Pivot | XYZ | XYZ pivot to apply the above operations around. |
| `constraint` | Constraint | Menu | Constraint and its parameters allows the noise curve to start and/or end at selected values. The mean value may also be enforced. Note: This only works when Time Slice is Off because time slicing h... |
| `constrstart` | Starting Value | Float | Value for the starting position. |
| `constrend` | Ending Value | Float | Value for the ending position. |
| `constrmean` | Mean Value | Float | Value for the mean value of the noise. |
| `normal` | Normalize | Toggle | Ensures that all noise curves fall between -1 and 1. Applied before the Amplitude parameter. Only valid for Random and Harmonic Summation noise types, since Hermite and Sparse noise are always norm... |
| `channelname` | Channel Names | Str | You can creates many channels with simple patterns like "chan[1-20]", which generates 20 channels from chan1 to chan20. See the section, Common CHOP Parameters for a description of this and all Opt... |
| `start` | Start | Float | Start of the interval, expressed in Units (seconds, frames or samples). |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `end` | End | Float | End of the interval, expressed in Units (seconds, frames or samples). |
| `endunit` | End Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. Default: me.time.rate |
| `left` | Extend Left | Menu | The left extend conditions (before/after range). |
| `right` | Extend Right | Menu | The right extend conditions (before/after range). |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP noiseCHOP operator
noisechop_op = op('noisechop1')

# Get/set parameters
freq_value = noisechop_op.par.active.eval()
noisechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
noisechop_op = op('noisechop1')
output_op = op('output1')

noisechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(noisechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **38** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
