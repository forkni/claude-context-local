---
title: "Atomic Compaction - Stream Compaction and Memory Optimization"
description: "Master advanced GPU memory optimization using atomic operations, stream compaction, and parallel data structures"
category: GLSL
difficulty: expert
concepts: ["atomic_operations", "stream_compaction", "parallel_prefix_sums", "memory_optimization", "gpu_synchronization", "data_structures", "performance_optimization"]
operators: ["glslTOP", "textDAT", "mathTOP", "nullTOP", "nullCHOP", "mathCHOP", "noiseTOP", "thresholdTOP", "selectTOP", "analyzeTOP", "renderselectTOP", "toptoCHOP", "geometryCOMP", "glslMAT", "renderTOP", "outTOP"]
user_personas: ["shader_programmer", "gpu_developer", "performance_engineer", "technical_artist", "data_scientist"]
techniques: ["atomic_counters", "stream_compaction", "memory_coalescing", "parallel_algorithms", "data_filtering", "performance_monitoring", "adaptive_algorithms"]
masterclass: true
source: "TouchDesigner Advanced GLSL Masterclass 2019"
---

# ATOMIC_COMPACTION - Stream Compaction and Memory Optimization Reference

## Module Overview

**Educational Objective**: Master advanced GPU memory optimization using atomic operations, stream compaction, and parallel data structures  
**Skill Level**: Expert to Professional  
**Key Concepts**: Atomic counters, stream compaction, parallel prefix sums, memory optimization, GPU synchronization  
**TouchDesigner Integration**: Dynamic data structures, performance analysis, adaptive algorithms, real-time optimization  

## Network Architecture Analysis

**Total Operators**: 38 operators in performance-optimized filtering network  
**Performance Profile**: 0.020ms active cost (1/38 operators active per frame)  
**GPU Performance**: 0.014ms GPU cost, 0.006ms CPU cost  
**Network Design**: Sophisticated data analysis and compaction pipeline  

### Major Network Components

```
atomic_compaction [baseCOMP] - GPU stream compaction system
├── STREAM COMPACTION CORE
│   ├── glsl1 [glslTOP] - Main atomic compaction compute shader
│   ├── math3 [mathTOP] - Compacted output processing
│   ├── newPos [nullTOP] - Compacted particle positions
│   └── posTOP [nullTOP] - Original sparse particle data
├── DATA FILTERING PIPELINE  
│   ├── noise2 [noiseTOP] - Input data generation
│   ├── thresh1 [thresholdTOP] - Filter threshold control
│   ├── select1 [selectTOP] - Data selection and masking
│   └── analyze1 [analyzeTOP] - Compaction analysis
├── ATOMIC COUNTER SYSTEM
│   ├── rs_count [renderselectTOP] - Atomic counter results
│   ├── topto1 [toptoCHOP] - Counter to parameter conversion  
│   └── nParts [nullCHOP] - Dynamic particle count tracking
├── PARAMETER CONTROL SYSTEM
│   ├── dSizeChop [nullCHOP] - Data size management  
│   ├── lSizeChop [nullCHOP] - Local work group size control
│   ├── resChop [nullCHOP] - Resolution management
│   └── math1, math2 [mathCHOP] - Parameter calculations
├── VISUALIZATION PIPELINE
│   ├── partsGeo [geometryCOMP] - Compacted geometry visualization
│   ├── phong1GLSL1 [glslMAT] - Particle rendering material  
│   ├── render1 [renderTOP] - Final compacted particle render
│   └── out1 [outTOP] - Performance visualization output
└── PERFORMANCE MONITORING
    ├── wireframe1 [wireframeMAT] - Debug visualization material
    ├── cam1 [cameraCOMP] - Analysis camera
    └── geo1 [geometryCOMP] - Performance analysis geometry
```

### Performance Architecture

- **Extreme Efficiency**: 50,844 FPS theoretical maximum (0.020ms actual cost)  
- **GPU Optimized**: 70% GPU workload, 30% CPU overhead
- **Dynamic Scaling**: Adaptive compaction based on input density
- **Memory Efficient**: Eliminates sparse data automatically

## Advanced GLSL Techniques Deep Dive

### 1. Stream Compaction with Atomic Counters (glsl1_compute)

