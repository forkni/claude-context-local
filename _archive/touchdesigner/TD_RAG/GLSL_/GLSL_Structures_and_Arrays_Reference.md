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
- glsl_data_structures
- arrays
- structs
- uniform_blocks
- data_organization
- complex_data_types
- multi_dimensional_arrays
- runtime_sized_arrays
- implicit_conversions
prerequisites:
- GLSL_fundamentals
- GLSL_Data_Types
- programming_data_structures
workflows:
- complex_shader_development
- data_organization
- uniform_management
- advanced_shader_techniques
- compute_shader_data_structures
keywords:
- glsl structures
- glsl arrays
- struct
- uniform blocks
- data organization
- complex types
- member access
- array indexing
- uniform arrays
- multi-dimensional arrays
- runtime sized arrays
- implicit conversions
- initializers
- scoping
tags:
- glsl
- reference
- structures
- arrays
- data_organization
- advanced
- programming
- complex_types
relationships:
  GLSL_Data_Types: strong
  GLSL_Built_In_Functions_Reference: strong
  GLSL_Compute_Shader_Reference: medium
related_docs:
- GLSL_Data_Types
- GLSL_Built_In_Functions_Reference
- GLSL_Compute_Shader_Reference
hierarchy:
  secondary: glsl_reference
  tertiary: data_structures
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- complex_shader_development
- data_organization
- uniform_management
- advanced_shader_techniques
---

# GLSL Structures and Arrays Reference

<!-- TD-META
category: GLSL
document_type: reference
operators: [GLSL_TOP, GLSL_MAT, Script_TOP]
concepts: [glsl_data_structures, arrays, structs, uniform_blocks, data_organization, complex_data_types, multi_dimensional_arrays, runtime_sized_arrays, implicit_conversions]
prerequisites: [GLSL_fundamentals, GLSL_Data_Types, programming_data_structures]
workflows: [complex_shader_development, data_organization, uniform_management, advanced_shader_techniques, compute_shader_data_structures]
related: [GLSL_Data_Types, GLSL_Built_In_Functions_Reference, GLSL_Compute_Shader_Reference]
relationships: {
  "GLSL_Data_Types": "strong",
  "GLSL_Built_In_Functions_Reference": "strong",
  "GLSL_Compute_Shader_Reference": "medium"
}
hierarchy:
  primary: "shader_programming"
  secondary: "glsl_reference"
  tertiary: "data_structures"
keywords: [glsl structures, glsl arrays, struct, uniform blocks, data organization, complex types, member access, array indexing, uniform arrays, multi-dimensional arrays, runtime sized arrays, implicit conversions, initializers, scoping]
tags: [glsl, reference, structures, arrays, data_organization, advanced, programming, complex_types]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming reference for GPU development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: complex_shader_development, data_organization, uniform_management

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Fundamentals] → [Glsl Data Types] → [Programming Data Structures]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Data Types] → [GLSL Built In Functions Reference] → [GLSL Compute Shader Reference]

**Related Topics**: complex shader development, data organization, uniform management

## Summary

Comprehensive reference for GLSL data structures covering user-defined structures, arrays, uniform blocks, and complex data organization. Essential for advanced shader development requiring sophisticated data management.

## Relationship Justification

Builds upon fundamental data types tutorial and connects to built-in functions reference. Important for compute shader development where complex data structures are common. Foundation for advanced shader programming techniques.

## Content

