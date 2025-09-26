---
title: "Particle Systems - N×N Interactions with Shared Memory Optimization"
description: "Master GPU-accelerated particle physics with N×N interactions and advanced shared memory optimization techniques"
category: GLSL
difficulty: expert
concepts: ["particle_systems", "n_squared_interactions", "shared_memory", "work_group_cooperation", "force_calculations", "memory_optimization", "gpu_physics"]
operators: ["glslTOP", "textDAT", "feedbackTOP", "nullTOP", "nullCHOP", "mathCHOP", "geometryCOMP", "glslMAT", "renderTOP", "outTOP"]
user_personas: ["shader_programmer", "technical_artist", "gpu_developer", "physics_programmer"]
techniques: ["shared_memory_optimization", "tiled_processing", "particle_physics", "force_integration", "memory_coalescing", "performance_optimization"]
masterclass: true
source: "TouchDesigner Advanced GLSL Masterclass 2019"
---

# PARTICLES_SYSTEMS - N×N Particle Interactions with Shared Memory Reference

## Module Overview

**Educational Objective**: Master GPU-accelerated particle physics with N×N interactions and advanced shared memory optimization techniques  
**Skill Level**: Advanced to Expert  
**Key Concepts**: N×N particle interactions, shared memory optimization, GPU work group cooperation, force calculations, memory access patterns  
**TouchDesigner Integration**: Feedback loops, real-time parameter control, particle visualization, CHOP-GLSL parameter binding  

## Network Architecture Analysis

**Total Operators**: 40 operators in sophisticated particle simulation network  
**Performance Profile**: 0.038ms active cost (6/40 operators active per frame)  
**Performance Efficiency**: 99.8% headroom available for 60fps  
**Network Design**: Optimized for real-time particle physics with parameter feedback loops  

### Major Network Components

```
particles [baseCOMP] - GPU particle simulation system
├── PARTICLE SIMULATION CORE
│   ├── glsl1 [glslTOP] - Main particle update compute shader
│   ├── feedback_pos [feedbackTOP] - Temporal particle position storage
│   ├── newPos [nullTOP] - Updated particle positions
│   └── posTOP [nullTOP] - Current particle state
├── SHADER VARIANTS  
│   ├── glsl2_compute [textDAT] - Naive N×N implementation
│   ├── glsl2_compute_shared [textDAT] - Shared memory optimized version
│   └── compute [nullDAT] - Active shader selector
├── PARAMETER CONTROL SYSTEM
│   ├── dSizeChop [nullCHOP] - Particle data size control  
│   ├── lSizeChop [nullCHOP] - Local work group size control
│   ├── nParts [nullCHOP] - Number of particles control
│   ├── resChop [nullCHOP] - Resolution management
│   └── math1, math2 [mathCHOP] - Parameter calculations
├── VISUALIZATION PIPELINE
│   ├── partsGeo [geometryCOMP] - Particle geometry generation
│   ├── phong1GLSL1 [glslMAT] - Particle rendering material
│   ├── render1 [renderTOP] - Final particle render
│   └── out1 [outTOP] - Composite output
├── DATA PROCESSING
│   ├── level1 [levelTOP] - Particle data conditioning
│   ├── noise1, noise2 [noiseTOP] - Initial particle distribution
│   ├── math3 [mathTOP] - Particle position calculations
│   └── reorder1 [reorderTOP] - Data format conversion
└── FEEDBACK & CONTROL
    ├── constants (1,2) [constantCHOP] - Force parameters
    ├── rename1 [renameCHOP] - Parameter routing
    └── cam1 [cameraCOMP] - Particle visualization camera
```

### Performance Architecture

- **Real-time Capability**: 26,109 FPS theoretical maximum (0.038ms actual cost)
- **Scalable Parameters**: Dynamic particle count and force adjustments  
- **Memory Efficient**: Optimized texture-based particle storage
- **Interactive Control**: Live parameter adjustment via CHOP operators

