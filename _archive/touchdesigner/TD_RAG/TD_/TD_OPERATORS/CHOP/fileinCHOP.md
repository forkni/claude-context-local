# CHOP fileinCHOP

## Overview

The File In CHOP reads in channel and audio files for use by CHOPs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | Channel File | File | The name of the file to load. Use http:// when specifying a URL. |
| `nameoption` | Name Options | Menu | Use this menu to control the names of the loaded channels. |
| `name` | Name | Str | Used to name the channels when the Name Options parameter is set to Use New Names. |
| `rateoption` | Rate Options | Menu | Use this menu to adjust the sample rate of the loaded channels. |
| `rate` | Sample Rate | Float | Samples per second, as utilized by the Rate Options parameter. |
| `left` | Extend Left | Menu | The left extend conditions (before/after range). |
| `right` | Extend Right | Menu | The right extend conditions (before/after range). |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `renamefrom` | Rename from | StrMenu | The channel pattern to rename. See Pattern Matching. |
| `renameto` | Rename to | StrMenu | The replacement pattern for the names. The default parameters do not rename the channels. See Pattern Replacement. |
| `overridpattern` | Value Override Pattern | Str | Scopes channels to apply the Override Value to. |
| `overridevalue` | Override Value | Float | The value given to channels scope by the Value Override Pattern parameter above. |
| `refresh` | Refresh | Toggle | Reload the file when this parameter is set to On. |
| `refreshpulse` | Refresh Pulse | Pulse | Instantly reload the file from disk. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP fileinCHOP operator
fileinchop_op = op('fileinchop1')

# Get/set parameters
freq_value = fileinchop_op.par.active.eval()
fileinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fileinchop_op = op('fileinchop1')
output_op = op('output1')

fileinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fileinchop_op)
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
