---
title: "Matrix Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["technical_artist", "shader_programmer", "advanced_user", "script_developer"]
completion_signals: ["can_access_matrix_properties", "understands_3d_transformations", "can_implement_matrix_math", "manages_coordinate_systems"]

operators:
- Object_COMP
- Camera_COMP
- Geometry_COMP
- GLSL_MAT
- GLSL_TOP
concepts:
- 3d_transformations
- matrix_math
- computer_graphics
- linear_algebra
- projection
- camera_model
- coordinate_systems
- transformations
prerequisites:
- Python_fundamentals
- 3d_concepts
- MODULE_td_Module
workflows:
- procedural_animation
- camera_control
- geometry_manipulation
- glsl_shaders
- rendering_setup
- 3d_scene_setup
keywords:
- 4x4 matrix
- transformation matrix
- projection matrix
- column-major
- identity matrix
- matrix multiplication
- inverse matrix
- transpose
- determinant
- translate
- rotate
- scale
- lookat
- decompose
- frustum
- fov
- stereo projection
- numpy
- tdu.Matrix
- 3d transformations
tags:
- python
- 3d
- math
- transform
- projection
- api
- linear_algebra
- tdu
- matrix
relationships:
  CLASS_Vector_Class: strong
  MODULE_td_Module: strong
  GLSL_Write_a_GLSL_Material: medium
  GLSL_Write_a_GLSL_TOP: medium
related_docs:
- CLASS_Vector_Class
- MODULE_td_Module
- GLSL_Write_a_GLSL_Material
- GLSL_Write_a_GLSL_TOP
# Enhanced search optimization
search_optimization:
  primary_keywords: ["matrix", "transformation", "3d", "math"]
  semantic_clusters: ["3d_mathematics", "matrix_operations", "coordinate_transformations"]
  user_intent_mapping:
    beginner: ["what is matrix class", "basic 3d transformations", "how to use matrices"]
    intermediate: ["matrix operations", "3d math", "transformation matrices"]
    advanced: ["complex transformations", "projection matrices", "advanced linear algebra"]

hierarchy:
  secondary: 3d_math
  tertiary: matrix_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- procedural_animation
- camera_control
- geometry_manipulation
- glsl_shaders
---