## Advanced GLSL Techniques Deep Dive

### 1. Naive N×N Particle Interaction (glsl2_compute)

**Purpose**: Educational demonstration of the N×N interaction problem and brute-force solution

```glsl
uniform float uAttForce;      // Attraction force strength
uniform float uRepulseForce;  // Repulsion force strength

layout (local_size_x = 8, local_size_y = 8) in;
void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Read current particle state (position + mass)
    vec4 posMass = texelFetch(sTD2DInputs[0], gId, 0);
    vec2 pos = posMass.xy;
    float mass = texture(sTD2DInputs[1], pos+vec2(.5)).x;
    
    // Calculate attraction force to center
    vec2 attForce = vec2(0) - pos;  // Force toward origin
    vec2 repulseForce = vec2(0);
    int texWidth = int(uTDOutputInfo.res.w);
    
    // BRUTE FORCE N×N INTERACTION LOOP
    for(int i = 0; i < texWidth; i++) {
        for (int j = 0; j < texWidth; j++) {
            if(ivec2(i,j) != gId) {  // Skip self-interaction
                
                // Read other particle data
                vec4 posMassOther = texelFetch(sTD2DInputs[0], ivec2(i,j), 0);
                vec2 posOther = posMassOther.xy;
                float massOther = posMassOther.w;
                
                // Calculate repulsion force (inverse square law)
                vec2 dir = pos - posOther;
                float dist = length(dir);
                
                if(dist > 0) {
                    repulseForce += (massOther * mass)/(dist*dist) * dir;
                }
            }
        }
    }
    
    // Integrate forces and update position
    vec2 vel = uAttForce * attForce + 0.0001*uRepulseForce*repulseForce;
    pos = pos + vel;
    
    // Store updated particle state
    posMass.xy = pos;
    posMass.w = mass;
    imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(posMass));
}
```

**N×N Problem Analysis**:

- **Computational Complexity**: O(N²) - each particle checks every other particle  
- **Memory Access**: Repeated texture fetches - very inefficient on GPU
- **Performance Impact**: 64×64 particles = 4,096×4,095 = 16,769,280 force calculations per frame!
- **Scaling Issues**: Becomes prohibitively expensive as particle count increases

**Educational Value**:

- Demonstrates the classic N×N interaction problem in particle physics
- Shows why naive implementations don't scale on GPU architecture  
- Provides baseline for comparison with optimized versions

### 2. Shared Memory Optimized N×N Interaction (glsl2_compute_shared)

**Purpose**: Professional GPU optimization using shared memory and work group cooperation

```glsl
uniform float uAttForce;
uniform float uRepulseForce;

layout (local_size_x = 8, local_size_y = 8) in;

// SHARED MEMORY DECLARATION - Critical optimization!
shared vec4 posMassShared[gl_WorkGroupSize.x][gl_WorkGroupSize.y];

void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Read current particle state
    vec4 posMass = texelFetch(sTD2DInputs[0], gId, 0);
    vec2 pos = posMass.xy;
    float mass = texture(sTD2DInputs[1], pos+vec2(.5)).x;
    
    vec2 attForce = vec2(0) - pos;
    vec2 repulseForce = vec2(0);
    int texWidth = int(uTDOutputInfo.res.w);
    
    // TILED PROCESSING WITH SHARED MEMORY
    for(int i = 0; i < gl_NumWorkGroups.x; i++) {
        for (int j = 0; j < gl_NumWorkGroups.y; j++) {
            
            // COOPERATIVE MEMORY LOADING
            // Each thread loads one particle into shared memory
            ivec2 lookup = ivec2(gl_LocalInvocationID.x + gl_WorkGroupSize.x*i,
                                gl_LocalInvocationID.y + gl_WorkGroupSize.y*j);
            
            posMassShared[gl_LocalInvocationID.x][gl_LocalInvocationID.y] = 
                texelFetch(sTD2DInputs[0], lookup, 0);
            
            // CRITICAL SYNCHRONIZATION
            memoryBarrier();  // Ensure writes are visible
            barrier();        // Wait for all threads in work group
            
            // PROCESS SHARED MEMORY TILE
            for(int k = 0; k < gl_WorkGroupSize.x; k++) {
                for (int l = 0; l < gl_WorkGroupSize.y; l++) {
                    
                    // Read from FAST shared memory instead of slow texture
                    vec4 posMassOther = posMassShared[k][l];
                    vec2 posOther = posMassOther.xy;
                    float massOther = posMassOther.w;
                    
                    // Same physics calculation as naive version
                    vec2 dir = pos - posOther;
                    float dist = length(dir);
                    
                    if(dist > 0) {
                        repulseForce += (massOther * mass)/(dist*dist) * dir;
                    }
                }
            }
            barrier();  // Synchronize before next tile
        }
        barrier();
    }
    
    // Same integration as naive version
    vec2 vel = uAttForce * attForce + 0.0001*uRepulseForce*repulseForce;
    pos = pos + vel;
    
    posMass.xy = pos;
    posMass.w = mass;
    imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(posMass));
}
```

