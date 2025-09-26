# CHOP handleCHOP

## Overview

he Handle CHOP is the "engine" which drives Inverse Kinematic solutions using the Handle COMP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `source` | Source | Object | Creates rx/ry/rz channels for each bone listed. |
| `fixed` | Fixed | Object | If you have entered bones which form a branch or should act as a unit, enter them here. An example may be two bones splitting at the shoulders. You want them to rotate, but only as a unit. |
| `iterations` | Iterations | Int | Increasing this parameters gives a more accurate solution at the cost of cooking time. Preroll (only when precalculating a range of frames, SingleFrame turned off): This will cook the solution a gi... |
| `init` | Init Frame | Float | Specifies a frame in which the bones are reset to their default rest angles. |
| `preroll` | Preroll | Int | Specifies the number of iterations to solve at the initialization frame. |
| `delta` | Max Angle Change | Float | Specifies the maximum change in degrees the solver is allowed to move each bone per frame. Use this parameter if the solution is too drastic. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP handleCHOP operator
handlechop_op = op('handlechop1')

# Get/set parameters
freq_value = handlechop_op.par.active.eval()
handlechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
handlechop_op = op('handlechop1')
output_op = op('output1')

handlechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(handlechop_op)
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
