# CHOP audiofilterCHOP

## Overview

The Audio Filter CHOP removes low frequencies, high frequencies, both low and high, or removes a mid-frequency range.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `filter` | Filter | Menu | The filter type: |
| `units` | Cutoff Units | Menu | The filter cutoff frequency can be expressed in Hz (menu set to Frequency) or power-of-10 (menu set to Logarithmic). It enables one of the next 2 Filter Cutoff parameters. |
| `cutofflog` | Filter Cutoff (Hz=10**val) | Float | The filter cutoff frequency expressed in power-of-10, where value 0 translates to 1 Hz (10**0), value 1 is 10 Hz (10**1), value 2 is 100 Hz (10**2), value 3 is 1000 Hz, value 4 is 10,000 Hz, value ... |
| `cutofffrequency` | Filter Cutoff (Hz) | Float | The filter cutoff frequency expressed in Hz (cycles per second). This parameter set to 1000 has exactly the same effect as the above parameter set to 3. |
| `resonance` | Filter Resonance | Float | Increasing the resonance will boost the loudness of the passed frequencies near the cutoff frequency. |
| `rolloff` | Roll-Off (dB per Octave) | Float | Rolloff determines how much the levels decrease near the cutoff frequency. This parameter will make it decrease by 12 decibels (dB) per octave, to, more extremely, 24 decibels per octave. 12 and 24... |
| `drywet` | Dry / Wet Mix | Float | As this parameter is reduced from 1 (Wet) toward 0 (Dry), it removes the effect of the filter. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiofilterCHOP operator
audiofilterchop_op = op('audiofilterchop1')

# Get/set parameters
freq_value = audiofilterchop_op.par.active.eval()
audiofilterchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiofilterchop_op = op('audiofilterchop1')
output_op = op('output1')

audiofilterchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiofilterchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