**Advanced GPU Optimization Techniques**:

#### A. Shared Memory Architecture

- **Declaration**: `shared vec4 posMassShared[8][8]` - 64 elements in fast on-chip memory
- **Scope**: Shared among all 64 threads in the work group (8×8)
- **Speed**: ~100x faster access than global texture memory
- **Limitations**: Limited size (~48KB total per work group on most GPUs)

#### B. Tiled Processing Pattern

- **Concept**: Process particles in 8×8 tiles instead of individual particles
- **Memory Reuse**: Each particle data loaded once per tile instead of once per thread
- **Coalesced Access**: All threads load contiguous memory locations
- **Bandwidth Reduction**: Dramatic reduction in memory traffic

#### C. Work Group Cooperation

```glsl
// Each thread cooperatively loads data for the group
posMassShared[gl_LocalInvocationID.x][gl_LocalInvocationID.y] = 
    texelFetch(sTD2DInputs[0], lookup, 0);
```

- **Thread Cooperation**: All 64 threads work together to load 64 particles
- **Single Load Per Thread**: Each thread loads exactly one particle per tile
- **Efficient Utilization**: Maximizes memory bandwidth utilization

#### D. Critical Synchronization

```glsl
memoryBarrier();  // Ensure memory writes are globally visible
barrier();        // Synchronize all threads in work group
```

- **Memory Barrier**: Ensures shared memory writes are visible to all threads
- **Execution Barrier**: Prevents threads from proceeding until all reach this point
- **Data Coherency**: Critical for shared memory correctness

#### E. Performance Improvements

- **Memory Bandwidth**: 10-50x reduction in memory traffic
- **Cache Efficiency**: Better GPU cache utilization  
- **Latency Hiding**: Parallel loading masks memory latency
- **Typical Speedup**: 5-15x faster than naive implementation

## TouchDesigner Integration Patterns

### 1. Parameter Control System

```python  
# Real-time parameter binding for particle forces
def setup_particle_parameters():
    # Force control via CHOP operators
    att_force = op('constant1')  # Attraction force
    rep_force = op('constant2')  # Repulsion force
    
    # Particle count control  
    particle_count = op('nParts')
    
    # Resolution management
    data_size = op('dSizeChop') 
    work_group_size = op('lSizeChop')
    
    # Automatic parameter synchronization
    glsl_op = op('glsl1')
    glsl_op.par.uattforce = att_force[0].eval()
    glsl_op.par.urepulseforce = rep_force[0].eval()
```

### 2. Feedback Loop Architecture

