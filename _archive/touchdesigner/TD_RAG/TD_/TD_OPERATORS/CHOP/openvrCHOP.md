# CHOP openvrCHOP

## Overview

The OpenVR CHOP receives positional data from the OpenVR SDK.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Control if this node is querying data from the OpenVR driver. |
| `output` | Output | Menu | Controls what kind of category of data will be output from this node. |
| `maxtrackers` | Max Trackers | Int | The maximum number of trackers whose data should be output from this node. |
| `firsttracker` | First Tracker | Int | The first tracker number to be output. For example if this is set to 2 and Max Trackers is 2, then data for trackers 2 and 3 will be output. |
| `orientation` | Orientation | Toggle | When doing 'Sensor' output, controls if the orientation channels will be output. By default the units for orientation are 1 unit = 1 meter. |
| `generalinfo` | General Info | Toggle | When doing 'Sensor' output, controls of general information channels will be output, such as render resolution and play area size. |
| `near` | Near | Float | When outputting 'Projection Matrices', controls the near plane the projection matrix will be built with. |
| `far` | Far | Float | When outputting 'Projection Matrices', controls the far plane the projection matrix will be built with. |
| `unitscale` | Unit Scale | Float | OpenVR by default works in a scale where 1 unit = 1 meter. This parameter allows the scale to be changed incase a scene is imported with a different scale. |
| `customactions` | Custom Actions | Toggle | Turn on to allow specifying a custom OpenVR Actions manifest file. |
| `actionmanifest` | Action Manifest | File | A path to a OpenVR Actions manifest file. By default this is using the same manifest OpenVR uses when Custom Actions is disabled. |
| `uselegacynames` | Use Legacy Names | File | Use legacy channel naming convention coming from the Action Manifest. This should stay off unless loading existing old files. |
| `skeletonrange` | Skeleton Range | Menu | Controls the range of motion of the skeleton values. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP openvrCHOP operator
openvrchop_op = op('openvrchop1')

# Get/set parameters
freq_value = openvrchop_op.par.active.eval()
openvrchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
openvrchop_op = op('openvrchop1')
output_op = op('output1')

openvrchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(openvrchop_op)
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
