# CHOP resampleCHOP

## Overview

The Resample CHOP resamples an input's channels to a new sample rate and/or start/end interval.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Method | Menu | The resample method to apply to the channels: |
| `rate` | Sample Rate | Float | The new sample rate. |
| `relative` | Unit Values | Menu | Determines how the Start/End parameters are interpreted. |
| `start` | Start | Float | The CHOP's new start position. |
| `startunit` | Start Unit | Menu |  |
| `end` | End | Float | The CHOP's new end position. |
| `endunit` | End Unit | Menu |  |
| `quatrot` | Quaternion Blend | Toggle | Uses quaternions to blend between samples. |
| `interp` | Interpolation | Menu | The interpolation method to use when resampling: |
| `constarea` | Constant Area | Toggle | If enabled, keeps the area under the channel constant by scaling the values of the channel. |
| `correct` | Correct for Cycles | Toggle | If enabled, compensates for cyclic channels (such as angles) by always choosing the shortest step between samples, like 360 to 0 for angles. |
| `cyclelen` | Cycle Length | Float | The length of the cycle. 360 is typical for angles. |
| `uselastframe` | Use Last Frame Only | Toggle | Trim to the input CHOP's last frame and perform the resample on that |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP resampleCHOP operator
resamplechop_op = op('resamplechop1')

# Get/set parameters
freq_value = resamplechop_op.par.active.eval()
resamplechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
resamplechop_op = op('resamplechop1')
output_op = op('output1')

resamplechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(resamplechop_op)
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
