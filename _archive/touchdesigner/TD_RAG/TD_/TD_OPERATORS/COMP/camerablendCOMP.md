# COMP camerablendCOMP

## Overview

The Camera Blend Component allows various effects by blending multiple Components together.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `parenttype` | Type | Menu | Method in which parent transforms (i.e. Translate, Rotate, Scale) are combined to produce a unique blended transform. |
| `sequence` | Sequence | Float | Select which input to use for the position when set to Sequence or Constrain. |
| `reset` | Reset Frame | Float | When in constrain mode, this will reset the final transform back to its original position. On other frames, when the constrained parent changes, the relative transform to this camera is maintained. |
| `blendw1` | Weight 1 | Float | These weights are used to weight each corresponding input parent. |
| `blendm1` | Mask 1 | Int | These masks are used to select which component of each parent is used in the blending process. |
| `blendw2` | Weight 2 | Float | These weights are used to weight each corresponding input parent. |
| `blendm2` | Mask 2 | Int | These masks are used to select which component of each parent is used in the blending process. |
| `blendw3` | Weight 3 | Float | These weights are used to weight each corresponding input parent. |
| `blendm3` | Mask 3 | Int | These masks are used to select which component of each parent is used in the blending process. |
| `blendw4` | Weight 4 | Float | These weights are used to weight each corresponding input parent. |
| `blendm4` | Mask 4 | Int | These masks are used to select which component of each parent is used in the blending process. |
| `noffset` | Normal Offset | Float | When exactly three parents are input, the child position may be offset in the direction perpendicular to the triangular plane they form. |
| `axesorient` | Orient Axes | Toggle | When exactly three parents are input, this option will orient the child's local axes to match the orientation of the parents as follows:      ### Arguments: *First Parent: Axes Center    *  Secon... |
| `shortrot` | Short Rotation | Toggle | Does quaternion blending in cases where 2 inputs are being blended. |
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
| `projection` | Projection | Menu | A pop-up menu lets you choose from Perspective and Orthographic projection types. A third option Perpective to Ortho Blend enables the Projection Blend parameter below which can be used to blend be... |
| `projectionblend` | Projection Blend | Float |  |
| `orthowidth` | Ortho Width | Float |  |
| `viewanglemethod` | Viewing Angle Method | Menu |  |
| `fov` | FOV Angle | Float |  |
| `focal` | Focal Length | Float |  |
| `aperture` | Aperture | Float |  |
| `near` | Near | Float | This control allows you to designate the near clipping planes. Geometry closer from the lens than these distances will not be visible.      NOTE: If geometry in your scene is producing z-depth arti... |
| `far` | Far | Float | This control allows you to designate the far clipping planes. Geometry further away from the lens than these distances will not be visible.      NOTE: If geometry in your scene is producing z-depth... |
| `win` | Window X/Y | XY | These parameters define the center of the window during the rendering process. The window parameter takes the view and expands it to fit the camera's field of vision. It is important to note that t... |
| `winsize` | Window Size | XYZ | The Window Size parameter specifies the dimensions for expanding the view. Similar to Window X / Y, this parameter creates a zoom effect by scaling the screen before rendering to the viewport. |
| `winroll` | Window Roll | XYZ | This parameter sets the amount, in degrees, the window area rolls. This can be set as a static value or as an aspect that changes over the course of the animation. The roll occurs about the centre ... |
| `ipdshift` | IPD Shift | XYZ |  |
| `projmatrixop` | Proj Matrix/CHOP/DAT | OP |  |
| `bgcolor` | Background Color | RGBA | Sets the background color and alpha of the camera's view. |
| `fog` | Fog | Menu | This menu determines the type of fog rendered in the viewport: Linear fog uses the following equation:       Image:Objects14.gif        Exponential fog uses the following equation:        Image:Obj... |
| `fogdensity` | Fog Density | Float | A value that specifies density or thickness, used in both exponential fog types. Only non-negative densities are accepted. |
| `fognear` | Fog Near | Float | The starting distance of the fog. If geometry is closer to the camera than this distance, fog will not be calculated in the color of the geometry. Used in the linear fog equation. |
| `fogfar` | Fog Far | Float | The far distance used in the linear fog equation. |
| `fogcolor` | Fog Color | RGB | The color of the fog. |
| `fogalpha` | Fog Alpha | Float | Used to control the background opacity of the scene. |
| `fogmap` | Fog Map | TOP |  |
| `camlightmask` | Camera Light Mask | Object |  |
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
# Access the COMP camerablendCOMP operator
camerablendcomp_op = op('camerablendcomp1')

# Get/set parameters
freq_value = camerablendcomp_op.par.active.eval()
camerablendcomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
camerablendcomp_op = op('camerablendcomp1')
output_op = op('output1')

camerablendcomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(camerablendcomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **91** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
