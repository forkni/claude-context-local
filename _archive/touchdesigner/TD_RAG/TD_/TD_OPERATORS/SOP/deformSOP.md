# SOP deformSOP

## Overview

The Deform SOP takes geometry along with point weights (assigned by the Capture SOP) and deforms geometry as Capture Regions are moved.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Optional point and/or primitive group to be deformed. Accepts patterns, as described in Pattern Matching. |
| `delcaptatr` | Delete Capture Attributes | Toggle | The point capture attributes can significantly increase the memory usage of the geometry. This option will delete the point capture attributes after it deforms the geometry in order to save memory ... |
| `delcolatr` | Delete Point Colors | Toggle | You may find that you are using point coloring from the Capture SOP to assist in the capturing process. If you do not need these point colors after the Deform SOP, you can turn this parameter on to... |
| `donormal` | Deform Normals | Toggle | Turn this on to deform the normals as the geometry deforms. |
| `skelrootpath` | Skeleton Root Path | Object | Specify the path to the root of the skeleton. |

## Usage Examples

### Basic Usage

```python
# Access the SOP deformSOP operator
deformsop_op = op('deformsop1')

# Get/set parameters
freq_value = deformsop_op.par.active.eval()
deformsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
deformsop_op = op('deformsop1')
output_op = op('output1')

deformsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(deformsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **5** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
