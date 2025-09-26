# SOP rectangleSOP

## Overview

The Rectangle SOP creates a 4-sided polygon. It is a planar surface.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `orient` | Orientation | Menu | Picks the major plane the rectangle's y-axis orients itself with. Set it to camera if it is to point towards a camera. |
| `camera` | Camera | Object | Specifies which camera to use if Orientation is set to camera. |
| `camz` | Camera Z | Float | Used when using 'Fill Camera View'. Camera Z is an arbitrary distance you specify from the camera. It will move the rectangle so it is this many units away from the camera, then scale the rectangle... |
| `cameraaspect` | Camera Aspect | XY | Specify the aspect ratio of the camera with this parameter and the Restangle SOP's aspect ratio will match. This makes it easy to apply a texture on the rectangle which matches the camera's viewpor... |
| `modifybounds` | Modify Bounds | Toggle | If a SOP is connected to the node's input, then the rectangle will be sized based on the bounding box of that SOP. Enabling Modify Bounds allows the resulting rectangle to be further modified by sc... |
| `size` | Size | XY | Adjusts the size of the rectangle in X and Y. If the size of the rectangle is being chosen from a Camera, or from a connected input SOP, then this parameter behaves as a scale. Otherwise it will se... |
| `t` | Center | XYZ | These X, Y, and Z Values determine where the center of the Rectangle is located. If the position of the rectangle is being chosen from a Camera, or from a connected input SOP, then this parameter b... |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `texture` | Texture Coordinates | Menu | Texture addes (0,1) coordinates to the vertices when set to Face. Creates a rectangle without uv attributes when set to Off. |
| `normals` | Compute Normals | Toggle | Create a normal (N) attribute for this geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP rectangleSOP operator
rectanglesop_op = op('rectanglesop1')

# Get/set parameters
freq_value = rectanglesop_op.par.active.eval()
rectanglesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
rectanglesop_op = op('rectanglesop1')
output_op = op('output1')

rectanglesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(rectanglesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
