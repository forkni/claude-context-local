# SOP latticeSOP

## Overview

The Lattice SOP allows you to create animated deformations of its input geometry by manipulating grids or a subdivided box that encloses the input source's geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Subset of points in the first input to be deformed. Accepts patterns, as described in Pattern Matching. |
| `deformtype` | Deform Type | Menu | Choose if deformation should be done using a regularly spaced lattice or an arbitary point cloud. |
| `divs` | Divisions | Int | Must be set to match the number of divisions in the lattice grid object(s). |
| `kernel` | Kernel Function | StrMenu | Deformation by specifying a Kernal Function and Points makes it easier to deform arbitrary clouds of points, as this makes the topology of the lattice behave more like a metaball rather than as a f... |
| `radius` | Radius | Float | The size of the points capture regions. |

## Usage Examples

### Basic Usage

```python
# Access the SOP latticeSOP operator
latticesop_op = op('latticesop1')

# Get/set parameters
freq_value = latticesop_op.par.active.eval()
latticesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
latticesop_op = op('latticesop1')
output_op = op('output1')

latticesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(latticesop_op)
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
