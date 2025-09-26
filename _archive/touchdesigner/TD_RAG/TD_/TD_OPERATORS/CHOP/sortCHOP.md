# CHOP sortCHOP

## Overview

The Sort CHOP re-orders the inputs channels samples by value or by random.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Sorting Method | Menu | There are three different sorting methods. CHOP samples can be reordered by increasing values, decreasing values or in random order. |
| `seed` | Seed | Float | Any number, integer or non-integer, which starts the random number generator. Each number gives completely different noise patterns, but with similar characteristics. |
| `select` | Select Type | Menu | Specify if the channels to be sorted will be specified by index or name. |
| `indices` | Channel Indices | Str | Specify the index of the channel to be sorted. All not specified channels will reorder their samples according to the specified channels new sample order. If left empty, all channels will be sorted. |
| `names` | Channel Names | Str | Specify the name of the channel to be sorted. All not specified channels will reorder their samples according to the specified channels new sample order. If left empty, all channels will be sorted. |
| `indexchannel` | Index Channel | Toggle | Enable to output an index channel which holds the former samples location before sorting. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP sortCHOP operator
sortchop_op = op('sortchop1')

# Get/set parameters
freq_value = sortchop_op.par.active.eval()
sortchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sortchop_op = op('sortchop1')
output_op = op('output1')

sortchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sortchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
