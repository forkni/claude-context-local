# CHOP audiospectrumCHOP

## Overview

The Audio Spectrum CHOP calculates and displays the frequency spectrum of the input channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `mode` | Mode | Menu | Select which mode to use, modes described below. |
| `fftsize` | FFT Size | Menu | Converting to frequency needs a power-of-2 number of samples, like 512, 1024, 2048. (FFT means Fast Fourier Transform.) The more samples, the more accurate the spectrum but the more it doesn't repr... |
| `frequencylog` | Frequency <-> Logarithmic Scaling | Float | Logarithmic (=1) is more tangible for human hearing. Each octave is represented with the same number of samples, so low frequencies are more readable. Frequency (=0) shows one sample for a fixed nu... |
| `highfreqboost` | High Frequency Boost | Float | When 0, the levels are not changed. When greater than 1, the levels are boosted, mostly at the high frequencies. High Frequency Boost can be over-driven past 1. |
| `outputmenu` | Output Length | Menu | The method how output length will be determined. |
| `outlength` | Set Output Length | Int | Number of Samples desired in output. The fewer the samples, the less the frequency resolution. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiospectrumCHOP operator
audiospectrumchop_op = op('audiospectrumchop1')

# Get/set parameters
freq_value = audiospectrumchop_op.par.active.eval()
audiospectrumchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiospectrumchop_op = op('audiospectrumchop1')
output_op = op('output1')

audiospectrumchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiospectrumchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
