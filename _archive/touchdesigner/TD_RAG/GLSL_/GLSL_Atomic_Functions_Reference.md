---
category: GLSL
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- GLSL_TOP
- GLSL_MAT
- Compute_Shader
concepts:
- atomic_operations
- thread_synchronization
- compute_shaders
- parallel_computing
- gpu_synchronization
- atomic_counters
- race_condition_prevention
- parallel_data_processing
prerequisites:
- GLSL_fundamentals
- GLSL_Compute_Shader_Reference
- parallel_programming_concepts
workflows:
- compute_shader_development
- gpu_synchronization
- parallel_data_processing
- advanced_gpu_computing
- thread_safe_operations
- multi_threaded_algorithms
keywords:
- atomic functions
- atomicAdd
- atomicMin
- atomicMax
- atomicAnd
- atomicOr
- atomicXor
- atomicExchange
- atomicCompSwap
- atomicCounter
- thread synchronization
- compute shaders
- race conditions
- parallel computing
- gpu synchronization
tags:
- glsl
- reference
- atomic
- synchronization
- compute
- parallel
- gpu
- advanced
- thread_safe
- multi_threaded
relationships:
  GLSL_Compute_Shader_Reference: strong
  GLSL_Built_In_Functions_Reference: strong
  CLASS_glslTOP_Class: strong
related_docs:
- GLSL_Compute_Shader_Reference
- GLSL_Built_In_Functions_Reference
- CLASS_glslTOP_Class
hierarchy:
  secondary: compute_shaders
  tertiary: atomic_functions
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- compute_shader_development
- gpu_synchronization
- parallel_data_processing
- advanced_gpu_computing
---

# GLSL Atomic Functions Reference

<!-- TD-META
category: GLSL
document_type: reference
operators: [GLSL_TOP, GLSL_MAT, Compute_Shader]
concepts: [atomic_operations, thread_synchronization, compute_shaders, parallel_computing, gpu_synchronization, atomic_counters, race_condition_prevention, parallel_data_processing]
prerequisites: [GLSL_fundamentals, GLSL_Compute_Shader_Reference, parallel_programming_concepts]
workflows: [compute_shader_development, gpu_synchronization, parallel_data_processing, advanced_gpu_computing, thread_safe_operations, multi_threaded_algorithms]
related: [GLSL_Compute_Shader_Reference, GLSL_Built_In_Functions_Reference, CLASS_glslTOP_Class]
relationships: {
  "GLSL_Compute_Shader_Reference": "strong",
  "GLSL_Built_In_Functions_Reference": "strong",
  "CLASS_glslTOP_Class": "strong"
}
hierarchy:
  primary: "shader_programming"
  secondary: "compute_shaders"
  tertiary: "atomic_functions"
keywords: [atomic functions, atomicAdd, atomicMin, atomicMax, atomicAnd, atomicOr, atomicXor, atomicExchange, atomicCompSwap, atomicCounter, thread synchronization, compute shaders, race conditions, parallel computing, gpu synchronization]
tags: [glsl, reference, atomic, synchronization, compute, parallel, gpu, advanced, thread_safe, multi_threaded]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming reference for GPU development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: compute_shader_development, gpu_synchronization, parallel_data_processing

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Fundamentals] → [Glsl Compute Shader Reference] → [Parallel Programming Concepts]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Compute Shader Reference] → [GLSL Built In Functions Reference] → [CLASS glslTOP Class]

**Related Topics**: compute shader development, gpu synchronization, parallel data processing

## Summary

Comprehensive reference for GLSL atomic functions essential for thread-safe operations in parallel computing scenarios. Covers both atomic counter functions and atomic memory functions for preventing race conditions in compute shaders.

## Relationship Justification

Core component of compute shader programming, strongly connected to compute shader reference and GLSL TOP class. Essential for understanding parallel GPU computing and thread synchronization patterns.

## Content

