# CHOP kinectazureCHOP

## Overview

The Kinect Azure CHOP can be used to obtain body tracking information, including joint positions and rotations, and IMU sensor data from a Microsoft Kinect Azure camera or a Kinect compatible Orbbec Camera (Femto Mega, Femto Bolt, etc).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enable to disable the capturing of body tracking data. The primary Kinect Azure TOP must also be active to receive data. |
| `top` | Kinect Azure TOP | TOP | The name of the Kinect Azure TOP that is connected to the camera. |
| `maxplayers` | Max Players | Int | The number of player skeletons that should be tracked by the device. If the camera does not find enough skeletons, then the extra channels will be set to zero. |
| `relbonerotations` | Relative Bone Rotations | Toggle | Include rotation data for all bone in the skeleton. Rotation is measured in degrees around the XYZ axes relative to the bone's parent. |
| `absbonerotations` | Absolute Bone Rotations | Toggle | Include absolute rotation data for all bone in the skeleton. Rotation is measured in degrees around the XYZ axes relative to the world. |
| `bonelengths` | Bone Lengths | Toggle | Include channels for the length of each bone. A bone's length is the distance between a joint and its parent joint. See the Kinect Azure SDK for a diagram of the joint heirarchy. |
| `worldspace` | World Space Positions | Toggle | Include channels for the bone's absolute world position in meters. |
| `colorspace` | Color Image Positions | Toggle | Include channels for the skeleton positions in UV coordinates of the Color Image. |
| `depthspace` | Depth Image Positions | Toggle | Include channels for the skeleton positions in UV coordinates of the Depth Image. |
| `aspectcorrectuv` | Aspect Correct UVs | Toggle | Scale the image space positions to that they match the aspect ratio of the corresponding camera. |
| `flipimagev` | Mirror Image V Positions | Toggle | Flip the v coordinate of the image space positions so that 0,0 would be in the top-left corner. This was the default behaviour prior to version 2020.44130. |
| `flipskelu` | Mirror U Positions | Toggle | Mirror's the U coordintate of Color Image Positions and Depth Image Positions above which is useful when those images have been flipped in U (x axis flip like a mirror). |
| `confidence` | Bone Confidence | Toggle | The confidence that the sensor has that a joint's position and rotation is correct. It can be one of the following values:       0 - The joint is out of range (too far from the camera)  1 - The joi... |
| `imuchans` | IMU Channels | Toggle | Include temperature, acceleration and rotation data from the camera's IMU sensor. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP kinectazureCHOP operator
kinectazurechop_op = op('kinectazurechop1')

# Get/set parameters
freq_value = kinectazurechop_op.par.active.eval()
kinectazurechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
kinectazurechop_op = op('kinectazurechop1')
output_op = op('output1')

kinectazurechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(kinectazurechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
