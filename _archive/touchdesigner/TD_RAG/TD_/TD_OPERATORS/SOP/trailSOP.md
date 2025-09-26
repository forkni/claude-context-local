# SOP trailSOP

## Overview

The Trail SOP takes an input SOP and makes a trail of each point of the input SOP over the past several frames, and connects the trails in different ways.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `result` | Result Type | Menu | How to construct the trail geometry. |
| `length` | Trail Length | Int | This sets the length of the trail by establishing the maximum number of frames for the Trail SOP to use, i.e. a Trail Length of 25will connect the geometry from the previous twenty-five frames. |
| `inc` | Trail Increment | Int | This will skip the given number of frames to build a trail with fewer points in it, but the same length. This will lower the resolution of the trail by reducing the number of points in the trail. T... |
| `cache` | Cache Size | Int | The number of frames to keep cached in available memory. |
| `evalframe` | Evaluate Within Frame Range | Toggle | This option specifies that the Trail SOP will only evaluate, or cook, within the current frame range ($FSTART, $FEND). If this option is not enabled, the SOP can evaluate prior to the start frame. |
| `surftype` | Connectivity | Menu | This option is used to select the type of surface, when using a Mesh Primitive Type. |
| `close` | Close Rows | Toggle | When selected, closes the rows in the output selection. |
| `velscale` | Velocity Scale | Float | Scales the velocity by a specific value when Compute Velocity is selected. |
| `reset` | Reset | Toggle | While on, clears any cached geometries, resetting the trail to mirror the input. |
| `resetpulse` | Reset Pulse | Pulse | Reset the geometry for a single frame. |

## Usage Examples

### Basic Usage

```python
# Access the SOP trailSOP operator
trailsop_op = op('trailsop1')

# Get/set parameters
freq_value = trailsop_op.par.active.eval()
trailsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
trailsop_op = op('trailsop1')
output_op = op('output1')

trailsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(trailsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
