# CHOP facetrackCHOP

## Overview

The Face Track CHOP can detect faces and facial landmarks in a given image stream.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enables the face tracking features. |
| `modelfolder` | Model Folder | Folder | The location of the AI model files used for face detection. By default these files are located in the Config/Models folder. |
| `meshfile` | Mesh File | File | The 3D morphable mesh file in Nvidia 'nvf' format to use in mesh fitting. When available, the fitted mesh can be accessed with a Face Track SOP. |
| `top` | TOP | TOP | A path to the TOP operator that will provides the image to perform face tracking on. |
| `bbox` | Bounding Boxes | Toggle | Output channels that describe a bounding box around the detected face. The channels give the u and v positions of the center of the face as well as the width and height of the box. The positions ar... |
| `bboxconfidence` | Bounding Box Confidence | Toggle | Outputs a channel that describes the level of certainty that the AI model has detected a face in the input image. Higher numbers indicate greater confidence. |
| `rotations` | Rotations | Toggle | Output rx, ry, and rz values that indicate how the face is oriented in the image. (0,0,0) indicates that the face is oriented directly towards the camera. Values can range from +/- 180 degrees as t... |
| `landmarks` | Number of Landmarks | Menu |  |
| `landmarkconfidence` | Landmark Confidence | Toggle | Adds a confidence value for each landmark feature. Higher values indicate the feature is more likely to be accurate. |
| `meshtransform` | Mesh Transform | Toggle | Enable to output translate, rotate and scale channels for the fitted face mesh. This feature requires a valid 3D morphable face mesh file (see notes above). The values from these channels can be us... |
| `aspectcorrectuv` | Aspect Correct UVs | Toggle | Rescales the the u and v positions so that they have the correct aspect ratio of the input image. This is useful when using the u, v positions as 3D coordinates rather than as image positions. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP facetrackCHOP operator
facetrackchop_op = op('facetrackchop1')

# Get/set parameters
freq_value = facetrackchop_op.par.active.eval()
facetrackchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
facetrackchop_op = op('facetrackchop1')
output_op = op('output1')

facetrackchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(facetrackchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
