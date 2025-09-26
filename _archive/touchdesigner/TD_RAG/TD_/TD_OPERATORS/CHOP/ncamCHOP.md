# CHOP ncamCHOP

## Overview

The Ncam CHOP receives camera tracking data from an external Ncam Reality system for use in virtual production.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turn off this parameter to stop receiving data from the Ncam system. |
| `protocol` | Protocol | Menu | A parameter for future options. |
| `netaddress` | Network Address | Str | The network address of the Ncam server that is sending the data. |
| `port` | Network Port | Int | The network port to connect to on the Ncam server. |
| `cameraview` | Camera View | Menu | Select how the camera's orientation and position are outputted. |
| `cameraproj` | Camera Projection | Menu | Select how the camera's projection settings are outputted. |
| `cameraprops` | Camera Properties | Menu | Controls the output of additional camera properties like zoom and focus. These properties can either be normalized (0 to 1) or in their native physical units. |
| `timecode` | Timecode | Menu | Select whether the embedded timecode is presented as a single counter or in separate hour, minute, second and frame channels. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP ncamCHOP operator
ncamchop_op = op('ncamchop1')

# Get/set parameters
freq_value = ncamchop_op.par.active.eval()
ncamchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
ncamchop_op = op('ncamchop1')
output_op = op('output1')

ncamchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(ncamchop_op)
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
