---
title: "Vertex Class"
category: CLASS
document_type: reference
difficulty: beginner
time_estimate: 5-10 minutes
user_personas: ["script_developer", "3d_developer"]
operators: []
concepts: ["geometry", "vertex", "primitive", "point", "attribute"]
prerequisites: ["Python_fundamentals", "3d_geometry"]
workflows: ["procedural_geometry", "geometry_manipulation"]
keywords: ["vertex", "geometry", "prim", "point", "attribute"]
tags: ["python", "api", "core", "3d", "geometry"]
related_docs:
- CLASS_Prim
- CLASS_Point
- CLASS_Attribute
- CLASS_OP
---

# Vertex Class

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Attributes](#attributes)
- [Methods](#methods)

## Introduction

A Vertex describes an instance to a single geometry vertex, contained within a [CLASS_Prim] object.

## Members

### index

`index` → `int` (Read Only):

> The vertex position in its primitive.

### owner

`owner` → `[CLASS_OP]` (Read Only):

> The OP to which this object belongs.

### point

`point` → `[CLASS_Point]`:

> Get or set the point to which the vertex refers.

### prim

`prim` → `[CLASS_Prim]` (Read Only):

> The prim to which the vertex belongs.

## Attributes

In addition to the above members, all attributes are members as well.

For example, if the Vertex contains texture coordinates, they may be accessed with: `Vertex.uv`

See: [CLASS_Attribute] for more information.

## Methods

No operator specific methods.
