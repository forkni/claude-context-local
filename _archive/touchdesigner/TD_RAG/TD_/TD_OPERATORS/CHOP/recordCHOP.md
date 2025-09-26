# CHOP recordCHOP

## Overview

The Record CHOP takes the channels coming in the first (Position) input, converts and records them internally, and outputs the stored channels as the CHOP output.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `record` | Record | Menu | When and how much to record: |
| `sample` | Record Input | Menu | Determines whether record should sample the time slice or the current frame. You would generally want to use Current Time Slice, for audio, as all frames will be evaluated.      If the interval is ... |
| `interp` | Interpolation | Menu | Determines how to compute missed input samples using interpolation. Using Hold Previous Value does just that; Linear and Cubic interpolation will create a mathematical blend of values in a linear (... |
| `output` | Record Output | Menu | Determines the frame range that gets output from the CHOP. |
| `segment` | Record Segment | Float | The data gets recorded in a fixed-range interval and the most recent data gets recorded at the end of the interval and the remaining samples get shifted toward the start of the interval. This is us... |
| `segmentunit` | Record Segment Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `reset` | Reset Channels | Pulse | The current output is cleared and all subsequent channels will commence single sample lengths. |
| `resetcondition` | Reset Condition | Menu | Enabled when a CHOP is connected to the Record CHOP's 3rd input (ie. Input 2). Determines what condition is required to trigger a reset using this input. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP recordCHOP operator
recordchop_op = op('recordchop1')

# Get/set parameters
freq_value = recordchop_op.par.active.eval()
recordchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
recordchop_op = op('recordchop1')
output_op = op('output1')

recordchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(recordchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