# Matrix Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Object_COMP, Camera_COMP, Geometry_COMP, GLSL_MAT, GLSL_TOP]
concepts: [3d_transformations, matrix_math, computer_graphics, linear_algebra, projection, camera_model, coordinate_systems, transformations]
prerequisites: [Python_fundamentals, 3d_concepts, MODULE_td_Module]
workflows: [procedural_animation, camera_control, geometry_manipulation, glsl_shaders, rendering_setup, 3d_scene_setup]
related: [CLASS_Vector_Class, MODULE_td_Module, GLSL_Write_a_GLSL_Material, GLSL_Write_a_GLSL_TOP]
relationships: {
  "CLASS_Vector_Class": "strong",
  "MODULE_td_Module": "strong",
  "GLSL_Write_a_GLSL_Material": "medium",
  "GLSL_Write_a_GLSL_TOP": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "3d_math"
  tertiary: "matrix_class"
keywords: [4x4 matrix, transformation matrix, projection matrix, column-major, identity matrix, matrix multiplication, inverse matrix, transpose, determinant, translate, rotate, scale, lookat, decompose, frustum, fov, stereo projection, numpy, tdu.Matrix, 3d transformations]
tags: [python, 3d, math, transform, projection, api, linear_algebra, tdu, matrix]
TD-META -->

<!-- TD-META
category: CLASS
document_type: reference
operators: [Object_COMP, Camera_COMP, Geometry_COMP, GLSL_MAT, GLSL_TOP]
concepts: [3d_transformations, matrix_math, computer_graphics, linear_algebra, projection, camera_model, coordinate_systems, transformations]
prerequisites: [Python_fundamentals, 3d_concepts, MODULE_td_Module]
workflows: [procedural_animation, camera_control, geometry_manipulation, glsl_shaders, rendering_setup, 3d_scene_setup]
related: [CLASS_Vector_Class, MODULE_td_Module, GLSL_Write_a_GLSL_Material, GLSL_Write_a_GLSL_TOP]
relationships: {
  "CLASS_Vector_Class": "strong",
  "MODULE_td_Module": "strong",
  "GLSL_Write_a_GLSL_Material": "medium",
  "GLSL_Write_a_GLSL_TOP": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "3d_math"
  tertiary: "matrix_class"
keywords: [4x4 matrix, transformation matrix, projection matrix, column-major, identity matrix, matrix multiplication, inverse matrix, transpose, determinant, translate, rotate, scale, lookat, decompose, frustum, fov, stereo projection, numpy, tdu.Matrix, 3d transformations]
tags: [python, 3d, math, transform, projection, api, linear_algebra, tdu, matrix]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: procedural_animation, camera_control, geometry_manipulation

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [3D Concepts] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Vector Class] → [MODULE td Module] → [GLSL Write a GLSL Material]

**Related Topics**: procedural animation, camera control, geometry manipulation

## Summary

Core 3D transformation class providing matrix operations for all 3D work in TouchDesigner. Essential for camera control, object transformations, and projection calculations.

## Relationship Justification

Paired with Vector class for complete 3D math coverage. Connected to GLSL guides since matrices are fundamental for shader transformations. Core component of td module's 3D capabilities.

## Content

- [Introduction](#introduction)
- [Instantiators](#instantiators)
  - [tdu.Matrix()](#tdumatrix)
  - [tdu.Matrix(columns)](#tdumatrixcolumns)
  - [tdu.Matrix(values)](#tdumatrixvalues)
  - [tdu.Matrix(quaternion)](#tdumatrixquaternion)
- [Members](#members)
- [Methods Overview](#methods-overview)
  - [transpose()](#transpose)
  - [getTranspose()](#gettranspose)
  - [invert()](#invert)
  - [getInverse()](#getinverse)
  - [determinant()](#determinant)
  - [mapUnitSquareToQuad()](#mapunitsquaretoquad)
  - [mapQuadToUnitSquare()](#mapquadtounitsquare)
  - [fillTable()](#filltable)
  - [numpyArray()](#numpyarray)
  - [identity()](#identity)
  - [copy()](#copy)
  - [translate()](#translate)
  - [rotate()](#rotate)
  - [rotateOnAxis()](#rotateonaxis)
  - [scale()](#scale)
  - [lookat()](#lookat)
  - [decompose()](#decompose)
  - [projectionFrustum()](#projectionfrustum)
  - [projectionFovX()](#projectionfovx)
  - [projectionStereo()](#projectionstereo)
- [Special Functions](#special-functions)
  - [[row, column]](#row-column)
  - [Matrix * Matrix](#matrix--matrix)
  - [Matrix - Matrix](#matrix---matrix)
  - [Matrix + Matrix](#matrix--matrix-1)
  - [Matrix * Vector](#matrix--vector)
  - [Matrix * Position](#matrix--position)

## Introduction

The matrix class holds a single 4x4 matrix for use in transformations. The matrix's data layout is in column-major format, which is to say that the matrix is multiplied from the left of vectors and positions. The translation values are stored in the last column of the matrix. A matrix is created with this line, and will always be initialized to the identity matrix.

```python
m = tdu.Matrix()
```

You can also initialize a matrix with an initial set of values. Valid arguments for initialization is another [CLASS_Matrix], a list of 16 values or 4 lists of 4 values. The entries are specified column-by-column. For example the following lines of code will produce the shown matrix:

```python
m = tdu.Matrix([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])
# or
m = tdu.Matrix([1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16])
# matrix values
1  5  9   13
2  6  10  14
3  7  11  15
4  8  12  16
```

You can also get transformation and projection matrices from [CLASS_ObjectCOMP] and [CLASS_CameraCOMP] by using the various methods such as `transform()`, `pretransform()`, `projection()`.

## Instantiators

### tdu.Matrix()

tdu.Matrix()→ `[CLASS_Matrix]`:

Initialize the matrix as a identity matrix.

### tdu.Matrix(columns)

tdu.Matrix([1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [13, 14, 15, 16])→ `[CLASS_Matrix]`:

Initialize the matrix with a set of 4 lists of 4 values. Each list is a column in the matrix.

### tdu.Matrix(values)

tdu.Matrix([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16])→ `[CLASS_Matrix]`:

Initialize the matrix with a set of 16 values. The values are listed column-by-column.

### tdu.Matrix(quaternion)

tdu.Matrix([0, 0, 0, 1])→ `[CLASS_Matrix]`:

Initialize the matrix using a quaternion.

## Members

`vals` → `float`:
Get or set the set of Matrix values.

`rows` → `list of lists` **(Read Only)**:
The list of Matrix rows, each a list of values.

`cols` → `list of lists` **(Read Only)**:
The list of Matrix columns, each a list of values.

## Methods Overview

### transpose()

transpose()→ `None`:

Transpose the values in the matrix.

```python
m.transpose() # m now contains the transpose of the matrix
```

### getTranspose()

getTranspose()→ `None`:

Returns the transpose of the matrix, leaving the matrix itself unchanged.

```python
m2 = m.getTranspose()
```

### invert()

invert()→ `None`:

Inverts the values in the matrix.

```python
m.invert() # m now contains the inverse of the matrix
```

### getInverse()

getInverse()→ `[CLASS_Matrix]`:

Returns the inverse of the matrix, leaving the matrix itself unchanged.

```python
m2 = m.getInverse()
```

### determinant()

determinant()→ `float`:

Returns the determinant of the matrix.

```python
l = m.determinant()
```

### mapUnitSquareToQuad()

mapUnitSquareToQuad(blX, blY, brX, brY, tlX, tlY, trX, trY)→ `None`:

Set the matrix to be a projection matrix that maps coordinates from to a unit square (0,0) -> (1,1) space to a space defined by an arbitrary quadrilateral (blX, blY) -> (trX, trY). The 4 corners of the quadrilateral are given ('bl' means bottom left, 'tr' means top right etc.).

### mapQuadToUnitSquare()

mapQuadToUnitSquare(blX, blY, brX, brY, tlX, tlY, trX, trY)→ `None`:

Is the inverse of `mapUnitSquareToQuad()`. Mapping coordinates in an arbitrary quadrilateral into a space defined by the unit square.

### fillTable()

fillTable(tableDAT)→ `None`:

Fill in the contents of a table from the matrix which the method is called upon.

- `tableDAT` - The table to be filled.

### numpyArray()

numpyArray()→ `numpy.array`:

Returns this matrix as a 4x4 NumPy array.

### identity()

identity()→ `None`:

Replaces the values in the matrix with the identity matrix.

```python
m.identity() # now contains the identity matrix
```

### copy()

copy()→ `[CLASS_Matrix_Class]`:

Returns a new matrix that is a copy of the matrix.

```python
newM = m.copy() # newM will have the same values as m, m is unchanged
```

### translate()

translate(tx, ty, tz, fromRight=False)→ `None`:

Multiplies the current matrix by a new translation matrix created from tx, ty and tz. The translation is applied from the left of the matrix by default. That is to say, if T is the new translation matrix, and M is the current matrix, then the result of this operation is M = T * M.

- `tx, ty, tz` - The translation value in each axis.
- `fromRight` - (Keyword, Optional) If True, the translation matrix will be multiplied from the right instead of the left.

```python
m = tdu.Matrix()
m.translate(5, 0, 10)
```

### rotate()

rotate(rx, ry, rz, fromRight=False, pivot=None)→ `None`:

Multiplies the current matrix by 3 rotation matrices, first a rotation around the X axis by rx degrees, followed by a rotation around the Y axis by ry degrees, followed by the same for rz. The rotation values are in degrees. The rotation is applied from the left of the matrix by default. So if M is the current matrix, then the result of this operation is M = RZ *RY* RX * M.

- `rx, ry, rz` - The rotation value around each X, Y and Z axis. The value is in degrees. The rotation is applied in XYZ order.
- `fromRight` - (Keyword, Optional) If True, the rotation matrix will be multiplied from the right instead of the left. In this case the operation is M = M *RZ* RY * RX.
- `pivot` - (Keyword, Optional) If given, the rotation will be applied around the given pivot. The pivot should be a [CLASS_Vector_Class](CLASS_Vector_Class.md), [CLASS_Position_Class](CLASS_Position_Class.md) or a list with 3 entries.

```python
m = tdu.Matrix()
m.rotate(45, 0, 0)

m = tdu.Matrix()
m.rotate(0, 0, 90, pivot=[0, 5, 0])

m = tdu.Matrix()
p = tdu.Position(0, 5, 0)
m.rotate(0, 90, 0, pivot=p)
```

### rotateOnAxis()

rotateOnAxis(rotationAxis, angle, fromRight=False, pivot=None)→ `None`:

Multiplies the current matrix by a new rotation matrix created by rotation angle degrees around the axis specified by rotationAxis. The angle is in degrees. The rotation is applied from the left of the matrix by default. That is to say, if R is the new rotation matrix specified by rotationAxis and angle, and M is the current matrix, then the result of this operation is M = R * M.

- `rotationAxis` - A axis to rotate around. This should be a [CLASS_Vector_Class](CLASS_Vector_Class.md) or a list with 3 entries. It does not need to be normalized.
- `angle` - The amount to rotate around the axis, specified in degrees.
- `fromRight` - (Keyword, Optional) If True, the rotation matrix will be multiplied from the right instead of the left.
- `pivot` - (Keyword, Optional) If given, the rotation will be applied around the given pivot. The pivot should be a [CLASS_Vector_Class](CLASS_Vector_Class.md), [CLASS_Position_Class](CLASS_Position_Class.md) or a list with 3 entries.

### scale()

scale(sx, sy, sz, fromRight=False, pivot=None)→ `None`:

Multiplies the current matrix by a scale matrix created from sx, sy and sz. The scale is applied from the left of the matrix by default. That is to say, if S is the new scale matrix, and M is the current matrix, then the result of this operation is M = S * M.

- `sx, sy, sz` - The scale value along each X, Y and Z axis.
- `fromRight` - (Keyword, Optional) If True, the scale matrix will be multiplied from the right instead of the left.
- `pivot` - (Keyword, Optional) If given, the scale will be applied around the given pivot. The pivot should be a [CLASS_Vector_Class](CLASS_Vector_Class.md), [CLASS_Position_Class](CLASS_Position_Class.md) or a list with 3 entries.

```python
m = tdu.Matrix()
m.scale(2, 1, 1)

m = tdu.Matrix()
m.scale(2, 1, 2, pivot=[0, 5, 0])

m = tdu.Matrix()
p = tdu.Position(0, 5, 0)
m.scale(1, 2, 1, pivot=p)
```

### lookat()

lookat(eyePos, target, up)→ `None`:

Multiplies the current matrix by a lookat matrix created using the given values to the matrix. The lookat matrix is applied from the left of the matrix by default. That is to say, if L is the new lookat matrix, and M is the current matrix, then the result of this operation is M = L * M. The values for to parameters can be given as anything that can be treated as a list of 3 values. E.g a [CLASS_Vector_Class](CLASS_Vector_Class.md), [CLASS_Position_Class](CLASS_Position_Class.md) or simply a list of size 3.

- `eyePos` - The position in space of the eye/camera.
- `target` - The position in space that should be looked at, from the eyePos.
- `up` - The Up vector. Ensure the up vector isn't pointing in the same direction as the lookat direction.

```python
m = tdu.Matrix()
eyeP = tdu.Position(0, 0, -5)
target = tdu.Position(0, 5, 5)
up = tdu.Position(0, 1, 0)
m.lookat(eyeP, target, up)
```

### decompose()

decompose()→ `Tuple(Tuple, Tuple, Tuple)`:

Decomposes the matrix into its scale, rotate and translate values. These are the same as the translate, rotate and scale that are in the [CLASS_GeometryCOMP_Class](CLASS_GeometryCOMP_Class.md) and other Object components. However due to rotations being able to be solved in different ways, it's likely a decomposed transform matrix from a Geometry COMP will not have the same values as its parameter. The resulting transform is the same though. This function returns a tuple of tuples (3 tuples), which are the scale, rotate and translate values respectively.

```python
s, r, t = m.decompose()
```

### projectionFrustum()

projectionFrustum(left, right, bottom, top, near, far)→ `None`:

Replaces the contents of the matrix with a projection matrix using the given frustum extents. The left, right, bottom, top extents are located on the near plane. The depth range generated by this matrix will be [0,1] from near to far, as is required by Vulkan.

### projectionFovX()

projectionFovX(fovX, aspectX, aspectY, near, far)→ `None`:

Replaces the contents of the matrix with a projection matrix defined by the FOV(given in degrees), an aspect ratio and near/far planes. The depth range generated by this matrix will be [0,1] from near to far, as is required by Vulkan.

- `fovX` - The horizontal FOV, specified in degrees.
- `aspectX, aspectY` - The aspect ration values. These can be something like 16 and 9 for an aspect or the render resolution such as 1920 and 1080. The results will be the same for the same ratio.

### projectionStereo()

projectionStereo(ipd, convergeZ, fovX, aspectX, aspectY, near, far, rightEye = false)→ `None`:

Replaces the contents of the matrix with an asymetrical projection matrix suitable for stereo rendering. The left eye's projection matrix is given by default, set rightEye=True to get the right eye's instead. For proper rendering, the cameras will also need to be translated in X by -ipd/2 and +ipd/2 for the left and right eyes respectively. The depth range generated by this matrix will be [0,1] from near to far, as is required by Vulkan.

- `ipd` - Interpupillary distance of the user, generally specified in meters. Typically between 0.05 and 0.08
- `covergeZ` - distance in Z from the camera where the stereo convergence should occur, in the same units as ipd.
- `fovX` - The field of view in the X direction, in degrees.
- `aspectX, aspectY` - The aspect ratio values. These can be something like 16 and 9 for an aspect or the render resolution such as 1920 and 1080. The results will be the same for the same ratio.
- `near, far` - The near and far plane distances.
- `rightEye` - (Keyword, Optional) If set to True, the matrix will contain the projection for the right eye, otherwise it will contain the projection for the left eye.

## Special Functions

### [row, column]

[row, column]→ `float`:

Gets or sets the specified entry in the matrix.

```python
tx = m[0, 3]
m[0, 3] = tx + 5
```

### Matrix * Matrix

Matrix * Matrix→ `[CLASS_Matrix]`:

Performs a matrix multiplication returns the results in a new matrix.

```python
newM = m1 * m2
```

### Matrix - Matrix

Matrix - Matrix→ `[CLASS_Matrix_Class]`:

Subtracts the matrices, component-by-component, and returns the results in a new matrix.

### Matrix + Matrix

Matrix + Matrix→ `[CLASS_Matrix_Class]`:

Adds the matrices, component-by-component, and returns the results in a new matrix.

### Matrix * Vector

[CLASS_Matrix_Class] * [CLASS_Vector_Class]→ `[CLASS_Vector_Class]`:

Multiplies the vector by the matrix and returns the a new vector as the result. Since a Vector is direction only and has no notion of a position, the translate part of the matrix does not get applied to the vector.

```python
newV = M * v
```

### Matrix * Position

[CLASS_Matrix_Class] * [CLASS_Position_Class]→ `[CLASS_Position_Class]`:

Multiplies the position by the matrix and returns the a new position as the result. If the matrix was not an transformation matrix, such as a projection matrix instead, the perspective divide by W will automatically be applied to X, Y and Z.

```python
newP = M * p
```
