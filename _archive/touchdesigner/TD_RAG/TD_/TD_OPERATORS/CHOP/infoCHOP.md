# CHOP infoCHOP

## Overview

The Info CHOP gives you extra information about a node.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `op` | Operator | OP | The path of the node that the Info CHOP is getting information from. You can drag and drop any node onto this path, or type the path directly into the field. |
| `infotype` | Info Type | None | Select the channel set associated with the Info Type. |
| `values` | Values | Menu | Select channel with values inside or outside the range specified in Range. |
| `range` | Range | Float | Set the bounds for selecting channels by value. |
| `passive` | Passive | Toggle | When Passive is Off the Info CHOP will cook the Operator it is pointing to before querying its values. When Passive is On it will not force a cook. A side effect: If the Info CHOP and the target ar... |
| `childcooktime` | Children Cook Time | Toggle | When the Info CHOP is monitoring a Component, this toggle will enable a channel called children_cpu_cook_time which is the total cooktime of all the component's children. This is off by default, en... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP infoCHOP operator
infochop_op = op('infochop1')

# Get/set parameters
freq_value = infochop_op.par.active.eval()
infochop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
infochop_op = op('infochop1')
output_op = op('output1')

infochop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(infochop_op)
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
