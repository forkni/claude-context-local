# CHOP nullCHOP

## Overview

The Null CHOP is used as a place-holder and does not alter the data coming in.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `cooktype` | Cook Type | Menu | This controls how nodes downstream from the Null CHOP are triggered for recooking when the Null CHOP output changes. See also: Cook |
| `checkvalues` | Check Values | Toggle | Recook when the Null CHOP values change. |
| `checknames` | Check Names | Toggle | Recook when the Null CHOP channel names change. |
| `checkrange` | Check Range | Toggle | Recook when the Null CHOP channel range changes.      Please note that downstream cooks may also cook for a variety of reasons including viewing the contents of the data while editing nodes, etc. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP nullCHOP operator
nullchop_op = op('nullchop1')

# Get/set parameters
freq_value = nullchop_op.par.active.eval()
nullchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
nullchop_op = op('nullchop1')
output_op = op('output1')

nullchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(nullchop_op)
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
