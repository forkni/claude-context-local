---
category: GLSL
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- GLSL_TOP
- GLSL_MAT
- Script_TOP
concepts:
- glsl_functions
- mathematical_functions
- texture_functions
- geometric_functions
- vector_operations
- matrix_operations
- trigonometric_functions
- exponential_functions
- common_functions
prerequisites:
- GLSL_fundamentals
- vector_math
- linear_algebra
workflows:
- shader_development
- mathematical_operations_in_shaders
- texture_sampling
- geometric_calculations
- procedural_animation
- generative_graphics
keywords:
- glsl built-in functions
- mathematical functions
- trigonometric
- sin
- cos
- tan
- length
- normalize
- dot
- cross
- mix
- step
- smoothstep
- texture
- texelFetch
- abs
- floor
- ceil
- fract
- mod
- min
- max
- clamp
- pow
- sqrt
- exp
- log
- radians
- degrees
tags:
- glsl
- reference
- functions
- mathematical
- texture
- geometric
- comprehensive
- core
- foundation
relationships:
  GLSL_Structures_and_Arrays_Reference: strong
  GLSL_TexelFetch_vs_texture: strong
  GLSL_Ray_Marching_Tutorial: medium
  GLSL_Distance_Functions: medium
related_docs:
- GLSL_Structures_and_Arrays_Reference
- GLSL_TexelFetch_vs_texture
- GLSL_Ray_Marching_Tutorial
- GLSL_Distance_Functions
hierarchy:
  secondary: glsl_reference
  tertiary: built_in_functions
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- shader_development
- mathematical_operations_in_shaders
- texture_sampling
- geometric_calculations
---

# GLSL Built-In Functions Reference

<!-- TD-META
category: GLSL
document_type: reference
operators: [GLSL_TOP, GLSL_MAT, Script_TOP]
concepts: [glsl_functions, mathematical_functions, texture_functions, geometric_functions, vector_operations, matrix_operations, trigonometric_functions, exponential_functions, common_functions]
prerequisites: [GLSL_fundamentals, vector_math, linear_algebra]
workflows: [shader_development, mathematical_operations_in_shaders, texture_sampling, geometric_calculations, procedural_animation, generative_graphics]
related: [GLSL_Structures_and_Arrays_Reference, GLSL_TexelFetch_vs_texture, GLSL_Ray_Marching_Tutorial, GLSL_Distance_Functions]
relationships: {
  "GLSL_Structures_and_Arrays_Reference": "strong",
  "GLSL_TexelFetch_vs_texture": "strong",
  "GLSL_Ray_Marching_Tutorial": "medium",
  "GLSL_Distance_Functions": "medium"
}
hierarchy:
  primary: "shader_programming"
  secondary: "glsl_reference"
  tertiary: "built_in_functions"
keywords: [glsl built-in functions, mathematical functions, trigonometric, sin, cos, tan, length, normalize, dot, cross, mix, step, smoothstep, texture, texelFetch, abs, floor, ceil, fract, mod, min, max, clamp, pow, sqrt, exp, log, radians, degrees]
tags: [glsl, reference, functions, mathematical, texture, geometric, comprehensive, core, foundation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming reference for GPU development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: shader_development, mathematical_operations_in_shaders, texture_sampling

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Fundamentals] → [Vector Math] → [Linear Algebra]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Structures and Arrays Reference] → [GLSL TexelFetch vs texture] → [GLSL Ray Marching Tutorial]

**Related Topics**: shader development, mathematical operations in shaders, texture sampling

## Summary

Comprehensive reference for all GLSL built-in functions covering mathematical, trigonometric, texture sampling, and geometric operations. Essential foundation reference for all shader development in TouchDesigner.

## Relationship Justification

Core reference that connects to all GLSL documentation areas. Strong links to texture sampling guides and data structures. Foundation for advanced techniques like ray marching and distance functions.

## Content

