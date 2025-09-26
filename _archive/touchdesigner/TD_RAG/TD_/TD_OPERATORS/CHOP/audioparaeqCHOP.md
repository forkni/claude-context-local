# CHOP audioparaeqCHOP

## Overview

The Audio Para EQ CHOP (parametric equalizer) applies up to 3 parametric filters to the incoming sound.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `units` | Frequency Units | Menu | How frequency is expressed: |
| `enableeq1` | Enable EQ1 | Toggle | When off, it passes the sound through the first equalizer unchanged. |
| `boost1` | Boost (dB) EQ1 | Float | When boost is greater than 0, it will make louder the audio around the center frequency. When boost is less than 0, it will make the audio quieter around the center frequency. Boost is in decibels ... |
| `frequencylog1` | Frequency (Hz=10**val) EQ1 | Float | The frequency is expressed in power-of-10, where value 0 translates to 1 Hz (10**0), value 1 is 10 Hz (10**1), value 2 is 100 Hz (10**2), value 3 is 1000 Hz, value 4 is 10,000 Hz, value 4.5 is 31,6... |
| `frequencyhz1` | Frequency (Hz) EQ1 | Float | The filter frequency is expressed in Hz (cycles per second). This parameter set to 1000 has exactly the same effect as the above parameter set to 3. |
| `bandwidth1` | Bandwidth EQ1 | Float | Bandwidth determines how much the levels decrease near the center frequency, expressed in octaves. |
| `enableeq2` | Enable EQ2 | Toggle | When off, it passes the sound through the second equalizer unchanged. |
| `boost2` | Boost (dB) EQ2 | Float | When boost is greater than 0, it will make louder the audio around the center frequency. When boost is less than 0, it will make the audio quieter around the center frequency. Boost is in decibels ... |
| `frequencylog2` | Frequency (Hz=10**val) EQ2 | Float | The frequency is expressed in power-of-10, where value 0 translates to 1 Hz (10**0), value 1 is 10 Hz (10**1), value 2 is 100 Hz (10**2), value 3 is 1000 Hz, value 4 is 10,000 Hz, value 4.5 is 31,6... |
| `frequencyhz2` | Frequency (Hz) EQ2 | Float | The filter frequency is expressed in Hz (cycles per second). This parameter set to 1000 has exactly the same effect as the above parameter set to 3. |
| `bandwidth2` | Bandwidth EQ2 | Float | Bandwidth determines how much the levels decrease near the center frequency, expressed in octaves. |
| `enableeq3` | Enable EQ3 | Toggle | When off, it passes the sound through the third equalizer unchanged. |
| `boost3` | Boost (dB) EQ3 | Float | When boost is greater than 0, it will make louder the audio around the center frequency. When boost is less than 0, it will make the audio quieter around the center frequency. Boost is in decibels ... |
| `frequencylog3` | Frequency (Hz=10**val) EQ3 | Float | The frequency is expressed in power-of-10, where value 0 translates to 1 Hz (10**0), value 1 is 10 Hz (10**1), value 2 is 100 Hz (10**2), value 3 is 1000 Hz, value 4 is 10,000 Hz, value 4.5 is 31,6... |
| `frequencyhz3` | Frequency (Hz) EQ3 | Float | The filter frequency is expressed in Hz (cycles per second). This parameter set to 1000 has exactly the same effect as the above parameter set to 3. |
| `bandwidth3` | Bandwidth EQ3 | Float | Bandwidth determines how much the levels decrease near the center frequency, expressed in octaves. |
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
# Access the CHOP audioparaeqCHOP operator
audioparaeqchop_op = op('audioparaeqchop1')

# Get/set parameters
freq_value = audioparaeqchop_op.par.active.eval()
audioparaeqchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audioparaeqchop_op = op('audioparaeqchop1')
output_op = op('output1')

audioparaeqchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audioparaeqchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