**Purpose**: Professional GPU stream compaction using hardware atomic operations

```glsl
// Atomic counter declaration - critical for thread-safe operations
layout(binding = 0, offset = 0) uniform atomic_uint uCount;

layout (local_size_x = 8, local_size_y = 8) in;
void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Sample input data to determine if element qualifies for compaction
    float val = texelFetch(sTD2DInputs[0], gId, 0).x;
    
    uint c = 0;  // Local counter value
    
    // STREAM COMPACTION ALGORITHM
    if(val > 0) {  // Qualification test - customize this condition
        
        // ATOMIC INCREMENT - Thread-safe, hardware-accelerated
        c = atomicCounterIncrement(uCount);
        
        // COMPACTED STORAGE CALCULATION
        int texWidth = int(uTDOutputInfo.res.w);
        ivec2 writeLoc = ivec2(0);
        
        // Convert linear index to 2D texture coordinates
        writeLoc.x = int(c) % texWidth;
        writeLoc.y = int(c) / texWidth;
        
        // WRITE ORIGINAL DATA TO COMPACTED LOCATION
        // Store original thread ID (gId) at compacted location
        imageStore(mTDComputeOutputs[0], writeLoc, 
                   TDOutputSwizzle(vec4(gId, 0, 1)));
    }
    
    // DEBUG OUTPUT - counter value per thread
    imageStore(mTDComputeOutputs[1], ivec2(gl_GlobalInvocationID.xy), 
               TDOutputSwizzle(vec4(c)));
}
```

**Advanced Stream Compaction Concepts**:

#### A. Atomic Counter Architecture

```glsl
layout(binding = 0, offset = 0) uniform atomic_uint uCount;
```

- **Hardware Support**: Uses GPU's native atomic units
- **Thread Safety**: Guaranteed atomic read-modify-write operations
- **Global Scope**: Shared across all compute threads in dispatch
- **High Performance**: Optimized at hardware level for parallel access

#### B. Stream Compaction Algorithm

1. **Input Filtering**: Each thread tests its data against qualification criteria
2. **Atomic Increment**: Qualifying threads get unique, consecutive indices
3. **Data Compaction**: Original data written to compacted locations
4. **Gap Elimination**: Result contains no "holes" or invalid entries

#### C. Coordinate Transformation

```glsl
// Linear index to 2D texture mapping
writeLoc.x = int(c) % texWidth;
writeLoc.y = int(c) / texWidth;
```

- **Linear Packing**: Converts 1D compacted indices to 2D texture coordinates
- **Memory Efficiency**: Ensures contiguous memory layout
- **Cache Friendly**: Sequential access patterns for optimal performance

#### D. Qualification Criteria Customization

```glsl
if(val > 0) {  // Basic threshold test
// if(val > threshold && val < maxThreshold) {  // Range test
// if(length(position - center) < radius) {     // Spatial test
// if(particle.age < particle.lifespan) {      // Temporal test
```

**Use Cases for Stream Compaction**:

- **Particle Systems**: Remove dead/inactive particles
- **Culling Systems**: Pack visible objects after frustum/occlusion culling
- **Data Processing**: Extract elements meeting specific criteria
- **Memory Optimization**: Eliminate sparse arrays and empty slots

### 2. Multi-Stage Stream Processing

**Advanced Workflow Integration**:

```glsl
// Stage 1: Data Generation (noise2 → thresh1)
// Stage 2: Stream Compaction (glsl1_compute)
// Stage 3: Compacted Processing (math3)
// Stage 4: Visualization (render1)
```

This demonstrates a complete pipeline from sparse data generation to compacted processing, showing real-world stream compaction applications.

## TouchDesigner Integration Patterns

### 1. Dynamic Data Structure Management

