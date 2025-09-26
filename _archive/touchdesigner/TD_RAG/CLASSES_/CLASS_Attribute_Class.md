---
title: "CLASS_Attribute_Class"
category: CLASS
document_type: reference
difficulty: intermediate
n# Enhanced metadata
user_personas: ["script_developer", "intermediate_user", "automation_specialist"]
completion_signals: ["can_access_class_properties", "understands_class_management", "can_implement_class_functionality"]

time_estimate: 10-15 minutes
operators:
- Script_SOP
- Attribute_SOP
- AttributeCreate_SOP
concepts:
- geometry_attributes
- sop_scripting
- data_manipulation
- procedural_geometry
- attribute_properties
- geometry_metadata
prerequisites:
- Python_fundamentals
- SOP_basics
- CLASS_Attributes_Class
workflows:
- procedural_modeling
- geometry_data_processing
- custom_attribute_management
- point_cloud_processing
- mesh_analysis
keywords:
- attribute definition
- geometry properties
- sop scripting
- normal
- uv
- color
- Cd
- N
- P
- destroy attribute
- attribute values
- standard attributes
- custom attributes
- point attributes
- primitive attributes
- vertex attributes
tags:
- python
- sop
- geometry
- attribute
- scripting
- api
- procedural
- metadata
- properties
relationships:
  CLASS_Attributes_Class: strong
  CLASS_AttributeData_Class: strong
  CLASS_Point_Class: strong
  CLASS_Prim_Class: strong
  CLASS_Vertex_Class: strong
  CLASS_SOP_Class: medium
related_docs:
- CLASS_Attributes_Class
- CLASS_AttributeData_Class
- CLASS_Point_Class
- CLASS_Prim_Class
- CLASS_Vertex_Class
- CLASS_SOP_Class
hierarchy:
  secondary: sop_scripting
  tertiary: attribute_definition
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- procedural_modeling
- geometry_data_processing
- custom_attribute_management
- point_cloud_processing
---

# Attribute Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_SOP, Attribute_SOP, AttributeCreate_SOP]
concepts: [geometry_attributes, sop_scripting, data_manipulation, procedural_geometry, attribute_properties, geometry_metadata]
prerequisites: [Python_fundamentals, SOP_basics, CLASS_Attributes_Class]
workflows: [procedural_modeling, geometry_data_processing, custom_attribute_management, point_cloud_processing, mesh_analysis]
related: [CLASS_Attributes_Class, CLASS_AttributeData_Class, CLASS_Point_Class, CLASS_Prim_Class, CLASS_Vertex_Class, CLASS_SOP_Class]
relationships: {
  "CLASS_Attributes_Class": "strong",
  "CLASS_AttributeData_Class": "strong",
  "CLASS_Point_Class": "strong",
  "CLASS_Prim_Class": "strong",
  "CLASS_Vertex_Class": "strong",
  "CLASS_SOP_Class": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "sop_scripting"
  tertiary: "attribute_definition"
keywords: [attribute definition, geometry properties, sop scripting, normal, uv, color, Cd, N, P, destroy attribute, attribute values, standard attributes, custom attributes, point attributes, primitive attributes, vertex attributes]
tags: [python, sop, geometry, attribute, scripting, api, procedural, metadata, properties]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: procedural_modeling, geometry_data_processing, custom_attribute_management

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Sop Basics] → [Class Attributes Class]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Attributes Class] → [CLASS AttributeData Class] → [CLASS Point Class]

**Related Topics**: procedural modeling, geometry data processing, custom attribute management

## Summary

Core geometry attribute class for SOP scripting. Defines individual attributes like normals, UVs, and colors for geometry processing workflows.
A Attribute describes a general geometric Attribute, associated with a [CLASS_Prim_Class](CLASS_Prim_Class.md), [CLASS_Point_Class](CLASS_Point_Class.md), or [CLASS_Vertex_Class](CLASS_Vertex_Class.md). Specific values for each Prim, Point or Vertex are described with the [CLASS_AttributeData_Class](CLASS_AttributeData_Class.md). Lists of attributes for the SOP are described with the [CLASS_Attributes_Class](CLASS_Attributes_Class.md).

## Relationship Justification

Strong bidirectional connections to Attributes collection class and AttributeData value class. Connected to geometry component classes (Point, Prim, Vertex) since attributes are applied to these elements. Links to SOP class for broader geometry scripting context.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods Overview](#methods-overview)
  - [destroy()](#destroy)
  - [vals()](#vals)
- [Accessing Attributes](#accessing-attributes)

## Introduction

An Attribute describes a general geometric Attribute, associated with a [CLASS_Prim_Class](CLASS_Prim_Class.md), [CLASS_Point_Class](CLASS_Point_Class.md), or [CLASS_Vertex_Class](CLASS_Vertex_Class.md). Specific values for each Prim, Point or Vertex are described with the [CLASS_AttributeData_Class](CLASS_AttributeData_Class.md). Lists of attributes for the SOP are described with the [CLASS_Attributes_Class](CLASS_Attributes_Class.md).

## Members

`owner` → `[CLASS_OP_Class]` **(Read Only)**:
The OP to which this object belongs.

`name` → `str` **(Read Only)**:
The name of this attribute.

`size` → `int` **(Read Only)**:
The number of values associated with this attribute. For example, a normal attribute has a size of 3.

`type` → `float | int | str | tuple | [CLASS_Position_Class] | [CLASS_Vector_Class]` **(Read Only)**:
The type associated with this attribute: float, integer, string, tuple, Position, or Vector.

`default` → `float | int | str | tuple | [CLASS_Position_Class] | [CLASS_Vector_Class]` **(Read Only)**:
The default values associated with this attribute. Dependent on the type of attribute, it may return a float, integer, string, tuple, Position, or Vector.

## Methods Overview

### destroy()

destroy()→ `None`:

Destroy the attribute referenced by this object.

```python
n = scriptOP.pointAttribs['N'].destroy()
```

### vals()

vals(delayed=False)→ `list`:

Returns the attribute values as a list.

- `delayed` - (Keyword, Optional) If set to True, the download results will be delayed until the next call to `vals()`, avoiding stalling the GPU waiting for the result immediately.

## Accessing Attributes

See [CLASS_Attributes_Class](CLASS_Attributes_Class.md) for examples on how to access individual attributes.
