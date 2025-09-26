# CHOP scurveCHOP

## Overview

This CHOP generates S curves.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Curve Type | Menu | What Curve Type to Generate. |
| `length` | Length | Int | Set the number of samples for this CHOP. |
| `prepend` | Prepend | Int | Add this number of samples to the beginning of the curve. |
| `append` | Append | Int | Add this number of samples to the end of the curve. |
| `steepness` | Steepness | Float | Controls the steepness of the S Curve. |
| `linearize` | Linearize | Float | Control the amount of cruvature in the curve. |
| `bias` | Bias | Float | Move the curve's bias backward or forward. |
| `fromrange` | From Range | Float | Specify the low and high range of the input index. |
| `torange` | To Range | Float | Specify the low and high range of the curve. |
| `channelname` | Channel Names | Str | You can creates many channels with simple patterns like "chan[1-20]", which generates 20 channels from chan1 to chan20. See the section, Common CHOP Parameters for a description of this and all Opt... |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. Default: me.time.rate |
| `left` | Extend Left | Menu | The left extend condition (before range). |
| `right` | Extend Right | Menu | The right extend conditions (after range). |
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
# Access the CHOP scurveCHOP operator
scurvechop_op = op('scurvechop1')

# Get/set parameters
freq_value = scurvechop_op.par.active.eval()
scurvechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
scurvechop_op = op('scurvechop1')
output_op = op('output1')

scurvechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(scurvechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
