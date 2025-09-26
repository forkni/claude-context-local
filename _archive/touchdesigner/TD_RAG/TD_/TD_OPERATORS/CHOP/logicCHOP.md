# CHOP logicCHOP

## Overview

The Logic CHOP first converts channels of all its input CHOPs into binary (0 = off, 1 = on) channels and then combines the channels using a variety of logic operations.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `convert` | Convert Input | Menu | This menu determines the method to convert inputs to binary: |
| `preop` | Channel Pre OP | Menu | Once converted by the Convert Input stage, Channel Pre OP defines a unary operation on each input sample: |
| `chanop` | Combine Channels | Menu | Takes the first input and combines its channels, then the second input and combines its channels, and so on. |
| `chopop` | Combine CHOPs | Menu | Combine CHOPs combines the first channels of each CHOP, the second channels of each CHOP, etc.. Channels between inputs can be combined by number or name. Combining (Logic) Operations are: |
| `match` | Match by | Menu | Channels are matched between inputs by Channel Name or Channel Number. |
| `align` | Align | Menu | Inputs that don't start at the same frame can be aligned. Se the section, Align Options. |
| `bound` | Bounds | Float | Set lower and upper bounds for when Convert Input is set to Off When Outside Bounds. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP logicCHOP operator
logicchop_op = op('logicchop1')

# Get/set parameters
freq_value = logicchop_op.par.active.eval()
logicchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
logicchop_op = op('logicchop1')
output_op = op('output1')

logicchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(logicchop_op)
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
