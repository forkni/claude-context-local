# CHOP lookupCHOP

## Overview

The Lookup CHOP outputs values from a lookup table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `index` | Index Range | Float | The Index Range maps the index channel's values to the lookup table's start and end and defaults to 0 and 1. The first parameter represents the start of the lookup table. When the index channel has... |
| `cyclic` | Cyclic Range | Menu | Adapts the range of the Lookup Table (2nd input) for cyclic or non-cyclic input indices. When using a cyclic input index (1st input), the lookup value for index 0.0 and 1.0 result in the same value... |
| `chanmatch` | Per Index Channel | Menu | Determines how index channels are mapped to lookup Channel tables. |
| `match` | Match by | Menu | Determines how index channels are matched with a lookup channel in 'One Lookup Table Channel' mode. |
| `interp` | Interpolate | Toggle | When on, the input can be interpolated between samples. When off, the nearest sample is used. |
| `left` | Extend Left | Menu | The left extend conditions (before/after range) for the lookup output. |
| `right` | Extend Right | Menu | The right extend conditions (before/after range) for the lookup output. |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP lookupCHOP operator
lookupchop_op = op('lookupchop1')

# Get/set parameters
freq_value = lookupchop_op.par.active.eval()
lookupchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lookupchop_op = op('lookupchop1')
output_op = op('output1')

lookupchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lookupchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
