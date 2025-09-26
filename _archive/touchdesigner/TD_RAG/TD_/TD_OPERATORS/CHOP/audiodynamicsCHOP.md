# CHOP audiodynamicsCHOP

## Overview

The Audio Dynamics CHOP is designed to control the dynamic range of an audio signal.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `inputgain` | Input Gain (dB) | Float | This parameter controls the volume of the channel before it reaches the compressor.  If the signal to be compressed is not in a useful dynamic range, this parameter can be used to repair it. |
| `enablecompressor` | Enable Compressor | Toggle | Turns the compressor on or off. |
| `compressiontype` | Compression Type | Menu | Determines which compression method to use. |
| `chanlinkingcomp` | Channel Linking | Menu | As various channels come into the CHOP, they can either be compressed by an equal amount, or individually.  If they are compressed equally, all of the channels will be evaluated for the highest pea... |
| `thresholdcompressor` | Threshold (dB) | Float | This parameter sets the threshold value which a signal must cross before compression is applied. It uses a decibel scale, where '0 decibels' would be considered the loudest possible signal*, and '-... |
| `ratiocompressor` | Ratio | Float | The ratio is the amount of compression that will be applied to the signal, with respect to how far the signal has gone past the threshold value. A ratio of '0' will apply no compression. A value of... |
| `kneecompressor` | Knee | Float | The knee defines how the CHOP will transition into compression as signals approach or cross the threshold. With a knee of '0' (a hard knee), think of the compressor as applying a flat compression r... |
| `attackcompressor` | Attack (msec=10**val) | Float | The attack will control how quickly the compressor responds when a signal crosses the threshold.  Increasing the attack parameter will cause the compressor to apply compression at a slower and smoo... |
| `releasecompressor` | Release (msec=10**val) | Float | The release will control how quickly the compressor responds when a signal drops to a lower level, or goes below the threshold altogether. Just like the attack, higher value will slow down the resp... |
| `gaincompressor` | Output Gain (dB) | Float | After applying compression, the signal can be reduced with Gain to a lower volume level. To make up the lost volume, this parameter can be increased. |
| `enablelimiter` | Enable Limiter | Toggle | Turns the limiter on or off. |
| `chanlinkinglim` | Channel Linking | Menu | Same as compressor. |
| `thresholdlimiter` | Threshold (dB) | Float | This is the threshold value which a signal must cross before limiting is applied. Usually, this value should be left at '0' decibels. Just like the compressor, a value of '0' decibels is considered... |
| `releaselimiter` | Release (msec=10**val) | Float | Although the attack of a limiter is always quick, the release can still be set by the user. This will determine how long the limiter takes to transition out of a limiting situation. Increasing the ... |
| `kneelimiter` | Knee | Float | Similar to the compressor, this parameter controls how the CHOP will transition into limiting, when a signal becomes louder. A larger knee will mean a smoother transition. See the Knee diagram abov... |
| `drywet` | Dry / Wet Mix | Float | As this parameter is reduced from 1 (Wet) toward 0 (Dry), it removes the effect of the filter. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiodynamicsCHOP operator
audiodynamicschop_op = op('audiodynamicschop1')

# Get/set parameters
freq_value = audiodynamicschop_op.par.active.eval()
audiodynamicschop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiodynamicschop_op = op('audiodynamicschop1')
output_op = op('output1')

audiodynamicschop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiodynamicschop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