- [Introduction](#introduction)
- [Structures](#structures)
  - [Structure Declaration](#structure-declaration)
  - [Structure Definition Syntax](#structure-definition-syntax)
  - [Structure Members](#structure-members)
  - [Structure Restrictions](#structure-restrictions)
  - [Structure Examples](#structure-examples)
- [Arrays](#arrays)
  - [Array Declaration](#array-declaration)
  - [Array Sizing](#array-sizing)
  - [Array Types](#array-types)
  - [Multi-Dimensional Arrays](#multi-dimensional-arrays)
  - [Array Initialization](#array-initialization)
  - [Array Length Method](#array-length-method)
  - [Runtime-Sized Arrays](#runtime-sized-arrays)
- [Implicit Conversions](#implicit-conversions)
  - [Conversion Table](#conversion-table)
  - [Binary Operator Conversions](#binary-operator-conversions)
- [Initializers](#initializers)
  - [Initializer Syntax](#initializer-syntax)
  - [Assignment Expression Initializers](#assignment-expression-initializers)
  - [List Initializers](#list-initializers)
  - [Type Matching Rules](#type-matching-rules)
  - [Initializer Examples](#initializer-examples)
- [Scoping](#scoping)
  - [Scope Determination](#scope-determination)
  - [Variable Declaration Scope](#variable-declaration-scope)
  - [Function Scope](#function-scope)
  - [Loop and Control Structure Scope](#loop-and-control-structure-scope)
  - [Name Space Rules](#name-space-rules)
  - [Shared Globals](#shared-globals)

## Introduction

GLSL supports user-defined data types through structures and collections of data through arrays. This reference covers the declaration, initialization, and usage of structures and arrays in GLSL, along with related concepts like implicit conversions, initializers, and scoping rules.

## Structures

### Structure Declaration

User-defined types can be created by aggregating other already defined types into a structure using the `struct` keyword:

```glsl
struct light {
    float intensity;
    vec3 position;
} lightVar;
```

In this example, `light` becomes the name of the new type, and `lightVar` becomes a variable of type `light`.

To declare variables of the new type, use its name (without the keyword `struct`):

```glsl
light lightVar2;
```

### Structure Definition Syntax

The formal structure definition syntax is:

```
struct-definition : 
    qualifieropt struct nameopt { member-list } declaratorsopt ;

member-list : 
    member-declaration ;
    member-declaration member-list ;

member-declaration : 
    basic-type declarators ;
```

Where:

- `name` becomes the user-defined type
- `name` can be used to declare variables of this new type
- The name shares the same namespace as other variables, types, and functions
- All previously visible variables, types, constructors, or functions with that name are hidden
- The optional qualifier only applies to any declarators, not to the type being defined

### Structure Members

**Member Requirements:**

- Structures must have at least one member declaration
- Bit fields are not supported
- Member types must be already defined (no forward references)
- Member declarations may contain precision qualifiers
- Use of any other qualifier results in a compile-time error
- Member declarations cannot contain initializers
- Member declarators can contain arrays (must be explicitly sized)

**Precision Qualifiers:**
Where a member declaration does not include a precision qualifier, the member's precision is inferred as described in [REF_DefaultPrecisionQualifiers] at the point of the struct type's declaration.

**Array Members:**
Arrays in member declarations must:

- Have a size specified
- Size must be a constant integral expression greater than zero

### Structure Restrictions

**Forbidden Constructs:**

```glsl
struct S { float f; };        // Allowed: S is defined as a structure

struct T { S; };              // Error: anonymous structures disallowed
struct { ... };               // Error: embedded structures disallowed
S s;                          // Allowed: nested structure with a name
```

**Namespace Rules:**

- Each level of structure has its own namespace for member names
- Names need only be unique within that namespace
- Anonymous structures are not supported
- Embedded structure definitions are not supported

### Structure Examples

**Basic Structure:**

```glsl
struct Material {
    vec3 ambient;
    vec3 diffuse;
    vec3 specular;
    float shininess;
};

Material gold = Material(
    vec3(0.24725, 0.1995, 0.0745),
    vec3(0.75164, 0.60648, 0.22648),
    vec3(0.628281, 0.555802, 0.366065),
    0.4
);
```

**Structure with Arrays:**

```glsl
struct LightArray {
    vec3 positions[8];
    vec3 colors[8];
    int count;
};
```

## Arrays

### Array Declaration

Variables of the same type can be aggregated into arrays by declaring a name followed by brackets (`[]`) enclosing an optional size:

```glsl
float frequencies[3];
uniform vec4 lightPosition[4];
light lights[];                    // unsized array
const int numLights = 2;
light lights[numLights];           // sized with constant
```

### Array Sizing

**Sizing Requirements:**

- When an array size is specified, it must be an integral constant expression greater than zero
- Except for the last member of a shader storage block, arrays must be explicitly sized before being indexed with non-constant expressions
- Array size must be declared before passing to a function
- Arrays declared as function formal parameters must specify a size

**Size Declaration Rules:**

- Legal to declare unsized array, then later redeclare with size
- Illegal to declare sized array, then index with constant ≥ declared size
- Illegal to redeclare unsized array with size ≤ any previously used index
- Illegal to index array with negative constant expression

**Runtime Behavior:**

- Undefined behavior results from indexing with non-constant expression ≥ array size or < 0

### Array Types

**Array Type Formation:**
Arrays can be formed from all types (basic types, structures, arrays). All arrays are inherently homogeneous, except for shader storage blocks with unsized arrays as the last member.

**Array Type Syntax:**

```glsl
float[5]        // array of size [5] of float
float[2][3]     // array of size [2][3] of float, not size [3] of float[2]
```

**Usage Examples:**

```glsl
// Return type
float[5] foo() { }

// Constructor
float[5](3.4, 4.2, 5.0, 5.2, 1.1)

// Function parameter
void foo(float[5])

// Variable declaration
float[5] a;
```

### Multi-Dimensional Arrays

**Declaration:**

```glsl
vec4 a[3][2];           // size-3 array of size-2 array of vec4
vec4[2] a[3];           // equivalent declaration
vec4[3][2] a;           // equivalent declaration
```

**Memory Layout:**
In transparent memory (like uniform blocks), inner-most dimensions iterate faster:

```
Low address : a[0][0] : a[0][1] : a[1][0] : a[1][1] : a[2][0] : a[2][1] : High address
```

**Type for Constructors:**
The type needed for constructors and parameters is the full array specification:

```glsl
vec4 b[2] = vec4[2](vec4(0.0), vec4(0.1));
vec4[3][2] a = vec4[3][2](b, b, b);        // constructor
void foo(vec4[3][2]);                      // prototype
```

### Array Initialization

**Constructor Initialization:**

```glsl
float a[5] = float[5](3.4, 4.2, 5.0, 5.2, 1.1);
float a[5] = float[](3.4, 4.2, 5.0, 5.2, 1.1);   // same thing
```

**Initializer List Syntax:**

```glsl
vec4 a[3][2] = {
    vec4[2](vec4(0.0), vec4(1.0)),
    vec4[2](vec4(0.0), vec4(1.0)),
    vec4[2](vec4(0.0), vec4(1.0))
};
```

**Explicit Sizing by Initializer:**

```glsl
float a[5];
float b[] = a;                             // b is explicitly size 5
float b[5] = a;                            // means the same thing
float b[] = float[](1,2,3,4,5);           // also explicitly sizes to 5
```

**Multi-Dimensional Explicit Sizing:**

```glsl
vec4 a[][] = {                             // okay, size to a[3][2]
    vec4[2](vec4(0.0), vec4(1.0)),
    vec4[2](vec4(0.0), vec4(1.0)),
    vec4[2](vec4(0.0), vec4(1.0))
};
```

**Important:** It is a compile-time error to assign to an unsized array (initializers and assignments have different semantics).

### Array Length Method

Arrays provide a `length()` method to determine the number of elements:

```glsl
float a[5];
a.length();     // returns 5 (type int)
```

**Compile-Time vs Runtime Length:**

- If array is explicitly sized: `length()` returns a constant expression
- If array is runtime-sized (last member of shader storage block): `length()` determined at runtime
- For runtime-sized arrays: undefined behavior if indexed with non-constant expression out of bounds

**Multi-Dimensional Arrays:**

```glsl
vec4 a[3][2];
a.length()      // this is 3
a[x].length()   // this is 2
```

**Side Effects Restriction:**
When `length()` returns compile-time constant, the expression cannot contain side effects:

```glsl
float a, b;
const int s = float[2](a=3.0, ++b).length();  // illegal side effects
```

**Evaluation Rules:**

- Compile-time constant: expression parsed but array not dereferenced
- Runtime value: array dereferenced and expressions fully evaluated

### Runtime-Sized Arrays

**Shader Storage Block Context:**
In shader storage blocks, the last member may be declared without explicit size:

```glsl
buffer b {
    float u[];      // error, unless u gets statically sized by link time
    vec4 v[];       // okay, v will be sized dynamically
} name[3];
```

**Restrictions:**

- Only outer-most dimension can lack size
- Cannot form arrays of unknown-sized types (except shader storage blocks)
- Compile-time error to pass as function argument
- Compile-time error to index with negative constant

## Implicit Conversions

### Conversion Table

In some situations, expressions are implicitly converted to different types:

| Type of expression | Can be implicitly converted to |
|-------------------|--------------------------------|
| `int` | `uint`, `float`, `double` |
| `uint` | `float`, `double` |
| `float` | `double` |
| `ivec2`, `ivec3`, `ivec4` | `uvec2`, `uvec3`, `uvec4` |
| `ivec2`, `ivec3`, `ivec4` | `vec2`, `vec3`, `vec4` |
| `uvec2`, `uvec3`, `uvec4` | `vec2`, `vec3`, `vec4` |
| `ivec2`, `ivec3`, `ivec4` | `dvec2`, `dvec3`, `dvec4` |
| `uvec2`, `uvec3`, `uvec4` | `dvec2`, `dvec3`, `dvec4` |
| `vec2`, `vec3`, `vec4` | `dvec2`, `dvec3`, `dvec4` |
| `mat2`, `mat3`, `mat4` | `dmat2`, `dmat3`, `dmat4` |
| `mat2x3`, `mat2x4`, etc. | `dmat2x3`, `dmat2x4`, etc. |

**Important:** There are no implicit array or structure conversions.

### Binary Operator Conversions

When multiple conversion options exist for binary operators:

1. **Floating-point precedence:** Floating-point type chosen if either operand is floating-point
2. **Unsigned precedence:** Unsigned integer type chosen if either operand is unsigned
3. **Signed fallback:** Signed integer type chosen otherwise
4. **Size preference:** Smallest component size used when multiple options from same base type

## Initializers

### Initializer Syntax

At declaration, variables may have initial values:

```
initializer : 
    assignment-expression
    { initializer-list }
    { initializer-list , }

initializer-list : 
    initializer
    initializer-list , initializer
```

### Assignment Expression Initializers

**Global Scope:**
Assignment expressions at global scope can include calls to user-defined functions.

**Type Matching:**
The initializer must be either:

- Same type as the object being initialized
- Type that can be converted according to [REF_ImplicitConversions]

**Constructor Usage:**
Composite variables can be initialized by constructors or initializer lists.

### List Initializers

**Composite Requirement:**
Variables initialized with list initializers must be vectors, matrices, arrays, or structures:

```glsl
int i = { 1 };      // illegal, i is not a composite
```

**Application Rules:**
List initializers are applied to composites with specific rules:

**Vectors:**

- Initializers applied to components in order, starting with component 0
- Number of initializers must match number of components

**Matrices:**

- Initializers must be vector initializers
- Applied to columns in order, starting with column 0  
- Number of initializers must match number of columns

**Structures:**

- Initializers applied to members in declaration order
- Number of initializers must match number of members

**Arrays:**

- Initializers applied to elements in order
- Number of initializers must match number of elements

### Type Matching Rules

**Exact Matching:**
Variable type and initializer must exactly match in:

- Nesting structure
- Number of components/elements/members at each level
- Types of components/elements/members

**Inner-most Initializers:**
Must have same type as object being initialized or be convertible via [REF_ImplicitConversions].

### Initializer Examples

**Valid Matrix Initializations:**

```glsl
mat2x2 a = mat2(vec2(1.0, 0.0), vec2(0.0, 1.0));
mat2x2 b = {vec2(1.0, 0.0), vec2(0.0, 1.0)};
mat2x2 c = {{1.0, 0.0}, {0.0, 1.0}};
```

**Invalid Initializations:**

```glsl
float a[2] = { 3.4, 4.2, 5.0 };                    // illegal
vec2 b = { 1.0, 2.0, 3.0 };                        // illegal  
mat3x3 c = { vec3(0.0), vec3(1.0), vec3(2.0), vec3(3.0) }; // illegal
mat2x2 d = { 1.0, 0.0, 0.0, 1.0 };                 // illegal, can't flatten
struct { float a; int b; } e = { 1.2, 2, 3 };      // illegal
```

**Valid Structure Initializations:**

```glsl
struct { float a; int b; } e = { 1.2, 2 };     // legal, types match
struct { float a; int b; } e = { 1, 3 };       // legal, first converted
```

**Array Sizing by Initializers:**

```glsl
float a[] = float[](3.4, 4.2, 5.0, 5.2, 1.1);     // size 5
float b[] = { 3.4, 4.2, 5.0, 5.2, 1.1 };          // size 5
float c[] = a;                                       // size 5
float d[5] = b;                                      // equivalent
```

## Scoping

### Scope Determination

**Global Scope:**
Variables declared outside all function definitions have global scope from declaration to end of shader.

**Statement Scope:**
Variables declared in control structures are scoped to the end of the associated statement or sub-statement.

**Compound Statement Scope:**
Variables declared within compound statements are scoped to the end of that compound statement.

**Function Parameter Scope:**
Parameters are scoped until the end of the function definition.

### Variable Declaration Scope

**Scope Start:**
Within a declaration, scope starts:

- Immediately after the initializer (if present)
- Immediately after the name being declared (if no initializer)

**Examples:**

```glsl
int x = 1;
{
    int x = 2, y = x;   // y is initialized to 2
}

struct S { int x; };
{
    S S = S(0);         // 'S' visible as struct and constructor
}                       // 'S' now visible as variable

int x = x;              // Error if x not previously defined

int f(int k) {
    int k = k + 3;      // redeclaration error of name k
}

int f(int k) {
    {
        int k = k + 3;  // 2nd k is parameter, initializing first k
        int m = k;      // use of new k, hiding parameter
    }
}
```

### Function Scope

**Function Parameters and Body:**
A function's parameter declarations and body together form a single scope nested in the global scope.

**Function Declaration Scope:**
Function declarations (prototypes) cannot occur inside functions; they must be at global scope.

### Loop and Control Structure Scope

**For and While Loops:**

```glsl
for (int i = 0; i < 10; i++) {
    int i;              // redeclaration error
}
```

The sub-statement does not introduce new scope, so redeclaration causes error.

**Do-While Loops:**

```glsl
int i = 17;
do 
    int i = 4;          // okay, in nested scope
while (i == 0);         // i is 17, scoped outside do-while body
```

**Switch Statements:**
The statement following `switch(...)` forms a nested scope.

**If Statement Expression:**
The if statement's expression does not allow new variable declarations and does not form new scope.

### Name Space Rules

**Shared Namespace:**
All variable names, structure type names, and function names in a given scope share the same namespace.

**Redeclaration Rules:**

- Function names can be redeclared in same scope with same or different parameters
- Implicitly-sized arrays can be redeclared as explicitly-sized arrays of same base type
- Otherwise, redeclaration in same scope causes compile-time error

**Name Hiding:**

- Nested scope redeclaration hides all existing uses of that name
- No way to access hidden name without exiting hiding scope
- Built-in functions exist in scope outside global scope

### Shared Globals

**Cross-Compilation Unit Sharing:**
Shared globals are variables declared with same name in independently compiled units within the same language stage.

**Requirements:**

- Must be declared with same type
- Share same storage
- Arrays must have same base type and explicit size
- Scalars must have exactly same type name and definition
- Structures must have same name, type sequence, and member names

**Initialization Rules:**

- Multiple initializers must all be constant expressions with same value
- Otherwise, link-time error occurs
- Single initializer does not require constant expression

**Array Sizing Across Units:**

- Implicitly sized array in one shader can be explicitly sized by another
- If no explicit size in stage, largest implicit size used
- No cross-stage array sizing
- Unused arrays without static access get size 1
