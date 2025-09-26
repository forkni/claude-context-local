# SOP alembicSOP

## Overview

The Alembic SOP loads and plays back Alembic file geometry sequences.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | Alembic File | File | The file path to the Alembic file. |
| `objectpath` | Object Path | StrMenu | Specify which geometry object to be loaded. Each geometry object can represent a hierarchies of multiple geometries. It is also possible to choose the "All Objects" option from the list of availabl... |
| `time` | Time | Float | Specify which part of the Alembic samples sequence is loaded. The time unit menu converts the current time units to the selected unit. The available options are Frames, Seconds, and Fraction. |
| `timeunit` | Time Unit | Menu |  |
| `xform` | Transform | Menu | Select which transform is applied if the transform data is available from the input Alembic file. |
| `interp` | Interpolation | Menu | Interpolate between the samples/keyframes in the Alembic file. This parameter only works if the selected geometries are defined as dynamic and the transformation information are available from the ... |
| `straightgpu` | Straight to GPU | Toggle | Load the geometry directly to the GPU. This options is much faster than the default loading to CPU, however you can not use the geometry output to other SOPs or access the geometry data in the SOP ... |
| `compnml` | Compute Normal | Toggle | Creates normals for the input geometry. |
| `loadfile` | Unload | Toggle | Toggling the unload to "on" will unload the file and close it. By setting it to "off", the file will be loaded again. When the file is unloaded it can be overwritten by other applications or deleted. |

## Usage Examples

### Basic Usage

```python
# Access the SOP alembicSOP operator
alembicsop_op = op('alembicsop1')

# Get/set parameters
freq_value = alembicsop_op.par.active.eval()
alembicsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
alembicsop_op = op('alembicsop1')
output_op = op('output1')

alembicsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(alembicsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
