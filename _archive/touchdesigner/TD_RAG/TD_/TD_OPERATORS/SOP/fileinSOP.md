# SOP fileinSOP

## Overview

The File In SOP allows you to read a geometry file that may have been previously created in the Model Editor, output geometry from a SOP, or generated from other software such as Houdini.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | Geometry File | File | Contains the full pathname of the geometry file to be read in.   Some of the geometry formats that can be read:     TouchDesigner : .tog   Houdini : .classic, .bhclassic  Common : .obj |
| `flipfacing` | Flip Primitive Faces | Toggle | Flips the primitive faces of the geometry. |
| `normals` | Compute Normals if None Exist | Toggle | Creates normals if the geometry does not have them. |
| `refresh` | Refresh | Toggle | Reload the file when this parameter is set to On. |
| `refreshpulse` | Refresh Pulse | Pulse | Instantly reload the file from disk. |

## Usage Examples

### Basic Usage

```python
# Access the SOP fileinSOP operator
fileinsop_op = op('fileinsop1')

# Get/set parameters
freq_value = fileinsop_op.par.active.eval()
fileinsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fileinsop_op = op('fileinsop1')
output_op = op('output1')

fileinsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fileinsop_op)
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
