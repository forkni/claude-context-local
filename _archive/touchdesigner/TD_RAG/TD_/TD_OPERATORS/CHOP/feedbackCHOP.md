# CHOP feedbackCHOP

## Overview

The Feedback CHOP stores channels from the current frame to be used in a later frame, without forcing recooking back one frame.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `output` | Output | Menu | Choose what to output from this menu. |
| `delta` | Delta Time | Toggle | Time differential during feedback. If on, it adds a 'dt' channel whose value is the elapsed time since the last cook. |
| `reset` | Reset | Toggle | Activates feedback when set to 0. Disables feedback when set to 1. When disabled, the Feedback CHOP passes thru the data connected to its input. |
| `resetpulse` | Reset Pulse | Pulse | Resets the feedback in a single frame when clicked. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP feedbackCHOP operator
feedbackchop_op = op('feedbackchop1')

# Get/set parameters
freq_value = feedbackchop_op.par.active.eval()
feedbackchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
feedbackchop_op = op('feedbackchop1')
output_op = op('output1')

feedbackchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(feedbackchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
