---
title: "Vector Class"
category: CLASS
document_type: reference
difficulty: beginner
time_estimate: 15-20 minutes
user_personas: ["script_developer", "3d_developer"]
operators: []
concepts: ["vector_math", "3d_geometry", "linear_algebra"]
prerequisites: ["Python_fundamentals", "3d_transforms"]
workflows: ["procedural_geometry", "3d_animation", "shader_programming"]
keywords: ["vector", "3d", "math", "matrix", "normalize", "dot", "cross"]
tags: ["python", "api", "core", "3d", "math"]
related_docs:
- CLASS_Matrix
- CLASS_Position
- MODULE_tdu
---

# Vector Class

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods](#methods)
- [Special Functions](#special-functions)

## Introduction

The vector class holds a single 3 component vector. A vector describes a direction in space, and it's important to use a vector or Position as appropriate for the data that is being calculated. When being multiplied by a Matrix, this class will implicitly have a 4th component (W component) of 0. A new vector can be created without any arguments, with 3 arguments for the x,y,z values, or with a single argument which is a variable that has 3 entries such as a list of length 3, or a position or vector.

Examples of creating a vector:

```python
v = tdu.Vector() # starts as (0, 0, 0)
v2 = tdu.Vector(0, 0, -1)
values = [0, 1, 0]
v3 = tdu.Vector(values)

# vectors can be accessed like Python lists
print(v3[1])# same as v3.y
v3[2] = 1# same as v3.z
```

## Members

### x

`x` → `float`:

> Gets or sets the X component of the vector.

### y

`y` → `float`:

> Gets or sets the Y component of the vector.

### z

`z` → `float`:

> Gets or sets the Z component of the vector.

## Methods

### angle()

`angle(vec)`→ `float`:

> Returns the angel (in degrees) between the current vector and specified vector (vec).
>
> - `vec` - The other vector to calculate the angle to.
>
> ```python
> d = v.angle(v2)
> ```

### scale()

`scale(x, y, z)`→ `None`:

> Scales each component of the vector by the specified values.
>
> - `x`, `y`, `z` - The values to scale each component of the vector by.
>
> ```python
> v.scale(1, 2, 1)
> ```

### normalize()

`normalize()`→ `None`:

> Makes the length of this vector 1.
>
> ```python
> m.normalize()
> ```

### length()

`length()`→ `float`:

> Returns the length of this vector.
>
> ```python
> l = m.length()
> ```

### lengthSquared()

`lengthSquared()`→ `float`:

> Returns the squared length of this vector.
>
> ```python
> l = v.lengthSquared()
> ```

### copy()

`copy()`→ `tdu.Vector`:

> Returns a new vector that is a copy of the vector.
>
> ```python
> newV = v.copy()
> ```

### distance()

`distance(vec)`→ `float`:

> Returns the distance of the current vector to specified vector (vec).
>
> - `vec` - The other vector to calculate the distance to.
>
> ```python
> l = v.distance(v2)
> ```

### lerp()

`lerp(vec2, t)`→ `tdu.Vector`:

> Returns the linear interpolation of this vector and vec2. That is `vec1 * (1.0 - t) + vec2 * t`, where `vec1` is the current vector. The value for `t` is not restricted to the range [0, 1].
>
> - `vec2` - The other vector to interpolate to.
> - `t` - The interpolation factor.
>
> ```python
> l = v.lerp(v2, t)
> ```

### slerp()

`slerp(vec2, t)`→ `tdu.Vector`:

> Returns the spherical interpolation of this vector and vec2. The value for `t` is not restricted to the range [0, 1].
>
> - `vec2` - The other vector to interpolate to.
> - `t` - The interpolation factor.
>
> ```python
> l = v.slerp(v2, t)
> ```

### dot()

`dot(vec)`→ `float`:

> Returns the dot product of this vector and the passed vector.
>
> - `vec` - The other vector to use to calculate the dot product
>
> ```python
> d = v.dot(otherV)
> ```

### cross()

`cross(vec)`→ `tdu.Vector`:

> Returns the cross product of this vector and the passed vector. The operation is `self cross vec`.
>
> - `vec` - The other vector to use to calculate the cross product.
>
> ```python
> c = v.cross(otherV)
> ```

### project()

`project(vec, vec)`→ `None`:

> Projects this vector onto the plan defined by `vec1` and `vec2`. Both `vec1` and `vec2` must be normalized. The result may not be normalized.
>
> - `vec1`, `vec2` - The vectors that specify the plane to project onto. Must be normalized.
>
> ```python
> v.project(v1, v2)
> ```

### reflect()

`reflect(vec)`→ `None`:

> Reflects the current vector about the specified vector (vec).
>
> - `vec` - The vector to reflect about.
>
> ```python
> v.reflect(v2)
> ```

## Special Functions

### tdu.Vector[i]

`tdu.Vector[i]`→ `float`:

> Gets or sets the component of the vector specified by `i`, where `i` can be 0, 1, or 2.
>
> ```python
> y = v[1]
> v[1] = y * 2.0
> ```

### tdu.Vector * float

`tdu.Vector * float`→ `tdu.Vector`:

> Scales the vector by the give float scalar and returns a new vector as the result.
>
> ```python
> v = v * 2.0
> v = 2.0 * v
> ```

### tdu.Vector + float

`tdu.Vector + float`→ `tdu.Vector`:

> Adds the given scalar to all 3 components of the vector and returns a new vector as the result.
>
> ```python
> v = v + 5.0
> v = 5.0 + v
> ```

### tdu.Vector - float

`tdu.Vector - float`→ `tdu.Vector`:

> Subtracts the given scalar from all 3 components of the vector and returns a new vector as the result.
>
> ```python
> v = v - 1.5
> v = 1.5 - v
> ```

### tdu.Vector + tdu.Vector

`tdu.Vector + tdu.Vector`→ `tdu.Vector`:

> Adds the two vectors to create a new vector.
>
> ```python
> v3 = v1 + v2
> ```

### tdu.Vector - tdu.Vector

`tdu.Vector - tdu.Vector`→ `tdu.Vector`:

> Subtracts the two vectors to create a new vector.
>
> ```python
> v3 = v1 - v2
> ```

### tdu.Vector += tdu.Vector

`tdu.Vector += tdu.Vector`→ `tdu.Vector`:

> Adds the 2nd vector to the 1st vector, the 1st vector will contain the result of the operation.
>
> ```python
> v1 += v2
> ```

### tdu.Vector += float

`tdu.Vector += float`→ `tdu.Vector`:

> Adds the given scalar to all 3 components of the vector, the vector will contain the result of the operation.
>
> ```python
> v1 += 0.4
> ```

### tdu.Vector -= tdu.Vector

`tdu.Vector -= tdu.Vector`→ `tdu.Vector`:

> Subtracts the 2nd vector from the 1st vector, the 1st vector will contain the result of the operation.
>
> ```python
> v1 -= v2
> ```

### tdu.Matrix * tdu.Vector

`tdu.Matrix * tdu.Vector`→ `tdu.Vector`:

> Multiplies the vector by the matrix and returns the a new vector as the result. Since a Vector is direction only and has no notion of a position, the translate part of the matrix does not get applied to the vector.
>
> ```python
> v = M * v
> ```

### tdu.Vector / float

`tdu.Vector / float`→ `tdu.Vector`:

> Divides each component of the vector by the scalar and returns the a new vector as the result.
>
> ```python
> v = v / 0.2
> ```

### tdu.Vector *= tdu.Matrix

`tdu.Vector *= tdu.Matrix`→ `tdu.Vector`:

> Multiplies the vector by the matrix, the vector will contain the result. The vector is multiplied on the right of the matrix. This is the same as doing `v = M * v`, although more efficient since it doesn't require assigning a new vector to `v`. Since a Vector is direction only and has no notion of a position, the translate part of the matrix does not get applied to the vector.
>
> ```python
> v *= M
> ```

### tdu.Vector *= float

`tdu.Vector *= float`→ `tdu.Vector`:

> Scales all 3 components of the vector by the given scalar. The vector will contain the result.
>
> ```python
> v *= 1.1
> ```

### tdu.Vector *= tdu.Vector

`tdu.Vector *= tdu.Vector`→ `tdu.Vector`:

> Does a component-wise scale of all 3 components of the vector by the components of the 2nd vector. The vector will contain the result.
>
> ```python
> v1 *= v2
> ```

### abs(tdu.Vector)

`abs(tdu.Vector)`→ `tdu.Vector`:

> Returns a new vector with all 3 components being the absolute value of the given vector's components.
>
> ```python
> v2 = abs(v1)
> ```

### -tdu.Vector

`-tdu.Vector`→ `tdu.Vector`:

> Returns a new vector with all 3 components being negated.
>
> ```python
> v2 = -v1
> ```
