# SOP oculusriftSOP

## Overview

Loads geometry for the Oculus Rift Touch controllers.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `model` | Model | Menu | Select which controller model to load. |

## Usage Examples

### Basic Usage

```python
# Access the SOP oculusriftSOP operator
oculusriftsop_op = op('oculusriftsop1')

# Get/set parameters
freq_value = oculusriftsop_op.par.active.eval()
oculusriftsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oculusriftsop_op = op('oculusriftsop1')
output_op = op('output1')

oculusriftsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oculusriftsop_op)
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
