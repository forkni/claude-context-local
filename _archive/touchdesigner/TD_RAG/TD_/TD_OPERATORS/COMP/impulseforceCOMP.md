# COMP impulseforceCOMP

## Overview

An Impulse Force COMP will create a force in the simulation that can be applied for 1 frame using the Pulse Force parameter.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `pulse` | Pulse Force | button | Pulse for the impulse force. When pulsed, on the next frame it will apply the impulse force. |
| `force` | Force | float | The linear force in Newtons to be applied when the node is pulsed. |
| `relpos` | Relative Position | float | The position at which to apply the linear force, relative to the center of the body (Note: the physical center of the object, not the center of mass). Having a nonzero relative position will also c... |
| `torque` | Torque | float | The rotational force in Newtons that will be applied. |
| `ext` | Extension | Sequence | Sequence of info for creating extensions on this component |
| `reinitextensions` | Re-Init Extensions | Pulse | Recompile all extension objects. Normally extension objects are compiled only when they are referenced and their definitions have changed. |
| `parentshortcut` | Parent Shortcut | COMP | Specifies a name you can use anywhere inside the component as the path to that component. See Parent Shortcut. |
| `opshortcut` | Global Shortcut | COMP | Specifies a name you can use anywhere at all as the path to that component. See Global OP Shortcut. |
| `iop0shortcut` | Shortcut | COMP | Specifies a name you can use anywhere inside the component as a path to "Internal OP" below. See Internal Operators. |
| `iop0op` | OP | COMP | The path to the Internal OP inside this component. See Internal Operators. |
| `nodeview` | Node View | Menu | Determines what is displayed in the node viewer, also known as the Node Viewer. Some options will not be available depending on the Component type (Object Component, Panel Component, Misc.) |
| `opviewer` | Operator Viewer | OP | Select which operator's node viewer to use when the Node View parameter above is set to Operator Viewer. |
| `keepmemory` | Keep in Memory | Toggle | Used only for Panel Components this keeps the panel in memory to it doesn't reload every time it is displayed. |
| `enablecloning` | Enable Cloning | Toggle | Control if the OP should be actively cloneing. Turning this off causes this node to stop cloning it's 'Clone Master'. |
| `enablecloningpulse` | Enable Cloning Pulse | Pulse | Instantaneously clone the contents. |
| `clone` | Clone Master | COMP | Path to a component used as the Master Clone. |
| `loadondemand` | Load on Demand | Toggle | Loads the component into memory only when required. Good to use for components that are not always used in the project. |
| `externaltox` | External .tox | File | Path to a .tox file on disk which will source the component's contents upon start of a .toe. This allows for components to contain networks that can be updated independently. If the .tox file can n... |
| `reloadtoxonstart` | Reload .tox on Start | Toggle | When on (default), the external .tox file will be loaded when the .toe starts and the contents of the COMP will match that of the external .tox. This can be turned off to avoid loading from the ref... |
| `reloadcustom` | Reload Custom Parameters | Toggle | When this checkbox is enabled, the values of the component's Custom Parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on nod... |
| `reloadbuiltin` | Reload Built-In Parameters | Toggle | When this checkbox is enabled, the values of the component's built-in parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on n... |
| `savebackup` | Save Backup of External | Toggle | When this checkbox is enabled, a backup copy of the component specified by the External .tox parameter is saved in the .toe file.  This backup copy will be used if the External .tox can not be foun... |
| `subcompname` | Sub-Component to Load | Str | When loading from an External .tox file, this option allows you to reach into the .tox and pull out a COMP and make that the top-level COMP, ignoring everything else in the file (except for the con... |
| `reinitnet` | Re-Init Network | Pulse | This button will re-load from the external .tox file (if present), followed by re-initializing itself from its master, if it's a clone. |

## Usage Examples

### Basic Usage

```python
# Access the COMP impulseforceCOMP operator
impulseforcecomp_op = op('impulseforcecomp1')

# Get/set parameters
freq_value = impulseforcecomp_op.par.active.eval()
impulseforcecomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
impulseforcecomp_op = op('impulseforcecomp1')
output_op = op('output1')

impulseforcecomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(impulseforcecomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
