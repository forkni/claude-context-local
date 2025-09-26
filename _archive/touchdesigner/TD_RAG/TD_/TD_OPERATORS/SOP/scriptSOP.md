# SOP scriptSOP

## Overview

The Script SOP runs a script each time the Script SOP cooks.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `callbacks` | Callbacks DAT | DAT | Specifies the DAT which holds the callbacks. See scriptSOP_Class for usage. |
| `setuppars` | Setup Parameters | Pulse | Clicking the button runs the setupParameters() callback function. |

## Usage Examples

### Basic Usage

```python
# Access the SOP scriptSOP operator
scriptsop_op = op('scriptsop1')

# Get/set parameters
freq_value = scriptsop_op.par.active.eval()
scriptsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
scriptsop_op = op('scriptsop1')
output_op = op('output1')

scriptsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(scriptsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **2** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
