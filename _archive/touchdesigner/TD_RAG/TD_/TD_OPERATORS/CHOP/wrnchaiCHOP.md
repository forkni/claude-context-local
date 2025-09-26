# CHOP wrnchaiCHOP

## Overview

Uses the wrnchAI engine to track human motion in any video stream.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `license` | wrnchAI License | Str | Add the Edge License Key from your wrnchAI account here. Requires a separate license from wrnchAI. |
| `modelfolder` | Model Folder | Folder | Specify the path the the folder that contains the trained models. See Quickstart Guide above for details. |
| `gpu` | GPU Device | Menu | A menu of available GPU(s) to run wrnchAI on. Selecting 'Default' uses the same GPU TouchDesigner is currently running on. |
| `top` | TOP | TOP | Specify the TOP to process for tracking. |
| `body3d` | Body 3D | Toggle | Enable the channels (tx, ty, tz) for body tracking points in 3D space. |
| `body2d` | Body 2D | Toggle | Enable the channels (u, v) for body tracking points in 2D. |
| `body3dik` | Body 3D IK | Toggle | Enable the IK channels (tx, ty, tz, rx, ry, rz and associated roll channels) for body tracking points in 3D space. |
| `facebounds` | Face Bounds | Toggle | Enable the position and bounds channels (u, v, width, height) for faces. |
| `face` | Face | Toggle | Enable the position channels (u, v) for all face tracking points. |
| `handsbounds` | Hands Bounds | Toggle | Enable the position and bounds channels (u, v, width, height) for hands. |
| `hands` | Hands | Toggle | Enable the position channels (u, v) for all hand tracking points. |
| `maxplayers` | Max Players | Int | Sets the maximum number of people that can be tracked. For each person/player a new set of channels is created prefixed p1, p2, p3, ... etc.  NOTE: The parameter slider goes to 10 but higher number... |
| `aspectcorrectuv` | Aspect Correct UVs | Toggle | Adjusts the values of u and v channels to take the TOP's aspect ratio into account. When using non-square input TOP, turn this on to line up u and v position with the image. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP wrnchaiCHOP operator
wrnchaichop_op = op('wrnchaichop1')

# Get/set parameters
freq_value = wrnchaichop_op.par.active.eval()
wrnchaichop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
wrnchaichop_op = op('wrnchaichop1')
output_op = op('output1')

wrnchaichop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(wrnchaichop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
