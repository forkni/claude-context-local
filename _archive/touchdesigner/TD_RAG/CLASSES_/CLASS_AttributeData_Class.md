---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Script_SOP
- Attribute_SOP
- Point_SOP
concepts:
- geometry_attributes
- sop_scripting
- data_access
- procedural_geometry
- attribute_values
- geometry_data_types
prerequisites:
- Python_fundamentals
- CLASS_Attribute_Class
- CLASS_Point_Class
- CLASS_Prim_Class
- CLASS_Vertex_Class
workflows:
- procedural_modeling
- geometry_data_processing
- reading_geometry_data
- writing_geometry_data
- data_analysis
- attribute_querying
keywords:
- attribute data
- attribute value
- geometry data
- sop scripting
- point data
- primitive data
- vertex data
- val property
- N normal
- P position
- Cd color
- float values
- vector values
- string values
- tuple values
tags:
- python
- sop
- geometry
- attribute
- scripting
- api
- data
- values
- types
relationships:
  CLASS_Attribute_Class: strong
  CLASS_Point_Class: strong
  CLASS_Prim_Class: strong
  CLASS_Vertex_Class: strong
  CLASS_Attributes_Class: medium
related_docs:
- CLASS_Attribute_Class
- CLASS_Point_Class
- CLASS_Prim_Class
- CLASS_Vertex_Class
- CLASS_Attributes_Class
hierarchy:
  secondary: sop_scripting
  tertiary: attribute_value
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- procedural_modeling
- geometry_data_processing
- reading_geometry_data
- writing_geometry_data
---

# AttributeData Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_SOP, Attribute_SOP, Point_SOP]
concepts: [geometry_attributes, sop_scripting, data_access, procedural_geometry, attribute_values, geometry_data_types]
prerequisites: [Python_fundamentals, CLASS_Attribute_Class, CLASS_Point_Class, CLASS_Prim_Class, CLASS_Vertex_Class]
workflows: [procedural_modeling, geometry_data_processing, reading_geometry_data, writing_geometry_data, data_analysis, attribute_querying]
related: [CLASS_Attribute_Class, CLASS_Point_Class, CLASS_Prim_Class, CLASS_Vertex_Class, CLASS_Attributes_Class]
relationships: {
  "CLASS_Attribute_Class": "strong",
  "CLASS_Point_Class": "strong",
  "CLASS_Prim_Class": "strong",
  "CLASS_Vertex_Class": "strong",
  "CLASS_Attributes_Class": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "sop_scripting"
  tertiary: "attribute_value"
keywords: [attribute data, attribute value, geometry data, sop scripting, point data, primitive data, vertex data, val property, N normal, P position, Cd color, float values, vector values, string values, tuple values]
tags: [python, sop, geometry, attribute, scripting, api, data, values, types]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: procedural_modeling, geometry_data_processing, reading_geometry_data

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Class Attribute Class] → [Class Point Class]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Attribute Class] → [CLASS Point Class] → [CLASS Prim Class]

**Related Topics**: procedural modeling, geometry data processing, reading geometry data

## Summary

Contains specific attribute values for geometry elements. Essential for reading and writing geometric data at the point, primitive, and vertex level.

## Relationship Justification

Strong connection to Attribute class as the definition counterpart. Directly linked to Point, Prim, and Vertex classes since AttributeData provides the actual values for these geometry components. Medium connection to Attributes collection for context.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods Overview](#methods-overview)

## Introduction

An AttributeData contains specific geometric Attribute values, associated with a [CLASS_Prim_Class](CLASS_Prim_Class.md), [CLASS_Point_Class](CLASS_Point_Class.md), or [CLASS_Vertex_Class](CLASS_Vertex_Class.md). Each value of the attribute must be of the same type, and can be one of float, string or integer. For example, a point or vertex normal attribute data, consists of 3 float values.

## Members

`owner` → `[CLASS_OP_Class]` **(Read Only)**:
The OP to which this object belongs.

`val` → `float | int | str | tuple | [CLASS_Position_Class] | [CLASS_Vector_Class]` **(Read Only)**:
The set of values contained within this object. Dependent on the type of attribute, it may return a float, integer, string, tuple, Position, or Vector. For example Normal attribute data is expressed as a Vector, while Position attribute data is expressed as a Position.

## Methods Overview

No operator specific methods.
