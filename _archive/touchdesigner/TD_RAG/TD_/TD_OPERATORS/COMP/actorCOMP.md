# COMP actorCOMP

## Overview

An Actor COMP is analogous to a body (or bodies) in a physics system.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `initialize` | Initialize Actor | Pulse | Recreates the collision shapes for all the bodies in the Actor COMP. Also resets all velocities and position to their default state. Initialize Actor should be pulsed when any changes are made to t... |
| `updatecs` | Update Collision Shape | Toggle | If enabled the Actor COMP will automatically update collision shapes. This will occur when the "Collision SOPs" or "Collision Shape" parameters are changes or the underlying SOPs used to create the... |
| `updatecspulse` | Update Collision Shape | Pulse | When clicked this will instantly update the collosion shape. |
| `active` | Active | Toggle | Toggle the actor on/off. If the actor is active, then it will be updated as the simulation progress. However, if it is inactive, then it will be removed from the simulation and no longer collide wi... |
| `kinstate` | Kinematic State | Menu | The kinematic state defines the Actor COMPs ability to move from external forces. If an object is dynamic, then it is moveable in the simulation, but if it static then it is not. |
| `sops` | Collision SOPs | OP | Specifies SOPs or COMPs to use for the collision shape. If a SOP is referenced, then just that SOP will be used for the collision shape. But if a COMP is selected then all SOPs inside of that (recu... |
| `shape` | Collision Shape | Menu | The type of collision shape to make from the selected SOPs. Collision shapes can be viewed using a guide in the Actor COMP's viewer |
| `elltol` | Ellipsoid Tolerance | Float | The tolerance of the minimum volume bounding ellipsoid. In other words, how close to the optimal solution it is. |
| `infinitemass` | Infinite Mass | Toggle | Give the actor infinite mass. If the object is dynamic this will make it unmovable and static. Toggling infinite mass on or off will not require recreation of the collision shape, unlike changing t... |
| `mass` | Mass | Float | The mass in kilograms of the actor. |
| `cuevel` | Cue Velocity | Toggle | Holds the linear and angular velocity and values given by linvel and angvel. The object will still collide with any other bodies in the simulation. |
| `cuevelpulse` | Cue Pulse | Pulse | Pulse the linear and angular velocity to values given by linvel and angvel. This will set the velocity to the given value at the beginning of the next frame. |
| `linvel` | Linear Velocity | XYZ | The initial linear velocity of the actor in m/s. This parameter can also be used to modify an actor's linear velocity during a simulation. Additionally, it is used in conjunction with the "Cue Velo... |
| `angvel` | Angular Velocity | XYZ | The initial angular velocity of the actor in degrees per second in m/s. This parameter can also be used to modify the actor's angular velocity during a simulation. Additionally, it is used in conju... |
| `forces` | Forces | OBJ | A list of local forces, meaning forces (ie. Force COMPs) that will only be applied to this actor. |
| `globalgrav` | Use Global Gravity | Toggle | Toggle for whether to use the Bullet Solver COMP's gravity (global), or its own local gravity. |
| `gravity` | Gravitational Acceleration | XYZ | Actor's local gravity in m/s^2. Will only be applied if the actor is not using the Bullet Solver COMP's global gravity ie. the "Use Global Gravity" parameter above is turned off. |
| `friction` | Friction | Float | The kinetic friction of the actor. It is the resistance between two bodies rubbing/sliding. The overall friction is the product of the two bodies touching. For example, if one body has 0 friction a... |
| `rollfric` | Rolling Friction | Float | The rolling friction of the actor. It is the resistance/drag of one body (such as a sphere or cone) rolling on another. |
| `rest` | Restitution | Float | The coefficient of restitution of the actor. The coefficient of restitution is the ratio of the final to initial relative between two bodies/actors when they collide. In other words, restitution is... |
| `ccd` | Continuous Collision Detection | Toggle | Toggles continuous collision detection on/off for this actor. Typically, collision detection is done discretely, meaning that collision is verified at the beginning/end of a frame. However, if a bo... |
| `dispguide` | Display Guide | Toggle | Toggles on the display for the collision shape in the COMP viewer. |
| `com` | Center of Mass | XYZ | Specifies the center of mass of the collision shape. The center of mass is the point around which the body will rotate. Center of mass can be viewed using a guide in the Actor COMP's viewer. It is ... |
| `bulletfb` | Bullet Feedback CHOP | CHOP | A reference to a CHOP from which to feedback. The Actor COMP will read transformation and velocity data (in the correct format, see Bullet Solver CHOP for more information) from the CHOP, and overw... |
| `tricolldir` | Triangle Collision Direction | Menu |  |
| `flextype` | Flex Type | Menu | The type of dynamic Flex actor. |
| `emit` | Enable Emission | Toggle | When enabled, the Actor COMP will actively emit particles. |
| `emitsize` | Emission Size | XY | The size of the 2D emission grid. The size represents the number of particles on each side of the emission grid. For example, a 2x5 emission size will emit a grid 2 particles wide and 5 particles h... |
| `emitspeed` | Emission Speed | Float | The speed the particles come out of the emitter. |
| `emitmax` | Max Emission Particles | Float | Sets the maximum number of particles in the Actor COMP. Once this number is reached, emission will be done by recycling existing particles in the Actor COMP. |
| `flexposfb` | Position Feedback TOP | TOP | A reference to a TOP to feedback position. The TOP should be encoded with the position data that will be used to override position in the simulation. The texture data will be read to correspond wit... |
| `flexvelfb` | Velocity Feedback TOP | TOP | A reference to a TOP to feedback velocity. The TOP should be encoded with the velocity data that will be used to override velocity in the simulation. The texture data will be read to correspond wit... |
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
| `instancing` | Instancing | Toggle | Turns on instancing for the Geometry Component. |
| `instancecountmode` | Instance Count Mode | Menu | Two modes to determine how many instances will be created. |
| `numinstances` | Num Instances | Int | When using the Manual mode for Instance Count, this parameter set the number of instances. |
| `instanceop` | Default Instance OP | OP | Specify a path to a CHOP or DAT used to transform the instances. Number of samples/rows in this CHOP or DAT determines the number of instances when using the CHOP Length/DAT Num Rows mode for Insta... |
| `instancefirstrow` | First Row is | Menu | What to do with the first row of a table DAT when using DAT rows for Instance Count. |
| `instxord` | Transform Order | Menu | Controls the order the transform operations will be applied to each instance. Refer to the documentation for the Xform page for more details. |
| `instrord` | Rotate Order | Menu | The rotational matrix presented when you click on this option allows you to set the transform order for the Component's rotations. As with transform order (above), changing the order in which the C... |
| `instancetop` | Translate OP | OP | Select a specific operator to get data from for the Translate instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page can... |
| `instanceactive` | Active | StrMenu | Select the data channel that will be used to control which instances are rendered. Only instances with a non-zero value in this channel will be rendered; instances with a zero active channel value ... |
| `instancetx` | Translate X | StrMenu | Select what data to use to translate instances, use the drop-down menu on the right to easily select from the available options. |
| `instancety` | Translate Y | StrMenu | Select what data to use to translate instances, use the drop-down menu on the right to easily select from the available options. |
| `instancetz` | Translate Z | StrMenu | Select what data to use to translate instances, use the drop-down menu on the right to easily select from the available options. |
| `instancerop` | Rotate OP | OP | Select a specific operator to get data from for the Rotate instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page can be... |
| `instancerx` | Rotate X | StrMenu | Select what data to use to rotate instances, use the drop-down menu on the right to easily select from the available options. |
| `instancery` | Rotate Y | StrMenu | Select what data to use to rotate instances, use the drop-down menu on the right to easily select from the available options. |
| `instancerz` | Rotate Z | StrMenu | Select what data to use to rotate instances, use the drop-down menu on the right to easily select from the available options. |
| `instancesop` | Scale OP | OP | Select a specific operator to get data from for the Scale instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page can be ... |
| `instancesx` | Scale X | StrMenu | Select what data to use to scale instances, use the drop-down menu on the right to easily select from the available options. |
| `instancesy` | Scale Y | StrMenu | Select what data to use to scale instances, use the drop-down menu on the right to easily select from the available options. |
| `instancesz` | Scale Z | StrMenu | Select what data to use to scale instances, use the drop-down menu on the right to easily select from the available options. |
| `instancepop` | Pivot OP | OP | Select a specific operator to get data from for the Pivot instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page can be ... |
| `instancepx` | Pivot X | StrMenu | Select what data to use for the pivot of the instances, use the drop-down menu on the right to easily select from the available options. |
| `instancepy` | Pivot Y | StrMenu | Select what data to use for the pivot of the instances, use the drop-down menu on the right to easily select from the available options. |
| `instancepz` | Pivot Z | StrMenu | Select what data to use for the pivot of the instances, use the drop-down menu on the right to easily select from the available options. |
| `instancerottoorder` | Rotate to Vector: Order | Menu | Controls where in the transform equation the Rotate To Vector operation is applied. |
| `instancerottoforward` | Rotate to Vector: Forward Direction | Menu | Determine which axis for the geometry original orientation is considered 'forward'. That is, it'll treat the part of the geometry that is looking down that axis as the front and rotate it so it's a... |
| `instancerottoop` | Rotate to OP | OP | Select a specific operator to get data from for the Rotate to Vector instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter p... |
| `instancerottox` | Rotate to Vector X | StrMenu | Select what data to use to rotate to vector instances, use the drop-down menu on the right to easily select from the available options. |
| `instancerottoy` | Rotate to Vector Y | StrMenu | Select what data to use to rotate to vector instances, use the drop-down menu on the right to easily select from the available options. |
| `instancerottoz` | Rotate to Vector Z | StrMenu | Select what data to use to rotate to vector instances, use the drop-down menu on the right to easily select from the available options. |
| `instancerotupop` | Rotate Up OP | OP | Select a specific operator to get data from for the Rotate Up instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page can... |
| `instancerotupx` | Rotate Up X | StrMenu | Select what data to use to rotate up instances, use the drop-down menu on the right to easily select from the available options. |
| `instancerotupy` | Rotate Up Y | StrMenu | Select what data to use to rotate up instances, use the drop-down menu on the right to easily select from the available options |
| `instancerotupz` | Rotate Up Z | StrMenu | Select what data to use to rotate up instances, use the drop-down menu on the right to easily select from the available options |
| `instanceorder` | Instance Order | Menu | Sets how transforms are applied to the instances. |
| `instancetexmode` | Texture Mode | Menu | Set how the texture coordinates are applied to the instances. |
| `instancetexcoordop` | Tex Coord OP | OP | Select a specific operator to get data from for the Texture Coord instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page... |
| `instanceu` | U | StrMenu | Select what data to apply to texture coordinates of the instances, use the drop-down menu on the right to easily select from the available options. This interacts with the first texture layer uv[0]... |
| `instancev` | V | StrMenu | Select what data to apply to texture coordinates of the instances, use the drop-down menu on the right to easily select from the available options. This interacts with the first texture layer uv[0]... |
| `instancew` | W | StrMenu | Select what data to apply to texture coordinates of the instances, use the drop-down menu on the right to easily select from the available options. This interacts with the first texture layer uv[0]... |
| `instancecolormode` | Color Mode | Menu | Controls how the instance color values interact with the SOPs 'Cd' (diffuse color) attribute. If the SOP doesn't have a 'Cd' attribute, then it will behave as if its 'Cd' is (1, 1, 1, 1). |
| `instancecolorop` | Color OP | OP | Select a specific operator to get data from for the Color instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page can be ... |
| `instancer` | R | StrMenu | Select what data to apply to the diffuse color of the instances, use the drop-down menu on the right to easily select from the available options. These parameters will be combined/replaced with the... |
| `instanceg` | G | StrMenu | Select what data to apply to the diffuse color of the instances, use the drop-down menu on the right to easily select from the available options. These parameters will be combined/replaced with the... |
| `instanceb` | B | StrMenu | Select what data to apply to the diffuse color of the instances, use the drop-down menu on the right to easily select from the available options. These parameters will be combined/replaced with the... |
| `instancea` | A | StrMenu | Select what data to apply to the diffuse color of the instances, use the drop-down menu on the right to easily select from the available options. These parameters will be combined/replaced with the... |
| `instancetexs` | Instance Textures | TOP | Specify the paths one or more TOP containing the textures to use with the instances. Wildcards and pattern matching is supported. |
| `instancetexindexop` | Tex Index OP | OP | Select a specific operator to get data from for the Texture Index instance attribute below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page ... |
| `instancetexindex` | Texture Index | StrMenu | Select what data to select which texture to use for the instances, use the drop-down menu on the right to easily select from the available options. |
| `instance` | Custom Instance | Sequence | Sequence of arbitrary attributes to be assigned to instances |
| `instance0customop` | OP | OP | Select a specific operator to get data from for the instance attributes below. If not specified, the the operator specified in the 'Default Instance OP' on the Instance parameter page can be used. |
| `instance0customx` | X | StrMenu | Select what data to use for this instance attribute, use the drop-down menu on the right to easily select from the available options. |
| `instance0customy` | Y | StrMenu | Select what data to use for this instance attribute, use the drop-down menu on the right to easily select from the available options. |
| `instance0customz` | Z | StrMenu | Select what data to use for this instance attribute, use the drop-down menu on the right to easily select from the available options. |
| `instance0customw` | W | StrMenu | Select what data to use for this instance attribute, use the drop-down menu on the right to easily select from the available options. |
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
# Access the COMP actorCOMP operator
actorcomp_op = op('actorcomp1')

# Get/set parameters
freq_value = actorcomp_op.par.active.eval()
actorcomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
actorcomp_op = op('actorcomp1')
output_op = op('output1')

actorcomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(actorcomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **141** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
