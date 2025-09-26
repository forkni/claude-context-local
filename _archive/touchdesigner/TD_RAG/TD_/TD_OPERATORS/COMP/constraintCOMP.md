# COMP constraintCOMP

## Overview

A Constraint COMP is used to restrict the movement of the bodies in a set of Actor COMPs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | toggle | Toggle the constraint on/off in the simulation. |
| `type` | Type | dropmenu | The type of constraint to create: point to point, hinge, or slider. |
| `bodytobody` | Body to Body | toggle | Toggle body to body mode on/off. Body to body mode creates a constraint between two bodies (Actor 1 Bodies and Actor 2 Bodies). When toggled off it will create constrain bodies individually. If Act... |
| `collisions` | Collisions between Bodies | toggle | Turns on/off collisions between the body to body constraints. |
| `dispcom` | Display Constraint | toggle | Turns on/off the display of the constraint guide in the viewer. |
| `actor1` | Actor COMP | objref | A reference to an Actor COMP. This specifies the Actor COMP of which you want to constrain some bodies. |
| `bodies1` | Actor Bodies | string | A list (regular expression) of the IDs of the bodies in actor1 to constrain. If an Actor COMP contains N bodies, then body IDs will go from 0 to N-1 for that Actor COMP. The number of bodies can be... |
| `pivot1` | Pivot | float | The pivot point for the constraint. |
| `axis1` | Hinge Axis | float | The axis around which to create the hinge. Each value is typically a number between 0 and 1. For example, to spin around the Z axis set to 0, 0, 1. |
| `sliderrot1` | Slider Rotation | float | The rotation of the slider constraint axis. By default the slider constraint is applied on the X axis. |
| `actor2` | Actor COMP | objref | A reference to an Actor COMP. This specifies the Actor COMP of which you want to constrain some bodies. This Actor COMP is only used when body to body mode is toggled on. |
| `bodies2` | Actor Bodies | string | A list (regular expression) of the IDs of the bodies in actor2 to constrain. If an Actor COMP contains N bodies, then body IDs will go from 0 to N-1 for that Actor COMP. The number of bodies can be... |
| `pivot2` | Pivot | float | The pivot point for the constraint. |
| `axis2` | Hinge Axis | float | The axis around which to create the hinge. Each value is typically a number between 0 and 1. For example, to spin around the Z axis set to 0, 0, 1. |
| `sliderrot2` | Slider Rotation | float | The rotation of the slider constraint axis. By default the slider constraint is applied on the X axis. |
| `enablelimits` | Enable Limits | toggle | Enables limits on the constraint. Without constraints, the bodies will be able to rotate a full 360 degrees, or translate any distance. |
| `lowerlinlim` | Lower Linear Limit | float | The lower limit for translation of the body along the constraint. Only used with slider constraints. |
| `upperlinlim` | Upper Linear Limit | float | The upper limit for translation of the body along the constraint. Only used with slider constraints. |
| `loweranglim` | Lower Angular Limit | anglejack | The lower limit for rotation of the body around its axis. Used with slider constraints or hinge constraints. |
| `upperanglim` | Upper Angular Limit | anglejack | The upper limit for rotation of the body around its axis. Used with slider constraints or hinge constraints. |
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
# Access the COMP constraintCOMP operator
constraintcomp_op = op('constraintcomp1')

# Get/set parameters
freq_value = constraintcomp_op.par.active.eval()
constraintcomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
constraintcomp_op = op('constraintcomp1')
output_op = op('output1')

constraintcomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(constraintcomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **39** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
