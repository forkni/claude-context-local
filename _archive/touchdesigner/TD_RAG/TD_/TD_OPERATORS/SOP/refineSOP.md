# SOP refineSOP

## Overview

The Refine SOP allows you to increase the number of CVs in any NURBS, Bzier, or polygonal surface or face without changing its shape.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `firstu` | First U | Toggle | Enable or disable the First U controls. |
| `domainu1` | First U | Float | This specifies a starting / ending location to complete the operation. Select this and a parametric U location between 0 and 1. |
| `secondu` | Second U | Toggle | Enable or disable the Second U controls. |
| `domainu2` | Second U | Float | This specifies a starting / ending location to complete the operation. Select this and a parametric U location between 0 and 1. |
| `divsu` | U Divisions | Int | If refining or sub-dividing, this option specifies the number of refines to be performed between First U and Second U. |
| `firstv` | First V | Toggle | Enable or disable the First V controls. |
| `domainv1` | First V | Float | This specifies a starting / ending location to complete the operation. Select this and a parametric V location between 0 and 1. |
| `secondv` | Second V | Toggle | Enable or disable the Second V controls. |
| `domainv2` | Second V | Float | This specifies a starting / ending location to complete the operation. Select this and a parametric V location between 0 and 1. |
| `divsv` | V Divisions | Int | If refining or sub-dividing, this option specifies the number of refines to be performed between First V and Second V. |
| `refineu` | NURB Count U | Int | Number of knots to insert at each location in the U / V basis when refining NURBS. |
| `refinev` | NURB Count V | Int | Number of knots to insert at each location in the U / V basis when refining NURBS. |
| `space` | Spacing | Menu | Specify how to measure along splines / curves. |
| `unrefineu` | NURB Count U |  | Number of knots to remove at each location in the U / V basis if refining NURBS. |
| `unrefinev` | NURB Count V |  | Number of knots to remove at each location in the U / V basis if refining NURBS. |
| `tolu` | Tolerance U | Float | Only remove knots that do change the curve, polygon, or surface by more than this distance. |
| `tolv` | Tolerance V | Float | Only remove knots that do change the curve, polygon, or surface by more than this distance. |
| `subdivspace` | Spacing |  | Subdivide refines a primitive such that the subdivision causes a sharp discontinuity if ever displaced. In essence subdivide is equivalent to refine for polygons and Bziers, since any refinement ca... |

## Usage Examples

### Basic Usage

```python
# Access the SOP refineSOP operator
refinesop_op = op('refinesop1')

# Get/set parameters
freq_value = refinesop_op.par.active.eval()
refinesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
refinesop_op = op('refinesop1')
output_op = op('output1')

refinesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(refinesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
