# COMP Pallette:depthProjection Ext

## Overview

The depthProjection component converts a 2D depth map image into a 3D point cloud stored in a floating point texture.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `Depthtype` | Depth Type | Menu | Determines what kind of depth is stored in the source depth image i.e. whether the point cloud is projected in rays from a single camera point, or from the image plane. |
| `Fromrange` | From Range | Float | Used for scaling the point cloud depth. This parameter defines the range of depths in the source image. Depths outside this range are extrapolated. |
| `Torange` | To Range | Float | Determines the output range for the depth values. The range of input values is mapped linearly to the output range and values outside of the range are extrapolated. |
| `Viewanglemethod` | View Angle Method | Menu | Determines how the field of view is defined for the projection. |
| `Fov` | FOV Angle | Float | The field of view measured in degrees when using Horizontal FOV mode. |
| `Focallengths` | Focal Lengths (Fx, Fy) | Float | The normalized focal length values when using the Focal Length view angle method. |
| `Center` | Optical Center (Cx, Cy) | Float | The position of the camera relative to the image plane in normalized values i.e. (0.5, 0.5) assumes the camera point is directly in the center of the image plane. |
| `Help` | Help | Pulse |  |
| `Version` | Version | Str |  |
| `Toxsavebuild` | .tox Save Build | Str |  |

## Usage Examples

### Basic Usage

```python
# Access the COMP Pallette:depthProjection Ext operator
pallettedepthprojection_ext_op = op('pallettedepthprojection_ext1')

# Get/set parameters
freq_value = pallettedepthprojection_ext_op.par.active.eval()
pallettedepthprojection_ext_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pallettedepthprojection_ext_op = op('pallettedepthprojection_ext1')
output_op = op('output1')

pallettedepthprojection_ext_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pallettedepthprojection_ext_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
