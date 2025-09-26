# CHOP parameterCHOP

## Overview

The Parameter CHOP gets parameter values, including custom parameters, from all OP types.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `ops` | Operators |  | The operators determine where to obtain the channels. Specify or more operator names or paths. Examples: wave1, slider*, constant[1-9] constant[10-19:2], ../base1. Or select the operators using the... |
| `fetch` | Fetch |  | Pick between fetching Parameters or Sequences. |
| `sequences` | Sequences |  | The list of sequence names (which can include wildcards) you want to get from the OP(s). Used by the Parameters and ParGroups parameters to select from within the picked sequences. One or more sequ... |
| `pargroups` | ParGroups |  | The list of pargroup names (which can include wildcards) you want to get from the OP(s). One or more pargroups, or * for all pargroups. You can also specify a "NOT" selection with an ^. Or select t... |
| `parameter` | Parameter |  | The list of parameters names (which can include wildcards) you want to get from the OP(s). One or more parameter, or * for all parameters. You can also specify a "NOT" selection with an ^. Or selec... |
| `custom` | Custom |  | Output the operators' custom parameters. |
| `builtin` | Built-In |  | Output the operators' built-in parameters. |
| `nameformat` | Name Format |  | Channels can be named suitably for multi-exporting. See CHOP_Export. |
| `renamefrom` | Rename from |  | See Pattern Matching. |
| `renameto` | Rename to |  | See Pattern Replacement. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP parameterCHOP operator
parameterchop_op = op('parameterchop1')

# Get/set parameters
freq_value = parameterchop_op.par.active.eval()
parameterchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
parameterchop_op = op('parameterchop1')
output_op = op('output1')

parameterchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(parameterchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