```python
# Adaptive data structure sizing based on compaction results
def manage_dynamic_arrays():
    compaction_op = op('glsl1')
    counter_result = op('rs_count')
    
    # Get actual number of elements after compaction
    active_count = int(counter_result[0][0])
    original_count = int(op('nParts')[0].eval())
    
    # Calculate compression ratio
    compression_ratio = active_count / original_count if original_count > 0 else 0
    
    # Adaptive memory allocation
    if compression_ratio > 0.8:  # High density - increase capacity
        new_size = min(1024, original_count * 1.2)
    elif compression_ratio < 0.3:  # Low density - reduce capacity  
        new_size = max(64, original_count * 0.8)
    else:
        new_size = original_count
    
    # Update data structure sizes
    op('dSizeChop').par.value0 = new_size
    
    # Log performance metrics
    debug(f"Compaction: {original_count} → {active_count} "
          f"({compression_ratio:.1%} density)")
```

### 2. Performance Analysis and Optimization

```python
# Comprehensive compaction performance monitoring
def analyze_compaction_performance():
    glsl_op = op('glsl1')
    analyze_op = op('analyze1')
    
    # Performance metrics
    cook_time = glsl_op.cookTime
    gpu_memory = glsl_op.gpuMemUsage
    
    # Compaction statistics
    input_pixels = op('noise2').width * op('noise2').height
    output_count = int(op('rs_count')[0][0])
    efficiency = output_count / input_pixels if input_pixels > 0 else 0
    
    # Memory savings calculation
    original_memory = input_pixels * 4  # 4 bytes per pixel (RGBA)
    compacted_memory = output_count * 4
    memory_savings = (original_memory - compacted_memory) / original_memory
    
    # Performance per compacted element
    elements_per_ms = output_count / cook_time if cook_time > 0 else 0
    
    # Adaptive quality control
    if cook_time > (1.0/60.0) * 0.1:  # Using >10% of frame budget
        # Reduce input resolution to maintain performance
        reduce_input_quality()
    elif efficiency < 0.1:  # Very sparse data
        # Consider different filtering thresholds
        adjust_filtering_parameters()
    
    # Log comprehensive metrics
    debug(f"Compaction Performance:")
    debug(f"  Input: {input_pixels} pixels")
    debug(f"  Output: {output_count} elements ({efficiency:.1%} density)")
    debug(f"  Memory Savings: {memory_savings:.1%}")
    debug(f"  Processing Rate: {elements_per_ms:.0f} elements/ms")
    debug(f"  Cook Time: {cook_time:.3f}ms")
```

### 3. Threshold-Based Filtering Integration

```python
# Dynamic threshold control for optimal compaction
def optimize_filtering_threshold():
    threshold_op = op('thresh1')
    analyze_op = op('analyze1')
    
    # Get input data statistics
    input_stats = analyze_op.par
    mean_value = input_stats.mean
    std_deviation = input_stats.std
    max_value = input_stats.maximum
    
    # Calculate optimal threshold based on data distribution
    if std_deviation > 0:
        # Use statistical approach for natural data
        optimal_threshold = mean_value + (std_deviation * 1.5)
    else:
        # Use percentage-based approach for uniform data
        optimal_threshold = max_value * 0.7
    
    # Apply threshold with hysteresis to prevent oscillation
    current_threshold = threshold_op.par.threshold.eval()
    threshold_change = abs(optimal_threshold - current_threshold)
    
    if threshold_change > 0.1:  # Only update for significant changes
        threshold_op.par.threshold = optimal_threshold
        
    # Target specific compaction density (e.g., 30% of original data)
    target_density = 0.3
    current_density = get_current_compaction_density()
    
    if current_density > target_density * 1.2:  # Too dense
        threshold_op.par.threshold = current_threshold * 1.05
    elif current_density < target_density * 0.8:  # Too sparse
        threshold_op.par.threshold = current_threshold * 0.95
```

### 4. Real-time Visualization of Compaction

```python
# Visualize compaction effectiveness in real-time
def setup_compaction_visualization():
    # Color-code particles based on compaction status
    material_op = op('phong1GLSL1')
    
    # Green for compacted particles, red for discarded
    compacted_color = (0.2, 1.0, 0.3)  # Bright green
    discarded_color = (1.0, 0.2, 0.2)  # Bright red
    
    # Update material colors based on compaction results
    density = get_current_compaction_density()
    
    if density > 0.7:  # High density - mostly green
        material_op.par.diffr = 0.2 + (density * 0.8)
        material_op.par.diffg = 1.0
        material_op.par.diffb = 0.3
    else:  # Low density - more red
        material_op.par.diffr = 1.0
        material_op.par.diffg = density
        material_op.par.diffb = 0.2
    
    # Scale particle size based on importance (compacted elements larger)
    geometry_op = op('partsGeo')
    compaction_ratio = get_compaction_ratio()
    particle_scale = 1.0 + (compaction_ratio * 2.0)  # Larger for more compaction
    geometry_op.par.scale = particle_scale
```

