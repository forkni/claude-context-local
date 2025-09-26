# SOP groupSOP

## Overview

The Group SOP generates groups of points or primitives according to various criteria and allows you to act upon these groups.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `crname` | Group Name | Str | The name of the group to be created. The default name is set to match the name of the SOP. |
| `entity` | Entity | Menu | Primitives or Points. |
| `geotype` | Geometry Type | Menu | Select the geometry type group. The selection will only pertain to the geometry type specified. e.g. If you only wanted to group polygons. |
| `usenumber` | Use Number | Toggle | Allows selection of grouping of entities by number. When the Enable button is Active, the selection options become active and can be used to select entities. The fields available are listed below. |
| `ordered` | Create Ordered | Toggle | When selected, elements in the group are traversed in the order they are selected; otherwise they are traversed in creation order. |
| `groupop` | Operation | Menu | When the Number Enable button is checked, this option groups entities based on a defined Pattern or by a Range. |
| `pattern` | Pattern | Str | Activated when Operation is set to Group by Pattern. In this field, enter the range of primitives to select. The required syntax is "S.P", where S is the index of the parent surface, and P the prof... |
| `transfer` | Transfer Selection to Pattern | Pulse | This allows you to define the range of points / primitives visually by selecting them in the Viewport with the Select state. Clicking this button transfers the selected points/primitives into the P... |
| `range` | Start / End | Int | Activated when Operation is set to Group by Range. Select the start and end of the primitive/point number selection. |
| `select` | Select _of_ | Int | Activated when Operation is set to Group by Range. Select every nth occurrence of every mth entity in the above Start/End range.  For Example: entering 1 and 2 selects 1 out of every 2 entities. |
| `filter` | Filter Expression | Int | The Filter Expression provided is evaluated for every point/primitive. Wherever it is true, the entity is added. All the local variables of point and primitive are present, though only accessable w... |
| `usebounds` | Use Bounds | Toggle | This option is used for selecting entities based on bounding volumes: Bounding Box, or Bounding Sphere. When Active, the selection options become active and can be used to select entities. The fiel... |
| `boundtype` | Bounding Type | Menu | Selects the type of bounding volume to use |
| `size` | Size | XYZ | Dimensions of either the Bounding Box or Bounding Sphere in X, Y and Z. |
| `t` | Center | XYZ | The X, Y, and Z coordinates of the center of the bounding volume. |
| `usenormal` | Use Normal | Toggle | This option is used for selecting entities based on the angle of the entity normals. When the Active, the selection options become active and can be used to select entities. The fields available ar... |
| `dir` | Direction | XYZ | The default values of 0, 1, 0 create a normal vector straight up in Y, which is perpendicular to the XZ plane, which becomes the primary axis. The 1, 0, 0 points the normal in positive X, giving a ... |
| `angle` | Spread Angle | Float | The value entered in this field generates an angle of deviation from the primary axis. This can be visualized as a cone where the radius of the base of the cone is defined by the Spread Angle and t... |
| `camera` | Backface from | Object | This menu allows you to select an object. Typically, a camera object would be chosen. The primitives which are backface when viewed from the object specified will be grouped or selected. |
| `useedges` | Use Edges | Toggle | Allows you to group primitives by edges. |
| `doangle` | Edge Angle | Toggle | Enables the Edge Angle parameter. |
| `edgeangle` | Edge Angle | Float | Specifies an angle between edges in which to group. Works only for primitive groups. |
| `dodepth` | Edge Depth | Toggle | Enables the Edge Depth parameter. |
| `edgestep` | Edge Depth | Int | Enter the depth of the edge (only for point groups). |
| `point` | Point Number | Int | Enter the specific point numbers (only for point groups). |
| `unshared` | Unshared Edges | Toggle | When selecting points, this option selects the points of a ploygonal mesh which appear on the boundary (i.e. those which are not shared) for inclusion in the group, and orders them. In addition to ... |
| `boundarygroups` | Create Boundary Groups | Toggle | When selecting points with the Unshared Edges parameter, this option becomes available. Enabling it creates new groups of the form: __ , (two underscores) where the  is the Group Name specified in ... |
| `grpequal` | Group = | StrMenu | Specify the group whose members you wish to edit. This can be one of the input groups or a new group created in this SOP specified in the Group Name parameter on the Group page. |
| `not1` | Not | Toggle | When Off, include the members of the group specified in Group 1 parameter below. When On, include all members that are not part of the group specified in Group 1 parameter below. |
| `grp1` | Group 1 | StrMenu | Select one of the input groups to start with, noting the setting of the Not (not1) parameter above. |
| `op1` | Operation | Menu | Select the operation used to combine the group specified in Group 1 parameter with the group specified in Group 2 parameter. |
| `not2` | Not | Toggle | When Off, include the members of the group specified in Group 2 parameter below. When On, include all members that are not part of the group specified in Group 2 parameter below. |
| `grp2` | Group 2 | StrMenu | Select one of the input groups to combine with the group above, noting the setting of the Not (not2) parameter above. |
| `op2` | Operation | Menu | Select the operation used to combine the group specified in Group 2 parameter with the group specified in Group 3 parameter. |
| `not3` | Not | Toggle | When Off, include the members of the group specified in Group 3 parameter below. When On, include all members that are not part of the group specified in Group 3 parameter below. |
| `grp3` | Group 3 | StrMenu | Select one of the input groups to combine with the group combination above, noting the setting of the Not (not3) parameter above. |
| `op3` | Operation | Menu | Select the operation used to combine the group specified in Group 3 parameter with the group specified in Group 4 parameter. |
| `not4` | Not | Toggle | When Off, include the members of the group specified in Group 4 parameter below. When On, include all members that are not part of the group specified in Group 4 parameter below. |
| `grp4` | Group 4 | StrMenu | Select one of the input groups to combine with the group combination above, noting the setting of the Not (not4) parameter above. |
| `cnvtype` | Convert Type | Menu | Converts a group from a point group to a primitive group, and vice versa. |
| `convertg` | Group | StrMenu | Name of the group to convert. |
| `cnvtname` | Convert Name | Str | New group name. |
| `preserve` | Preserve Original | Toggle | When checked, preserves original geometry. |
| `oldname` | Group | StrMenu | Allows you to rename an existing group to something else. |
| `newname` | New Name | Str | Allows you to rename an existing group to something else. |
| `destroyname` | Group | StrMenu | Allows you to delete an existing point or primitive group. |

## Usage Examples

### Basic Usage

```python
# Access the SOP groupSOP operator
groupsop_op = op('groupsop1')

# Get/set parameters
freq_value = groupsop_op.par.active.eval()
groupsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
groupsop_op = op('groupsop1')
output_op = op('output1')

groupsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(groupsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **46** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
