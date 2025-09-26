# SOP nullSOP

## Overview

The Null SOP has no effect on the geometry. It is an instance of the SOP connected to its input.

## Parameters

*No parameters documented.*

## Usage Examples

### Basic Usage

```python
# Access the SOP nullSOP operator
nullsop_op = op('nullsop1')

# Get/set parameters
freq_value = nullsop_op.par.active.eval()
nullsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
nullsop_op = op('nullsop1')
output_op = op('output1')

nullsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(nullsop_op)
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
