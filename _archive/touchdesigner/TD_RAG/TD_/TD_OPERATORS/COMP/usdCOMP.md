# COMP usdCOMP

## Overview

The USD COMP loads and imports most geometric schemas from a USD file in crate/binary or ASCII file formats with extensions as (.usd), (.usda), (.usdc), and (.usdz). Currently the USD version 20.08 is being used in USD COMP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | USD File | filepath load | The path to the USD file. The file can be a binary (.usd or .usdc) or ASCII format (.usda). |
| `reload` | Reload File | button | A pulse to reload the assets from the file without making any changes to the existing network. |
| `usematerial` | Use Material | toggle | A toggle to specify whether the material/shading be enabled for all the geometry primitives with material binding or not. By turning this toggle on, the MAT nodes and -according to the need- the Im... |
| `cameras` | Cameras | toggle | A toggle to specify whether the Camera nodes (subject to be defined in the USD file) created for the USD COMP or not. |
| `genactors` | Generate Actor COMPs | toggle | When enabled, will generate Actor COMPs in place of Geometry COMPs as the parents' of Import Select SOPs. |
| `mergegeo` | Merge Geometry | toggle | A toggle to merge the mergeable geometries SOPs and their transformation COMPs up to a specified merge level. This feature can noticeably increase the performance of the USD COMP network. |
| `mergelevel` | Merge Level | integer | Defines the desired merge level for merging the nodes. The start value is 1 which is the root of the network and it increases for the children of nodes the same as their positions within tree hiera... |
| `maxwiredchildren` | Max Wired Children | integer | This value is used to define how many wired children a Geometry/Null COMP node can have on the same network level (note that this network level refers to all the nodes that can be seen on the same ... |
| `computenormals` | Compute Normals | toggle | A toggle for generating normal vectors from subdivision schema specified from USD file using OpenSubdiv library. Turning this toggle to OFF makes will make the SOPs use the TouchDesigner generated ... |
| `gpudirect` | Direct to GPU | toggle | A toggle to load the geometry directly to the GPU. This makes the rendering much faster than CPU mode. However, currently the only supported geometries are mesh and point primitives. If a USD scene... |
| `buildnetwork` | Build Network | button | Every time (including the first time) you specify a new file, or change any parameter from the USD page, you need to re-build it, so it generates the network according to the current selected param... |
| `keepparams` | Keep Parameters | toggle | A toggle to keep the parameters of the current network over parameters of the re-imported (via Update parameter) network. |
| `keepconnections` | Keep Connections | toggle | A toggle to keep the connection of the current network over the connections of the re-imported (via Update parameter) network. |
| `update` | Update | button | Updates the network. This option is specifically useful when the USD file is edited after the USD network is imported in TouchDesigner. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute during import or update allowing for modification and customization of the imported operators and resulting network. |
| `shiftanimationstart` | Shift Animation Start | toggle | A toggle to specify whether to shift the animation to the start of animation indicated in the USD file. |
| `sampleratemode` | Sample Rate Mode | dropmenu | A menu to choose between the file FPS or custom sample rate. |
| `samplerate` | Sample Rate | float | It is used to specify the sample rate (FPS) for the animation. This parameter is disabled by default and can be enabled once the Custom option is selected from the Sample Rate Menu. |
| `playmode` | Play Mode | dropmenu | A menu to specify the method used to play the animation. |
| `initialize` | Initialize | button | Resets the animation to its initial state. |
| `start` | Start | button | Resets the animation to its initial state and starts playback. |
| `cue` | Cue | joinpair toggle | A toggle to jump to Cue Point when its set to ON and it stays at that position. Only available when Play Mode is Sequential. |
| `cuepulse` | Cue Pulse | nolabel button | When pressed the animation jumps to the Cue Point and continues from that point. |
| `cuepoint` | Cue Point | joinpair float | Set any index in the animation as a point to jump to. |
| `cuepointunit` | Cue Point Unit | nolabel shortvalues dropmenu | Specifies a unit type for Cue Point. Changing this will convert the previous unit to the selected unit. |
| `play` | Play | toggle | A toggle that makes the animation to play when it sets to ON. This Parameter is only available/enabled if the Sequential mode is selected from the Play Mode. |
| `index` | Index | joinpair float | This parameter explicitly sets the animation position when Play Mode is set to Specify Index. The units menu on the right lets you specify the index in the following units: Index, Frames, Seconds, ... |
| `indexunit` | Index Unit | nolabel shortvalues dropmenu | Specifies a unit type for Index. Changing this will convert the previous unit to the selected unit. |
| `speed` | Speed | float | This is a speed multiplier which only works when Play Mode is Sequential. A value of 1 is the default playback speed. A value of 2 is double speed, 0.5 is half speed and so on. |
| `trim` | Trim | toggle | A toggle to enable the Trim Start and Trim End parameters. |
| `tstart` | Trim Start | joinpair float | Sets an in point from the beginning of the animation, allowing you to trim the starting index of the animation. The units menu on the right let you specify this position by index, frames, seconds, ... |
| `tstartunit` | Trim Start Unit | nolabel shortvalues dropmenu | Specifies a unit type for Trim Start. Changing this will convert the previous unit to the selected unit. |
| `tend` | Trim End | joinpair float | Sets an end point from the end of the movie, allowing you to trim the ending index of the animation. The units menu on the right let you specify this position by index, frames, seconds, or fraction... |
| `tendunit` | Trim End Unit | nolabel shortvalues dropmenu | Specifies a unit type for Trim End. Changing this will convert the previous unit to the selected unit. |
| `textendleft` | Extend Left | dropmenu | Determines how USD COMP handles animation positions that lie before the Trim Start position. For example, if Trim Start is set to 1, and the animation current index is -10, the Extend Left menu det... |
| `textendright` | Extend Right | dropmenu | Determines how USD COMP handles animation positions that lie after the Trim End position. For example, if Trim End is set to 20, and the animation current index is 25, the Extend Right menu determi... |
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
# Access the COMP usdCOMP operator
usdcomp_op = op('usdcomp1')

# Get/set parameters
freq_value = usdcomp_op.par.active.eval()
usdcomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
usdcomp_op = op('usdcomp1')
output_op = op('output1')

usdcomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(usdcomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **90** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
