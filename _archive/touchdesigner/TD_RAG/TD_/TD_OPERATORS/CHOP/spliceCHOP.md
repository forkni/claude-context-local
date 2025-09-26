# CHOP spliceCHOP

## Overview

The Splice CHOP inserts CHOP channels connected to the second input into the channels of the first input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `outputtrimmed` | Output Trimmed Section | Toggle | When Off the output is the spliced and trimmed channels based and on the parameters below. When On the output is the opposite and contains the trimmed out portion of the channels. |
| `direction` | Direction | Menu | Specify which direction the Start and Trim parameters below work. |
| `start` | Start | Float | The position the Trim and Insert operations start from. This will be from the first sample or the last sample in the channel depending on the Direction parameter above. |
| `startunits` | Start Units |  | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `trimmethod` | Trim Method | Menu | Gives options for how to set the trim length. |
| `trimlength` | Trim Length | Float | The how long the trimmed region is. To output just the trimmed region, switch Output Trimmed Section to On. |
| `trimlengthunits` | Trim Length Units | Menu |  |
| `insertmethod` | Insert Method | Menu | Handles how the 2nd input is spliced into the channel. |
| `insertlength` | Insert Length | Float | Used to set the length of the inserted data based on the Insert Method above. When set to Trim to Insert Length, the inserted data will be trimmed when this parameter value is shorter than the 2nd ... |
| `insertunits` | Insert Units | Menu |  |
| `insertinterp` | Insert Interpolate | Menu | Choose interpolation method for stretched insert channel. |
| `match` | Match by | Menu | Match channels between inputs by name or number. |
| `unmatchedinterp` | Unmatched Chan Interpolate | Menu | Choose interpolation method for any channels that are unmatched using "Match Channels". |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP spliceCHOP operator
splicechop_op = op('splicechop1')

# Get/set parameters
freq_value = splicechop_op.par.active.eval()
splicechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
splicechop_op = op('splicechop1')
output_op = op('output1')

splicechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(splicechop_op)
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
