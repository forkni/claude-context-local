# CHOP oculusriftCHOP

## Overview

The Oculus Rift CHOP connects to an Oculus Rift device and outputs several useful sets of channels that can be used to integrate the Oculus Rift into projects.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When on, this CHOP will update it's data when it cooks. |
| `output` | Output | Menu | Switches between three different output modes. |
| `orientation` | Orientation | Toggle | When on, the output channels will include sensor orientation. |
| `recenter` | Re-Center | Pulse | Resets the xyz positional components and the y orientation component of the tracking space for the HMD and controllers using the HMD's current tracking position. |
| `acceleration` | Acceleration | Toggle | When on, the output channels will include acceleration. |
| `velocity` | Velocity | Toggle | When on, the output channels will include velocity. |
| `deviceinfo` | Device Info | Toggle | When on, the output channels will include device info. |
| `controllerbuttons` | Controller Buttons | Toggle | When on, the output channels will include controller button states. |
| `near` | Near | Float | Specifies the distance of the near clipping plane for the projection matrix. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT |  |

## Usage Examples

### Basic Usage

```python
# Access the CHOP oculusriftCHOP operator
oculusriftchop_op = op('oculusriftchop1')

# Get/set parameters
freq_value = oculusriftchop_op.par.active.eval()
oculusriftchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oculusriftchop_op = op('oculusriftchop1')
output_op = op('output1')

oculusriftchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oculusriftchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
