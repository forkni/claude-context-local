# CHOP gestureCHOP

## Overview

The Gesture CHOP records a short segment of the first input and loops this segment in time with options as specified in the Gesture Page.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `playmode` | Play Mode | Menu | Controls the gesture playback. |
| `fitmethod` | Fit to Nearest Cycle | Toggle | When on the captured gesture will be extended or trimmed to be a multiple of the Beats Per Cycle. |
| `numbeats` | Beats per Cycle | Int | Specifies the number of beats to cycle the recorded animation around. If the recorded animation is longer than a multiple of the Beats Per Cycle, it will loop at that multiplied length. |
| `step` | Step Output | Toggle | If on, the cycled animation will adjust up or down each iteration to avoid jumps when looping to the beginning.  For example, it would turn a simple 0-1 ramp gesture into a continuously increasing ... |
| `stepreset` | Step Reset | Toggle | When On and you re-record a gesture, the step will be zeroed. |
| `blend` | Blend Time | Float | How much of the recorded segment to use as a blend region. The blend region is used to blend the beginning of the segment to the end so that a seemless loop is produced. |
| `blendunit` | Blend Time Unit | Menu |  |
| `interp` | Interpolate Samples | Toggle | If on, recorded samples are interpolated when scaling occurs, otherwise the nearest sample is selected. |
| `speed` | Speed | Float | Scales the rate of playback for the segment. |
| `speedunit` | Speed Unit | Menu |  |
| `resetcondition` | Reset Condition | Menu | This menu determines how the Reset input (the third input) triggers a reset of the channel(s). |
| `reset` | Reset | Toggle | Resets the gesture while On when in Sequential Play Mode. |
| `resetpulse` | Reset Pulse | Pulse | Resets the gesture. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP gestureCHOP operator
gesturechop_op = op('gesturechop1')

# Get/set parameters
freq_value = gesturechop_op.par.active.eval()
gesturechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
gesturechop_op = op('gesturechop1')
output_op = op('output1')

gesturechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(gesturechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
