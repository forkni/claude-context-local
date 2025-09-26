# SOP inversecurveSOP

## Overview

The Inverse Curve SOP takes data from an Inverse Curve CHOP and builds a curve from it.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `chop` | CHOP | CHOP | The path to the Inverse Curve CHOP supplying the data. |

## Usage Examples

### Basic Usage

```python
# Access the SOP inversecurveSOP operator
inversecurvesop_op = op('inversecurvesop1')

# Get/set parameters
freq_value = inversecurvesop_op.par.active.eval()
inversecurvesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
inversecurvesop_op = op('inversecurvesop1')
output_op = op('output1')

inversecurvesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(inversecurvesop_op)
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
