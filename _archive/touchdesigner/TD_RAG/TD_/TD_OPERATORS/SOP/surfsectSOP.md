# SOP surfsectSOP

## Overview

The Surfsect SOP performs boolean operations with NURBS and Bezier surfaces, or only generates profiles where the surfaces intersect.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `groupa` | Group A | StrMenu | Subset of NURBS and Bezier surfaces. Accepts patterns, as described in Pattern Matching. |
| `groupb` | Group B | StrMenu | Subset of NURBS and Bezier surfaces to intersect with A. Accepts patterns, as described in Pattern Matching. |
| `tol3d` | 3D Tolerance | Float | World space precision of the intersection. |
| `tol2d` | 2D Tolerance | Float | Domain precision of the intersection. |
| `step` | Marching Steps | Int | Number of steps for tracing each profile span. |
| `boolop` | Operation | Menu | Select from the following operations: Union, Intersect, A-B, B-A, or User-defined.      If the Operation is set to User-defined, the following options become available: |
| `insidea` | Keep Inside A | Toggle | Preserve the inside sections of the A surfaces. |
| `insideb` | Keep Inside B | Toggle | Preserve the inside sections of the B surfaces. |
| `outsidea` | Keep Outside A | Toggle | Preserve the outside sections of the A surfaces. |
| `outsideb` | Keep Outside B | Toggle | Preserve the outside sections of the B surfaces. |
| `target` | Target | Menu | Which surface to output profiles for: A, B, or both. |
| `creategroupa` | A Profiles Group | Toggle | Place the A profiles in a user-defined group. |
| `profilesa` |  | Str | The name assigned to profile group A. |
| `creategroupb` | B Profiles Group | Toggle | Place the B profiles in a user-defined group. |
| `profilesb` |  | Str | The name assigned to profile group B. |
| `mindholes` | Avoid Already Trimmed-Out Parts | Toggle | Intersect only the visible surface parts and truncate the intersection profile at the trimmed-in surface boundaries. |
| `join` | Join Profiles Created by Multiple Surfaces | Toggle | If a surface has several adjacent profiles caused by its intersection with two or more surfaces, the profiles will be joined into a single curve-on-surface. |

## Usage Examples

### Basic Usage

```python
# Access the SOP surfsectSOP operator
surfsectsop_op = op('surfsectsop1')

# Get/set parameters
freq_value = surfsectsop_op.par.active.eval()
surfsectsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
surfsectsop_op = op('surfsectsop1')
output_op = op('output1')

surfsectsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(surfsectsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
