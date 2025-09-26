# CHOP audiobandeqCHOP

## Overview

The Audio Band EQ CHOP is a 16-band equalizer which filters audio input channels in the same way that a conventional band (graphic) equalizer uses a bank of sliders to filter fixed-frequency bands of sound.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `drywet` | Dry / Wet Mix | Float | As this parameter is reduced from 1 (Wet) toward 0 (Dry), it removes the effect of the filter. |
| `band1` | 25 Hz | Float | Controls boost/cut centered at 25 Hz. |
| `band2` | 40 Hz | Float | Controls boost/cut at the 40 Hz band. |
| `band3` | 60 Hz | Float | Controls boost/cut at the 60 Hz band. |
| `band4` | 90 Hz | Float | Controls boost/cut at the 90 Hz band. |
| `band5` | 150 Hz | Float | Controls boost/cut at the 150 Hz band. |
| `band6` | 240 Hz | Float | Controls boost/cut at the 240 Hz band. |
| `band7` | 370 Hz | Float | Controls boost/cut at the 370 Hz band. |
| `band8` | 590 Hz | Float | Controls boost/cut at the 590 Hz band. |
| `band9` | 930 Hz | Float | Controls boost/cut at the 930 Hz band. |
| `band10` | 1.5 KHz | Float | Controls boost/cut at the 1.5 Hz band. |
| `band11` | 2.3 KHz | Float | Controls boost/cut at the 2.3 Hz band. |
| `band12` | 3.6 KHz | Float | Controls boost/cut at the 3.6 Hz band. |
| `band13` | 5.6 KHz | Float | Controls boost/cut at the 5.6 Hz band. |
| `band14` | 8.9 KHz | Float | Controls boost/cut at the 8.9 Hz band. |
| `band15` | 14 KHz | Float | Controls boost/cut at the 14 Hz band. |
| `band16` | 22 KHz | Float | Controls boost/cut at the 22 Hz band. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiobandeqCHOP operator
audiobandeqchop_op = op('audiobandeqchop1')

# Get/set parameters
freq_value = audiobandeqchop_op.par.active.eval()
audiobandeqchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiobandeqchop_op = op('audiobandeqchop1')
output_op = op('output1')

audiobandeqchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiobandeqchop_op)
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
