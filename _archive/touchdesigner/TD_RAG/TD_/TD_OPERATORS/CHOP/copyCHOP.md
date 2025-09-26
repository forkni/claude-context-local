# CHOP copyCHOP

## Overview

The Copy CHOP produces multiple copies of the second input along the timeline of the first input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Copy Method | Menu | Select which copy method to use from the menu options below. |
| `output` | Output Method | Menu | Select which output method to use from the menu options below. |
| `threshold` | Trigger Threshold | Float | The threshold value for triggering copies. |
| `remainder` | Remainder | Menu | See Remainder parameter below.. |
| `keep` | Keep Non-Scoped Channels | Toggle | If enabled, non-scoped channels are copied to the output, otherwise they are deleted. |
| `stamp` | Stamp Inputs | Toggle | Recook the second input for each triggered copy. |
| `copy` | Copy | Sequence | Sequence of values available as stamps. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP copyCHOP operator
copychop_op = op('copychop1')

# Get/set parameters
freq_value = copychop_op.par.active.eval()
copychop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
copychop_op = op('copychop1')
output_op = op('output1')

copychop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(copychop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
