# CHOP zedCHOP

## Overview

The ZED CHOP reads positional tracking data from the ZED camera.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When 'On' data is captured from the ZED camera. |
| `zedtop` | ZED TOP | TOP | The name of the primary ZED TOP that is configuring the camera. The primary TOP controls which camera the CHOP receives data from. |
| `cameratransform` | Camera Transform | Toggle | Enables transformation, which returns the position and rotation of the camera. |
| `resetcameratransform` | Camera Transform | Pulse | Zeros out the current camera position, effectively makes the current position the new origin. |
| `planeorientation` | Plane Orientation | Toggle | Enables plane at point, which returns the position of the plane corresponding the UV coordinate. |
| `getplane` | Get Plane | Toggle | Returns the camera position relative to the initial position of the camera. A tx, ty, tz triplet of channels will be output for the position of the camera in meters. An rx, ry, rz triplet will be o... |
| `getplanepulse` | Pulse | Pulse | Instantly returns the camera position relative to the initial position of the camera. |
| `planereferenceframe` | Plane Reference Frame | Menu | Controls if the panel coordinates will be given relative to the camera or the world. |
| `planepointu` | Plane Point U | Float | Sets the U coordinate of the point in the image to extract plane position. |
| `planepointv` | Plane Point V | Float | Sets the V coordinate of the point in the image to extract plane position. |
| `planeposition` | Plane Position | Toggle | Returns tx, ty, and tz position channels of the center of the plane. |
| `planerotation` | Plane Rotation | Toggle | Returns rx, ry, and rz rotation channels for the plane. |
| `planenormal` | Plane Normal | Toggle | Returns nx, ny, and nz normal channels of the plane. |
| `planesize` | Plane Size | Toggle | Returns size of the bounding rectangle of the plane. |
| `bodytracking` | Body Tracking | Menu | Body tracking allows for tracking human skeletons that are found in the video frame. Each mode uses an AI model that will need to be trained one for your GPU. This will take several minutes, but on... |
| `maxbodies` | Max Bodies | Int | The maximum number of bodies that will be tracked. |
| `body3d` | Body 3D | Toggle | Enable to output 3D positions. Rotations will be included if the Joint Mode is set to 'Relative'. |
| `jointmode` | Joint Mode | Menu | Controls if the joint values are given in absolute in scene or relative to each other. |
| `body2d` | Body 2D | Toggle | 2D normalized UV coordinates for each joint, giving their position within the image. |
| `aspectcorrectuv` | Aspect Correct UVs | Toggle | Apply a correct to the UVs so they as aspect correct. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP zedCHOP operator
zedchop_op = op('zedchop1')

# Get/set parameters
freq_value = zedchop_op.par.active.eval()
zedchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
zedchop_op = op('zedchop1')
output_op = op('output1')

zedchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(zedchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
