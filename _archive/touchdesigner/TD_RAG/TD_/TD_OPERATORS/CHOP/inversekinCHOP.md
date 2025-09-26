# CHOP inversekinCHOP

## Overview

The Inverse Kin CHOP calculates an inverse kinematics simulation for Bone objects.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `solvertype` | Solver Type | Menu | This parameter defines the method used to determine the motion of the Bone object when it, its ancestor, or its children are moved. |
| `boneroot` | Root Bone | Object | The starting bone of the chain; where the chain starts. |
| `boneend` | End Bone | Object | If you specify a bone as the last bone in chain, then you will be defining a bone chain that has the current bone as the first in the chain and the bone chosen from the menu as the final bone in th... |
| `endaffector` | End Affector | Object | This specifies which object will serve as the chain's end affector. |
| `twistaffector` | Twist Affector | Object | If you specify a twist affector, the entire bone chain will twist along the axis from the chain's root to its end-affector so that the first bone is pointing as much as it can at the twist affector... |
| `iktwist` | IK Twist | Float | Amount of twist allowed by the kinematics solution. |
| `ikdampen` | IK Dampening | Float | Amount of damping (slows down at the extremes of angular allowability). |
| `curve` | Curve Object | SOP | Curve object to follow. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP inversekinCHOP operator
inversekinchop_op = op('inversekinchop1')

# Get/set parameters
freq_value = inversekinchop_op.par.active.eval()
inversekinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
inversekinchop_op = op('inversekinchop1')
output_op = op('output1')

inversekinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(inversekinchop_op)
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