```python
# Temporal particle state management
def setup_particle_feedback():
    # Current positions feed back as next frame's input
    feedback_top = op('feedback_pos')
    particle_glsl = op('glsl1')
    
    # Feedback loop: Output → Feedback → Input
    feedback_top.inputs[0] = particle_glsl
    particle_glsl.inputs[0] = feedback_top
    
    # Initialize with noise for particle distribution
    initial_noise = op('noise1')
    feedback_top.par.seedframe = 1  # Reset condition
```

### 3. Visualization Pipeline  

```python
# Convert particle data to renderable geometry
def setup_particle_visualization():
    # Particle positions to geometry
    parts_geo = op('partsGeo')
    particle_data = op('newPos')
    
    # Data conversion: TOP → CHOP → SOP → Geometry
    topo_chop = op('topto1')  # TOP to CHOP conversion
    topo_chop.par.top = particle_data
    
    # SOP creation from particle positions
    datto_sop = op('datto1')  # DAT to SOP conversion  
    
    # Rendering with custom materials
    particle_material = op('phong1GLSL1')
    parts_geo.par.material = particle_material
```

### 4. Performance Monitoring

```python
# Adaptive quality based on performance  
def monitor_particle_performance():
    glsl_op = op('glsl1')
    render_time = glsl_op.cookTime
    
    current_particles = op('nParts')[0].eval()
    target_frametime = 1.0/60.0  # 60 FPS target
    
    if render_time > target_frametime * 1.2:
        # Reduce particle count
        new_count = max(16, current_particles * 0.9)
        op('constant1').par.value0 = new_count
    elif render_time < target_frametime * 0.5:
        # Increase particle count  
        new_count = min(128, current_particles * 1.1)
        op('constant1').par.value0 = new_count
```

## Reusable Code Templates

### 1. Basic N×N Particle Interaction Template

```glsl
// Simple N×N particle physics template
uniform float uAttractionStrength;
uniform float uRepulsionStrength;  
uniform float uDamping;
uniform float uTimeStep;

layout (local_size_x = 8, local_size_y = 8) in;

void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Read particle state: position (xy), velocity (zw)
    vec4 particle = texelFetch(sTD2DInputs[0], gId, 0);
    vec2 pos = particle.xy;
    vec2 vel = particle.zw;
    
    vec2 totalForce = vec2(0);
    int gridSize = int(uTDOutputInfo.res.w);
    
    // Calculate forces from all other particles
    for(int i = 0; i < gridSize; i++) {
        for(int j = 0; j < gridSize; j++) {
            if(ivec2(i,j) != gId) {
                vec4 otherParticle = texelFetch(sTD2DInputs[0], ivec2(i,j), 0);
                vec2 otherPos = otherParticle.xy;
                
                vec2 dir = pos - otherPos;
                float dist = length(dir);
                
                if(dist > 0.01) {  // Avoid singularity
                    vec2 force = normalize(dir) / (dist * dist);
                    totalForce += uRepulsionStrength * force;
                }
            }
        }
    }
    
    // Add global attraction force
    totalForce += -uAttractionStrength * pos;
    
    // Integrate physics (Verlet or Euler)
    vel = vel * (1.0 - uDamping) + totalForce * uTimeStep;
    pos = pos + vel * uTimeStep;
    
    // Store updated state
    vec4 newParticle = vec4(pos, vel);
    imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(newParticle));
}
```

### 2. Optimized Shared Memory Template

