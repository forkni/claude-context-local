# SOP bridgeSOP

## Overview

The Bridge SOP is useful for skinning trimmed surfaces, holes, creating highly controllable joins between arms and body, branches or tube intersections.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | The Group edit field allows you to enter profile groups for profiles and/or faces to bridge. This is optional if you have regular geometric curves or surfaces, however, you must enter something her... |
| `bridge` | Bridge | Menu | Allows bridging of subgroups of N primitives or patterns of primitives. |
| `inc` | N | Int | Determines the pattern of primitives to bridge using this SOP. |
| `order` | Order | Int | Sets the spline order for both profile extraction and skinning operations. |
| `isodivs` | Min X-Sections | Int | The minimum number of cross-sections in the resulting skin. If you create a high-density surface, TouchDesigner's level of detail may display the surface less smoothly than it actually is. You can ... |
| `frenet` | Use | Menu | Specifies the type of normal to use for computing direction: |
| `circular` | Circular Arc Fillet | Toggle | Tells TouchDesigner to try to generate a round fillet rather than a free-form fillet. Only the sign (positive or negative) of the tangent scales is used; the scale magnitude is ignored when buildin... |
| `rotatet` | Rotate Tangents | Float | The scaling and rotation parameters contain three fields. The rotation fields (degrees) apply further rotation to the tangents, while the scale parameter further scales the tangents. |
| `scalet` | Scale  Tangents | Float | The scaling and rotation parameters contain three fields. The rotation fields (degrees) apply further rotation to the tangents, while the scale parameter further scales the tangents. |
| `curvature` | Use Curvature | Toggle | Takes curvature into consideration as well. |
| `scalec` | Scale Curvatures | Float | Further scaling of the curvature.      Note: If the resulting skin bulges too greatly, you can achieve a smooth resulting transition between surfaces by disabling the Preserve Tangent & Preserve Cu... |
| `sdivs` | Divisions per Span | Int | Number of 2-D points evaluated in each span. |
| `tolerance` | Tolerance | Float | Precision of 2-D fitting algorithm. |
| `csharp` | Preserve Sharp Corners | Toggle | Enables or disables fitting of sharp turns. If cracks appear in the resulting skin, Preserve Sharp Corners is usually a good solution; however, it may add additional knots which can create undesira... |

## Usage Examples

### Basic Usage

```python
# Access the SOP bridgeSOP operator
bridgesop_op = op('bridgesop1')

# Get/set parameters
freq_value = bridgesop_op.par.active.eval()
bridgesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
bridgesop_op = op('bridgesop1')
output_op = op('output1')

bridgesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(bridgesop_op)
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
