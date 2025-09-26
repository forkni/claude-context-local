# SOP forceSOP

## Overview

The Force SOP adds force attributes to the input metaball field that is used by either Particle SOP or Spring SOP as attractor or repulsion force fields.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `doradial` | Radial Force | Toggle | When checked, triggers a force towards or away from the centre of the metaball field, depending on the value of the force. |
| `radial` | Force | Float | When Radial Force is checked, this controls the strength of the Radial Force field. |
| `doaxis` | Directional Force | Toggle | When checked, enables all parameters below to allow control of specific force attributes. |
| `dir` | Direction | XYZ | When Directional Force is checked, determines the direction vector axis, and activates forces along the directional vector for the directional forces below. |
| `axial` | Axial Force | Float | When Directional Force is checked, controls the force along the primary axis. Increasing this value will cause the particles to move up the primary axis of the metaball field as defined by the dire... |
| `vortex` | Vortex Force | Float | When Directional Force is checked, this field controls the amount of twist particles are given around the primary axis. Positive values cause the particles to spin clockwise, negative values cause ... |
| `spiral` | Spiral Force | Float | Controls the attraction/repulsion force perpendicular to the primary axis (Direction field). Values greater than 0 will cause the points to be drawn toward the primary axis. Values less than 0 push... |

## Usage Examples

### Basic Usage

```python
# Access the SOP forceSOP operator
forcesop_op = op('forcesop1')

# Get/set parameters
freq_value = forcesop_op.par.active.eval()
forcesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
forcesop_op = op('forcesop1')
output_op = op('output1')

forcesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(forcesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **7** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
