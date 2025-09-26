# COMP flexsolverCOMP

## Overview

The Nvidia Flex Solver COMP is a physics solver COMP similar to the Bullet Solver COMP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `actors` | Actors | OBJ | The Actor COMPs to include in the simulation. These actors cannot already be a part of another Solver COMP. |
| `forces` | Global Forces | OBJ | The Force COMPs to include in the simulation. Only force fields are supported in Flex. |
| `gravity` | Gravitational Acceleration | XYZ | Gravity applied to all actors in the simulation in m/s^2. Gravity is applied to actors irrespective of their mass. |
| `init` | Initialize Sim | Pulse | Reset all bodies to their initial state (ie. position, orientation, velocity). This will not begin stepping through the simulation, it will only initialize. |
| `start` | Start Sim | Pulse | Initialize the simulation and run it (begin stepping). |
| `play` | Play | Toggle | Play the simulation. Will step through the simulation when toggled on, but will be paused when toggled off. |
| `rate` | Sample Rate | Float | The sample rate of the simulation. The sample rate affects the timestep, which is 1/rate |
| `preroll` | Pre-Roll | Toggle | Enables simulation pre-roll. Pre-roll can used to step forward the simulation to a desired start state. Pre-roll will happen during the initialization phase. To get info on the state of pre-roll, s... |
| `prerolltime` | Pre-Roll Simulation Time (Sec) | Float | The time in seconds to step forward the simulation before start. |
| `prerollstep` | Pre-Roll Steps per Frame | Int | The amount of steps to take per TouchDesigner frame during pre-roll. Eg. If pre-roll simulation time is 1 second and pre-roll step is 2 then it will take 0.5 seconds to pre-roll. |
| `showpreroll` | Show Pre-Roll | Toggle | When enabled the results of the pre-roll will be shown in the Actor COMP (ie. have their transforms updated). When disabled, the Actor COMPs will remain in their initial state until pre-roll is com... |
| `substeps` | Number of Substeps | Int | Number of substeps to take during one step of the simulation. |
| `iterations` | Number of Iterations | Int | Number of iterations in each substep. |
| `alwayssim` | Always Simulate | Toggle | When enabled the simulation will always step forward. |
| `bounds` | Enable Boundaries | Toggle | Enable simulation boundaries. These can either be set through a bounding box or individual planes. |
| `boundmode` | Boundary Mode | Menu | Use either a Bounding Box SOP specified below or individual planes (also specified below) to set the boundaries. |
| `bbox` | Bounding Box SOP | SOP | The SOP used to calculate the bounding box. |
| `plane` | Plane | Sequence | Sequence of planes to add to the solver |
| `plane0r` | Rotation | XYZ | Rotate the default plane. Default plane is a +Z XY plane (same as Grid SOP). |
| `plane0t` | Translation | XYZ | Translate the default plane. Default plane is a +Z XY plane (same as Grid SOP). |
| `radius` | Particle Radius | XYZ | Radius of the particles in the simulation. Note: This is used by all Actor's in the simulation. |
| `dfriction` | Dynamic Friction | XYZ | The force of friction between a moving particle and a static shape. |
| `sfriction` | Static Friction | XYZ | The force of friction between a non-moving particle and a static shape. |
| `pfriction` | Particle Friction | XYZ | Dynamic friction between particles. |
| `rest` | Restitution | XYZ | The coefficient of restitution for particles. |
| `adhesion` | Adhesion | XYZ | How strongly particles stick to surfaces/shapes they hit. |
| `sleepthresh` | Sleep Threshold | XYZ | Particles with a velocity less than this threshold will be considered non-moving. |
| `clampspeed` | Clamp Speed | Toggle | Enable speed clamping. |
| `maxspeed` | Max Speed | XYZ | The magnitude of particle velocity will be clamped to this value. |
| `clampaccel` | Clamp Acceleration | Toggle | Enable acceleration clamping. |
| `maxaccel` | Max Acceleration | XYZ | The magnitude of particle acceleration will be clamped to this value. |
| `diss` | Dissipation | XYZ | Damps particle velocity based on how many particle contacts it has. |
| `damping` | Damping | XYZ | Viscous drag force. Applies a force proportional and opposite to the particle velocity. |
| `cohesion` | Cohesion | XYZ | Controls how strongles particles hold to each other. |
| `surftension` | Surface Tension | XYZ | Controls how strongly particles attempt to minimize surface area. |
| `viscosity` | Viscosity | XYZ | Smoothes particle velocities using XSPH viscosity. |
| `buoyancy` | Buoyancy | XYZ | A gravity scale for fluid particles. |
| `colldist` | Collision Distance | XYZ | The distance particles maintain when colliding against shapes. |
| `scollmargin` | Shape Collision Margin | XYZ | Increases the particle radius during contact finding against shapes. |
| `smoothing` | Smoothing | XYZ | Controls the strength of Laplacian smoothing in particles for rendering. |
| `vortconf` | Vorticity Confinement | XYZ | Increases vorticity by applying rotational forces to particles. |
| `anisoscale` | Anisotropy Scale | XYZ | Control how much anisotropys is present in resulting ellipsoids for rendering. |
| `anisomin` | Anisotropy Min | XYZ | Clamp the anisotropy scale to this fraction of the radius. |
| `anisomax` | Anisotropy Max | XYZ | Clamp the anisotropy scale to this fraction of the radius. |
| `diffuse` | Enable Diffuse Particles | XYZ | When enabled, diffuse particles will be created in the simulation. Diffuse particle position/velocity can be fetched using the Nvidia Flex TOP. |
| `maxdiffuse` | Max Diffuse Particles | XYZ | The maximum number of diffuse particles that can exist in a simulation simultaneously. Note: if the maximum is too low or the diffuse lifetime too high, then the simulation may not be able to creat... |
| `diffthresh` | Diffuse Threshold | XYZ | Particles with kinetic energy + divergence above this threshold will spawn new diffuse particles |
| `diffbuoy` | Diffuse Buoyancy | XYZ | A gravity scale for diffuse particles. |
| `diffdrag` | Diffuse Drag | XYZ | Scales the force that diffuse particles receive in direction of neighbouring fluid particles. |
| `diffball` | Diffuse Ballistic | XYZ | The number of neighbours below which a diffuse particle is considered ballistic. |
| `difflife` | Diffuse Lifetime | XYZ | Time in seconds that a diffuse particle will live for after being spawned. |
| `xord` | Transform Order | Menu | This allows you to specify the order in which the changes to your Component will take place. Changing the Transform Order will change where things go much the same way as going a block and turning ... |
| `rord` | Rotate Order | Menu | This allows you to set the transform order for the Component's rotations. As with transform order (above), changing the order in which the Component's rotations take place will alter the Component'... |
| `t` | Translate | XYZ | This allows you to specify the amount of movement along any of the three axes; the amount, in degrees, of rotation around any of the three axes; and a non-uniform scaling along the three axes. As a... |
| `r` | Rotate | XYZ | Theis specifies the amount of movement along any of the three axes; the amount, in degrees, of rotation around any of the three axes; and a non-uniform scaling along the three axes. As an alternati... |
| `s` | Scale | XYZ | This specifies the amount of movement along any of the three axes; the amount, in degrees, of rotation around any of the three axes; and a non-uniform scaling along the three axes. As an alternativ... |
| `p` | Pivot | XYZ | The Pivot point edit fields allow you to define the point about which a Component scales and rotates. Altering the pivot point of a Component produces different results depending on the transformat... |
| `scale` | Uniform Scale | Float | This field allows you to change the size of an Component uniformly along the three axes.      Note: Scaling a camera's channels is not generally recommended. However, should you decide to do so, th... |
| `parentxformsrc` | Parent Transform Source | Object | Select what position is used as the transform source for this obejct. Can be one of "Parent (Hierarchy)", "Specify Parent Object", or "World Origin". |
| `parentobject` | Parent Object | Object | Allows the location of the object to be constrained to any other object whose path is specified in this parameter. |
| `lookat` | Look At | Object | Allows you to orient this Component by naming another 3D Component you would like it to Look At, or point to. Once you have designated this Component to look at, it will continue to face that Compo... |
| `forwarddir` | Forward Direction | Menu | Sets which axis and direction is considered the forward direction. |
| `lookup` | Look At Up Vector | StrMenu | When specifying a Look At, it is possible to specify an up vector for the lookat. Without using an up vector, it is possible to get poor animation when the lookat Component, for example, passes thr... |
| `pathsop` | Path SOP | SOP | Names the SOP that functions as the path you want this Component to move along. For instance, you can name a SOP that provides a path for the camera to follow. |
| `roll` | Roll | Float | Using the angle control you can specify a Component's rotation as it animates along the path. |
| `pos` | Position | Float | This parameter lets you specify the Position of the Component along the path. The values you can enter for this parameter range from 0 to 1, where 0 equals the starting point and 1 equals the end p... |
| `pathorient` | Orient along Path | Toggle | If this option is selected, the Component will be oriented along the path. The positive Z axis of the Component will be pointing down the path. |
| `up` | Orient Up Vector | XYZ | When orienting a Component, the Up Vector is used to determine where the positive Y axis points. |
| `bank` | Auto-Bank Factor | Float | The Auto-Bank Factor rolls the Component based on the curvature of the path at its current position. To turn off auto-banking, set the bank scale to 0. |
| `pxform` | Apply Pre-Transform | Toggle | Enables the transformation on this page. |
| `pxord` | Transform Order | Menu | Refer to the documentation on Xform page for more information. |
| `prord` | Rotate Order | Menu | Refer to the documentation on Xform page for more information. |
| `pt` | Translate | XYZ | Refer to the documentation on Xform page for more information. |
| `pr` | Rotate | XYZ | Refer to the documentation on Xform page for more information. |
| `ps` | Scale | XYZ | Refer to the documentation on Xform page for more information. |
| `pp` | Pivot | XYZ | Refer to the documentation on Xform page for more information. |
| `pscale` | Uniform Scale | XYZ | Refer to the documentation on Xform page for more information. |
| `preset` | Reset Transform | Pulse | This button will reset this page's transform so it has no translate/rotate/scale. |
| `pcommit` | Commit to Main Transform | Pulse | This button will copy the transform from this page to the main Xform page, and reset this page's transform. |
| `xformmatrixop` | Xform Matrix/CHOP/DAT | OP | This parameter can be used to transform using a 4x4 matrix directly. For information on ways to specify a matrix directly, refer to the Matrix Parameters page. This transform will be applied after ... |
| `material` | Material | MAT | Selects a MAT to apply to the geometry inside. |
| `render` | Render | Toggle | Whether the Component's geometry is visible in the Render TOP. This parameter works in conjunction (logical AND) with the Component's Render Flag. |
| `drawpriority` | Draw Priority | Float | Determines the order in which the Components are drawn. Smaller values get drawn after larger values. The value is compared with other Components in the same parent Component, or if the Component i... |
| `pickpriority` | Pick Priority | Float | When using a Render Pick CHOP or a Render Pick DAT, there is an option to have a 'Search Area'. If multiple objects are found within the search area, the pick priority can be used to select one obj... |
| `wcolor` | Wireframe Color | RGB | Use the R, G, and B fields to set the Component's color when displayed in wireframe shading mode. |
| `lightmask` | Light Mask | OBJ | By default all lights used in the Render TOP will affect geometry renderer. This parameter can be used to specify a sub-set of lights to be used for this particular geometry. The lights must be lis... |
| `ext` | Extension | Sequence | Sequence of info for creating extensions on this component |
| `reinitextensions` | Re-Init Extensions | Pulse | Recompile all extension objects. Normally extension objects are compiled only when they are referenced and their definitions have changed. |
| `parentshortcut` | Parent Shortcut | COMP | Specifies a name you can use anywhere inside the component as the path to that component. See Parent Shortcut. |
| `opshortcut` | Global OP Shortcut | COMP | Specifies a name you can use anywhere at all as the path to that component. See Global OP Shortcut. |
| `iop` | Internal OP | Sequence | Sequence header for internal operators. |
| `nodeview` | Node View | Menu | Determines what is displayed in the node viewer, also known as the Node Viewer. Some options will not be available depending on the Component type (Object Component, Panel Component, Misc.) |
| `opviewer` | Operator Viewer | OP | Select which operator's node viewer to use when the Node View parameter above is set to Operator Viewer. |
| `enablecloning` | Enable Cloning | Toggle | Control if the OP should be actively cloneing. Turning this off causes this node to stop cloning it's 'Clone Master'. |
| `enablecloningpulse` | Enable Cloning Pulse | Pulse | Instantaneously clone the contents. |
| `clone` | Clone Master | COMP | Path to a component used as the Master Clone. |
| `loadondemand` | Load on Demand | Toggle | Loads the component into memory only when required. Good to use for components that are not always used in the project. |
| `enableexternaltox` | Enable External .tox | Toggle | When on (default), the external .tox file will be loaded when the .toe starts and the contents of the COMP will match that of the external .tox. This can be turned off to avoid loading from the ref... |
| `enableexternaltoxpulse` | Enable External .tox Pulse | Pulse | This button will re-load from the external .tox file (if present). |
| `externaltox` | External .tox Path | File | Path to a .tox file on disk which will source the component's contents upon start of a .toe. This allows for components to contain networks that can be updated independently. If the .tox file can n... |
| `reloadcustom` | Reload Custom Parameters | Toggle | When this checkbox is enabled, the values of the component's Custom Parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on nod... |
| `reloadbuiltin` | Reload Built-In Parameters | Toggle | When this checkbox is enabled, the values of the component's built-in parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on n... |
| `savebackup` | Save Backup of External | Toggle | When this checkbox is enabled, a backup copy of the component specified by the External .tox parameter is saved in the .toe file.  This backup copy will be used if the External .tox can not be foun... |
| `subcompname` | Sub-Component to Load | Str | When loading from an External .tox file, this option allows you to reach into the .tox and pull out a COMP and make that the top-level COMP, ignoring everything else in the file (except for the con... |
| `relpath` | Relative File Path Behavior | Menu | Set whether the child file paths within this COMP are relative to the .toe itself or the .tox, or inherit from parent. |

## Usage Examples

### Basic Usage

```python
# Access the COMP flexsolverCOMP operator
flexsolvercomp_op = op('flexsolvercomp1')

# Get/set parameters
freq_value = flexsolvercomp_op.par.active.eval()
flexsolvercomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
flexsolvercomp_op = op('flexsolvercomp1')
output_op = op('output1')

flexsolvercomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(flexsolvercomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **105** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
