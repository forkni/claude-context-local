# CHOP delayCHOP

## Overview

The Delay CHOP delays the input. Multiple channels can be fed in to delay each separately and each channels can have a separate delay time.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `delay` | Delay | Float | Delay in seconds, or in units determined by its Units menu. To get a delay per channel, use me.chanIndex. From a table where each row has a delay amount, use op['delaysTable'](me.chanIndex,0). |
| `delayunit` | Delay Unit | Menu |  |
| `maxdelay` | Max Delay | Float | Useful for optimizing performance when the Delay parameter above is changing dynamically. Set Max Delay to a value higher than the expected range of the Delay parameter. |
| `maxdelayunit` | Max Delay Unit | Menu |  |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP delayCHOP operator
delaychop_op = op('delaychop1')

# Get/set parameters
freq_value = delaychop_op.par.active.eval()
delaychop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
delaychop_op = op('delaychop1')
output_op = op('output1')

delaychop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(delaychop_op)
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
