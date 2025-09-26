# SOP modelSOP

## Overview

The Model SOP holds the surface modeler in TouchDesigner.

## Parameters

*No parameters documented.*

## Usage Examples

### Basic Usage

```python
# Access the SOP modelSOP operator
modelsop_op = op('modelsop1')

# Get/set parameters
freq_value = modelsop_op.par.active.eval()
modelsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
modelsop_op = op('modelsop1')
output_op = op('output1')

modelsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(modelsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **0** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
