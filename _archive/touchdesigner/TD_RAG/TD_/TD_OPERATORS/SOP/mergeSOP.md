# SOP mergeSOP

## Overview

The Merge SOP merges geometry from multiple SOPs.

## Parameters

*No parameters documented.*

## Usage Examples

### Basic Usage

```python
# Access the SOP mergeSOP operator
mergesop_op = op('mergesop1')

# Get/set parameters
freq_value = mergesop_op.par.active.eval()
mergesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mergesop_op = op('mergesop1')
output_op = op('output1')

mergesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mergesop_op)
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
