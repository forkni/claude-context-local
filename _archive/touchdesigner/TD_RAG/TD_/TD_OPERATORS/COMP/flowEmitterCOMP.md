# COMP flowEmitterCOMP

## Overview

The Nvidia Flow COMP is the fuel emitter for the Flow simulation and can be placed anywhere in the 3D scene.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | toggle | Turns the emitter On or Off. |
| `mode` | Mode | dropmenu | Select Emitter or Collider mode. |
| `type` | Type | dropmenu | Select the shape type used for the emitter. |
| `size` | Size | float | Controls the dimensions of the emitter when using Box or Shape TOP types. |
| `radius` | Radius | float | Controls the radius of the emitter when using the Sphere or Capsule types. |
| `length` | Length | float | Control the length of the emitter when using the Capsule type. |
| `shapeop` | Shape OP | string | Specify the TOP or SOP to use as an emitter when Type parameter is set to Shape TOP / Shape SOP respectively. For TOP emitters the resolution cannot exceed 2048x2048. |
| `shapechannel` | Shape Channel | dropmenu | Allows use of different channels to determine the shape of the emitter created when using Shape TOP. |
| `shapethreshold` | Shape Threshold | float | Pixels greater than or equal to the threshold value are used for emission, pixels below the threshold value are ignored. |
| `centerofmass` | Center of Mass | float | Specifies the center of mass of the emitter. |
| `innerwidth` | Inner Width | float | The shape of the emitter sets the surface shape, and the Inner Width adds to the emitter by filling in the shape from the surface inwards. The default setting of 1.0 effectively fills in the shape ... |
| `outerwidth` | Outer Width | float | The shape of the emitter set the surface shape, and the Outer Width adds to the emitter by extending the shape outwards from the surface. |
| `linearvel` | Linear Velocity | float | Target linear velocity of the fuel added to the system. |
| `angularvel` | Angular Velocity | float | Target angular velocity of the fuel added to the system. Think of this as 'rotational velocity. |
| `velcorrate` | Velocity Correction Rate | float | Rate at which the the system gets to the target velocity. Each simulation block has its own velocity level, the emitter tries to change any blocks it overlaps with to match its emitter value. The c... |
| `smoke` | Smoke | float | Amount of smoke produced per unit of fuel in the system. |
| `smokecorrate` | Smoke Correction Rate | float | Rate at which the the system gets to the target smoke level. Each simulation block has its own smoke level, the emitter tries to change any blocks it overlaps with to match its emitter value. The c... |
| `temp` | Temp | float | Temperature of the system. Note a temperature value of 0 will not ignite the simlulation, a minimum temperature is required for the simulation to burn. |
| `tempcorrate` | Temp Correction Rate | float | Rate at which the the system gets to the target temperature level. Each simulation block has its own temperature level, the emitter tries to change any blocks it overlaps with to match its emitter ... |
| `fuel` | Fuel | float | Amount of fuel added to the system per simulation step. The fuel is treated as gaseous and is converted into temperature (and a certain density) when combustion is taking place. |
| `fuelcorrate` | Fuel Correction Rate | float | Rate at which the the system gets to the target fuel level. Each simulation block has its own fuel level, the emitter tries to change any blocks it overlaps with to match its emitter value. The cor... |
| `fuelreleasetemp` | Fuel Release Temp | float | THe temperature required in the system to trigger addition Fuel Release set in the parameter below. |
| `fuelrelease` | Fuel Release | float | An additional amount of fuel is released into the system when the Fuel Release Temperature threshold set above is met. TIP: This can help simulate solid fuels where heat must be applied for a gaseo... |
| `allocscale` | Alloc Scale | float | The emitter allocates 'blocks' to contain the simulation. This parameter controls this where 0.0 turns off emitter allocation, 1.0 is default, and values greater than 1.0 can help pre-allocate whic... |
| `allocpredict` | Alloc Predict | float | Controls the emitter's direction block allocation prediction, used for pre-allocation of blocks for fast emitters.      The effect of this parameter can be visualized by turning 'Show Blocks' param... |
| `color` | Color | rgb | The base color of the combustion. |
| `colorramp` | Color Ramp | chopref | This color ramp will be multiplied with the Color Parameter above. The left-side of the color ramp is used for the cooler temperatures in the system ie. further away from center of combustion and w... |
| `alphascale` | Alpha Scale | float | Alpha calculations (determined by Alpha Bias and Alpha Masks below) are multiplied by this value for a final Alpha value. |
| `alphabias` | Alpha Bias | float | This value is added to alpha before final alpha values are calculated using the Alpha Mask parameters below. |
| `intensitybias` | Intensity Bias | float | A mulitplier for the color contribution. Useful to use with the Additive Factor parameter below. |
| `additivefactor` | Additive Factor | float | Controls an additive effect in the rendering ie. transparency is added together giving hotspots and brighter color where there is more gas burning. |
| `burncolormask` | Burn Color Mask | float | Controls the color contribution of the ignition point of the fuel in the system. The value determines which position in the Color Ramp to use for Burn color. |
| `smokecolormask` | Smoke Color Mask | float | Controls the color contribution of the smoke in the system. The value determines which position in the Color Ramp to use for Smoke color. |
| `tempcolormask` | Temp Color Mask | float | Controls the color contribution of the temperature in the system. Note: Fuel is converted to Temperature when combustion is active. The value determines which position in the Color Ramp to use for ... |
| `fuelcolormask` | Fuel Color Mask | float | Controls the color contribution of the fuel in the system before it is burned. The value determines which position in the Color Ramp to use for Fuel color. |
| `burnalphamask` | Burn Alpha Mask | float | Controls the transparency of the Burn Color above. |
| `smokealphamask` | Smoke Alpha Mask | float | Controls the transparency of the Smoke Color above. |
| `tempalphamask` | Temp Alpha Mask | float | Controls the transparency of the Temp Color above. |
| `fuelalphamask` | Fuel Alpha Mask | float | Controls the transparency of the Fuel Color above. |
| `burnintensitymask` | Burn Intensity Mask | float | Controls the intensity of the Burn Color above. This value is a multiplier and accepts values greater than 1.0. |
| `smokeintensitymask` | Smoke Intensity Mask | float | Controls the intensity of the Smoke Color above. This value is a multiplier and accepts values greater than 1.0. |
| `tempintensitymask` | Temp Intensity Mask | float | Controls the intensity of the Temp Color above. This value is a multiplier and accepts values greater than 1.0. |
| `fuelintensitymask` | Fuel Intensity Mask | float | Controls the intensity of the Fuel Color above. This value is a multiplier and accepts values greater than 1.0. |
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
# Access the COMP flowEmitterCOMP operator
flowemittercomp_op = op('flowemittercomp1')

# Get/set parameters
freq_value = flowemittercomp_op.par.active.eval()
flowemittercomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
flowemittercomp_op = op('flowemittercomp1')
output_op = op('output1')

flowemittercomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(flowemittercomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **146** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
