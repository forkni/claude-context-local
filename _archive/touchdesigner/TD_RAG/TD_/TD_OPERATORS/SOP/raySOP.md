# SOP raySOP

## Overview

The Ray SOP is used to project one surface onto another.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `method` | Method | Menu | Select the method of projection for the Ray SOP. |
| `dotrans` | Transform Points | Toggle | If selected, it will transform the input points as defined below. Leave this off when only interested in updating the source point attributes. |
| `lookfar` | Intersect Farthest Surface | Toggle | If selected, this option allows the user to choose between intersecting with the closest intersecting object or the furthest. See example, below. |
| `normal` | Point Intersection Normal | Menu | If selected, updates each point in the source geometry with the normal at the collision surface it intersects with. If the point doesn't intersect at the collision surface, a normal of (0,0,0) is u... |
| `bounces` | Bounces | Int | The number of times to bounce the ray off of the collision surface before creating the output position. For example, if bounces is set to 1, then the point will be projected onto surface at the fir... |
| `bouncegeo` | Save Bounce Geometry | Toggle | When enabled, the projected geometry will be saved each time the projected ray bounces off a surface resulting in multiple copies of the input geometry. See the second Ray snippet for an example. |
| `putdist` | Point Intersection Distance | Toggle | If selected, updates each point intersected with the distance to the collision surface. If the point doesn't intersect at the collision surface a distance of 0 is used. This value is placed in the ... |
| `scale` | Scale | Float | A value of zero will leave the input point unaffected. A value of one will land the point on the intersection surface. Negative values and values > 1 are also valid. |
| `lift` | Lift | Float | This value further offsets the surface input by offsetting it in the direction of its normal. |
| `sample` | Sample | Int | This value determines the number of rays sent per point. If greater than one, the remaining rays are perturbed randomly, and averaged. |
| `jitter` | Jitter Scale | Float | Controls the perturbation of the extra sample rays. |
| `seed` | Seed | Int | Allows a different random sequence at higher sampling rates. |
| `newgrp` | Create Point Group | Toggle | If selected, it will create a point group containing all the points which were intersected successfully. |
| `hitgrp` | Ray Hit Group | Str | Specifies the name of the above point group. |

## Usage Examples

### Basic Usage

```python
# Access the SOP raySOP operator
raysop_op = op('raysop1')

# Get/set parameters
freq_value = raysop_op.par.active.eval()
raysop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
raysop_op = op('raysop1')
output_op = op('output1')

raysop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(raysop_op)
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