```glsl
// Optimized shared memory particle system template
uniform float uForceStrength;
uniform int uParticleCount;

layout (local_size_x = WORK_GROUP_SIZE, local_size_y = WORK_GROUP_SIZE) in;

// Shared memory for cooperative processing
shared vec4 particleData[WORK_GROUP_SIZE][WORK_GROUP_SIZE];

void main()
{
    ivec2 globalId = ivec2(gl_GlobalInvocationID.xy);
    ivec2 localId = ivec2(gl_LocalInvocationID.xy);
    
    if(globalId.x >= uParticleCount || globalId.y >= uParticleCount) return;
    
    // Read current particle
    vec4 currentParticle = texelFetch(sTD2DInputs[0], globalId, 0);
    vec2 currentPos = currentParticle.xy;
    vec2 totalForce = vec2(0);
    
    // Process particles in tiles
    int tilesX = (uParticleCount + WORK_GROUP_SIZE - 1) / WORK_GROUP_SIZE;
    int tilesY = (uParticleCount + WORK_GROUP_SIZE - 1) / WORK_GROUP_SIZE;
    
    for(int tileY = 0; tileY < tilesY; tileY++) {
        for(int tileX = 0; tileX < tilesX; tileX++) {
            
            // Cooperatively load tile into shared memory
            ivec2 tilePos = ivec2(localId.x + tileX * WORK_GROUP_SIZE,
                                 localId.y + tileY * WORK_GROUP_SIZE);
            
            if(tilePos.x < uParticleCount && tilePos.y < uParticleCount) {
                particleData[localId.x][localId.y] = 
                    texelFetch(sTD2DInputs[0], tilePos, 0);
            }
            
            barrier();  // Wait for all threads to load data
            
            // Process interactions with particles in shared memory
            for(int ly = 0; ly < WORK_GROUP_SIZE; ly++) {
                for(int lx = 0; lx < WORK_GROUP_SIZE; lx++) {
                    vec4 otherParticle = particleData[lx][ly];
                    vec2 otherPos = otherParticle.xy;
                    
                    vec2 dir = currentPos - otherPos;
                    float dist = length(dir);
                    
                    if(dist > 0.01) {
                        vec2 force = calculateForce(dir, dist);
                        totalForce += force;
                    }
                }
            }
            
            barrier();  // Wait before loading next tile
        }
    }
    
    // Update particle based on calculated forces
    vec4 updatedParticle = integrateForces(currentParticle, totalForce);
    imageStore(mTDComputeOutputs[0], globalId, TDOutputSwizzle(updatedParticle));
}

vec2 calculateForce(vec2 dir, float dist) {
    // Customize force calculation here
    return uForceStrength * normalize(dir) / (dist * dist);
}

vec4 integrateForces(vec4 particle, vec2 force) {
    // Customize integration method here
    vec2 pos = particle.xy;
    vec2 vel = particle.zw;
    
    vel += force * 0.016;  // Assume 60 FPS
    pos += vel * 0.016;
    
    return vec4(pos, vel);
}
```

### 3. Multi-Physics Particle Template

