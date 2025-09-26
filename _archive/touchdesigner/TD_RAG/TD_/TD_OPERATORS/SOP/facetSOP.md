# SOP facetSOP

## Overview

The Facet SOP lets you control the smoothness of faceting of a given object.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `unit` | Make Normals Unit Length | Toggle | Checking this option will normalize the length of normals to a length of one unit. |
| `prenml` | Compute Normals | Toggle | Checking this option means that the surface normals will be computed. Where points are shared between polygons, smooth shading results, and where points are not shared (unique), faceted edges resul... |
| `unique` | Unique Points | Toggle | Makes each vertex have a unique point. The result of selecting this option is that all vertices are made into unique points, thus making all edges hard, with no smooth shading. |
| `cons` | Consolidate | Menu | Consolidate eliminates the redundancy of having many points that are close to each other, by merging them together to form a fewer set of common points. Consolidate is useful for cleaning up an edg... |
| `dist` | Distance | Float | Points and normals less than this distance apart will be consolidated, or have their normals averaged, based on the setting in the Consolidate menu.  Usually very small numbers, such as 0.01 should... |
| `inline` | Remove Inline Points | Toggle | Removes points that lie inline with its neighboring points. |
| `inlinedist` | Distance | Float | Set the distance threshold for removing inline points when the above parameter is On. |
| `orientpolys` | Orient Polygons | Toggle | Orients all polygons so they have the same winding direction. |
| `cusp` | Cusp Polygons | Toggle | Most of the time, you want some polygons to be smooth shaded and others to be faceted. Usually polygons that meet at low angles should be smooth shaded, and polygon edges that meet at sharper angle... |
| `angle` | Cusp Angle | Float | Cusping allows you to specify the threshold angle at which the edges become faceted. A good typical value is 20. |
| `remove` | Remove Degenerate | Toggle | Sometimes (not often) your geometry can get messed up, where there are points hanging around that are not used for anything, or there are primitives that don't make sense. This option checks for th... |
| `postnml` | Compute Normals | Toggle | Again, allows you to compute the normals after the consolidation or cusping stages. You should select this if you have set either the Cusp or Consolidate option. |

## Usage Examples

### Basic Usage

```python
# Access the SOP facetSOP operator
facetsop_op = op('facetsop1')

# Get/set parameters
freq_value = facetsop_op.par.active.eval()
facetsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
facetsop_op = op('facetsop1')
output_op = op('output1')

facetsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(facetsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