- [Introduction](#introduction)
- [Atomic Counter Functions](#atomic-counter-functions)
  - [Overview](#overview)
  - [atomicCounterIncrement()](#atomiccounterincrement)
  - [atomicCounterDecrement()](#atomiccounterdecrement)
  - [atomicCounter()](#atomiccounter)
  - [atomicCounterAdd()](#atomiccounteradd)
  - [atomicCounterSubtract()](#atomiccountersubtract)
  - [atomicCounterMin()](#atomiccountermin)
  - [atomicCounterMax()](#atomiccountermax)
  - [atomicCounterAnd()](#atomiccounterand)
  - [atomicCounterOr()](#atomiccounteror)
  - [atomicCounterXor()](#atomiccounterxor)
  - [atomicCounterExchange()](#atomiccounterexchange)
  - [atomicCounterCompSwap()](#atomiccountercompswap)
- [Atomic Memory Functions](#atomic-memory-functions)
  - [Overview](#overview-1)
  - [atomicAdd()](#atomicadd)
  - [atomicMin()](#atomicmin)
  - [atomicMax()](#atomicmax)
  - [atomicAnd()](#atomicand)
  - [atomicOr()](#atomicor)
  - [atomicXor()](#atomicxor)
  - [atomicExchange()](#atomicexchange)
  - [atomicCompSwap()](#atomiccompswap)
- [See Also](#see-also)

## Introduction

GLSL provides atomic functions for thread-safe operations on counters and memory locations. These functions are essential for parallel computing scenarios where multiple shader invocations need to safely access shared data without race conditions.

There are two categories of atomic functions:

- **Atomic Counter Functions:** Operate on special `atomic_uint` counter variables
- **Atomic Memory Functions:** Operate on individual integers in buffer object or shared variable storage

## Atomic Counter Functions

### Overview

The atomic-counter operations operate atomically with respect to each other. They are atomic for any single counter, meaning any operation on a specific counter in one shader invocation will be indivisible by any operation on the same counter from another shader invocation.

**Important Notes:**

- No guarantee of atomicity with respect to other forms of counter access
- No guarantee of serialization when applied to separate counters
- Additional synchronization (fences, barriers) may be required for complex scenarios
- The underlying counter is a 32-bit unsigned integer
- Operation results wrap to [0, 2³²-1]

### atomicCounterIncrement()

```glsl
uint atomicCounterIncrement(atomic_uint c)
```

Atomically:

1. Increments the counter for `c`
2. Returns its value **prior to** the increment operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Generating unique IDs across shader invocations
- Counting processed elements in parallel algorithms
- Stream compaction operations

### atomicCounterDecrement()

```glsl
uint atomicCounterDecrement(atomic_uint c)
```

Atomically:

1. Decrements the counter for `c`
2. Returns the value **resulting from** the decrement operation

Both steps are performed atomically with respect to other atomic counter functions.

**Note:** Unlike increment, this returns the value **after** the decrement operation.

### atomicCounter()

```glsl
uint atomicCounter(atomic_uint c)
```

Returns the current counter value for `c`.

**Use Cases:**

- Reading current counter state for conditional logic
- Debugging counter values
- Non-modifying counter queries

### atomicCounterAdd()

```glsl
uint atomicCounterAdd(atomic_uint c, uint data)
```

Atomically:

1. Adds the value of `data` to the counter for `c`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Adding variable amounts to counters
- Accumulating values across shader invocations

### atomicCounterSubtract()

```glsl
uint atomicCounterSubtract(atomic_uint c, uint data)
```

Atomically:

1. Subtracts the value of `data` from the counter for `c`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

### atomicCounterMin()

```glsl
uint atomicCounterMin(atomic_uint c, uint data)
```

Atomically:

1. Sets the counter for `c` to the **minimum** of the counter value and `data`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Finding minimum values across parallel computations
- Implementing reduction operations

### atomicCounterMax()

```glsl
uint atomicCounterMax(atomic_uint c, uint data)
```

Atomically:

1. Sets the counter for `c` to the **maximum** of the counter value and `data`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Finding maximum values across parallel computations
- Implementing reduction operations

### atomicCounterAnd()

```glsl
uint atomicCounterAnd(atomic_uint c, uint data)
```

Atomically:

1. Sets the counter for `c` to the **bitwise AND** of the counter value and `data`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Implementing bit-based flags or masks
- Parallel bit manipulation operations

### atomicCounterOr()

```glsl
uint atomicCounterOr(atomic_uint c, uint data)
```

Atomically:

1. Sets the counter for `c` to the **bitwise OR** of the counter value and `data`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Setting bit flags across multiple invocations
- Implementing parallel bit accumulation

### atomicCounterXor()

```glsl
uint atomicCounterXor(atomic_uint c, uint data)
```

Atomically:

1. Sets the counter for `c` to the **bitwise XOR** of the counter value and `data`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Implementing toggle operations
- Parallel bit manipulation with XOR properties

### atomicCounterExchange()

```glsl
uint atomicCounterExchange(atomic_uint c, uint data)
```

Atomically:

1. Sets the counter value for `c` to the value of `data`
2. Returns the counter value **prior to** the operation

Both steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Atomic value swapping
- Implementing atomic assignment with return of previous value

### atomicCounterCompSwap()

```glsl
uint atomicCounterCompSwap(atomic_uint c, uint compare, uint data)
```

Atomically:

1. Compares the value of `compare` and the counter value for `c`
2. If the values are **equal**, sets the counter value for `c` to the value of `data`
3. Returns the counter value **prior to** the operation

All three steps are performed atomically with respect to other atomic counter functions.

**Use Cases:**

- Lock-free data structure implementations
- Conditional atomic updates
- Compare-and-swap algorithms

## Atomic Memory Functions

### Overview

Atomic memory functions perform atomic operations on individual signed or unsigned integers stored in buffer object or shared variable storage.

**Operation Process:**

1. Read a value from memory
2. Compute a new value using the specified operation
3. Write the new value to memory
4. Return the original value read (converted to shader precision)

**Important Notes:**

- Operations performed at in-memory precision (may differ from shader precision)
- Memory contents guaranteed not to be modified by other operations during atomic execution
- Only supported for limited set of variables (buffer or shared variables)
- Compile error if `mem` argument doesn't correspond to buffer or shared variable
- Array elements and vector components acceptable if underlying storage is buffer/shared
- Functions accept `restrict`, `coherent`, and `volatile` memory qualifications

### atomicAdd()

```glsl
uint atomicAdd(inout uint mem, uint data)
int atomicAdd(inout int mem, int data)
```

Computes a new value by **adding** the value of `data` to the contents of `mem`.

Returns the original value of `mem` before the addition.

**Use Cases:**

- Parallel accumulation operations
- Counting operations across multiple invocations
- Implementing histograms or statistics

### atomicMin()

```glsl
uint atomicMin(inout uint mem, uint data)
int atomicMin(inout int mem, int data)
```

Computes a new value by taking the **minimum** of the value of `data` and the contents of `mem`.

Returns the original value of `mem` before the operation.

**Use Cases:**

- Finding minimum values in parallel reductions
- Implementing bounding box calculations
- Distance field computations

### atomicMax()

```glsl
uint atomicMax(inout uint mem, uint data)
int atomicMax(inout int mem, int data)
```

Computes a new value by taking the **maximum** of the value of `data` and the contents of `mem`.

Returns the original value of `mem` before the operation.

**Use Cases:**

- Finding maximum values in parallel reductions
- Implementing bounding box calculations
- Peak detection algorithms

### atomicAnd()

```glsl
uint atomicAnd(inout uint mem, uint data)
int atomicAnd(inout int mem, int data)
```

Computes a new value by performing a **bit-wise AND** of the value of `data` and the contents of `mem`.

Returns the original value of `mem` before the operation.

**Use Cases:**

- Implementing bit masks
- Parallel bit clearing operations
- Flag management systems

### atomicOr()

```glsl
uint atomicOr(inout uint mem, uint data)
int atomicOr(inout int mem, int data)
```

Computes a new value by performing a **bit-wise OR** of the value of `data` and the contents of `mem`.

Returns the original value of `mem` before the operation.

**Use Cases:**

- Setting bit flags
- Parallel bit accumulation
- Implementing bit sets

### atomicXor()

```glsl
uint atomicXor(inout uint mem, uint data)
int atomicXor(inout int mem, int data)
```

Computes a new value by performing a **bit-wise EXCLUSIVE OR** of the value of `data` and the contents of `mem`.

Returns the original value of `mem` before the operation.

**Use Cases:**

- Implementing toggle operations
- Parallel bit manipulation
- Cryptographic operations

### atomicExchange()

```glsl
uint atomicExchange(inout uint mem, uint data)
int atomicExchange(inout int mem, int data)
```

Computes a new value by simply **copying** the value of `data`.

Returns the original value of `mem` before the operation.

**Use Cases:**

- Atomic value swapping
- Implementing spinlocks
- Lock-free data structure updates

### atomicCompSwap()

```glsl
uint atomicCompSwap(inout uint mem, uint compare, uint data)
int atomicCompSwap(inout int mem, int compare, int data)
```

Compares the value of `compare` and the contents of `mem`. If the values are **equal**, the new value is given by `data`; otherwise, it is taken from the original contents of `mem`.

Returns the original value of `mem` before the operation.

**Use Cases:**

- Lock-free programming algorithms
- Implementing atomic conditional updates
- Building complex synchronization primitives
- Compare-and-swap loops
