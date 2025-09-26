# CHOP fanCHOP

## Overview

The Fan CHOP converts one channel out to many channels, or converts many channels down to one.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `fanop` | Operation | Menu | Selects either Fan In or Fan Out. |
| `channame` | Channel Names | Str | The names for the output channels that this CHOP creates. This also controls how many output channels are created (one for each name) in Fan Out mode. In Fan In mode, only one channel is created, a... |
| `range` | Outside Range | Menu | Determines how to handle input values that are outside the index range (0 to N-1). |
| `alloff` | All Channels Off | Menu | For a Fan In operation, when all input channels are off, set the output to -1 or 0. |
| `quantize` | Quantize Output | Toggle | On by default. Channels are quatized to the nearest integer. For example, if the input channel's value is 5.6 and 6 channels are created, channel 5 is 1, while the rest are 0. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP fanCHOP operator
fanchop_op = op('fanchop1')

# Get/set parameters
freq_value = fanchop_op.par.active.eval()
fanchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fanchop_op = op('fanchop1')
output_op = op('output1')

fanchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fanchop_op)
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
