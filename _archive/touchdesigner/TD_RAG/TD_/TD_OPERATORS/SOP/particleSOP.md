# SOP particleSOP

## Overview

The Particle SOP is used for creating and controlling motion of "particles" for particle systems simulations.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sourcegrp` | Source Group | StrMenu | Limit the particle emission to the points found in the specified point groups. |
| `prtype` | Particle Type | Menu | Selects how the particles are rendered. |
| `behave` | Behavior | Menu | Select between emitting particles from the geometry's points or deforming the original geometry using the Particle SOP's behavior. |
| `normals` | Compute Normals | Toggle | Creates normals on the geometry.  Only used when Behaviour is set to Modify Source Geometry. |
| `ptreuse` | Point Reuse | Menu | Decide how the internal memory for points is reused when a point needs to be created or when a point dies. |
| `timepreroll` | Preroll Time | Float | How many seconds of the simulation to bypass, after the reset time is reached. For example, if you put the number 33 into this field (and reset is at Tstart), frame one will show the simulation tha... |
| `timeinc` | Time Inc | Float | The Time Inc parameter determines how often to cook the SOP. By default, this parameter is set to 1/me.time.rate. This means that the SOP will cook once for every frame. When complex dynamics are i... |
| `maxsteps` | Max Steps | Int | Limits how far back in time TouchDesigner calculates particle positions for proper interactions.  If frame rates are slow this computation back in time can become high, this parameter limits that e... |
| `jitter` | Jitter Births | Toggle | This allows you to jitter the location pixels of each particle as they are born. |
| `accurate` | Accurate Moves | Toggle | This option makes the particles move more accurately between frames by calculating their trajectories for fractional frame values. |
| `rmunused` | Remove Unused Points | Toggle | Removes all unused points from the input geometry. This is provided as an explicit option instead of automatically because it saves the time needed to purge the points from memory during the simula... |
| `attractmode` | Attractor Use | Menu | Select which mode of attraction to use for Surface Attractors. |
| `reset` | Reset | Toggle | When On the particle system is held in a reset state and does not emit particles. |
| `resetpulse` | Reset Pulse | Pulse | Instantly reset the particle system to its starting state. |
| `external` | External Force | XYZ | Forces of gravity acting on the particles. When drag is zero, the particles can accelerate with no limit on their speed. |
| `wind` | Wind | XYZ | Wind forces acting on the particles. Similar to External Force. Using Wind (and no other forces, such as Turbulence), the particles will not exceed the wind velocity.      ====Discussion - Wind vs ... |
| `turb` | Turbulence | XYZ | The amplitude of turbulent (chaotic) forces along each axis. Use positive values, if any. |
| `period` | Turb Period | Float | A small period means that the turbulence varies quickly over a small area, while a larger value will cause points close to each other to be affected similarly. |
| `seed` | Seed | Int | Random number seed for the particle simulation. |
| `doid` | Add Particle ID | Toggle | Adds an ID number to each particle as it is born. Note: New attributes only appear once the particle system is reset via the reset parameter or loads for first time. |
| `domass` | Add Mass Attribute | Toggle | When selected, calculates the mass of the particle, as specified in the Mass field. |
| `mass` | Mass | Float | The relative mass of each particle. Heavier particles take longer to start moving, and longer to slow down. |
| `dodrag` | Add Drag Attribute | Toggle | When selected, calculates the drag coefficient of the particle, as entered in the Drag field. |
| `drag` | Drag | Float | Drag of each particle. |
| `birth` | Birth | Float | The number of particles born each second. Particles are not released in clusters. They are born at random times during the first frame of their existence. Their birth time is set randomly during th... |
| `life` | Life Expect | Float | How long each particle will exist, in seconds. The default is 3 seconds. You may want to adjust this number based on the length of your animation. |
| `lifevar` | Life Variance | Float | Variance of a particle's life expectancy in seconds. If life expectancy is one second, and the variance is zero seconds, each particle will live exactly one second. If variance is set to 0.5, then ... |
| `alpha` | Alpha Speed | Float | As a particle goes faster, it should become more transparent. The Alpha Speed parameter defaults to 0, which doesn't change alpha as the speed increases. A typical value of 0.5 causes the particle ... |
| `subattract` | Surface Attraction | Float | Gives control over how much particles are attracted towards the Particle SOP's 4th input surface attractor. |
| `birthcount` | Birth Count | Float | Specifies the number of particles created when the Birth pulse parameter is hit. |
| `birthpulse` | Birth | Pulse | Manually create n particles when pulsed. The number of particles created is controlled by the Birth Count parameter. |
| `limitpos` | + Limit Plane | XYZ | The particles will die or bounce off the limit planes when it reaches them. The six limit plane fields define a bounding cube. The default settings are 1000 units away, which is very large. Reduce ... |
| `limitneg` | - Limit Plane | XYZ | The particles will die or bounce off the limit planes when it reaches them. The six limit plane fields define a bounding cube. The default settings are 1000 units away, which is very large. Reduce ... |
| `hit` | Hit Behavior | Menu | Control over what happens when a particle hits either the six collision planes or the collide object. The options are: |
| `gaintan` | Gain Tangent | Float | Friction parameters which can be regarded as energy loss upon collision. The first parameter affects the energy loss (gain) perpendicular to the surface. 0 means all energy (velocity) is lost, 1 me... |
| `gainnorm` | Gain Normal | Float | Friction parameters which can be regarded as energy loss upon collision. The first parameter affects the energy loss (gain) perpendicular to the surface. 0 means all energy (velocity) is lost, 1 me... |
| `splittype` | Split | Menu | Select if the particle will split and under what conditions. |
| `split` | Min/Max Splits | Int | When a particle splits, it splits into a number of other particles. The number of particles is randomly set between this range. |
| `splitvel` | Split Velocity | XYZ | Each split particle is given this base velocity. |
| `splitvar` | Velocity Variance | XYZ | This is a random amount that is added to the split velocity. When creating fireworks, the variance is large while the velocity is low. When rendering raindrops splashing, the split velocity is larg... |

## Usage Examples

### Basic Usage

```python
# Access the SOP particleSOP operator
particlesop_op = op('particlesop1')

# Get/set parameters
freq_value = particlesop_op.par.active.eval()
particlesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
particlesop_op = op('particlesop1')
output_op = op('output1')

particlesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(particlesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **40** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
