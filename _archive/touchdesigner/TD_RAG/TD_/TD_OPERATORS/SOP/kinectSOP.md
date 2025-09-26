# SOP kinectSOP

## Overview

The Kinect SOP uses the Kinect v1 sensor to scan and create geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `hwversion` | Hardware Version | Menu | Only Kinect v1 sensors supported at this time. |
| `sensor` | Sensor | StrMenu | Selects which Kinect sensor to use. Only available when using Kinect v1. |
| `skeleton` | Skeleton | Menu | Only used for Kinect 1 devices. Specify whether to track full skeleton or seated skeleton. |
| `neardepthmode` | Near Depth Mode | Toggle | Only used for Kinect 1 devices. Enables near mode which allows camera to see objects as close as 40cm to the camera (instead of the default 80cm). |
| `normals` | Compute Normals | Toggle | Creates normals on the geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP kinectSOP operator
kinectsop_op = op('kinectsop1')

# Get/set parameters
freq_value = kinectsop_op.par.active.eval()
kinectsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
kinectsop_op = op('kinectsop1')
output_op = op('output1')

kinectsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(kinectsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **5** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
