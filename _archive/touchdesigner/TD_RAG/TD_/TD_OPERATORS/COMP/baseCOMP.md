# COMP baseCOMP

## Overview

The Base Component has no panel parameters and no 3D object parameters.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `ext` | Extension | Sequence | Sequence of info for creating extensions on this component |
| `reinitextensions` | Re-Init Extensions | Pulse | Recompile all extension objects. Normally extension objects are compiled only when they are referenced and their definitions have changed. |
| `parentshortcut` | Parent Shortcut | COMP | Specifies a name you can use anywhere inside the component as the path to that component. See Parent Shortcut. |
| `opshortcut` | Global OP Shortcut | COMP | Specifies a name you can use anywhere at all as the path to that component. See Global OP Shortcut. |
| `iop` | Internal OP | Sequence | Sequence header for internal operators. |
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
# Access the COMP baseCOMP operator
basecomp_op = op('basecomp1')

# Get/set parameters
freq_value = basecomp_op.par.active.eval()
basecomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
basecomp_op = op('basecomp1')
output_op = op('output1')

basecomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(basecomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **18** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