## Reusable Code Templates

### 1. Basic Stream Compaction Template

```glsl
// Generic stream compaction with customizable criteria
layout(binding = 0, offset = 0) uniform atomic_uint uCompactedCount;

uniform float uThreshold;
uniform vec2 uRangeMin;
uniform vec2 uRangeMax;

layout (local_size_x = 8, local_size_y = 8) in;

void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Sample input data
    vec4 inputData = texelFetch(sTD2DInputs[0], gId, 0);
    
    // CUSTOMIZABLE QUALIFICATION TEST
    bool qualifies = false;
    
    // Threshold-based qualification
    if(inputData.x > uThreshold) {
        qualifies = true;
    }
    
    // Range-based qualification  
    // if(inputData.xy >= uRangeMin && inputData.xy <= uRangeMax) {
    //     qualifies = true;
    // }
    
    // Distance-based qualification
    // float dist = length(inputData.xy);
    // if(dist > uThreshold && dist < uThreshold * 2.0) {
    //     qualifies = true;  
    // }
    
    uint compactedIndex = 0;
    
    if(qualifies) {
        // Get unique compacted index
        compactedIndex = atomicCounterIncrement(uCompactedCount);
        
        // Calculate output position in compacted array
        int outputWidth = int(uTDOutputInfo.res.w);
        ivec2 outputPos = ivec2(
            int(compactedIndex) % outputWidth,
            int(compactedIndex) / outputWidth
        );
        
        // Store original data at compacted location  
        imageStore(mTDComputeOutputs[0], outputPos, TDOutputSwizzle(inputData));
        
        // Optional: Store original coordinates for reconstruction
        vec4 originalCoords = vec4(gId, 0, 1);
        imageStore(mTDComputeOutputs[1], outputPos, TDOutputSwizzle(originalCoords));
    }
    
    // Debug output: compacted index per thread (0 for non-qualifying)
    imageStore(mTDComputeOutputs[2], gId, TDOutputSwizzle(vec4(compactedIndex)));
}
```

### 2. Multi-Criteria Stream Compaction

```glsl
// Advanced stream compaction with multiple qualification criteria
layout(binding = 0, offset = 0) uniform atomic_uint uActiveCount;
layout(binding = 1, offset = 0) uniform atomic_uint uVisibleCount;
layout(binding = 2, offset = 0) uniform atomic_uint uImportantCount;

struct Element {
    vec2 position;
    vec2 velocity;
    float age;
    float importance;
    int category;
    int flags;
};

uniform float uMaxAge;
uniform float uMinImportance;
uniform vec4 uViewFrustum;  // left, right, bottom, top
uniform int uCategoryMask;

layout (local_size_x = 8, local_size_y = 8) in;

void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Read element data from multiple textures
    vec4 posVel = texelFetch(sTD2DInputs[0], gId, 0);
    vec4 ageImpCatFlags = texelFetch(sTD2DInputs[1], gId, 0);
    
    Element elem;
    elem.position = posVel.xy;
    elem.velocity = posVel.zw;
    elem.age = ageImpCatFlags.x;
    elem.importance = ageImpCatFlags.y;
    elem.category = int(ageImpCatFlags.z);
    elem.flags = int(ageImpCatFlags.w);
    
    // MULTI-CRITERIA QUALIFICATION
    bool isActive = elem.age < uMaxAge;
    bool isVisible = (elem.position.x >= uViewFrustum.x && 
                      elem.position.x <= uViewFrustum.y &&
                      elem.position.y >= uViewFrustum.z && 
                      elem.position.y <= uViewFrustum.w);
    bool isImportant = elem.importance >= uMinImportance;
    bool categoryMatches = (elem.category & uCategoryMask) != 0;
    
    uint activeIndex = 0;
    uint visibleIndex = 0; 
    uint importantIndex = 0;
    
    // PARALLEL COMPACTION INTO MULTIPLE STREAMS
    if(isActive && categoryMatches) {
        activeIndex = atomicCounterIncrement(uActiveCount);
        writeToCompactedArray(0, activeIndex, elem);
    }
    
    if(isVisible && isActive) {
        visibleIndex = atomicCounterIncrement(uVisibleCount);  
        writeToCompactedArray(1, visibleIndex, elem);
    }
    
    if(isImportant && isActive) {
        importantIndex = atomicCounterIncrement(uImportantCount);
        writeToCompactedArray(2, importantIndex, elem);
    }
    
    // Debug output showing classification
    vec4 debugInfo = vec4(
        isActive ? 1.0 : 0.0,
        isVisible ? 1.0 : 0.0, 
        isImportant ? 1.0 : 0.0,
        categoryMatches ? 1.0 : 0.0
    );
    imageStore(mTDComputeOutputs[3], gId, TDOutputSwizzle(debugInfo));
}

void writeToCompactedArray(int arrayIndex, uint compactedIndex, Element elem) {
    int outputWidth = int(uTDOutputInfo.res.w);
    ivec2 outputPos = ivec2(
        int(compactedIndex) % outputWidth,
        int(compactedIndex) / outputWidth  
    );
    
    vec4 posVelData = vec4(elem.position, elem.velocity);
    vec4 propData = vec4(elem.age, elem.importance, elem.category, elem.flags);
    
    imageStore(mTDComputeOutputs[arrayIndex * 2], outputPos, TDOutputSwizzle(posVelData));
    imageStore(mTDComputeOutputs[arrayIndex * 2 + 1], outputPos, TDOutputSwizzle(propData));
}
```

