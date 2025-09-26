---
category: GLSL
document_type: tutorial
difficulty: intermediate
time_estimate: 30-45 minutes
operators:
- GLSL_TOP
- GLSL_MAT
concepts:
- glsl_data_types
- precision_qualifiers
- mobile_graphics
- embedded_systems
- type_conversions
- variable_declarations
- swizzle_operations
- vector_types
- matrix_types
prerequisites:
- programming_fundamentals
- GLSL_fundamentals
workflows:
- shader_development_fundamentals
- mobile_shader_development
- cross_platform_graphics
- optimization_for_embedded_systems
- learning_glsl
keywords:
- glsl es data types
- precision qualifiers
- highp
- mediump
- lowp
- float
- int
- bool
- vec2
- vec3
- vec4
- mat2
- mat3
- mat4
- sampler2D
- samplerCube
- swizzle notation
- type conversion
- variable initialization
- storage qualifiers
tags:
- glsl
- tutorial
- data_types
- mobile
- embedded
- precision
- learning
- fundamentals
- beginner
relationships:
  GLSL_Built_In_Functions_Reference: strong
  GLSL_Structures_and_Arrays_Reference: strong
  GLSL_Write_a_GLSL_TOP: medium
related_docs:
- GLSL_Built_In_Functions_Reference
- GLSL_Structures_and_Arrays_Reference
- GLSL_Write_a_GLSL_TOP
hierarchy:
  secondary: glsl_fundamentals
  tertiary: data_types_tutorial
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- shader_development_fundamentals
- mobile_shader_development
- cross_platform_graphics
- optimization_for_embedded_systems
---

# GLSL ES Data Types Tutorial

<!-- TD-META
category: GLSL
document_type: tutorial
operators: [GLSL_TOP, GLSL_MAT]
concepts: [glsl_data_types, precision_qualifiers, mobile_graphics, embedded_systems, type_conversions, variable_declarations, swizzle_operations, vector_types, matrix_types]
prerequisites: [programming_fundamentals, GLSL_fundamentals]
workflows: [shader_development_fundamentals, mobile_shader_development, cross_platform_graphics, optimization_for_embedded_systems, learning_glsl]
related: [GLSL_Built_In_Functions_Reference, GLSL_Structures_and_Arrays_Reference, GLSL_Write_a_GLSL_TOP]
relationships: {
  "GLSL_Built_In_Functions_Reference": "strong",
  "GLSL_Structures_and_Arrays_Reference": "strong",
  "GLSL_Write_a_GLSL_TOP": "medium"
}
hierarchy:
  primary: "shader_programming"
  secondary: "glsl_fundamentals"
  tertiary: "data_types_tutorial"
keywords: [glsl es data types, precision qualifiers, highp, mediump, lowp, float, int, bool, vec2, vec3, vec4, mat2, mat3, mat4, sampler2D, samplerCube, swizzle notation, type conversion, variable initialization, storage qualifiers]
tags: [glsl, tutorial, data_types, mobile, embedded, precision, learning, fundamentals, beginner]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming tutorial for GPU development
**Difficulty**: Intermediate
**Time to read**: 30-45 minutes
**Use for**: shader_development_fundamentals, mobile_shader_development, cross_platform_graphics

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Programming Fundamentals] → [Glsl Fundamentals]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Built In Functions Reference] → [GLSL Structures and Arrays Reference] → [GLSL Write a GLSL TOP]

**Related Topics**: shader development fundamentals, mobile shader development, cross platform graphics

## Summary

Comprehensive tutorial covering GLSL ES data types, precision qualifiers, and variable declarations. Essential foundation for understanding shader programming concepts and cross-platform development considerations.

## Relationship Justification

Foundation tutorial that connects to all GLSL reference materials. Prerequisites for advanced topics and directly applicable in GLSL TOP development. Critical for understanding precision and optimization in mobile/embedded contexts.

## Content

