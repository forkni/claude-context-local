# COMP boneCOMP

## Overview

The Bone Component is the foundation of all of the Character Tools.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
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
| `displaylink` | Display Link | Toggle | Enabling this option allows you to toggle the display of the link geometry in the Viewport on and off. |
| `restangles` | Rest Angles | XYZ | Defines the relative weighting of rotations about Rx, Ry, Rz, the bone's x,y,z axis for the Inverse Kinematics solver. |
| `length` | Bone Length | Float | This parameter changes the overall length of the Bone Component. It affects the size of the bone geometry and the positioning of the capture geometry and also determines the "end" of the bone -- i.... |
| `ikdamp` | Dampening | Float | This parameter prevents bone chains from locking in a dramatically straight line when they are fully extended. This type of locking motion tends to make characters look robotic. The dampening field... |
| `xrange` | X Angle Range | Float | Specifies the maximum and minimum rotation angles. |
| `xdamp` | X Damping Angle | Float | Applies damping to the rotation of the bone when the rotation in each axis falls within the angle specified by X / Y Angle Range. |
| `xrolloff` | X Damping Rolloff | Float | Specifes the rate at which the damping increases as the rotation varies through the angle specifed by X / Y Angle Range. |
| `yrange` | Y Angle Range | Float | Specifies the maximum and minimum rotation angles. |
| `ydamp` | Y Damping Angle | Float | Applies damping to the rotation of the bone when the rotation in each axis falls within the angle specified by X / Y Angle Range. |
| `yrolloff` | Y Damping Rolloff | Float | Specifes the rate at which the damping increases as the rotation varies through the angle specifed by X / Y Angle Range. |
| `displaycapture` | Display Capture Geometry | Toggle |  |
| `crcenter` | Region Center | XYZ | Position of the center of the region. |
| `crtopheight` | Top Height | Float | Height of the region from the centre to the top cap. |
| `crtopcap` | Top Cap | XYZ | The X, Y, Z radii of the top/bottom hemisphere. |
| `crbotheight` | Bot Height | Float | Height of the region from the centre to the top cap. |
| `crbotcap` | Bot Cap | XYZ | The X, Y, Z radii of the top/bottom hemisphere. |
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
# Access the COMP boneCOMP operator
bonecomp_op = op('bonecomp1')

# Get/set parameters
freq_value = bonecomp_op.par.active.eval()
bonecomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
bonecomp_op = op('bonecomp1')
output_op = op('output1')

bonecomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(bonecomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **70** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
