# SOP carveSOP

## Overview

The Carve SOP works with any face or surface type, be that polygon, Bzier, or NURBS.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the Group specified. Accepts patterns, as described in the Scripting Guide under Pattern Matching. |
| `firstu` | First U | Toggle | Enables the parameter to set the first position in U. |
| `domainu1` | First U | Float | This specifies a starting location to begin the cut/extract. Select this and a parametric U location between 0 and 1. |
| `secondu` | Second U | Toggle | Enables the parameter to set the second position in U. |
| `domainu2` | Second U | Float | This specifies an ending location to complete the cut / extract. Select this and a parametric U location between 0 and 1. |
| `firstv` | First V | Toggle | Enables the parameter to set the first position in V. |
| `domainv1` | First V | Float | This specifies a starting location to begin the cut/extract. Select this and a parametric V location between 0 and 1. Applies only to surfaces. |
| `secondv` | Second V | Toggle | Enables the parameter to set the second position in V. |
| `domainv2` | Second V | Float | This specifies an ending location to complete the cut / extract. Select this and a parametric V location between 0 and 1. Applies only to surfaces. |
| `method` | Carve Method | Menu | Select between Cut and Extract methods. |
| `keepin` | Keep Inside | Toggle | Keep the primitives specified between the first and second locations. |
| `keepout` | Keep Outside | Toggle | Keep the primitives lying outside the first and second locations. |
| `extractop` | Extract Type | Menu | If enabled, it will extract a cross-section along each location specified above.      Note: if a face is used, only points can be extracted and the V parameters have no effect. |
| `keeporiginal` | Keep Original | Toggle | If selected, it will not remove the original primitive. |
| `location` | Location | Menu | Determines how the Cut/Extract is defined at the boundaries. Additionally, extra subdivisions can be added in two ways using the parameters below. |
| `divsu` | U Divisions | Int | This specifies the number of cuts / extracts to be performed between first U and the second U. |
| `divsv` | V Divisions | Int | Specifies the number of cuts/extracts to be performed between first V and second V. |
| `allubreakpoints` | Cut at All Internal U Breakpoints | Toggle | When using Location = Breakpoints, the resulting primitive is divided at all U breakpoints into separate primitives. |
| `allvbreakpoints` | Cut at All Internal V Breakpoints | Toggle | When using Location = Breakpoints, the resulting primitive is divided at all V breakpoints into separate primitives. |

## Usage Examples

### Basic Usage

```python
# Access the SOP carveSOP operator
carvesop_op = op('carvesop1')

# Get/set parameters
freq_value = carvesop_op.par.active.eval()
carvesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
carvesop_op = op('carvesop1')
output_op = op('output1')

carvesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(carvesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
