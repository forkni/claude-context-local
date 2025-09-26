# SOP springSOP

## Overview

The Spring SOP deforms and moves the input geometry using spring "forces" on the edges of polygons and on masses attached to each point.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `timepreroll` | Preroll Time | Float | How many seconds of the simulation to bypass, after the reset time is reached. For example, if you put the number 33 into this field (and reset is at $TSTART), frame one will show the simulation th... |
| `timeinc` | Time Inc | Float | The Time Inc parameter determines how often to cook the SOP. By default, this parameter is set to 1/$FPS. This means that the SOP will cook once for every frame. When complex dynamics are involved,... |
| `accurate` | Accurate Moves | Toggle | This option makes the nodes move more accurately between frames by calculating their trajectories for fractional frame values. |
| `attractmode` | Attractor Use | Menu | Describes how attractor points are assigned to each particle. |
| `reset` | Reset | Toggle | While On resets the spring effect of the SOP. |
| `resetpulse` | Reset Pulse | Pulse | Instantly reset the spring effect. |
| `external` | External Force | XYZ | Forces of gravity acting on the points. When drag is zero, the points can accelerate with no limit on their speed. |
| `wind` | Wind | XYZ | Wind forces acting on the points. Similar to external force. Using wind (and no other forces, such as turbulence), the points will not exceed the wind velocity. |
| `turb` | Turbulence | XYZ | The amplitude of turbulent (chaotic) forces along each axis. Use positive values, if any. |
| `period` | Turb Period | Float | A small period means that the turbulence varies quickly over a small area, while a larger value will cause points close to each other to be affected similarly. |
| `seed` | Seed | Int | Random number seed for the simulation. |
| `fixed` | Fixed Points | StrMenu | This is a point group. All points in the point group will remain unaffected by the forces. Also see the Group SOP for notes on how to specify point ranges. |
| `revertfixed` | Fixed Points go to Source Positions | Toggle | Determines whether or not points in the Fixed Points group should be moved to the positions of the corresponding points in the Source geometry. |
| `copygroups` | Copy Groups from Source | Toggle | Determines if the Spring SOP should copy groups from the Source geometry at each frame. This lets you specify the name of an animating group in the Fixed Points field, and the contents of this grou... |
| `domass` | Add Mass Attribute | Toggle | When selected, the Mass is computed for the deforming geometry. |
| `mass` | Mass | Float | Mass of each point. Heavier points take longer to get into motion, and longer to stop. |
| `dodrag` | Add Drag Attribute | Toggle | When selected, the geometry is deformed by the Drag attribute. |
| `drag` | Drag | Float | Drag of each point. |
| `springbehavior` | Spring Behavior | Menu | How the springs will behave: |
| `springk` | Spring Constant | Float | The spring constant. How tight the springs are. Increase this value to make the springs tighter and thus make the object more rigid. As this number becomes higher, the springs can oscillate out of ... |
| `tension` | Initial Tension | Float | The Initial k constant of the geometry before being deformed by the spring operation. |
| `limitpos` | + Limit Plane | XYZ | The points will bounce off the limit planes when it reaches them. The six limit plane fields define a bounding cube. The default settings are one thousand units away, which is very large. Reduce th... |
| `limitneg` | - Limit Plane | XYZ | The points will bounce off the limit planes when it reaches them. The six limit plane fields define a bounding cube. The default settings are one thousand units away, which is very large. Reduce th... |
| `hit` | Hit Behavior | Menu | Control over what happens when the geometry hits either the six collision planes or the collision object. The options are: |
| `gaintan` | Gain Tangent | Float | Friction parameters which can be regarded as energy-loss upon collision. The first parameter affects the energy loss (gain) perpendicular to the surface. 0 means all energy (velocity) is lost, 1 me... |
| `gainnorm` | Gain Normal | Float | Friction parameters which can be regarded as energy-loss upon collision. The first parameter affects the energy loss (gain) perpendicular to the surface. 0 means all energy (velocity) is lost, 1 me... |

## Usage Examples

### Basic Usage

```python
# Access the SOP springSOP operator
springsop_op = op('springsop1')

# Get/set parameters
freq_value = springsop_op.par.active.eval()
springsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
springsop_op = op('springsop1')
output_op = op('output1')

springsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(springsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
