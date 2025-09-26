# CHOP deleteCHOP

## Overview

The Delete CHOP removes entire channels and/or individual samples of its input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `delchannels` | Delete Channels | Toggle | Toggle to enable channel deleting. |
| `discard` | Delete | Menu | Determines whether the scoped channels should be deleted or retained: |
| `select` | Select Channels | Menu | How to select channels - By Name, or By Numeric index. |
| `delscope` | Channel Names | StrMenu | Enter a scope pattern here to specify the names of channels to delete or extract. You do this by specifying a scope pattern, as detailed in Pattern Matching.       The default scope pattern t* will... |
| `selnumbers` | Channel Numbers | Str | The indices of the channels to delete or extract. - See possible number patterns below. |
| `chanvalue` | Channel Value | Menu | Chooses the type of value range selection: |
| `selrange` | Value Range | Float | The lower and upper values of the range used for Range Selection. |
| `selconst` | Select Constant Valued Channels | Toggle | Select channels which have the same value for all samples. These kinds of channel name patterns are used to select existing channels in an input CHOP, see Pattern Matching for details.      Also th... |
| `delsamples` | Delete Samples | Toggle | Toggle to enable sample deleting. |
| `compchans` | Channels to Compare | Menu | How to select channels used to compare against criteria - By Name, by Numeric index, by using the First Channel, or by using the Last Channel. |
| `compnames` | Channel Names | StrMenu | Enter a scope pattern here to specify the names of channels to be used as compare channels. You do this by specifying a scope pattern, as detailed in Pattern Matching. |
| `compnums` | Channel Numbers | Str | The indices of the channels to be used as compare channels, the default being 0, the first channel. - See possible number patterns above. |
| `compmulti` | Multi-Compare Channels | Menu | If there is more that one compare channel, this determines how to treat the values in the compare channels before checking against the criteria: |
| `condition` | Delete Condition | Menu | Choose the criteria for the samples to be compare against: |
| `value1` | Value 1 | Float | Set a value for Value 1. |
| `inclvalue1` | Include Value 1 | Toggle | Toggle the inclusivity of Value 1. |
| `value2` | Value 2 | Float | Set a value for Value 2. |
| `inclvalue2` | Include Value 2 | Toggle | Toggle the inclusivity of Value 2. |
| `deletecomp` | Delete Compare Channels | Toggle | Determines whether the compare channels should be deleted or retained. |
| `onesample` | One Sample if All Deleted | Toggle | Leaves one sample even when all samples are deleted. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP deleteCHOP operator
deletechop_op = op('deletechop1')

# Get/set parameters
freq_value = deletechop_op.par.active.eval()
deletechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
deletechop_op = op('deletechop1')
output_op = op('output1')

deletechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(deletechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