- [Introduction](#introduction)
- [Type Placeholders](#type-placeholders)
- [Precision Qualifications](#precision-qualifications)
- [Angle and Trigonometry Functions](#angle-and-trigonometry-functions)
  - [radians()](#radians)
  - [degrees()](#degrees)
  - [sin()](#sin)
  - [cos()](#cos)
  - [tan()](#tan)
  - [asin()](#asin)
  - [acos()](#acos)
  - [atan()](#atan)
  - [sinh()](#sinh)
  - [cosh()](#cosh)
  - [tanh()](#tanh)
  - [asinh()](#asinh)
  - [acosh()](#acosh)
  - [atanh()](#atanh)
- [Exponential Functions](#exponential-functions)
  - [pow()](#pow)
  - [exp()](#exp)
  - [log()](#log)
  - [exp2()](#exp2)
  - [log2()](#log2)
  - [sqrt()](#sqrt)
  - [inversesqrt()](#inversesqrt)
- [Common Functions](#common-functions)
  - [abs()](#abs)
  - [sign()](#sign)
  - [floor()](#floor)
  - [trunc()](#trunc)
  - [round()](#round)
  - [roundEven()](#roundeven)
  - [ceil()](#ceil)
  - [fract()](#fract)
  - [mod()](#mod)
  - [modf()](#modf)
  - [min()](#min)
  - [max()](#max)
  - [clamp()](#clamp)
  - [mix()](#mix)
  - [step()](#step)
  - [smoothstep()](#smoothstep)
  - [isnan()](#isnan)
  - [isinf()](#isinf)
  - [floatBitsToInt()](#floatbitstoint)
  - [intBitsToFloat()](#intbitstofloat)
  - [fma()](#fma)
  - [frexp()](#frexp)
  - [ldexp()](#ldexp)
- [Floating-Point Pack and Unpack Functions](#floating-point-pack-and-unpack-functions)
  - [packUnorm2x16()](#packunorm2x16)
  - [unpackUnorm2x16()](#unpackunorm2x16)
  - [packHalf2x16()](#packhalf2x16)
  - [unpackHalf2x16()](#unpackhalf2x16)
  - [packDouble2x32()](#packdouble2x32)
  - [unpackDouble2x32()](#unpackdouble2x32)
- [Geometric Functions](#geometric-functions)
  - [length()](#length)
  - [distance()](#distance)
  - [dot()](#dot)
  - [cross()](#cross)
  - [normalize()](#normalize)
  - [ftransform()](#ftransform)
  - [faceforward()](#faceforward)
  - [reflect()](#reflect)
  - [refract()](#refract)
- [Matrix Functions](#matrix-functions)
  - [matrixCompMult()](#matrixcompmult)
  - [outerProduct()](#outerproduct)
  - [transpose()](#transpose)
  - [determinant()](#determinant)
  - [inverse()](#inverse)
- [Vector Relational Functions](#vector-relational-functions)
  - [lessThan()](#lessthan)
  - [lessThanEqual()](#lessthanequal)
  - [greaterThan()](#greaterthan)
  - [greaterThanEqual()](#greaterthanequal)
  - [equal()](#equal)
  - [notEqual()](#notequal)
  - [any()](#any)
  - [all()](#all)
  - [not()](#not)
- [Integer Functions](#integer-functions)
  - [uaddCarry()](#uaddcarry)
  - [usubBorrow()](#usubborrow)
  - [umulExtended()](#umulextended)
  - [bitfieldExtract()](#bitfieldextract)
  - [bitfieldInsert()](#bitfieldinsert)
  - [bitfieldReverse()](#bitfieldreverse)
  - [bitCount()](#bitcount)
  - [findLSB()](#findlsb)
  - [findMSB()](#findmsb)

## Introduction

The OpenGL Shading Language defines an assortment of built-in convenience functions for scalar and vector operations. Many of these built-in functions can be used in more than one type of shader, but some are intended to provide a direct mapping to hardware and so are available only for a specific type of shader.

The built-in functions basically fall into three categories:

- **Hardware functionality exposure:** They expose some necessary hardware functionality in a convenient way such as accessing a texture map. There is no way in the language for these functions to be emulated by a shader.
- **Trivial operations:** They represent a trivial operation (clamp, mix, etc.) that is very simple for the user to write, but they are very common and may have direct hardware support. It is a very hard problem for the compiler to map expressions to complex assembler instructions.
- **Graphics hardware acceleration:** They represent an operation graphics hardware is likely to accelerate at some point. The trigonometry functions fall into this category.

Many of the functions are similar to the same named ones in common C libraries, but they support vector input as well as the more traditional scalar input.

Applications should be encouraged to use the built-in functions rather than do the equivalent computations in their own shader code since the built-in functions are assumed to be optimal (e.g. perhaps supported directly in hardware).

User code can replace built-in functions with their own if they choose, by simply redeclaring and defining the same name and argument list. Because built-in functions are in a more outer scope than user built-in functions, doing this will hide all built-in functions with the same name as the redeclared function.

## Type Placeholders

When the built-in functions are specified below, the following type placeholders are used:

- **genFType:** Where the input arguments (and corresponding output) can be `float`, `vec2`, `vec3`, or `vec4`
- **genIType:** Where the input arguments (and corresponding output) can be `int`, `ivec2`, `ivec3`, or `ivec4`
- **genUType:** Where the input arguments (and corresponding output) can be `uint`, `uvec2`, `uvec3`, or `uvec4`
- **genBType:** Where the input arguments (or corresponding output) can be `bool`, `bvec2`, `bvec3`, or `bvec4`
- **genDType:** Where the input arguments (and corresponding output) can be `double`, `dvec2`, `dvec3`, `dvec4`
- **mat:** Used for any matrix basic type with single-precision components
- **dmat:** Used for any matrix basic type with double-precision components

For any specific use of a function, the actual types substituted for these placeholders have to have the same number of components for all arguments and for the return type.

## Precision Qualifications

Built-in functions have an effective precision qualification. This qualification cannot be set explicitly and may be different from the precision qualification of the result.

**Note:** In general, precision qualification is ignored unless targeting Vulkan.

The precision qualification of the operation of a built-in function is based on the precision qualification of its formal parameters and actual parameters (input arguments). When a formal parameter specifies a precision qualifier, that is used, otherwise, the precision qualification of the actual (calling) argument is used. The highest precision of these will be the precision of the operation of the built-in function.

## Angle and Trigonometry Functions

Function parameters specified as angle are assumed to be in units of radians. In no case will any of these functions result in a divide by zero error. If the divisor of a ratio is 0, then results will be undefined. These all operate component-wise. The description is per component.

### radians()

```glsl
genFType radians(genFType degrees)
```

Converts degrees to radians, i.e., (π / 180) · degrees.

### degrees()

```glsl
genFType degrees(genFType radians)
```

Converts radians to degrees, i.e., (180 / π) · radians.

### sin()

```glsl
genFType sin(genFType angle)
```

The standard trigonometric sine function.

### cos()

```glsl
genFType cos(genFType angle)
```

The standard trigonometric cosine function.

### tan()

```glsl
genFType tan(genFType angle)
```

The standard trigonometric tangent.

### asin()

```glsl
genFType asin(genFType x)
```

Arc sine. Returns an angle whose sine is x. The range of values returned by this function is [-π / 2, π / 2]. Results are undefined if |x| > 1.

### acos()

```glsl
genFType acos(genFType x)
```

Arc cosine. Returns an angle whose cosine is x. The range of values returned by this function is [0, π]. Results are undefined if |x| > 1.

### atan()

```glsl
genFType atan(genFType y, genFType x)
genFType atan(genFType y_over_x)
```

Arc tangent. Returns an angle whose tangent is y / x. The signs of x and y are used to determine what quadrant the angle is in. The range of values returned by this function is [-π, π]. Results are undefined if x and y are both 0.

The single-parameter version returns an angle whose tangent is y_over_x. The range of values returned by this function is [-π / 2, π / 2].

### sinh()

```glsl
genFType sinh(genFType x)
```

Returns the hyperbolic sine function (e^x - e^-x) / 2.

### cosh()

```glsl
genFType cosh(genFType x)
```

Returns the hyperbolic cosine function (e^x + e^-x) / 2.

### tanh()

```glsl
genFType tanh(genFType x)
```

Returns the hyperbolic tangent function sinh(x) / cosh(x).

### asinh()

```glsl
genFType asinh(genFType x)
```

Arc hyperbolic sine; returns the inverse of sinh.

### acosh()

```glsl
genFType acosh(genFType x)
```

Arc hyperbolic cosine; returns the non-negative inverse of cosh. Results are undefined if x < 1.

### atanh()

```glsl
genFType atanh(genFType x)
```

Arc hyperbolic tangent; returns the inverse of tanh. Results are undefined if x ≥ 1.

## Exponential Functions

These all operate component-wise. The description is per component.

### pow()

```glsl
genFType pow(genFType x, genFType y)
```

Returns x raised to the y power, i.e., x^y. Results are undefined if x < 0. Results are undefined if x = 0 and y ≤ 0.

### exp()

```glsl
genFType exp(genFType x)
```

Returns the natural exponentiation of x, i.e., e^x.

### log()

```glsl
genFType log(genFType x)
```

Returns the natural logarithm of x, i.e., returns the value y which satisfies the equation x = e^y. Results are undefined if x ≤ 0.

### exp2()

```glsl
genFType exp2(genFType x)
```

Returns 2 raised to the x power, i.e., 2^x.

### log2()

```glsl
genFType log2(genFType x)
```

Returns the base 2 logarithm of x, i.e., returns the value y which satisfies the equation x = 2^y. Results are undefined if x ≤ 0.

### sqrt()

```glsl
genFType sqrt(genFType x)
genDType sqrt(genDType x)
```

Returns sqrt(x). Results are undefined if x < 0.

### inversesqrt()

```glsl
genFType inversesqrt(genFType x)
genDType inversesqrt(genDType x)
```

Returns 1 / sqrt(x). Results are undefined if x ≤ 0.

## Common Functions

These all operate component-wise. The description is per component.

### abs()

```glsl
genFType abs(genFType x)
genIType abs(genIType x)
genDType abs(genDType x)
```

Returns x if x ≥ 0; otherwise it returns -x.

### sign()

```glsl
genFType sign(genFType x)
genIType sign(genIType x)
genDType sign(genDType x)
```

Returns 1.0 if x > 0, 0.0 if x = 0, or -1.0 if x < 0.

### floor()

```glsl
genFType floor(genFType x)
genDType floor(genDType x)
```

Returns a value equal to the nearest integer that is less than or equal to x.

### trunc()

```glsl
genFType trunc(genFType x)
genDType trunc(genDType x)
```

Returns a value equal to the nearest integer to x whose absolute value is not larger than the absolute value of x.

### round()

```glsl
genFType round(genFType x)
genDType round(genDType x)
```

Returns a value equal to the nearest integer to x. The fraction 0.5 will round in a direction chosen by the implementation, presumably the direction that is fastest. This includes the possibility that round(x) returns the same value as roundEven(x) for all values of x.

### roundEven()

```glsl
genFType roundEven(genFType x)
genDType roundEven(genDType x)
```

Returns a value equal to the nearest integer to x. A fractional part of 0.5 will round toward the nearest even integer. (Both 3.5 and 4.5 for x will return 4.0.)

### ceil()

```glsl
genFType ceil(genFType x)
genDType ceil(genDType x)
```

Returns a value equal to the nearest integer that is greater than or equal to x.

### fract()

```glsl
genFType fract(genFType x)
genDType fract(genDType x)
```

Returns x - floor(x).

### mod()

```glsl
genFType mod(genFType x, float y)
genFType mod(genFType x, genFType y)
genDType mod(genDType x, double y)
genDType mod(genDType x, genDType y)
```

Modulus. Returns x - y · floor(x / y). **Note:** Implementations may use a cheap approximation to the remainder, and the error can be large due to the discontinuity in floor. This can produce mathematically unexpected results in some cases, such as mod(x,x) computing x rather than 0, and can also cause the result to have a different sign than the infinitely precise result.

### modf()

```glsl
genFType modf(genFType x, out genFType i)
genDType modf(genDType x, out genDType i)
```

Returns the fractional part of x and sets i to the integer part (as a whole number floating-point value). Both the return value and the output parameter will have the same sign as x.

### min()

```glsl
genFType min(genFType x, genFType y)
genFType min(genFType x, float y)
genDType min(genDType x, genDType y)
genDType min(genDType x, double y)
genIType min(genIType x, genIType y)
genIType min(genIType x, int y)
genUType min(genUType x, genUType y)
genUType min(genUType x, uint y)
```

Returns y if y < x; otherwise it returns x.

### max()

```glsl
genFType max(genFType x, genFType y)
genFType max(genFType x, float y)
genDType max(genDType x, genDType y)
genDType max(genDType x, double y)
genIType max(genIType x, genIType y)
genIType max(genIType x, int y)
genUType max(genUType x, genUType y)
genUType max(genUType x, uint y)
```

Returns y if x < y; otherwise it returns x.

### clamp()

```glsl
genFType clamp(genFType x, genFType minVal, genFType maxVal)
genFType clamp(genFType x, float minVal, float maxVal)
genDType clamp(genDType x, genDType minVal, genDType maxVal)
genDType clamp(genDType x, double minVal, double maxVal)
genIType clamp(genIType x, genIType minVal, genIType maxVal)
genIType clamp(genIType x, int minVal, int maxVal)
genUType clamp(genUType x, genUType minVal, genUType maxVal)
genUType clamp(genUType x, uint minVal, uint maxVal)
```

Returns min(max(x, minVal), maxVal). Results are undefined if minVal > maxVal.

### mix()

```glsl
genFType mix(genFType x, genFType y, genFType a)
genFType mix(genFType x, genFType y, float a)
genDType mix(genDType x, genDType y, genDType a)
genDType mix(genDType x, genDType y, double a)
```

Returns the linear blend of x and y, i.e., x · (1 - a) + y · a.

```glsl
genFType mix(genFType x, genFType y, genBType a)
genDType mix(genDType x, genDType y, genBType a)
genIType mix(genIType x, genIType y, genBType a)
genUType mix(genUType x, genUType y, genBType a)
genBType mix(genBType x, genBType y, genBType a)
```

Selects which vector each returned component comes from. For a component of a that is false, the corresponding component of x is returned. For a component of a that is true, the corresponding component of y is returned. Components of x and y that are not selected are allowed to be invalid floating-point values and will have no effect on the results.

### step()

```glsl
genFType step(genFType edge, genFType x)
genFType step(float edge, genFType x)
genDType step(genDType edge, genDType x)
genDType step(double edge, genDType x)
```

Returns 0.0 if x < edge; otherwise it returns 1.0.

### smoothstep()

```glsl
genFType smoothstep(genFType edge0, genFType edge1, genFType x)
genFType smoothstep(float edge0, float edge1, genFType x)
genDType smoothstep(genDType edge0, genDType edge1, genDType x)
genDType smoothstep(double edge0, double edge1, genDType x)
```

Returns 0.0 if x ≤ edge0 and 1.0 if x ≥ edge1, and performs smooth Hermite interpolation between 0 and 1 when edge0 < x < edge1. This is useful in cases where you would want a threshold function with a smooth transition.

This is equivalent to:

```glsl
genFType t;
t = clamp((x - edge0) / (edge1 - edge0), 0, 1);
return t * t * (3 - 2 * t);
```

Results are undefined if edge0 ≥ edge1.

### isnan()

```glsl
genBType isnan(genFType x)
genBType isnan(genDType x)
```

Returns true if x holds a NaN. Returns false otherwise. Always returns false if NaNs are not implemented.

### isinf()

```glsl
genBType isinf(genFType x)
genBType isinf(genDType x)
```

Returns true if x holds a positive infinity or negative infinity. Returns false otherwise.

### floatBitsToInt()

```glsl
genIType floatBitsToInt(highp genFType value)
genUType floatBitsToUint(highp genFType value)
```

Returns a signed or unsigned integer value representing the encoding of a floating-point value. The float value's bit-level representation is preserved.

### intBitsToFloat()

```glsl
genFType intBitsToFloat(highp genIType value)
genFType uintBitsToFloat(highp genUType value)
```

Returns a floating-point value corresponding to a signed or unsigned integer encoding of a floating-point value. If a NaN is passed in, it will not signal, and the resulting value is unspecified. If an Inf is passed in, the resulting value is the corresponding Inf. If a subnormal number is passed in, the result might be flushed to 0. Otherwise, the bit-level representation is preserved.

### fma()

```glsl
genFType fma(genFType a, genFType b, genFType c)
genDType fma(genDType a, genDType b, genDType c)
```

Computes and returns a * b + c. In uses where the return value is eventually consumed by a variable declared as precise:

- `fma()` is considered a single operation, whereas the expression `a * b + c` consumed by a variable declared precise is considered two operations.
- The precision of `fma()` can differ from the precision of the expression `a * b + c`.
- `fma()` will be computed with the same precision as any other `fma()` consumed by a precise variable, giving invariant results for the same input values of a, b, and c.

### frexp()

```glsl
genFType frexp(highp genFType x, out highp genIType exp)
genDType frexp(genDType x, out genIType exp)
```

Splits x into a floating-point significand in the range [0.5, 1.0], and an integral exponent of two, such that x = significand · 2^exponent.

The significand is returned by the function and the exponent is returned in the parameter exp. For a floating-point value of zero, the significand and exponent are both zero. If an implementation supports signed zero, an input value of minus zero should return a significand of minus zero.

### ldexp()

```glsl
genFType ldexp(highp genFType x, highp genIType exp)
genDType ldexp(genDType x, genIType exp)
```

Builds a floating-point number from x and the corresponding integral exponent of two in exp, returning: significand · 2^exponent.

If this product is too large to be represented in the floating-point type, the result is undefined. If exp is greater than +128 (single-precision) or +1024 (double-precision), the value returned is undefined. If exp is less than -126 (single-precision) or -1022 (double-precision), the value returned may be flushed to zero.

## Floating-Point Pack and Unpack Functions

These functions do not operate component-wise, rather, as described in each case.

### packUnorm2x16()

```glsl
highp uint packUnorm2x16(vec2 v)
highp uint packSnorm2x16(vec2 v)
uint packUnorm4x8(vec4 v)
uint packSnorm4x8(vec4 v)
```

First, converts each component of the normalized floating-point value v into 16-bit (2x16) or 8-bit (4x8) integer values. Then, the results are packed into the returned 32-bit unsigned integer.

The conversion for component c of v to fixed point is done as follows:

- **packUnorm2x16:** round(clamp(c, 0, +1) * 65535.0)
- **packSnorm2x16:** round(clamp(c, -1, +1) * 32767.0)
- **packUnorm4x8:** round(clamp(c, 0, +1) * 255.0)
- **packSnorm4x8:** round(clamp(c, -1, +1) * 127.0)

The first component of the vector will be written to the least significant bits of the output; the last component will be written to the most significant bits.

### unpackUnorm2x16()

```glsl
vec2 unpackUnorm2x16(highp uint p)
vec2 unpackSnorm2x16(highp uint p)
vec4 unpackUnorm4x8(highp uint p)
vec4 unpackSnorm4x8(highp uint p)
```

First, unpacks a single 32-bit unsigned integer p into a pair of 16-bit unsigned integers, a pair of 16-bit signed integers, four 8-bit unsigned integers, or four 8-bit signed integers, respectively. Then, each component is converted to a normalized floating-point value to generate the returned two- or four-component vector.

The conversion for unpacked fixed-point value f to floating-point is done as follows:

- **unpackUnorm2x16:** f / 65535.0
- **unpackSnorm2x16:** clamp(f / 32767.0, -1, +1)
- **unpackUnorm4x8:** f / 255.0
- **unpackSnorm4x8:** clamp(f / 127.0, -1, +1)

### packHalf2x16()

```glsl
uint packHalf2x16(vec2 v)
```

Returns an unsigned integer obtained by converting the components of a two-component floating-point vector to the 16-bit floating-point representation of the API, and then packing these two 16-bit integers into a 32-bit unsigned integer.

### unpackHalf2x16()

```glsl
vec2 unpackHalf2x16(uint v)
```

Returns a two-component floating-point vector with components obtained by unpacking a 32-bit unsigned integer into a pair of 16-bit values, interpreting those values as 16-bit floating-point numbers according to the API, and converting them to 32-bit floating-point values.

### packDouble2x32()

```glsl
double packDouble2x32(uvec2 v)
```

Returns a double-precision value obtained by packing the components of v into a 64-bit value. If an IEEE 754 Inf or NaN is created, it will not signal, and the resulting floating-point value is unspecified. Otherwise, the bit-level representation of v is preserved.

### unpackDouble2x32()

```glsl
uvec2 unpackDouble2x32(double v)
```

Returns a two-component unsigned integer vector representation of v. The bit-level representation of v is preserved.

## Geometric Functions

These operate on vectors as vectors, not component-wise.

### length()

```glsl
float length(genFType x)
double length(genDType x)
```

Returns the length of vector x, i.e., sqrt(x₀² + x₁² + ...).

### distance()

```glsl
float distance(genFType p0, genFType p1)
double distance(genDType p0, genDType p1)
```

Returns the distance between p0 and p1, i.e., length(p0 - p1).

### dot()

```glsl
float dot(genFType x, genFType y)
double dot(genDType x, genDType y)
```

Returns the dot product of x and y, i.e., x₀ · y₀ + x₁ · y₁ + ...

### cross()

```glsl
vec3 cross(vec3 x, vec3 y)
dvec3 cross(dvec3 x, dvec3 y)
```

Returns the cross product of x and y, i.e., (x₁ · y₂ - y₁ · x₂, x₂ · y₀ - y₂ · x₀, x₀ · y₁ - y₀ · x₁).

### normalize()

```glsl
genFType normalize(genFType x)
genDType normalize(genDType x)
```

Returns a vector in the same direction as x but with a length of 1, i.e. x / length(x).

### ftransform()

```glsl
vec4 ftransform()  // compatibility profile only
```

Available only when using the compatibility profile. For core OpenGL, use invariant. For vertex shaders only. This function will ensure that the incoming vertex value will be transformed in a way that produces exactly the same result as would be produced by OpenGL's fixed functionality transform.

### faceforward()

```glsl
genFType faceforward(genFType N, genFType I, genFType Nref)
genDType faceforward(genDType N, genDType I, genDType Nref)
```

If dot(Nref, I) < 0 return N, otherwise return -N.

### reflect()

```glsl
genFType reflect(genFType I, genFType N)
genDType reflect(genDType I, genDType N)
```

For the incident vector I and surface orientation N, returns the reflection direction: I - 2 · dot(N, I) · N. N must already be normalized in order to achieve the desired result.

### refract()

```glsl
genFType refract(genFType I, genFType N, float eta)
genDType refract(genDType I, genDType N, double eta)
```

For the incident vector I and surface normal N, and the ratio of indices of refraction eta, return the refraction vector. The input parameters for the incident vector I and the surface normal N must already be normalized to get the desired results.

## Matrix Functions

For each of the following built-in matrix functions, there is both a single-precision floating-point version, where all arguments and return values are single precision, and a double-precision floating-point version, where all arguments and return values are double precision. Only the single-precision floating-point version is shown.

### matrixCompMult()

```glsl
mat matrixCompMult(mat x, mat y)
```

Multiply matrix x by matrix y component-wise, i.e., result[i][j] is the scalar product of x[i][j] and y[i][j]. **Note:** To get linear algebraic matrix multiplication, use the multiply operator (*).

### outerProduct()

```glsl
mat2 outerProduct(vec2 c, vec2 r)
mat3 outerProduct(vec3 c, vec3 r)
mat4 outerProduct(vec4 c, vec4 r)
mat2x3 outerProduct(vec3 c, vec2 r)
mat3x2 outerProduct(vec2 c, vec3 r)
mat2x4 outerProduct(vec4 c, vec2 r)
mat4x2 outerProduct(vec2 c, vec4 r)
mat3x4 outerProduct(vec4 c, vec3 r)
mat4x3 outerProduct(vec3 c, vec4 r)
```

Treats the first parameter c as a column vector (matrix with one column) and the second parameter r as a row vector (matrix with one row) and does a linear algebraic matrix multiply c * r, yielding a matrix whose number of rows is the number of components in c and whose number of columns is the number of components in r.

### transpose()

```glsl
mat2 transpose(mat2 m)
mat3 transpose(mat3 m)
mat4 transpose(mat4 m)
mat2x3 transpose(mat3x2 m)
mat3x2 transpose(mat2x3 m)
mat2x4 transpose(mat4x2 m)
mat4x2 transpose(mat2x4 m)
mat3x4 transpose(mat4x3 m)
mat4x3 transpose(mat3x4 m)
```

Returns a matrix that is the transpose of m. The input matrix m is not modified.

### determinant()

```glsl
float determinant(mat2 m)
float determinant(mat3 m)
float determinant(mat4 m)
```

Returns the determinant of m.

### inverse()

```glsl
mat2 inverse(mat2 m)
mat3 inverse(mat3 m)
mat4 inverse(mat4 m)
```

Returns a matrix that is the inverse of m. The input matrix m is not modified. The values in the returned matrix are undefined if m is singular or poorly-conditioned (nearly singular).

## Vector Relational Functions

Relational and equality operators (<, <=, >, >=, ==, !=) are defined to operate on scalars and produce scalar Boolean results. For vector results, use the following built-in functions.

The following placeholders are used for the listed specific types:

- **bvec:** bvec2, bvec3, bvec4
- **ivec:** ivec2, ivec3, ivec4
- **uvec:** uvec2, uvec3, uvec4
- **vec:** vec2, vec3, vec4, dvec2, dvec3, dvec4

In all cases, the sizes of all the input and return vectors for any particular call must match.

### lessThan()

```glsl
bvec lessThan(vec x, vec y)
bvec lessThan(ivec x, ivec y)
bvec lessThan(uvec x, uvec y)
```

Returns the component-wise compare of x < y.

### lessThanEqual()

```glsl
bvec lessThanEqual(vec x, vec y)
bvec lessThanEqual(ivec x, ivec y)
bvec lessThanEqual(uvec x, uvec y)
```

Returns the component-wise compare of x ≤ y.

### greaterThan()

```glsl
bvec greaterThan(vec x, vec y)
bvec greaterThan(ivec x, ivec y)
bvec greaterThan(uvec x, uvec y)
```

Returns the component-wise compare of x > y.

### greaterThanEqual()

```glsl
bvec greaterThanEqual(vec x, vec y)
bvec greaterThanEqual(ivec x, ivec y)
bvec greaterThanEqual(uvec x, uvec y)
```

Returns the component-wise compare of x ≥ y.

### equal()

```glsl
bvec equal(vec x, vec y)
bvec equal(ivec x, ivec y)
bvec equal(uvec x, uvec y)
bvec equal(bvec x, bvec y)
```

Returns the component-wise compare of x == y.

### notEqual()

```glsl
bvec notEqual(vec x, vec y)
bvec notEqual(ivec x, ivec y)
bvec notEqual(uvec x, uvec y)
bvec notEqual(bvec x, bvec y)
```

Returns the component-wise compare of x ≠ y.

### any()

```glsl
bool any(bvec x)
```

Returns true if any component of x is true.

### all()

```glsl
bool all(bvec x)
```

Returns true only if all components of x are true.

### not()

```glsl
bvec not(bvec x)
```

Returns the component-wise logical complement of x.

## Integer Functions

These all operate component-wise. The description is per component. The notation [a, b] means the set of bits from bit-number a through bit-number b, inclusive. The lowest-order bit is bit 0. "Bit number" will always refer to counting up from the lowest-order bit as bit 0.

### uaddCarry()

```glsl
genUType uaddCarry(highp genUType x, highp genUType y, out lowp genUType carry)
```

Adds 32-bit unsigned integers x and y, returning the sum modulo 2³². The value carry is set to zero if the sum was less than 2³², or one otherwise.

### usubBorrow()

```glsl
genUType usubBorrow(highp genUType x, highp genUType y, out lowp genUType borrow)
```

Subtracts the 32-bit unsigned integer y from x, returning the difference if non-negative, or 2³² plus the difference otherwise. The value borrow is set to zero if x ≥ y, or one otherwise.

### umulExtended()

```glsl
void umulExtended(highp genUType x, highp genUType y, out highp genUType msb, out highp genUType lsb)
void imulExtended(highp genIType x, highp genIType y, out highp genIType msb, out highp genIType lsb)
```

Multiplies 32-bit unsigned or signed integers x and y, producing a 64-bit result. The 32 least-significant bits are returned in lsb. The 32 most-significant bits are returned in msb.

### bitfieldExtract()

```glsl
genIType bitfieldExtract(genIType value, int offset, int bits)
genUType bitfieldExtract(genUType value, int offset, int bits)
```

Extracts bits [offset, offset + bits - 1] from value, returning them in the least significant bits of the result. For unsigned data types, the most significant bits of the result will be set to zero. For signed data types, the most significant bits will be set to the value of bit offset + bits - 1.

**Note:** For vector versions of bitfieldExtract(), a single pair of offset and bits values is shared for all components.

### bitfieldInsert()

```glsl
genIType bitfieldInsert(genIType base, genIType insert, int offset, int bits)
genUType bitfieldInsert(genUType base, genUType insert, int offset, int bits)
```

Inserts the bits least significant bits of insert into base. The result will have bits [offset, offset + bits - 1] taken from bits [0, bits - 1] of insert, and all other bits taken directly from the corresponding bits of base.

**Note:** For vector versions of bitfieldInsert(), a single pair of offset and bits values is shared for all components.

### bitfieldReverse()

```glsl
genIType bitfieldReverse(highp genIType value)
genUType bitfieldReverse(highp genUType value)
```

Reverses the bits of value. The bit numbered n of the result will be taken from bit (bits - 1) - n of value, where bits is the total number of bits used to represent value.

### bitCount()

```glsl
genIType bitCount(genIType value)
genIType bitCount(genUType value)
```

Returns the number of one bits in the binary representation of value.

### findLSB()

```glsl
genIType findLSB(genIType value)
genIType findLSB(genUType value)
```

Returns the bit number of the least significant one bit in the binary representation of value. If value is zero, -1 will be returned.

### findMSB()

```glsl
genIType findMSB(highp genIType value)
genIType findMSB(highp genUType value)
```

Returns the bit number of the most significant bit in the binary representation of value. For positive integers, the result will be the bit number of the most significant one bit. For negative integers, the result will be the bit number of the most significant zero bit. For a value of zero or negative one, -1 will be returned.
