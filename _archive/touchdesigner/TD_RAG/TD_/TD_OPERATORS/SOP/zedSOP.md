# SOP zedSOP

## Overview

The ZED SOP uses the ZED to scan and create geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `zedtop` | ZED TOP | TOP | The name of the primary ZED TOP that is configuring the camera. The primary TOP controls which camera the SOP receives data from. |
| `sample` | Sample | Toggle | While enabled the ZED camera samples points in space. Once disabled it will generate the surface from the points, as well as any normal or texture attributes. |
| `reset` | Reset | Toggle | Clears the extracted geometry and resets spatial mapping. |
| `resetpulse` | Reset Pulse | Pulse | Triggers the Reset immediately on button release (button-up). This can be accessed in python using the pulse() method. |
| `preview` | Preview | Menu | Select level of detail of the preview when camera samples. |
| `maxmemory` | Maximum Memory | Int | Sets the maximum memory used for spatial mapping. |
| `resolution` | Resolution | Float | Sets the spatial mapping resolution used by the camera. A smaller resolution creates a detailed geometry and higher resolution keeps only bigger vairiations in geometry. |
| `range` | Range | Float | Sets distance range of objects that will be extracted after spatial mapping from the camera. A smaller depth range will use objects close to the camera and higher depth range will use objects that ... |
| `normals` | Normals | Toggle | When enabled, the extracted geometry will have normals. |
| `texture` | Texture | Toggle | The spatial mapping texture and texture coordinates of the mesh will be created when enabled. The spatial mapping texture can be retrieved using the ZED TOP. |
| `filter` | Filter | Menu | Set the filtering level of the mesh. |
| `consolidatepts` | Consolidate Points | Toggle | When enabled, redundant points that are closed together will be merged. |

## Usage Examples

### Basic Usage

```python
# Access the SOP zedSOP operator
zedsop_op = op('zedsop1')

# Get/set parameters
freq_value = zedsop_op.par.active.eval()
zedsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
zedsop_op = op('zedsop1')
output_op = op('output1')

zedsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(zedsop_op)
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
