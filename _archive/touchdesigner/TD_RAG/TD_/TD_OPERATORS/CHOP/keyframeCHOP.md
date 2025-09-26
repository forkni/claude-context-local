# CHOP keyframeCHOP

## Overview

The Keyframe CHOP uses channel and keys data in an Animation COMP and creates channels of samples at a selectable sample rate (frames per second).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `animation` | Animation Component | COMP | The path to the Animation Component holding the channel and key data. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left extend conditions (before range). |
| `right` | Extend Right | Menu | The right extend conditions (after range). |
| `defval` | Default Value | Float | The default value for extend conditions. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP keyframeCHOP operator
keyframechop_op = op('keyframechop1')

# Get/set parameters
freq_value = keyframechop_op.par.active.eval()
keyframechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
keyframechop_op = op('keyframechop1')
output_op = op('output1')

keyframechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(keyframechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