### 3. Prefix Sum Stream Compaction

```glsl
// More advanced: Parallel prefix sum approach to stream compaction
// This is a two-pass algorithm for better performance on large datasets

uniform int uPhase;  // 0 = scan phase, 1 = compact phase
layout(binding = 0, offset = 0) uniform atomic_uint uTotalCount;

// Shared memory for prefix sum calculation
shared uint prefixSums[gl_WorkGroupSize.x * gl_WorkGroupSize.y];
shared uint groupSum;

layout (local_size_x = 8, local_size_y = 8) in;

void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    uint localIndex = gl_LocalInvocationID.y * gl_WorkGroupSize.x + gl_LocalInvocationID.x;
    
    // Sample input and determine if element qualifies
    vec4 inputData = texelFetch(sTD2DInputs[0], gId, 0);
    uint qualifies = (inputData.x > 0) ? 1 : 0;
    
    if(uPhase == 0) {
        // PHASE 1: PARALLEL PREFIX SUM CALCULATION
        
        // Store qualification result in shared memory
        prefixSums[localIndex] = qualifies;
        barrier();
        
        // Up-sweep phase (reduce)
        uint stride = 1;
        while(stride < gl_WorkGroupSize.x * gl_WorkGroupSize.y) {
            if(localIndex % (stride * 2) == 0) {
                prefixSums[localIndex + stride * 2 - 1] += 
                    prefixSums[localIndex + stride - 1];
            }
            stride *= 2;
            barrier();
        }
        
        // Store total for this work group
        if(localIndex == 0) {
            groupSum = prefixSums[gl_WorkGroupSize.x * gl_WorkGroupSize.y - 1];
            prefixSums[gl_WorkGroupSize.x * gl_WorkGroupSize.y - 1] = 0;
        }
        barrier();
        
        // Down-sweep phase (distribute)
        stride = gl_WorkGroupSize.x * gl_WorkGroupSize.y / 2;
        while(stride > 0) {
            if(localIndex % (stride * 2) == 0) {
                uint temp = prefixSums[localIndex + stride - 1];
                prefixSums[localIndex + stride - 1] = 
                    prefixSums[localIndex + stride * 2 - 1];
                prefixSums[localIndex + stride * 2 - 1] += temp;
            }
            stride /= 2;
            barrier();
        }
        
        // Output prefix sum for this element
        uint prefixSum = prefixSums[localIndex];
        imageStore(mTDComputeOutputs[1], gId, TDOutputSwizzle(vec4(prefixSum)));
        
    } else {
        // PHASE 2: COMPACTION USING PREFIX SUMS
        
        if(qualifies == 1) {
            uint prefixSum = uint(texelFetch(sTD2DInputs[1], gId, 0).x);
            
            // Calculate final compacted position
            int outputWidth = int(uTDOutputInfo.res.w);  
            ivec2 outputPos = ivec2(
                int(prefixSum) % outputWidth,
                int(prefixSum) / outputWidth
            );
            
            // Store data at compacted location
            imageStore(mTDComputeOutputs[0], outputPos, TDOutputSwizzle(inputData));
        }
    }
}
```

