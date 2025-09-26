---
category: GLSL
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- GLSL_TOP
concepts:
- compute_shaders
- gpu_computing
- parallel_processing
- work_groups
- local_memory
- barriers
- image_operations
- dispatch_operations
- shared_variables
prerequisites:
- GLSL_fundamentals
- parallel_programming_concepts
- GPU_architecture_basics
workflows:
- gpu_computing
- parallel_data_processing
- image_processing
- scientific_computing
- advanced_gpu_workflows
- massively_parallel_algorithms
keywords:
- opengl compute shader
- work groups
- local work group
- gl_WorkGroupSize
- gl_LocalInvocationID
- gl_GlobalInvocationID
- gl_NumWorkGroups
- barriers
- shared memory
- image load store
- dispatch
- parallel computing
- gpu programming
tags:
- glsl
- compute
- opengl
- gpu_computing
- parallel
- work_groups
- advanced
- reference
- programming
relationships:
  GLSL_Atomic_Functions_Reference: strong
  GLSL_Built_In_Functions_Reference: strong
  CLASS_glslTOP_Class: strong
related_docs:
- GLSL_Atomic_Functions_Reference
- GLSL_Built_In_Functions_Reference
- CLASS_glslTOP_Class
hierarchy:
  secondary: compute_shaders
  tertiary: opengl_compute
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- gpu_computing
- parallel_data_processing
- image_processing
- scientific_computing
---

# OpenGL Compute Shader Reference

<!-- TD-META
category: GLSL
document_type: reference
operators: [GLSL_TOP]
concepts: [compute_shaders, gpu_computing, parallel_processing, work_groups, local_memory, barriers, image_operations, dispatch_operations, shared_variables]
prerequisites: [GLSL_fundamentals, parallel_programming_concepts, GPU_architecture_basics]
workflows: [gpu_computing, parallel_data_processing, image_processing, scientific_computing, advanced_gpu_workflows, massively_parallel_algorithms]
related: [GLSL_Atomic_Functions_Reference, GLSL_Built_In_Functions_Reference, CLASS_glslTOP_Class]
relationships: {
  "GLSL_Atomic_Functions_Reference": "strong",
  "GLSL_Built_In_Functions_Reference": "strong", 
  "CLASS_glslTOP_Class": "strong"
}
hierarchy:
  primary: "shader_programming"
  secondary: "compute_shaders"
  tertiary: "opengl_compute"
keywords: [opengl compute shader, work groups, local work group, gl_WorkGroupSize, gl_LocalInvocationID, gl_GlobalInvocationID, gl_NumWorkGroups, barriers, shared memory, image load store, dispatch, parallel computing, gpu programming]
tags: [glsl, compute, opengl, gpu_computing, parallel, work_groups, advanced, reference, programming]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming reference for GPU development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: gpu_computing, parallel_data_processing, image_processing

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Fundamentals] → [Parallel Programming Concepts] → [Gpu Architecture Basics]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Atomic Functions Reference] → [GLSL Built In Functions Reference] → [CLASS glslTOP Class]

**Related Topics**: gpu computing, parallel data processing, image processing

## Summary

Comprehensive OpenGL compute shader reference covering execution model, work groups, built-in variables, and parallel processing concepts. Essential for advanced GPU computing and massively parallel algorithms.

## Relationship Justification

Core compute shader documentation that works closely with atomic functions for thread synchronization and built-in functions for computation. Directly implemented through GLSL TOP class for practical application.

## Content