- [Introduction](#introduction)
- [Types](#types)
  - [float / vec](#float--vec)
  - [int / ivec](#int--ivec)
  - [bool / bvec](#bool--bvec)
  - [mat](#mat)
  - [sampler](#sampler)
  - [void](#void)
- [Initializing Variables](#initializing-variables)
- [Casting Between Data Types](#casting-between-data-types)
- [Dimensions and Components](#dimensions-and-components)
- [Swizzle Notation](#swizzle-notation)
  - [Array Notation](#array-notation)
  - [Dotted Notation](#dotted-notation)
- [Matrices](#matrices)
- [Storage Qualifiers](#storage-qualifiers)
  - [const](#const)
  - [attribute](#attribute)
  - [varying](#varying)
  - [uniform](#uniform)
- [Groups](#groups)
  - [Array](#array)
  - [Struct](#struct)
- [Precision Qualifiers](#precision-qualifiers)
  - [lowp](#lowp)
  - [mediump](#mediump)
  - [highp](#highp)
- [Summary](#summary)

## Introduction

This tutorial covers the data types in GLSL ES and how to use them.

In [GML_GameMakerLanguage], you can set variables to any value from tiny fractions to large integers to booleans without worrying about data types. However, in shaders you need to initialize what data type you are using for each variable, allowing shaders to be faster and more precise.

## Types

The first thing to learn about shader variables is the data types. You can use any of the following types:

### float / vec

These are standard (floating-point) numbers that can be a fraction or decimal number, but it must contain a decimal point like: `2.0`, `50.`, `1.57` or `-95.0`. You can also use scientific notation to write very large or small numbers. This can be written like: `2.0e3`, `3e7` or `4.7e-4` which is shorter way to write: `2000.0` (2.0*10^3), `3000000.0` (3.0*10^7) or `0.00047` (4.7*10^-4).

### int / ivec

Whole numbers or integers like `3`, `-8` or `400`. Adding any decimal points to an int will cause an error. Hexadecimal numbers can be defined by putting "0x" at the start and for octal numbers just start with "0". For example: `0xFF`, `017` are valid numbers.

### bool / bvec

Boolean values which can only be: `true` or `false`.

### mat

Floating-point matrices. A `mat2` contains 2 `vec2`s, `mat3` contains 3 `vec3`s and `mat4` contains 4 `vec4`s. More on this later.

### sampler

ID of a texture. GM only supports 2D textures (called a `sampler2D`), but GM does not support other type such as "samplerCube" for cubemaps. More on this in the next tutorial.

### void

No value at all. This is used in functions that don't return anything. More on this in the next tutorial.

## Initializing Variables

To declare your variables in code you must specify the type before the variable name and shader syntax requires a semi-colon at the end of the declaration:

```glsl
//Floats must include a decimal point.
float A = 5.0;
//You can declare the variable to set later:
//Integers must exclude a decimal point.
int B;
//Bools are either true or false.
bool C = false,
//"D" is also a bool because of the comma after the "C" definition.
D = true;
```

As you can see with the integer case, you can initialize a variable's type without setting a value. This is like local variables in GM (e.g. `var i = 0`). Also, you can use commas instead of semicolons when defining multiple variables of the same data type. This is shown with bool "D".

## Casting Between Data Types

Sometimes you need to convert from one data type to another and this is called "casting". To cast a value you use the replacement data type as function with the value you want to convert as the argument. Here's a quick example:

```glsl
//Cast an int to a float.
float A = float(5);
//Cast a bool to an int (false = 0, true = 1).
int B = int(true);
```

## Dimensions and Components

Unlike in [GML_GameMakerLanguage], some shader variables can contain up to 4 values at once and these values are called "components" of the variable. Vectors make it much easier to do math with 2,3 or 4 dimensions. If you want to add two vectors together you can do so with a single operation, like you would with any other variable (which will be very useful later).

So floats, vec2s, vec3s and vec4s are all floating-point numbers, so a float has 1 component while vec4 has 4. To set a vector with you use a function called a constructor which is just like a caster but can have multiple components separated by commas. Here's how it looks to initialize different variable types:

```glsl
//1D scalar with a value of 1.0. Scalars don't need constructors.
float line = 1.0;
//Construct a 2D integer vector containing 1 and 2 respectively.
ivec2 square = ivec2(1, 2);
//You can include floats as components:
//Construct a 3D vector containing 1.0, 2.0 and 3.0 respectively.
vec3 cube = vec3(line, 2.0, 3.0);
//You can also include vectors:
//Construct a 4D vector containing 1.0, 2.0, 3.0 and 4.0 respectively.
vec4 tess = vec4(cube, 4.0);
```

You can also do the same with integers by using `int`, `ivec2`, `ivec3`, and `ivec4`. As you may have guessed, you can do the same with Booleans (`bool`, `bvec2`, `bvec3`, and `bvec4`), but they aren't used as often.

## Swizzle Notation

So you now know how to cast data types and construct vectors, but to extract components from vectors you need to know about "swizzle notation". There are two ways to access components.

### Array Notation

Works with vectors like arrays in [GML_GameMakerLanguage]. So with a `vec4`, you can put a pair of square brackets with the component "index" being an integer ranging from 0-3. So `vector[2]` will extract the third component from "vector". It's helpful to understand this before learning "dotted notation".

### Dotted Notation

Can be used to access multiple components (as a new vector) at the same time. To access a component from a vector you just put a dot directly behind the vector with the component(s) that you want to access. The components can be represented as either "xyzw", "rgba", or "stpq". These all work the same, but the general guide is that:

- `xyzw` is used for positions or points in space
- `rgba` is used for red, green, blue and alpha "channels"
- `stpq` is meant for texture coordinates

Notice the order of each set. `x`, `r` or `s` will always represent the first component, `y`, `g` or `t` represents the second component, `z`, `b` or `p`, the third and `w`, `a` or `q` the fourth.

Dotted Notation is more widely used because it can be used to access floats or vectors whereas array notation only accesses floats. Here's an example to show both methods:

```glsl
//Construct a vec4 from ints for example.
vec4 A = vec4(0, 1, 2, 3);
//Get the first component of "A", 0.0.
float B = A.x;
//Get the second component of "A", 1.0.
float C = A[1];
//Reverse the component order of "A", vec4(3, 2, 1, 0).
vec4 D = A.abgr;
//This also works for setting vectors:
//Set the first two component to the last two components, vec2(2, 3).
A.st = A.pq;
```

**Important:** You CANNOT mix components from one set with another. So you can pick between `xyzw`, `rgba` or `stpq`, but you can't do something like `xyrg` because this will cause an error.

## Matrices

Matrices are a special data type that contain more components than their vector equivalents. It helps to think of matrices as tables with either 2, 3 or 4 rows and columns, so a `mat2` contains 2 `vec2`s (2x2 or 4 components), a `mat3` contains 3 `vec3`s (3x3 or 9 components) and a `mat4` contains 4 `vec4`s (4x4 or 16 components).

They can be initialized like so:

```glsl
//Set the first and second columns with vec2s.
mat2 rotate = mat2(vec2(0.6,0.8), vec2(-0.8,0.6));
//Get the vec2 from the second column which is vec2(-0.8,0.6).
vec2 y_dot = rotate[1];

//And here are some mat3 examples:
//Alternatively, you can set all components individually.
mat3 rotate2 = mat3(0.6, 0.8, 0.0, -0.8, 0.6, 0.0, 0.0, 0.0, 1.0);
//Get the first column, second row component which is 0.8
float y_z = rotate2[0][1];
```

Matrices can be used to scale, rotate or skew vectors simple by multiplying a vector by a matrix. Matrix multiplication is non-commutative, meaning that the result can be different depending on the order of multiplication. You can learn more on this in the next tutorial, but for now you just need to know it's used to "transform" vectors.

## Storage Qualifiers

"Storage qualifiers" control how you want your variable is handled. This can be used to receive vertex information, receive values from [GML_GameMakerLanguage] and more! These are the storage qualifiers and how they are used:

### const

Constant/unchanging variable. Must be initialized once to a "constant" value and it cannot be redefined again. Every number you type in a shader is a constant however using functions (more in the next tutorial) or any operations including non-constants will result in a non-constant.

### attribute

Read-only vertex input information which can only be accessed in the vertex shader. This can be vertex position, color, texture coordinates or even normals. All of GM's built-in attributes can be found in the [REF_GameMakerGLSLGlossary]!

### varying

Variables that get sent from the vertex shader to the fragment shader. These variables' values get blended across the pixels between the vertices. So halfway between a red vertex and blue vertex is purple.

### uniform

Read-only variables which are set from [GML_GameMakerLanguage] and received in either the fragment shader or vertex shader.

## Groups

Variables can be grouped:

### Array

A list of values in a single variable. They are similar to array notation, but instead of dealing with components, it's scalars or vectors. Because it is not limited by components, you can have an array of any constant size.

```glsl
//Initialize a integer array with 4 slots (indices 0 to 3).
ivec2 array[4];
//Set the 2 index value as a ivec2.
array[2] = ivec2(2,4);
```

### Struct

A structure or group of of the other data types in a single variable. It's a bit like how in GM, objects have many properties like `x`, `y`, `sprite_index`, etc, but with structures, you can use any data types.

```glsl
//Initialize structure format.
struct sample
{
    vec2 uv;
    sampler2D tex;
};
//Set create a "sample" structure.
sample pixel = sample(v_vTexcoord,gm_BaseTexture);

//Get pixel's uvs.
vec2 pix_uv = pixel.uv;
//Set pixel's texture to "uni_diffuse".
pixel.tex = uni_diffuse;
```

## Precision Qualifiers

Lastly, there are precision qualifiers, which can control the range and quality of variables. Modern hardware may use a higher precision than you specify, but precision qualifiers set the minimum acceptable precision (if the hardware supports it). This isn't used often, but it can be useful with cross-platform shaders. These are the three precision types:

### lowp

Float's range goes up to 2 (positive and negative) with a precision of 1/256.
Integers can range up to 256 (including positive and negative).
Lowp floats are adequate for colors, but may not be precise enough for other purposes.

### mediump

Float's range goes up to 16,384 with a precision of 1/1,024.
Integers can range up to 1,024.
Mediump floats are usually adequate for texture coordinates and normals.

### highp

Float's range goes up to ‭4,611,686,018,427,387,904! with a precision of 1/65536.
Integers can range up to 65536.
Highp floats are best used for positions.

Also, the keyword "precision" can be used to set the default precision for when a particular data type is used, but not specified. Here's an example:

```glsl
//Set the default float precision to highp.
precision highp float;
//Set the default integer precision to lowp.
precision lowp int;

//Set the color at low precision.
lowp vec3 color = vec3(0.2, 0.4, 0.8);
```

## Summary

Great job! You've learned about all the different data types and what they store. You've learned how to handle multi-dimensional variables (vectors) and their components. You now know how to access shader inputs (attributes, varyings, uniforms) and how to use constants, data groups (arrays and structs) and precision. This lays the framework necessary to understand functions and logic which is covered in the next tutorial. For now, pat yourself on the back and take a break if you need it!