## Performance Optimization Strategies

### 1. Atomic Operation Optimization

**Minimize Atomic Contention**:

```glsl
// Good: Reduce atomic operations with local aggregation
shared uint localCount;
if(gl_LocalInvocationID.x == 0 && gl_LocalInvocationID.y == 0) {
    localCount = 0;
}
barrier();

// Each thread adds to local counter
if(qualifies) {
    atomicAdd(localCount, 1);
}
barrier();

// Only one thread per work group updates global counter
if(gl_LocalInvocationID.x == 0 && gl_LocalInvocationID.y == 0) {
    uint groupOffset = atomicCounterAdd(uCount, localCount);
    // Distribute offsets to threads...
}
```

**Use Appropriate Atomic Types**:

```glsl
// For counters: atomic_uint (fastest)
layout(binding = 0, offset = 0) uniform atomic_uint uCounter;

// For floating point: Use atomicExchange or manual CAS
// layout(binding = 1, offset = 0) uniform coherent float uFloatValue;
```

### 2. Memory Access Optimization

**Coalesced Global Memory Access**:

```glsl
// Good: Sequential access pattern
ivec2 readPos = ivec2(gl_GlobalInvocationID.x, gl_GlobalInvocationID.y);
vec4 data = texelFetch(sTD2DInputs[0], readPos, 0);

// Bad: Random access pattern
ivec2 randomPos = ivec2(hash(gl_GlobalInvocationID.x), hash(gl_GlobalInvocationID.y));
vec4 data = texelFetch(sTD2DInputs[0], randomPos, 0);
```

**Optimal Work Group Size**:

```glsl
// Optimal for atomic operations: smaller work groups reduce contention
layout (local_size_x = 8, local_size_y = 8) in;  // 64 threads

// For memory-bound: larger work groups better utilize memory bandwidth  
layout (local_size_x = 16, local_size_y = 16) in;  // 256 threads
```

### 3. Algorithm-Level Optimization

**Two-Pass Algorithm for Large Datasets**:

1. **Pass 1**: Count qualifying elements per work group
2. **Pass 2**: Use prefix sums to determine final positions

**Hierarchical Compaction**:

1. **Level 1**: Work group level compaction (shared memory)
2. **Level 2**: Global level compaction (atomic counters)
3. **Level 3**: Host-side compaction if needed

**Adaptive Thresholds**:

```glsl
// Dynamic threshold based on data density
uniform float uBaseThreshold;
uniform float uAdaptiveScale;

float adaptiveThreshold = uBaseThreshold + 
    (texture(sDataDensityMap, vUV).x * uAdaptiveScale);
```

## Advanced Concepts Explained

### Stream Compaction Theory

**Problem Definition**:
Given a sparse array with many invalid/empty elements, create a dense array containing only valid elements while preserving their relative order.

**Applications**:

- **Graphics**: Culling invisible objects, active particle management
- **Data Processing**: Filtering datasets, removing null values
- **Memory Management**: Defragmentation, garbage collection
- **Scientific Computing**: Sparse matrix operations

**Algorithm Complexity**:

- **Naive Serial**: O(n) time, O(n) space
- **Parallel Atomic**: O(n) time, O(1) additional space, but with synchronization overhead
- **Parallel Prefix Sum**: O(log n) time, O(n) space, minimal synchronization

### Atomic Operations on GPU

**Hardware Support**:

- Modern GPUs have dedicated atomic units
- Support for integer atomics (add, min, max, and, or, xor, exchange, CAS)  
- Limited floating-point atomic support (varies by GPU)
- Performance varies significantly between GPU architectures

