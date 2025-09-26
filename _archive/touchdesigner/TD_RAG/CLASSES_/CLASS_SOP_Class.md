---
title: "SOP Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "technical_artist", "intermediate_user", "visual_programmer"]
completion_signals: ["can_access_geometry_data", "understands_procedural_geometry", "can_implement_sop_scripting", "manages_point_primitive_access"]

operators:
- Script_SOP
- Box_SOP
- Grid_SOP
- Geometry_COMP
concepts:
- geometry_data_access
- procedural_geometry
- sop_scripting
- bounding_box_calculation
- file_io
- point_primitive_access
- geometry_analysis
prerequisites:
- Python_fundamentals
- CLASS_OP_Class
- 3d_concepts
workflows:
- procedural_modeling
- geometry_analysis
- data_visualization_on_geometry
- baking_geometry
- point_cloud_processing
- mesh_generation
keywords:
- sop class
- geometry data
- access points
- python sop
- procedural geometry
- bounding box
- save geometry
- bgeo
- point attributes
- primitive groups
- vertex attributes
- numPoints
- numPrims
- computeBounds
- points
- prims
- pointAttribs
- primAttribs
- vertexAttribs
tags:
- python
- api_reference
- sop
- geometry
- 3d
- scripting
- procedural
- modeling
- analysis
relationships:
  CLASS_Points_Class: strong
  CLASS_Prims_Class: strong
  CLASS_Attributes_Class: strong
  CLASS_Position_Class: strong
  CLASS_Bounds_Class: strong
  PY_Working_with_OPs_in_Python: medium
related_docs:
- CLASS_Points_Class
- CLASS_Prims_Class
- CLASS_Attributes_Class
- CLASS_Position_Class
- CLASS_Bounds_Class
- PY_Working_with_OPs_in_Python
# Enhanced search optimization
search_optimization:
  primary_keywords: ["sop", "geometry", "points", "primitives"]
  semantic_clusters: ["geometry_processing", "3d_data_access", "procedural_modeling"]
  user_intent_mapping:
    beginner: ["what is sop class", "basic geometry access", "how to get points"]
    intermediate: ["geometry manipulation", "procedural modeling", "attribute access"]
    advanced: ["complex geometry workflows", "performance optimization", "advanced scripting"]

hierarchy:
  secondary: sop_scripting
  tertiary: sop_base_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- procedural_modeling
- geometry_analysis
- data_visualization_on_geometry
- baking_geometry
---

# SOP Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_SOP, Box_SOP, Grid_SOP, Geometry_COMP]
concepts: [geometry_data_access, procedural_geometry, sop_scripting, bounding_box_calculation, file_io, point_primitive_access, geometry_analysis]
prerequisites: [Python_fundamentals, CLASS_OP_Class, 3d_concepts]
workflows: [procedural_modeling, geometry_analysis, data_visualization_on_geometry, baking_geometry, point_cloud_processing, mesh_generation]
related: [CLASS_Points_Class, CLASS_Prims_Class, CLASS_Attributes_Class, CLASS_Position_Class, CLASS_Bounds_Class, PY_Working_with_OPs_in_Python]
relationships: {
  "CLASS_Points_Class": "strong",
  "CLASS_Prims_Class": "strong", 
  "CLASS_Attributes_Class": "strong",
  "CLASS_Position_Class": "strong",
  "CLASS_Bounds_Class": "strong",
  "PY_Working_with_OPs_in_Python": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "sop_scripting"
  tertiary: "sop_base_class"
keywords: [sop class, geometry data, access points, python sop, procedural geometry, bounding box, save geometry, bgeo, point attributes, primitive groups, vertex attributes, numPoints, numPrims, computeBounds, points, prims, pointAttribs, primAttribs, vertexAttribs]
tags: [python, api_reference, sop, geometry, 3d, scripting, procedural, modeling, analysis]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: procedural_modeling, geometry_analysis, data_visualization_on_geometry

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Class Op Class] → [3D Concepts]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Points Class] → [CLASS Prims Class] → [CLASS Attributes Class]

**Related Topics**: procedural modeling, geometry analysis, data visualization on geometry

## Summary

This class inherits from the OP class. It references a specific SOP operator. Core base class for all SOP operators, providing geometry data access and manipulation. Essential for 3D modeling workflows and procedural geometry generation.

## Relationship Justification

Central hub for SOP scripting ecosystem, strongly connected to geometry component classes (Points, Prims, Attributes). Links to Position and Bounds classes for spatial calculations. Connected to general OP scripting guide for foundational operator manipulation patterns.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods](#methods)
  - [computeBounds()](#computebounds)
  - [save()](#save)

## Introduction

A SOP describes a reference to a SOP operator, containing points and primitives.

## Members

`compare` → `bool`:
Get or set Compare Flag.

`template` → `bool`:
Get or set Template Flag.

`points` → `[CLASS_Points]` **(Read Only)**:
The set of points contained in this SOP.

`prims` → `[CLASS_Prims]` **(Read Only)**:
The set of primitives contained in this SOP.

`numPoints` → `int` **(Read Only)**:
The number of points contained in this SOP.

`numVertices` → `int` **(Read Only)**:
The number of vertices contained in all primitives within this SOP.

`numPrims` → `int` **(Read Only)**:
The number of primitivies contained in this SOP.

`pointAttribs` → `[CLASS_Attributes]` **(Read Only)**:
The set of point attributes defined in this SOP.

`primAttribs` → `[CLASS_Attributes]` **(Read Only)**:
The set of primitive attributes defined in this SOP.

`vertexAttribs` → `[CLASS_Attributes]` **(Read Only)**:
The set of vertex attributes defined in this SOP.

`pointGroups` → `dict` **(Read Only)**:
Returns a dictionary of point groups defined for this SOP.

`primGroups` → `dict` **(Read Only)**:
Returns a dictionary of primitive groups defined for this SOP.

`center` → `[CLASS_Position]`:
Get or set the barycentric coordinate of this operator's geometry. It is expressed as a Position.

`min` → `[CLASS_Position]` **(Read Only)**:
The minimum coordinates of this operator's geometry along each dimension, expressed as a Position.

`max` → `[CLASS_Position]` **(Read Only)**:
The maximum coordinates of this operator's geometry along each dimension, expressed as Position.

`size` → `[CLASS_Position]` **(Read Only)**:
The size of this operator's geometry along each dimension, expressed as a Position.

`isSOP` → `bool` **(Read Only)**:
True if the operator is a SOP.

## Methods

### computeBounds()

computeBounds()→ `[CLASS_Bounds]`:

Returns an object with the bounds, center and size of the SOP's geometry.

- `display` - (Keyword, Optional) If set to True, only **SOP operators** whose display flag set are included in the calculation. When False, the states of the display flag is ignored.
- `render` - (Keyword, Optional) If set to True, only **SOP operators** whose render flag set are included in the calculation. When False, the state of the render flag is ignored.

### save()

save(filepath, createFolders=False)→ `str`:

Saves the geometry to the file system. Multiple file types are supported. Returns the filename and path saved.

- `filepath` - (Optional) The path and filename to save to. If not given then a default filename will be used, and the file will be saved in the project.folder folder.
- `createFolders` - (Keyword, Optional) If True, it creates the not existent directories provided by the filepath.

```python
name = n.save()   # save in native format with default name.
n.save('output.bgeo')  # alternate format compatible with some other modelling packages.
```
