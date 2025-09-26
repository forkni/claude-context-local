# CHOP bodytrackCHOP

## Overview

The Body Track CHOP can track bounding boxes and 34 key points of one or more human bodies, with optional joint angles, in 2D or 3D.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enables the body tracking features. |
| `modelfolder` | Model Folder | Folder | The location of the AI model files used for body detection. By default these files are located in the Config/Models folder. |
| `top` | TOP | TOP | A path to the TOP operator that provides the image to perform body tracking on. |
| `highperformance` | High Performance | Toggle | Enable high performance while sacrificing quality. This is only available when Keypoints are on. |
| `bbox` | Bounding Boxes | Toggle | Output channels that describe a bounding box around the detected body. The channels give the u and v positions of the center of the body as well as the width and height of the box. The positions ar... |
| `bboxconfidence` | Bounding Box Confidence | Toggle | Outputs a channel that describes the level of certainty that the AI model has detected a body in the input image. Higher numbers indicate greater confidence. |
| `keypoints` | Keypoints | Toggle | Outputs either the UV or XYZ positions of the body's keypoints, depending on whether Body 3D is enabled. |
| `keypointsconfidence` | Keypoints Confidence | Toggle | Outputs a channel that describes the level of certainty that the AI model has detected for each keypoint on a body. Higher numbers indicate greater confidence. |
| `rotations` | Rotations | Toggle | Output rx, ry, and rz values for each keypoint on the body. (0,0,0) indicates that the body is oriented directly towards the camera. Values can range from +/- 180 degrees. |
| `body3d` | Body 3D | Toggle | If keypoints are enabled, output XYZ positions instead of UV positions for each keypoint. |
| `fov` | Field of View (Horz) | Float | If Body 3D is enabled, fov is the Field of View of the camera which produced the image given to the Body Track. |
| `aspectcorrectuv` | Aspect Correct UVs | Toggle | Rescales the u and v positions so that they have the correct aspect ratio of the input image. This is useful when using the u, v positions as 3D coordinates rather than as image positions. |
| `flipskelu` | Mirror U Positions | Toggle | Flips the u-coordinate of the UVs so that 1.0 becomes 0. and 0. becomes 1. |
| `peopletracking` | People Tracking | Toggle | Track multiple people within the input image. Each person will have a persistent ID which is accessible with the Bounding Boxes toggle. |
| `maxbodies` | Max Bodies | Toggle | The maximum number of people for the Maxine SDK to track. After the new maximum target tracked limit is met, any new targets will be discarded. This parameter does not affect the number of output c... |
| `shadowtrackingage` | Shadow Tracking Age | Int | Once a previously tracked body is no longer detected, an internal integer will be reset and incremented by one for each frame. The shadow tracking age is the threshold of this integer after which t... |
| `probationage` | Probation Age | Int | This option is the length of the tracker's probationary period. After a body reaches this age, it is considered to be valid and is appointed an ID. This will help with false positives, where false ... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |


## Usage Examples

### Basic Usage
```python
# Access the CHOP bodytrackCHOP operator
bodytrackchop_op = op('bodytrackchop1')

# Get/set parameters
freq_value = bodytrackchop_op.par.active.eval()
bodytrackchop_op.par.active = 1
```

### In Networks
```python
# Connect operators
input_op = op('source1')
bodytrackchop_op = op('bodytrackchop1')
output_op = op('output1')

bodytrackchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(bodytrackchop_op)
```

## Technical Details

### Operator Family
**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count
This operator has **23** documented parameters.

## Navigation
- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