- [Introduction](#introduction)
- [Execution Model](#execution-model)
  - [Compute Space](#compute-space)
  - [Work Groups](#work-groups)
  - [Local Size](#local-size)
  - [Invocation Hierarchy](#invocation-hierarchy)
- [Dispatch](#dispatch)
  - [glDispatchCompute()](#gldispatchcompute)
  - [glDispatchComputeIndirect()](#gldispatchcomputeindirect)
- [Inputs](#inputs)
  - [Built-in Input Variables](#built-in-input-variables)
  - [gl_NumWorkGroups](#gl_numworkgroups)
  - [gl_WorkGroupID](#gl_workgroupid)
  - [gl_LocalInvocationID](#gl_localinvocationid)
  - [gl_GlobalInvocationID](#gl_globalinvocationid)
  - [gl_LocalInvocationIndex](#gl_localinvocationindex)
  - [Local Size Declaration](#local-size-declaration)
- [Outputs](#outputs)
- [Shared Variables](#shared-variables)
  - [Declaration](#declaration)
  - [Initialization](#initialization)
  - [Shared Memory Coherency](#shared-memory-coherency)
  - [Synchronization](#synchronization)
- [Atomic Operations](#atomic-operations)
  - [atomicAdd()](#atomicadd)
  - [atomicMin()](#atomicmin)
  - [atomicMax()](#atomicmax)
  - [atomicAnd()](#atomicand)
  - [atomicOr()](#atomicor)
  - [atomicXor()](#atomicxor)
  - [atomicExchange()](#atomicexchange)
  - [atomicCompSwap()](#atomiccompswap)
- [Limitations](#limitations)
  - [Work Group Count Limits](#work-group-count-limits)
  - [Local Size Limits](#local-size-limits)
  - [Shared Memory Limits](#shared-memory-limits)
- [See Also](#see-also)

## Introduction

A Compute Shader is a shader stage that is used entirely for computing arbitrary information. While it can do rendering, it is generally used for tasks not directly related to drawing triangles and pixels.

**OpenGL Version Support:**

- Core in version 4.6
- Core since version 4.3
- Core ARB extension: [REF_ARBComputeShader]

Compute shaders operate differently from other shader stages and provide a flexible framework for general-purpose GPU computing.

## Execution Model

Compute shaders operate differently from other shader stages. All other shader stages have a well-defined set of input values and execute at frequencies determined by their nature (vertex shaders execute once per input vertex, fragment shaders execute per fragment).

Compute shaders work very differently:

- The "space" that a compute shader operates on is largely abstract
- It is up to each compute shader to decide what the space means
- The number of compute shader executions is defined by the dispatch function
- Compute shaders have no user-defined inputs and no outputs at all
- Built-in inputs only define where in the execution "space" a particular invocation is

**Data Access:**
If a compute shader wants to take values as input, it must fetch that data via:

- Texture access
- Arbitrary image load
- [GLSL_ShaderStorageBlocks]
- Other interface forms

Similarly, compute shaders must explicitly write to images or shader storage blocks to generate output.

### Compute Space

The space that compute shaders operate within is abstract. There is the concept of a **work group** - the smallest amount of compute operations that the user can execute.

The number of work groups is defined by the user when invoking the compute operation. The space is three-dimensional with "X", "Y", and "Z" groups. Any dimension can be 1, allowing 2D or 1D compute operations.

**Execution Order:**
The system can execute work groups in any order. For a work group set of (3, 1, 2), it could execute:

- Group (0, 0, 0) first
- Then skip to group (1, 0, 1)
- Then jump to (2, 0, 0)

**Important:** Your compute shader should not rely on the order in which individual groups are processed.

### Work Groups

A single work group is not the same as a single compute shader invocation. Within a single work group, there may be many compute shader invocations. The number is defined by the compute shader itself, not by the dispatch call. This is known as the **local size** of the work group.

### Local Size

Every compute shader has a three-dimensional local size (sizes can be 1 to allow 2D or 1D local processing). This defines the number of invocations of the shader within each work group.

### Invocation Hierarchy

**Example Calculation:**

- Local size: (128, 1, 1)
- Work group count: (16, 8, 64)
- Total invocations: 1,048,576 separate shader invocations

Each invocation has a set of inputs that uniquely identifies that specific invocation.

**Practical Application:**
This distinction is useful for image compression/decompression:

- Local size: size of an image block (e.g., 8x8)
- Group count: image size divided by block size
- Each block is processed as a single work group

**Communication:**

- Invocations within a work group execute "in parallel"
- They can communicate through shared variables and special functions
- Invocations in different work groups cannot effectively communicate without potential deadlocking

## Dispatch

Compute shaders are not part of the regular rendering pipeline. They are not involved when executing drawing commands.

### glDispatchCompute()

```c
void glDispatchCompute(GLuint num_groups_x, GLuint num_groups_y, GLuint num_groups_z);
```

Initiates compute operations using the currently active compute shader (via [CLASS_glBindProgramPipeline] or [CLASS_glUseProgram]).

**Parameters:**

- `num_groups_x`, `num_groups_y`, `num_groups_z`: Define the work group count in three dimensions
- These numbers cannot be zero
- Subject to limitations on the number of work groups that can be dispatched

**Note:** While not drawing commands, these are rendering commands and can be conditionally executed.

### glDispatchComputeIndirect()

```c
void glDispatchComputeIndirect(GLintptr indirect);
```

Executes dispatch operations where work group counts come from information stored in a [CLASS_BufferObject]. Similar to indirect drawing for vertex data.

**Parameters:**

- `indirect`: Byte-offset to the buffer currently bound to the `GL_DISPATCH_INDIRECT_BUFFER` target

**Warning:**

- Same limitations on work group counts apply
- Indirect dispatch bypasses OpenGL's usual error checking
- Attempting to dispatch with out-of-bounds work group sizes can cause crashes or GPU hard-locks

## Inputs

Compute shaders cannot have any user-defined input variables. To provide input, use implementation-defined inputs coupled with resources like storage buffers or textures. Use the shader's invocation and work group indices to decide which data to fetch and process.

### Built-in Input Variables

Compute shaders have the following built-in input variables:

```glsl
in uvec3 gl_NumWorkGroups;
in uvec3 gl_WorkGroupID;
in uvec3 gl_LocalInvocationID;
in uvec3 gl_GlobalInvocationID;
in uint  gl_LocalInvocationIndex;
```

### gl_NumWorkGroups

Contains the number of work groups passed to the dispatch function.

### gl_WorkGroupID

The current work group for this shader invocation. Each XYZ component will be on the half-open range [0, gl_NumWorkGroups.XYZ).

### gl_LocalInvocationID

The current invocation of the shader within the work group. Each XYZ component will be on the half-open range [0, gl_WorkGroupSize.XYZ).

### gl_GlobalInvocationID

Uniquely identifies this particular invocation among all invocations of this compute dispatch call. It's a short-hand for:

```glsl
gl_WorkGroupID * gl_WorkGroupSize + gl_LocalInvocationID;
```

### gl_LocalInvocationIndex

A 1D version of `gl_LocalInvocationID`. Identifies this invocation's index within the work group. Short-hand for:

```glsl
gl_LocalInvocationIndex =
    gl_LocalInvocationID.z * gl_WorkGroupSize.x * gl_WorkGroupSize.y +
    gl_LocalInvocationID.y * gl_WorkGroupSize.x + 
    gl_LocalInvocationID.x;
```

### Local Size Declaration

The local size of a compute shader is defined within the shader using a special layout input declaration:

```glsl
layout(local_size_x = X, local_size_y = Y, local_size_z = Z) in;
```

**Rules:**

- By default, local sizes are 1
- For 1D or 2D work group space, specify just X or X and Y components
- Must be integral constant expressions of value greater than 0
- Values must abide by implementation limitations
- Compiler or linker error occurs if they don't

**Built-in Constant:**
The local size is available as a compile-time constant:

```glsl
const uvec3 gl_WorkGroupSize;
```

## Outputs

Compute shaders do not have output variables. To generate output, use resources such as:

- [GLSL_ShaderStorageBlocks]
- [GLSL_ImageLoadStore] operations

## Shared Variables

Global variables in compute shaders can be declared with the `shared` storage qualifier. Values are shared between all invocations within a work group.

### Declaration

```glsl
shared uint sharedData;
shared float sharedArray[64];
shared MyStruct sharedStruct;
```

**Restrictions:**

- Cannot declare opaque types as shared
- Aggregates (arrays and structs) are allowed
- No initializers permitted

### Initialization

At the beginning of a work group, shared variables are uninitialized. Variable declarations cannot have initializers:

```glsl
shared uint foo = 0; // ERROR: No initializers for shared variables
```

To initialize a shared variable:

1. One invocation must explicitly set the variable to the desired value
2. Only one invocation should do so to avoid race conditions

### Shared Memory Coherency

Shared variable access uses the rules for [REF_IncoherentMemoryAccess]. Users must perform synchronization to ensure shared variables are visible.

**Memory Barriers:**

- Shared variables are implicitly declared `coherent`
- Use `memoryBarrierShared()` for shared variable ordering
- `groupMemoryBarrier()` orders memory writes for all variable types within current work group

### Synchronization

While all invocations within a work group execute "in parallel", they don't execute in lock-step. To ensure proper read/write ordering, use the `barrier()` function.

**barrier() Function:**

- Forces explicit synchronization between all invocations in the work group
- Execution will not proceed until all invocations reach this barrier
- After the barrier, all previously written shared variables across all invocations become visible

**Usage Restrictions:**

- `barrier()` can be called from flow-control, but only from uniform flow control
- All expressions leading to `barrier()` evaluation must be dynamically uniform
- Every execution must hit the exact same set of `barrier()` calls in the exact same order

## Atomic Operations

Atomic operations can be performed on shared variables of integral type (and vectors/arrays/structs of them). These functions are shared with [GLSL_ShaderStorageBlocks] atomics.

**Note:** All atomic functions return the original value. The term "nint" represents `int` or `uint`.

### atomicAdd()

```glsl
nint atomicAdd(inout nint mem, nint data)
```

Adds `data` to `mem`.

### atomicMin()

```glsl
nint atomicMin(inout nint mem, nint data)
```

Ensures `mem`'s value is no lower than `data`.

### atomicMax()

```glsl
nint atomicMax(inout nint mem, nint data)
```

Ensures `mem`'s value is no greater than `data`.

### atomicAnd()

```glsl
nint atomicAnd(inout nint mem, nint data)
```

`mem` becomes the bitwise-AND between `mem` and `data`.

### atomicOr()

```glsl
nint atomicOr(inout nint mem, nint data)
```

`mem` becomes the bitwise-OR between `mem` and `data`.

### atomicXor()

```glsl
nint atomicXor(inout nint mem, nint data)
```

`mem` becomes the bitwise-XOR between `mem` and `data`.

### atomicExchange()

```glsl
nint atomicExchange(inout nint mem, nint data)
```

Sets `mem`'s value to `data`.

### atomicCompSwap()

```glsl
nint atomicCompSwap(inout nint mem, nint compare, nint data)
```

If the current value of `mem` equals `compare`, then `mem` is set to `data`. Otherwise it is left unchanged.

## Limitations

### Work Group Count Limits

The number of work groups that can be dispatched is defined by `GL_MAX_COMPUTE_WORK_GROUP_COUNT`. Query with [CLASS_glGetIntegeri_v] with index on the closed range [0, 2], representing X, Y, and Z components.

**Minimum Requirements:**

- All three axes: 65535
- Exceeding this range with [CLASS_glDispatchCompute] is an error
- Exceeding with [CLASS_glDispatchComputeIndirect] may result in program termination

### Local Size Limits

Two sets of limitations apply:

**Dimensional Limitations:**

- Queried with `GL_MAX_COMPUTE_WORK_GROUP_SIZE`
- Minimum requirements:
  - X and Y: 1024
  - Z: 64

**Total Invocations:**

- Product of X, Y, Z components must be less than `GL_MAX_COMPUTE_WORK_GROUP_INVOCATIONS`
- Minimum value: 1024

### Shared Memory Limits

Total storage size for all shared variables is limited by `GL_MAX_COMPUTE_SHARED_MEMORY_SIZE` (in bytes).

**Requirements:**

- OpenGL-required minimum: 32KB
- OpenGL does not specify exact mapping between GL types and shared variable storage
- Use [REF_std140LayoutRules] and [GLSL_UBO]/[GLSL_SSBO] sizes as general guidelines

## See Also

- [GLSL_Write_a_GLSL_TOP](GLSL_Write_a_GLSL_TOP.md)
- [GLSL_Advanced_GLSL_in_Touchdesigner](GLSL_Advanced_GLSL_in_Touchdesigner.md)
