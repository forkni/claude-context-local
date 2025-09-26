# CHOP panelCHOP

## Overview

The Panel CHOP reads Panel Values from Panel Components into CHOP channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `component` | Component | PanelCOMP | The path of the Component being referenced. |
| `select` | Select | StrMenu | Specify which panel values to create channels for. Use * to select all panel values. Add individual values using the drop down menu on the right. |
| `rename` | Rename | StrMenu | Rename the panel value channels selected with the Select parameter here. For example, if "u v" are selected in the Select parameter, you can rename these channels to horizontal and vertical by ente... |
| `queue` | Queue Overlapping Events | Toggle | Queue all events that occur in a time slice. Some panel values, such as wheel or key, switches between a value and 0 in the same time slice and are considered instantaneous. When this parameter is ... |
| `queuesize` | Queue Size | Int | Size of queue. If the number of events is larger than the queue size, earlier events will be discarded. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP panelCHOP operator
panelchop_op = op('panelchop1')

# Get/set parameters
freq_value = panelchop_op.par.active.eval()
panelchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
panelchop_op = op('panelchop1')
output_op = op('output1')

panelchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(panelchop_op)
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