```glsl
// Advanced multi-physics particle system
uniform float uGravity;
uniform float uRepulsion;
uniform float uDrag;
uniform float uBoundary;
uniform vec2 uWindForce;

struct Particle {
    vec2 position;
    vec2 velocity; 
    float mass;
    float charge;
    float age;
    float lifespan;
};

layout (local_size_x = 8, local_size_y = 8) in;

void main()
{
    ivec2 gId = ivec2(gl_GlobalInvocationID.xy);
    
    // Read particle data from multiple textures
    vec4 posVel = texelFetch(sTD2DInputs[0], gId, 0);
    vec4 properties = texelFetch(sTD2DInputs[1], gId, 0);
    
    Particle p;
    p.position = posVel.xy;
    p.velocity = posVel.zw;
    p.mass = properties.x;
    p.charge = properties.y;
    p.age = properties.z;
    p.lifespan = properties.w;
    
    // Skip dead particles
    if(p.age > p.lifespan) {
        imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(posVel));
        imageStore(mTDComputeOutputs[1], gId, TDOutputSwizzle(properties));
        return;
    }
    
    vec2 totalForce = vec2(0);
    
    // Environmental forces
    totalForce += vec2(0, -uGravity * p.mass);  // Gravity
    totalForce += uWindForce;                   // Wind
    totalForce += -p.velocity * uDrag;          // Drag
    
    // Particle interactions (could use shared memory optimization here)
    int gridSize = int(uTDOutputInfo.res.w);
    for(int i = 0; i < gridSize; i++) {
        for(int j = 0; j < gridSize; j++) {
            if(ivec2(i,j) != gId) {
                vec4 otherPosVel = texelFetch(sTD2DInputs[0], ivec2(i,j), 0);
                vec4 otherProps = texelFetch(sTD2DInputs[1], ivec2(i,j), 0);
                
                vec2 dir = p.position - otherPosVel.xy;
                float dist = length(dir);
                
                if(dist > 0.01) {
                    // Coulomb force (charge interaction)
                    float force = (p.charge * otherProps.y) / (dist * dist);
                    totalForce += force * normalize(dir);
                    
                    // Van der Waals or other short-range forces
                    if(dist < 0.1) {
                        totalForce += uRepulsion * normalize(dir) / dist;
                    }
                }
            }
        }
    }
    
    // Boundary conditions  
    if(abs(p.position.x) > uBoundary || abs(p.position.y) > uBoundary) {
        p.velocity *= -0.8;  // Bounce with energy loss
        p.position = clamp(p.position, vec2(-uBoundary), vec2(uBoundary));
    }
    
    // Integrate physics
    p.velocity += totalForce / p.mass * 0.016;
    p.position += p.velocity * 0.016;
    p.age += 0.016;
    
    // Output updated particle data
    vec4 newPosVel = vec4(p.position, p.velocity);
    vec4 newProperties = vec4(p.mass, p.charge, p.age, p.lifespan);
    
    imageStore(mTDComputeOutputs[0], gId, TDOutputSwizzle(newPosVel));
    imageStore(mTDComputeOutputs[1], gId, TDOutputSwizzle(newProperties));
}
```

## Performance Optimization Strategies

### 1. Memory Access Optimization

**Coalesced Memory Access**:

```glsl
// Good: Sequential memory access
for(int i = 0; i < workGroupSize; i++) {
    vec4 data = texelFetch(sTD2DInputs[0], ivec2(threadId + i, 0), 0);
}

// Bad: Random memory access  
for(int i = 0; i < workGroupSize; i++) {
    vec4 data = texelFetch(sTD2DInputs[0], ivec2(randomId[i], 0), 0);
}
```

**Texture Cache Optimization**:

```glsl
// Cache-friendly: Process nearby particles together
ivec2 blockStart = (gId / 8) * 8;  // Align to 8×8 blocks
for(int dy = 0; dy < 8; dy++) {
    for(int dx = 0; dx < 8; dx++) {
        ivec2 neighbor = blockStart + ivec2(dx, dy);
        // Process neighbor
    }
}
```

### 2. Computational Optimization

**Early Termination**:

```glsl
// Skip distant particles (spatial partitioning)
vec2 dir = pos - otherPos;
if(length(dir) > cutoffDistance) continue;
```

**Force Approximation**:

```glsl
// Use fast approximations for distant forces
float invDist = inversesqrt(dot(dir, dir));  // Fast inverse square root
vec2 force = dir * invDist * invDist * invDist * strength;
```

**Reduced Precision**:

```glsl
// Use lower precision for intermediate calculations
mediump float dist = length(dir);
mediump vec2 force = calculateForce(dir, dist);
```

### 3. Algorithmic Optimization

**Spatial Partitioning**:

```glsl
// Divide space into grid cells, only check nearby cells
int cellX = int(pos.x / cellSize);
int cellY = int(pos.y / cellSize);

for(int dy = -1; dy <= 1; dy++) {
    for(int dx = -1; dx <= 1; dx++) {
        processCell(cellX + dx, cellY + dy);
    }
}
```

**Hierarchical Methods**:

- Barnes-Hut algorithm for long-range forces
- Multi-level grids for different force ranges
- Adaptive mesh refinement

## Advanced Concepts Explained

