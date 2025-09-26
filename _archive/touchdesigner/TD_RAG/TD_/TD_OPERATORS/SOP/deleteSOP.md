# SOP deleteSOP

## Overview

The Delete SOP deletes input geometry as selected by a group specification or a geometry selection by using either of the three selection options: by entity number, by a bounding volume, and by entity (primitive/point) normals.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | The name of the group to be created. The default name is set to match the name of the SOP. |
| `negate` | Operation | Menu | Choose to Delete the Selected Geometry or Delete the Non-Selected Geometry. |
| `entity` | Entity | Menu | Choose to delete primitives or points. |
| `geotype` | Geometry Type | Menu | Select the geometry type group. The selection will only pertain to the geometry type specified. e.g. If you only wanted to group polygons. |
| `usenumber` | Use Number | Toggle | When the Enable button is checked under the Number button, the selection options become active and can be used to select entities. The fields available are listed below. |
| `groupop` | Operation | Menu | When the Number Enable button is checked, this option groups entities based on a defined Pattern or by a Range. |
| `pattern` | Pattern | Str | Activated when Operation is set to Group by Pattern. In this field, enter the range of primitives to select. The required syntax is "S.P", where S is the index of the parent surface, and P the prof... |
| `range` | Start / End | Int | Activated when Operation is set to Group by Range. Select the start and end of the primitive/point number selection. |
| `select` | Select _of_ | Int | Activated when Operation is set to Group by Range. Select every nth occurrence of every mth entity in the above Start/End range.   For example; entering 1 and 2 selects 1 out of every 2 entities |
| `filter` | Filter Expression | Int | The Filter Expression provided is evaluated for every point/primitive. Wherever it is true, the entity is added to the selection. |
| `usebounds` | Use Bounds | Toggle | When the Enable button is checked under the Bounding button, the selection options become active and can be used to select entities. The fields available are listed below. The bounding volume can b... |
| `boundtype` | Bounding Type | Menu | Selects the type of bounding volume to use: |
| `size` | Size | XYZ | Dimensions of either the Bounding Box or Bounding Sphere in X, Y and Z. |
| `t` | Center | XYZ | The X, Y, and Z coordinates of the center of the bounding volume. |
| `usenormal` | Use Normal | Toggle | When the Enable button is checked under the Normal button, the selection options become active and can be used to select entities. The fields available are listed below.      The primary axis and t... |
| `dir` | Direction | XYZ | The default values of 0, 1, 0 create a normal vector straight up in Y, which is perpendicular to the XZ plane, which becomes the primary axis. The 1, 0, 0 points the normal in positive X, giving a ... |
| `angle` | Spread Angle | Float | The value entered in this field generates an angle of deviation from the primary axis. This can be visualized as a cone where the radius of the base of the cone is defined by the Spread Angle and t... |
| `camera` | Backface from | Object | This menu allows you to select an object. Typically, a camera object would be chosen. The primitives which are backface when viewed from the object specified will be grouped or selected. |
| `removegrp` | Delete Unused Groups | Toggle | If any group has 0 entries and if this parameter is enabled, then those groups are removed. If you want to keep empty groups, disable this parameter. |
| `keeppoints` | Delete Geometry, Keep Points | Toggle | Deletes the geometry but keeps the points. |

## Usage Examples

### Basic Usage

```python
# Access the SOP deleteSOP operator
deletesop_op = op('deletesop1')

# Get/set parameters
freq_value = deletesop_op.par.active.eval()
deletesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
deletesop_op = op('deletesop1')
output_op = op('output1')

deletesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(deletesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
