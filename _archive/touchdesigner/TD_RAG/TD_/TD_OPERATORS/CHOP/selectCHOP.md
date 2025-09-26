# CHOP selectCHOP

## Overview

The Select CHOP selects and renames channels from other CHOPs of any CHOP network.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `chop` | CHOP | CHOP | The source(s) of the channels. (Assuming the CHOP is not directly connected). |
| `channames` | Channel Names | StrMenu | The names of the channels to keep. Name patterns may be used. Ex:        chan[1-5] *x /project1/geo1:t[xyz]        The order of the names determine the order of the output channels. If a channel is... |
| `renamefrom` | Rename from | StrMenu | The channel pattern to rename. See Pattern Matching. |
| `renameto` | Rename to | StrMenu | The replacement pattern for the names. The default parameters do not rename the channels. See Pattern Replacement.      Example:         Channel Names: c[1-10:2] ambient     Rename From: c* ambient... |
| `filterbydigits` | Filter by Digits | Toggle | This toggle enables the two parameters below to select channels with the specified digits at the end of their name. For examples, this can be used to selct all channels with a name ending in the di... |
| `digits` | Digits | Integer | Specify the digit at then end of the channel names you want to select when using 'Filter by Digits' |
| `stripdigits` | Strip Digits | Toggle | Then On, the selected channel names are output without the digits. When Off, the selected channel names are not changed. |
| `align` | Align | Menu | This menu handles cases where multiple input CHOPs have different start or end times. All channels output from a CHOP share the same start/end interval, so the inputs must be treated with the Align... |
| `autoprefix` | Automatic Prefix | Toggle | When 2 channels have the same name, turning on this option will add the node's name (or the node's parent's name, etc.) as a  prefix to the channel name. For example, if selecting a channel from /w... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP selectCHOP operator
selectchop_op = op('selectchop1')

# Get/set parameters
freq_value = selectchop_op.par.active.eval()
selectchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
selectchop_op = op('selectchop1')
output_op = op('output1')

selectchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(selectchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
