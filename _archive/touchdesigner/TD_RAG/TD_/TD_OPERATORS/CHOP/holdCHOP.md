# CHOP holdCHOP

## Overview

The Hold CHOP waits for a 0 to 1 step on its second input, at which time it reads the current values from the first input (one value per channel).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sample` | Sample | Menu | Defines when to sample the input channels. The parameters are as follows. |
| `hold` | Hold Last | Toggle | When On continue to sample the input, when Off hold the values. |
| `holdpulse` | Hold Last Pulse | Pulse | Sample the input and hold those values when pulsed. |
| `holdsamples` | Hold per Sample | Toggle | Useful for working with multi-sample channels, this applies the hold to each sample of the channel instead of only the last sample in the channel. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP holdCHOP operator
holdchop_op = op('holdchop1')

# Get/set parameters
freq_value = holdchop_op.par.active.eval()
holdchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
holdchop_op = op('holdchop1')
output_op = op('output1')

holdchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(holdchop_op)
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
