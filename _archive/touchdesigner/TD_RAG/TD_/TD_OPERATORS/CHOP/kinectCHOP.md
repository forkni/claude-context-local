# CHOP kinectCHOP

## Overview

The Kinect CHOP reads positional and skeletal tracking data from the Kinect and Linect2 sensors.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When 'On' data is captured from the Kinect sensor. |
| `hwversion` | Hardware Version | Menu | Choose between Kinect v1 or Kinect v2 sensors. |
| `sensor` | Sensor | StrMenu | Selects which Kinect sensor to use. Only available when using Kinect v1. |
| `skeleton` | Skeleton | Menu | Selects options for skeletal tracking. |
| `maxplayers` | Max Players | Int | Limits how many players to track. |
| `interactions` | Interactions | Toggle | Enables interactions, which returns interaction data such as "grip" and "press".  The additional channels output are prefixed with  p[1-2]/hand_l_*and p[1-2]/hand_r_*.<  ### Arguments: *  For the ... |
| `relbonerotations` | Relative Bone Rotations | Toggle | Returns rx, ry, and rz relative rotation channels for each bone. The rotation is relative to the previous joint. |
| `absbonerotations` | Absolute Bone Rotations | Toggle | Returns rx, ry, and rz absolute rotation channels for each bone. |
| `bonelengths` | Bone Lengths | Toggle | Returns the length for each bone. |
| `unrollbones` | Unroll Bone Values | Toggle | Return the rx, ry, and rz values in a form that includes no discontinuities (or wrap arounds), so that they can be safely blended, filtered, lagged etc. For example, a rotation value running from 0... |
| `worldspace` | World Space Positions | Toggle | Returns the tracked positions in world space coordinates. For each tracked point, a tx, ty, tz triplet of channels will be output. |
| `colorspace` | Color Space Positions | Toggle | Returns the tracked positions in image space coordinates relative to the color camera. For each tracked point, a u, v, tz triplet of channels will be output. Note this is only available on Kinectv2. |
| `depthspace` | Depth Space Positions | Toggle | Returns the tracked positions in image space coordinates relative to the depth camera. For each tracked point, a depthu, depthv, tz triplet of channels will be output. Works on both Kinectv1 and Ki... |
| `facetracking` | Face Tracking | Toggle | Returns face tracking channels for detected faces. |
| `statuschans` | Status Channels | Toggle | A number of additional status channels are reported when this is turned on. A group of channels will report if a joint is currently being tracked, and another group of channels reports if part of t... |
| `neardepthmode` | Near Depth Mode | Toggle | Enables near mode for skeleton tracking, which allows the depth camera to see objects as close as 40cm to the camera (instead of the default 80cm). |
| `flipskelu` | Flip Skeleton U Direction | Toggle | Flips the u-axis for skeleton channels, helpful when using a mirror image from the camera. |
| `flipfaceu` | Flip Face U Direction | Toggle | Flips the u-axis for face channels, helpful when using a mirror image from the camera. |
| `jointsmoothing` | Joint Smoothing | Toggle | Activates Kinect's smoothing algorithm for joint tracking and enables the smoothing parameters below. |
| `smoothing` | Smoothing | Float | Increasing the smoothing parameter value leads to more highly-smoothed skeleton position values being returned. It is the nature of smoothing that, as the smoothing value is increased, responsivene... |
| `correction` | Correction | Float | Lower values are slower to correct towards the raw data and appear smoother, while higher values will correct toward the raw data more quickly. Values must be in the range 0 through 1.0. |
| `prediction` | Prediction | Float | The number of frames to predict into the future. Values must be greater than or equal to zero. Values greater than 0.5 will likely lead to overshooting when moving quickly. This effect can be dampe... |
| `jitterrad` | Jitter Radius | Float | The radius in meters for jitter reduction. Any jitter beyond this radius is clamped to the radius. |
| `maxdevrad` | Max Deviation Radius | Float | The maximum radius in meters that filtered positions are allowed to deviate from raw data. Filtered values that would be more than this radius from the raw data are clamped at this distance, in the... |
| `rotationsmoothing` | Rotation Smoothing | Float | Activates Kinect's smoothing algorithm for rotations. As with joint smoothing above, higher levels of smoothing will introduce more latency. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP kinectCHOP operator
kinectchop_op = op('kinectchop1')

# Get/set parameters
freq_value = kinectchop_op.par.active.eval()
kinectchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
kinectchop_op = op('kinectchop1')
output_op = op('output1')

kinectchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(kinectchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
