# SOP openvrSOP

## Overview

The OpenVR SOP loads various models that the OpenVR driver for the installed device provides.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `model` | Model | StrMenu | Select which model this node should output. This list is filled by what models the OpenVR driver provides. |

## Usage Examples

### Basic Usage

```python
# Access the SOP openvrSOP operator
openvrsop_op = op('openvrsop1')

# Get/set parameters
freq_value = openvrsop_op.par.active.eval()
openvrsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
openvrsop_op = op('openvrsop1')
output_op = op('output1')

openvrsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(openvrsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **1** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
