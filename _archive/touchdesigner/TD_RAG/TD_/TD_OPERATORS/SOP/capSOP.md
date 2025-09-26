# SOP capSOP

## Overview

The Cap SOP is used to close open areas with flat or rounded coverings.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Specify the Primitive Group to apply the caps to. See Group SOP to create primitive groups. |
| `pshapeu` | Preserve NURB Shape U | Toggle | When capping a NURBS surface, use this option to preserve the original surface by clamping it at the point of capping. |
| `firstu` | First U Cap | Menu | Select an option from the menu: |
| `divsu1` | Divisions | Int | Number of cross sections in the rounded cap. |
| `scaleu1` | Scale | Float | Affects the height of the rounded cap (both positive and negative). |
| `lastu` | Last U Cap | Menu | Similar to First Cap U / V, but builds a cap on the other end of the primitive in the opposite direction. |
| `divsu2` | Divisions | Int | Number of cross sections in the rounded cap. |
| `scaleu2` | Scale | Float | Affects the height of the rounded cap (both positive and negative). |
| `pshapev` | Preserve NURB Shape V | Toggle | When capping a NURBS surface, use this option to preserve the original surface by clamping it at the point of capping. |
| `firstv` | First V Cap | Menu | Select an option from the menu: |
| `divsv1` | Divisions | Int | Number of cross sections in the rounded cap. |
| `scalev1` | Scale | Float | Affects the height of the rounded cap (both positive and negative). |
| `lastv` | Last V Cap | Menu | Similar to First Cap U / V, but builds a cap on the other end of the primitive in the opposite direction. |
| `divsv2` | Divisions | Int | Number of cross sections in the rounded cap. |
| `scalev2` | Scale | Float | Affects the height of the rounded cap (both positive and negative). |

## Usage Examples

### Basic Usage

```python
# Access the SOP capSOP operator
capsop_op = op('capsop1')

# Get/set parameters
freq_value = capsop_op.par.active.eval()
capsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
capsop_op = op('capsop1')
output_op = op('output1')

capsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(capsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