**Memory Ordering**:

```glsl
// Memory barriers ensure ordering
memoryBarrier();        // General memory barrier
memoryBarrierShared();  // Shared memory only
memoryBarrierBuffer();  // Buffer memory only
memoryBarrierImage();   // Image memory only
```

**Atomic Counter vs. Atomic Add**:

```glsl
// Hardware atomic counter (fastest for simple increment)
uint index = atomicCounterIncrement(uCounter);

// Atomic add (more flexible, slightly slower)
uint index = atomicAdd(uCounter, 1);

// Compare and swap (most general, slowest)
uint expected = 0;
while(!atomicCompSwap(uLock, expected, 1)) {
    expected = 0;  // Try again
}
```

### Memory Coalescing and Bank Conflicts

**Optimal Memory Access**:

- **Coalesced Access**: Adjacent threads access adjacent memory locations
- **Stride Access**: Regular patterns that utilize memory bandwidth efficiently
- **Cache Line Alignment**: Align data structures to cache boundaries

**Bank Conflict Avoidance**:

```glsl
// Good: No bank conflicts
shared uint data[64];  // 64 threads, 64 elements
data[gl_LocalInvocationIndex] = input;

// Bad: Bank conflicts  
shared uint data[32];  // 64 threads, 32 elements
data[gl_LocalInvocationIndex % 32] = input;  // 2 threads per bank
```

## Future Development Guidance

### Progressive Skill Development

1. **Master Atomic Basics**: Understand atomic operations and their performance characteristics
2. **Stream Compaction Fundamentals**: Implement basic threshold-based compaction
3. **Multi-Criteria Filtering**: Extend to complex qualification tests
4. **Performance Optimization**: Learn memory access patterns and atomic optimization
5. **Advanced Algorithms**: Implement prefix sum and hierarchical approaches

### Advanced Extensions

**Parallel Data Structures**:

- **Hash Tables**: GPU-friendly hash table implementations
- **Priority Queues**: Parallel priority queue management
- **Spatial Structures**: Octrees, k-d trees, spatial hashing

**Advanced Compaction**:

- **Segmented Compaction**: Compact within groups/categories
- **Multi-Pass Compaction**: Handle very large datasets
- **Approximate Compaction**: Probabilistic filtering for extreme performance

**Integration with Other Algorithms**:

- **Sort-Compaction**: Combined sorting and compaction operations
- **Scan-Compaction**: Parallel prefix sum integration
- **Reduce-Compaction**: Combining reduction and compaction phases

### TouchDesigner Integration Excellence

**Adaptive Systems**:

```python
# Intelligent compaction parameter adjustment
def adaptive_compaction_control():
    # Monitor system performance
    frame_time = op('render1').cookTime
    compaction_efficiency = get_compaction_ratio()
    memory_pressure = get_gpu_memory_usage()
    
    # Adjust thresholds based on system state
    if frame_time > (1.0/60.0) * 0.8:  # High frame time
        # Increase threshold to compact more aggressively
        increase_compaction_threshold()
    elif compaction_efficiency < 0.1:  # Very sparse
        # Consider different data generation parameters
        adjust_input_parameters()
    
    # Memory pressure handling
    if memory_pressure > 0.8:
        # Force more aggressive compaction
        enable_aggressive_compaction()
```

**Real-time Analytics**:

```python
# Comprehensive compaction analytics dashboard
def create_compaction_dashboard():
    metrics = {
        'input_elements': get_input_count(),
        'output_elements': get_compacted_count(),
        'compression_ratio': get_compression_ratio(),
        'memory_saved': get_memory_savings(),
        'processing_time': get_compaction_time(),
        'throughput': get_elements_per_second(),
        'efficiency': get_compaction_efficiency()
    }
    
    # Update visualization operators
    for metric, value in metrics.items():
        op(f'{metric}_display').par.text = f"{metric}: {value:.2f}"
    
    # Historical tracking
    log_performance_history(metrics)
    
    # Automatic optimization suggestions  
    suggest_optimizations(metrics)
```

This comprehensive reference provides the foundation for professional GPU memory optimization and stream compaction techniques, essential for high-performance real-time applications and large-scale data processing.