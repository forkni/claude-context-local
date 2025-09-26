# CHOP crossCHOP

## Overview

The Cross CHOP is a multi input OP that blends between 2 inputs at a time.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `cross` | Cross | Float | This parameter controls the blending of the inputs. A value of 0 will select the first input, 1 will select the second input, 2 will select the third and so on. Using inbetween values will blend th... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP crossCHOP operator
crosschop_op = op('crosschop1')

# Get/set parameters
freq_value = crosschop_op.par.active.eval()
crosschop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
crosschop_op = op('crosschop1')
output_op = op('output1')

crosschop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(crosschop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **7** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