### Shared Memory Architecture

**GPU Memory Hierarchy**:

1. **Registers**: Fastest, private to each thread
2. **Shared Memory**: Fast, shared within work group (~100x faster than global)
3. **Global Memory**: Slow, accessible by all threads
4. **Constant Memory**: Fast for uniform access patterns

**Work Group Cooperation**:

- Each work group has 64 threads (8×8)
- All threads can access shared memory  
- Synchronization required for coherent access
- Memory coalescing improves bandwidth utilization

### N×N Interaction Problem

**Scaling Issues**:

- **Linear Scaling**: O(N) - manageable for large N
- **Quadratic Scaling**: O(N²) - becomes prohibitive
- **64 particles**: 4,096 interactions
- **256 particles**: 65,536 interactions  
- **1024 particles**: 1,048,576 interactions

**Solution Approaches**:

1. **Shared Memory**: Reduces memory bandwidth (this module's focus)
2. **Spatial Partitioning**: Reduces algorithm complexity to O(N log N)
3. **Hierarchical Methods**: Tree-based algorithms for O(N log N)
4. **Approximation**: Fast multipole methods for O(N)

### Force Integration Methods

**Euler Integration**:

```glsl
velocity += force * dt;
position += velocity * dt;
```

- Simple, fast, but unstable for large time steps

**Verlet Integration**:  

```glsl
newPos = 2*pos - oldPos + force * dt * dt;
```

- More stable, energy conserving, widely used in physics

**Runge-Kutta Methods**:

- Higher accuracy, more computationally expensive
- Better for stiff differential equations

## Future Development Guidance

### Progressive Skill Development

1. **Master N×N Interactions**: Understand the fundamental problem and solutions
2. **Shared Memory Optimization**: Learn GPU memory hierarchy and optimization techniques  
3. **Advanced Physics**: Implement different force models and integration methods
4. **Spatial Algorithms**: Move beyond brute force to spatial partitioning
5. **Multi-Physics**: Combine multiple physical phenomena

### Advanced Extensions

**Fluid Simulation**:

- Smoothed Particle Hydrodynamics (SPH)
- Position-based fluids  
- Grid-fluid coupling

**Rigid Body Physics**:

- Collision detection and response
- Constraint solving
- Multi-body dynamics

**Soft Body Physics**:

- Mass-spring systems
- Finite element methods
- Cloth and deformable objects

### TouchDesigner Integration Excellence

**Real-time Control**:

```python
# Advanced parameter binding with feedback
def setup_advanced_particle_control():
    # Audio-reactive particle parameters
    audio_in = op('audioin1')
    spectrum = op('audioSpectrum')
    
    # Map audio to particle forces
    bass_energy = spectrum[0][0]  # Low frequency energy
    particle_system = op('glsl1')
    particle_system.par.urepulseforce = bass_energy * 10.0
    
    # Visual feedback for parameter tuning
    force_visualization = op('forceViz')
    force_visualization.par.strength = particle_system.par.urepulseforce
```

**Performance Profiling**:

```python
# Comprehensive performance monitoring
def profile_particle_performance():
    particle_op = op('glsl1')
    
    # Measure different performance aspects
    cook_time = particle_op.cookTime
    memory_usage = particle_op.gpuMemUsage  
    particle_count = op('nParts')[0].eval()
    
    # Calculate performance metrics
    particles_per_ms = particle_count / cook_time if cook_time > 0 else 0
    fps_impact = cook_time / (1.0/60.0) * 100  # Percentage of frame budget
    
    # Log performance data
    debug(f"Particles: {particle_count}, Cook: {cook_time:.3f}ms, "
          f"Rate: {particles_per_ms:.0f} particles/ms, "
          f"Frame Budget: {fps_impact:.1f}%")
```

This comprehensive reference provides the foundation for professional GPU particle physics programming, from basic N×N interactions to advanced shared memory optimization techniques.