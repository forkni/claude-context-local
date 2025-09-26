---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Script_SOP
- Attribute_SOP
concepts:
- geometry_attributes
- sop_scripting
- procedural_geometry
- data_manipulation
- attribute_collections
- geometry_metadata_management
prerequisites:
- Python_fundamentals
- SOP_basics
- CLASS_SOP_Class
workflows:
- procedural_modeling
- custom_geometry_tool_creation
- geometry_data_management
- attribute_querying
- batch_attribute_operations
keywords:
- attributes collection
- geometry attributes
- sop scripting
- pointAttribs
- primAttribs
- vertexAttribs
- create attribute
- access attribute
- custom attribute
- standard attributes
- N normal
- Cd color
- uv coordinates
- attribute management
- batch operations
tags:
- python
- sop
- geometry
- attribute
- scripting
- api
- collection
- management
relationships:
  CLASS_Attribute_Class: strong
  CLASS_SOP_Class: strong
  CLASS_Point_Class: strong
  CLASS_Prim_Class: strong
  CLASS_Vertex_Class: strong
  CLASS_AttributeData_Class: medium
related_docs:
- CLASS_Attribute_Class
- CLASS_SOP_Class
- CLASS_Point_Class
- CLASS_Prim_Class
- CLASS_Vertex_Class
- CLASS_AttributeData_Class
hierarchy:
  secondary: sop_scripting
  tertiary: attribute_collection
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- procedural_modeling
- custom_geometry_tool_creation
- geometry_data_management
- attribute_querying
---

# Attributes Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_SOP, Attribute_SOP]
concepts: [geometry_attributes, sop_scripting, procedural_geometry, data_manipulation, attribute_collections, geometry_metadata_management]
prerequisites: [Python_fundamentals, SOP_basics, CLASS_SOP_Class]
workflows: [procedural_modeling, custom_geometry_tool_creation, geometry_data_management, attribute_querying, batch_attribute_operations]
related: [CLASS_Attribute_Class, CLASS_SOP_Class, CLASS_Point_Class, CLASS_Prim_Class, CLASS_Vertex_Class, CLASS_AttributeData_Class]
relationships: {
  "CLASS_Attribute_Class": "strong",
  "CLASS_SOP_Class": "strong",
  "CLASS_Point_Class": "strong",
  "CLASS_Prim_Class": "strong",
  "CLASS_Vertex_Class": "strong",
  "CLASS_AttributeData_Class": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "sop_scripting"
  tertiary: "attribute_collection"
keywords: [attributes collection, geometry attributes, sop scripting, pointAttribs, primAttribs, vertexAttribs, create attribute, access attribute, custom attribute, standard attributes, N normal, Cd color, uv coordinates, attribute management, batch operations]
tags: [python, sop, geometry, attribute, scripting, api, collection, management]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: procedural_modeling, custom_geometry_tool_creation, geometry_data_management

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Sop Basics] → [Class Sop Class]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Attribute Class] → [CLASS SOP Class] → [CLASS Point Class]

**Related Topics**: procedural modeling, custom geometry tool creation, geometry data management

## Summary

Collection class for managing sets of geometry attributes. Provides access to pointAttribs, primAttribs, and vertexAttribs collections for comprehensive geometry attribute management.

## Relationship Justification

Central hub for attribute management, strongly connected to individual Attribute class and all geometry component classes. Provides the main interface for accessing and creating attributes on SOPs. Links to AttributeData for value access patterns.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods Overview](#methods-overview)
  - [[name]](#name)
  - [create()](#create)

## Introduction

An Attributes object describes a set of [CLASS_Prim_Class](CLASS_Prim_Class.md), [CLASS_Point_Class](CLASS_Point_Class.md), or [CLASS_Vertex_Class](CLASS_Vertex_Class.md) attributes, contained within a [CLASS_SOP_Class](CLASS_SOP_Class.md).

## Members

`owner` → `[CLASS_OP_Class]` **(Read Only)**:
The OP to which this object belongs.

## Methods Overview

### [name]

[name]→ `[CLASS_Attribute_Class]`:

Attributes can be accessed using the [] subscript operator.

- `name` - The name of the attribute.

```python
attribs = scriptOP.pointAttribs # get the Attributes object
normals = attribs['N']
```

### create()

create(name, default)→ `[CLASS_Attribute_Class]`:

Create a new Attribute.

- `name` - The name of the attribute.
- `default` - (Optional) Specify default values for custom attributes. For standard attributes, default values are implied.

Standard attributes are: N (normal), uv (texture), T (tangent), v (velocity), Cd (diffuse color).

```python
# create a Normal attribute with implied defaults.
n = scriptOP.pointAttribs.create('N')

# set the X component of the first point's Normal attribute.
scriptOp.points[0].N[0] = 0.3 

# Create a Vertex Attribute called custom1 with defaults set to (0.0, 0.0)
n = scriptOP.vertexAttribs.create('custom1', (0.0, 0.0) )

# Create a Primitive Attribute called custom2 defaulting to 1
n = scriptOP.primAttribs.create('custom2', 1 )
```
