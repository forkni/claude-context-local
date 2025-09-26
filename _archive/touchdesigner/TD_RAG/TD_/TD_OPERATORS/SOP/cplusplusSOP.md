# SOP cplusplusSOP

## Overview

The CPlusPlus SOP allows you to make custom SOP operators by writing your own plugin using C++.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `plugin` | Plugin Path | File | The path to the plugin you want to load. |
| `reinit` | Re-Init Class | Toggle | When this parameter is On, it will delete the instance of the class created by the plugin, and create a new one. |
| `reinitpulse` | Re-Init Class | Pulse | Instantly reinitialize the class. |
| `unloadplugin` | Unload Plugin | Toggle | When this parameter goes above 1, it will delete the instance of the class created by the plugin and unload the plugin. If multiple SOPs have loaded the same plugin they will all need to unload it ... |

## Usage Examples

### Basic Usage

```python
# Access the SOP cplusplusSOP operator
cplusplussop_op = op('cplusplussop1')

# Get/set parameters
freq_value = cplusplussop_op.par.active.eval()
cplusplussop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
cplusplussop_op = op('cplusplussop1')
output_op = op('output1')

cplusplussop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(cplusplussop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **4** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
