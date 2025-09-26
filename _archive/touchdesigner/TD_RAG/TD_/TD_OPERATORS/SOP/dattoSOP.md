# SOP dattoSOP

## Overview

The DAT to SOP can be used to create geometry from DAT tables, or if a SOP input is specified, to modify attributes on existing geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `pointsdat` | Points DAT | DAT | DAT with point data. The optional index indicates the point number, if none is specified, row number will be used. Attributes can be specified in attribute_name(attribute_index). If there are no na... |
| `verticesdat` | Vertices DAT | DAT | DAT with vertex data.  index indicates the primitive number and vindex the vertex number in that primitive.  Attributes are specified in the same manner as for points.  ample vertex data:          ... |
| `primsdat` | Primitives DAT | DAT | DAT with primitive data. The optional index indicates the primitive number, if none is specified, row number will be used. Column headings are required; vertices list the point numbers in order, cl... |
| `detaildat` | Detail DAT | DAT | DAT with detail data. Attribute names are specified on the first row and attribute data on the second row. Sample detail data:                    pCaptPath  pCaptData(0) pCaptData(1) pCaptData(2) .... |
| `merge` | Merge | Menu | Specify whether to merge point data or primitive data. This parameter is only enabled when there is an input connected to the SOP. |
| `float` | Add Float Attributes | StrMenu | Add a non-standard attribute specified in the point or primitive DAT as a float. |
| `int` | Add Int Attributes | StrMenu | Add a non-standard attribute specified in the point or primitive DAT as an int. It will not be added if it has already been specified in the Float attributes. |
| `string` | Add String Attributes | StrMenu | Add a non-standard attribute specified in the point or primitive DAT as a string. It will not be added if it has already been specified in the Float or Int attributes. |
| `build` | Build | Menu | Specifies how to build geometry. |
| `n` | N | Int | Number of points used for building primitives. |
| `closed` | Closed U | Toggle | Closed curves in U. |
| `closedv` | Closed V | Toggle | Closed curves in V. |
| `connect` | Connectivity | Menu | Connectivity of polygons. |
| `prtype` | Particle Type | Menu | When creating a particle system, specify to render the particles as lines or point sprites. |

## Usage Examples

### Basic Usage

```python
# Access the SOP dattoSOP operator
dattosop_op = op('dattosop1')

# Get/set parameters
freq_value = dattosop_op.par.active.eval()
dattosop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
dattosop_op = op('dattosop1')
output_op = op('output1')

dattosop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(dattosop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
