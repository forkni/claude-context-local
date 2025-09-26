# CHOP inversecurveCHOP

## Overview

The Inverse Curve CHOP calculates an inverse kinematics simulation for bone objects using a curve object.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `guide` | Guide Components | Object | The set of objects describing the curve. |
| `bonestart` | Bone Start | Object | The first bone in the chain to place. |
| `boneend` | Bone End | Object | The last bone in the chain to place. |
| `span` | Span | Float |  |
| `interpolation` | Interpolation | Menu | The type of guide curve to create with the guide components. |
| `order` | Order | Int | The curve order when using NURBs or Bezier interpolation. |
| `upvector` | Up Vector | XYZ | Control bone twist with this parameter. |
| `mapexports` | Map Exports | Toggle | Export the calculated transform values directly onto the bone chain parameters. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP inversecurveCHOP operator
inversecurvechop_op = op('inversecurvechop1')

# Get/set parameters
freq_value = inversecurvechop_op.par.active.eval()
inversecurvechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
inversecurvechop_op = op('inversecurvechop1')
output_op = op('output1')

inversecurvechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(inversecurvechop_op)
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
