# SOP convertSOP

## Overview

The Convert SOP converts geometry from one geometry type to another type.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `fromtype` | From Type | Menu | Determines which geometry by type will be converted. The default is All Types: |
| `totype` | Convert to | Menu | Determines what the above From Type geometry will be converted to. Conversion to Polygons is the default:        Notes:   Not all geometry can be converted to specific types. For example, a triangu... |
| `surftype` | Connectivity | Menu | This option is used to select how the points of the created surface are connected. |
| `lodu` | U | Float | When set to Level of Detail, controls the number of points or CVs that are used in the newly generated geometry depending on the above setting. Converting a NURBS surface into a polygon mesh with a... |
| `lodv` | V | Float | When set to Level of Detail, controls the number of points or CVs that are used in the newly generated geometry depending on the above setting. Converting a NURBS surface into a polygon mesh with a... |
| `lodtrim` | Trim-Curve | Float | The trimmed part of a surface will be converted using this Trim lod (level of detail) instead of using an implicit "1" constant. |
| `divu` | U | Int | When set to Level of Detail, controls the number of points or CVs that are used in the newly generated geometry depending on the above setting. Converting a NURBS surface into a polygon mesh with a... |
| `divv` | V | Int | When set to Level of Detail, controls the number of points or CVs that are used in the newly generated geometry depending on the above setting. Converting a NURBS surface into a polygon mesh with a... |
| `divtrim` | Trim-Curve | Int | The trimmed part of a surface will be converted using this Trim lod (level of detail) instead of using an implicit "1" constant. |
| `orderu` | U Order | Int | When converting to a spline type, this specifies the degree + 1 of the U or V basis function.     Paste Coordinates      From Feature Surfaces - The resulting mesh will have the shape of the paste ... |
| `orderv` | V Order | Int | When converting to a spline type, this specifies the degree + 1 of the U or V basis function.     Paste Coordinates       From Feature Surfaces - The resulting mesh will have the shape of the paste... |
| `new` | Preserve Original | Toggle | When checked, the original geometry will be retained along with the converted geometry. |
| `interphull` | Interpolate Through Hulls | Toggle | This option applies to the conversion between polygonal faces and grids to NURBS and Bzier surfaces and curves. When selected, the resulting curves retain the same topology as the original polygon.... |
| `prtype` | Particle Type | Menu | Selects how the particles are rendered. |

## Usage Examples

### Basic Usage

```python
# Access the SOP convertSOP operator
convertsop_op = op('convertsop1')

# Get/set parameters
freq_value = convertsop_op.par.active.eval()
convertsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
convertsop_op = op('convertsop1')
output_op = op('output1')

convertsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(convertsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
