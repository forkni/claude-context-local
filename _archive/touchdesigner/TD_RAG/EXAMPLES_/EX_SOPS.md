---
title: "Surface Operators (SOPs) Examples"
category: EXAMPLES
document_type: examples
difficulty: intermediate
time_estimate: "25-35 minutes"
user_personas: ["3d_artist", "technical_artist", "generative_designer"]
operators: ["sphereSOP", "gridSOP", "lineSOP", "mergeSOP", "transformSOP", "scriptSOP"]
concepts: ["3d_geometry", "points", "primitives", "vertices", "attributes", "procedural_modeling"]
prerequisites: ["Python_fundamentals", "3D_geometry_basics", "TouchDesigner_SOPs"]
workflows: ["procedural_modeling", "geometry_processing", "3d_animation"]
keywords: ["sop", "geometry", "points", "primitives", "vertices", "attributes", "3d"]
tags: ["python", "sop", "geometry", "3d", "procedural", "modeling", "examples"]
related_docs: ["CLASS_SOP_Class", "CLASS_scriptSOP_Class", "TD_OPERATORS_SOP", "PY_TD_Python_Examples_Reference"]
example_count: 16
---

# TouchDesigner Python Examples: Surface Operators (SOPs)

## Quick Reference

TouchDesigner Surface Operators (SOPs) handle 3D geometry through points, primitives, and vertices. This category covers 16 essential patterns for geometry manipulation, attribute access, point operations, and procedural modeling through Python.

**Key SOP Elements:**

- **Points** - 3D positions in space (x, y, z)
- **Primitives** - Geometric elements (polygons, curves, surfaces)  
- **Vertices** - Points that define primitives
- **Attributes** - Data attached to points, vertices, or primitives

**Core Operations:**

- Point position access and modification
- Primitive iteration and analysis
- Vertex attribute manipulation
- Custom geometry generation
- Attribute system management

---

## Point Operations

### Basic Point Access

```python
# Access points from SOP operator
sphere = op('sphere2')
print(f"Point count: {len(sphere.points)}")

# Iterate through all points
for point in sphere.points:
    print(f"Point {point.index}: ({point.x}, {point.y}, {point.z})")
    print(f"  Owner: {point.owner}")

# Direct point access by index
if len(sphere.points) > 0:
    first_point = sphere.points[0]
    print(f"First point position: {first_point.x}, {first_point.y}, {first_point.z}")
```

### Point Position Manipulation

```python
def movePoints(sop_op, offset_vector):
    """Move all points by offset vector"""
    x_offset, y_offset, z_offset = offset_vector
    
    for point in sop_op.points:
        point.x += x_offset
        point.y += y_offset
        point.z += z_offset
    
    print(f"Moved {len(sop_op.points)} points by {offset_vector}")

def scalePoints(sop_op, scale_factor, center=(0, 0, 0)):
    """Scale points around center"""
    cx, cy, cz = center
    
    for point in sop_op.points:
        # Translate to origin
        rel_x = point.x - cx
        rel_y = point.y - cy 
        rel_z = point.z - cz
        
        # Scale
        rel_x *= scale_factor
        rel_y *= scale_factor
        rel_z *= scale_factor
        
        # Translate back
        point.x = rel_x + cx
        point.y = rel_y + cy
        point.z = rel_z + cz

# Usage examples
movePoints(op('grid1'), (1.0, 0.5, -0.2))
scalePoints(op('circle1'), 1.5, center=(0, 0, 0))
```

---

## Primitive Operations

### Primitive Access and Iteration

```python
# Access primitives from SOP
geometry = op('sphere3')
print(f"Primitive count: {len(geometry.prims)}")

# Iterate through primitives and their vertices
for primitive in geometry.prims:
    print(f"Primitive {primitive.index} has {len(primitive)} vertices")
    
    # Iterate through vertices of this primitive
    for vertex in primitive:
        point = vertex.point  # Get the point this vertex references
        print(f"  Vertex {vertex.index}: Point({point.x}, {point.y}, {point.z})")
```

### Primitive Analysis

```python
def analyzePrimitives(sop_op):
    """Analyze primitive structure of SOP"""
    analysis = {
        'total_primitives': len(sop_op.prims),
        'vertex_counts': {},
        'primitive_types': {},
        'total_vertices': 0
    }
    
    for prim in sop_op.prims:
        vertex_count = len(prim)
        analysis['total_vertices'] += vertex_count
        
        # Count primitives by vertex count
        if vertex_count in analysis['vertex_counts']:
            analysis['vertex_counts'][vertex_count] += 1
        else:
            analysis['vertex_counts'][vertex_count] = 1
        
        # Classify primitive types
        if vertex_count == 3:
            prim_type = 'triangle'
        elif vertex_count == 4:
            prim_type = 'quad'
        elif vertex_count > 4:
            prim_type = 'n-gon'
        else:
            prim_type = 'line'
        
        if prim_type in analysis['primitive_types']:
            analysis['primitive_types'][prim_type] += 1
        else:
            analysis['primitive_types'][prim_type] = 1
    
    return analysis

# Generate analysis report
def reportGeometry(sop_op):
    """Generate comprehensive geometry report"""
    analysis = analyzePrimitives(sop_op)
    
    print(f"Geometry Analysis for {sop_op.name}:")
    print(f"  Points: {len(sop_op.points)}")
    print(f"  Primitives: {analysis['total_primitives']}")
    print(f"  Total Vertices: {analysis['total_vertices']}")
    
    print("  Primitive Types:")
    for prim_type, count in analysis['primitive_types'].items():
        print(f"    {prim_type}: {count}")
    
    print("  Vertex Count Distribution:")
    for vertex_count, prim_count in sorted(analysis['vertex_counts'].items()):
        print(f"    {vertex_count} vertices: {prim_count} primitives")

# Usage
reportGeometry(op('sphere1'))
```

---

## Attribute System

### Point, Vertex, and Primitive Attributes

```python
# Access geometry with attributes
geometry = op('primitive1')

# Get first elements for attribute access
if geometry.points and geometry.prims:
    point = geometry.points[0]
    primitive = geometry.prims[0] 
    vertex = primitive[0] if len(primitive) > 0 else None
    
    # Point attributes (Normal vector)
    print("Point Normal:", point.N[0], point.N[1], point.N[2])
    
    # Vertex attributes (UV coordinates)  
    if vertex:
        print("Vertex UV:", vertex.uv[0], vertex.uv[1])
    
    # Primitive attributes (Color with alpha)
    print("Primitive Color:", primitive.Cd[0], primitive.Cd[1], primitive.Cd[2], primitive.Cd[3])
```

### Attribute Manipulation

```python
def setPointColors(sop_op, color_function=None):
    """Set point colors based on position or function"""
    if color_function is None:
        # Default: color based on Y position
        def color_function(point):
            # Normalize Y to 0-1 range for color
            y_norm = (point.y + 1.0) / 2.0  # Assuming Y range -1 to 1
            return (y_norm, 1.0 - y_norm, 0.5, 1.0)  # Red-green gradient
    
    for point in sop_op.points:
        color = color_function(point)
        point.Cd = color  # Set point color attribute

def setVertexUVs(sop_op, uv_function=None):
    """Set vertex UV coordinates"""
    if uv_function is None:
        # Default: simple planar UV mapping
        def uv_function(vertex):
            point = vertex.point
            u = (point.x + 1.0) / 2.0  # Normalize X to 0-1
            v = (point.z + 1.0) / 2.0  # Normalize Z to 0-1
            return (u, v)
    
    for prim in sop_op.prims:
        for vertex in prim:
            uv = uv_function(vertex)
            vertex.uv = uv

def modifyNormals(sop_op, normal_function=None):
    """Modify point normals"""
    if normal_function is None:
        # Default: point normals toward center
        def normal_function(point):
            # Calculate vector from origin to point
            length = (point.x**2 + point.y**2 + point.z**2)**0.5
            if length > 0:
                return (point.x/length, point.y/length, point.z/length)
            return (0, 1, 0)  # Default up vector
    
    for point in sop_op.points:
        normal = normal_function(point)
        point.N = normal

# Usage examples
setPointColors(op('grid1'))
setVertexUVs(op('sphere1'))
modifyNormals(op('torus1'))
```

---

## Advanced Geometry Operations

### Procedural Geometry Creation

```python
class ProceduralGeometry:
    """Helper class for procedural geometry operations"""
    
    @staticmethod
    def createGrid(sop_op, width=2.0, height=2.0, divisions_x=10, divisions_y=10):
        """Create procedural grid geometry"""
        # This would typically be done with Script SOP
        # Here we show the conceptual approach
        
        points_data = []
        for y in range(divisions_y + 1):
            for x in range(divisions_x + 1):
                # Calculate normalized position
                u = x / divisions_x
                v = y / divisions_y
                
                # Calculate world position
                world_x = (u - 0.5) * width
                world_z = (v - 0.5) * height
                world_y = 0.0
                
                points_data.append((world_x, world_y, world_z))
        
        return points_data
    
    @staticmethod
    def deformGeometry(sop_op, deform_function):
        """Apply custom deformation to geometry"""
        for point in sop_op.points:
            original_pos = (point.x, point.y, point.z)
            new_pos = deform_function(original_pos)
            
            point.x, point.y, point.z = new_pos

# Example deformation functions
def wave_deform(position):
    """Apply sine wave deformation"""
    import math
    x, y, z = position
    
    # Apply wave based on X position and time
    wave_height = math.sin(x * 4.0 + absTime.seconds) * 0.2
    
    return (x, y + wave_height, z)

def spiral_deform(position):
    """Apply spiral deformation"""
    import math
    x, y, z = position
    
    # Calculate distance from center
    radius = math.sqrt(x*x + z*z)
    
    if radius > 0:
        # Calculate angle and add spiral
        angle = math.atan2(z, x) + radius * 2.0
        
        new_x = radius * math.cos(angle)
        new_z = radius * math.sin(angle)
    else:
        new_x, new_z = x, z
    
    return (new_x, y, new_z)

# Apply deformations
ProceduralGeometry.deformGeometry(op('grid1'), wave_deform)
ProceduralGeometry.deformGeometry(op('circle1'), spiral_deform)
```

### Geometry Analysis and Measurement

```python
def calculateBounds(sop_op):
    """Calculate bounding box of geometry"""
    if not sop_op.points:
        return None
    
    # Initialize with first point
    first_point = sop_op.points[0]
    min_x = max_x = first_point.x
    min_y = max_y = first_point.y
    min_z = max_z = first_point.z
    
    # Find min/max values
    for point in sop_op.points[1:]:
        min_x = min(min_x, point.x)
        max_x = max(max_x, point.x)
        min_y = min(min_y, point.y)
        max_y = max(max_y, point.y)
        min_z = min(min_z, point.z)
        max_z = max(max_z, point.z)
    
    return {
        'min': (min_x, min_y, min_z),
        'max': (max_x, max_y, max_z),
        'center': ((min_x + max_x) / 2, (min_y + max_y) / 2, (min_z + max_z) / 2),
        'size': (max_x - min_x, max_y - min_y, max_z - min_z)
    }

def calculateSurfaceArea(sop_op):
    """Calculate approximate surface area of triangulated geometry"""
    import math
    total_area = 0.0
    
    for prim in sop_op.prims:
        if len(prim) == 3:  # Triangle
            # Get triangle vertices
            v0, v1, v2 = prim[0].point, prim[1].point, prim[2].point
            
            # Calculate triangle area using cross product
            # Vector from v0 to v1
            vec1 = (v1.x - v0.x, v1.y - v0.y, v1.z - v0.z)
            # Vector from v0 to v2  
            vec2 = (v2.x - v0.x, v2.y - v0.y, v2.z - v0.z)
            
            # Cross product
            cross = (
                vec1[1] * vec2[2] - vec1[2] * vec2[1],
                vec1[2] * vec2[0] - vec1[0] * vec2[2],
                vec1[0] * vec2[1] - vec1[1] * vec2[0]
            )
            
            # Magnitude of cross product = 2 * triangle area
            magnitude = math.sqrt(cross[0]**2 + cross[1]**2 + cross[2]**2)
            triangle_area = magnitude / 2.0
            
            total_area += triangle_area
    
    return total_area

# Usage and reporting
def reportGeometryMetrics(sop_op):
    """Generate comprehensive geometry metrics"""
    bounds = calculateBounds(sop_op)
    area = calculateSurfaceArea(sop_op)
    
    print(f"Geometry Metrics for {sop_op.name}:")
    print(f"  Points: {len(sop_op.points)}")
    print(f"  Primitives: {len(sop_op.prims)}")
    
    if bounds:
        print(f"  Bounds: {bounds['min']} to {bounds['max']}")
        print(f"  Center: {bounds['center']}")
        print(f"  Size: {bounds['size']}")
    
    print(f"  Surface Area: {area:.4f}")

# Generate metrics
reportGeometryMetrics(op('sphere1'))
```

---

## Script SOP Integration

### Script SOP Python Patterns

```python
# Common patterns for Script SOP operation

def script_sop_example():
    """Example Script SOP implementation patterns"""
    
    # Access script SOP parameters
    script_sop = me  # In Script SOP context
    
    # Get input geometry (if connected)
    input_geo = script_sop.inputs[0] if script_sop.inputs else None
    
    # Access script SOP-specific functions
    # These are available in Script SOP context:
    
    # Create points
    # createPoint(x, y, z)
    
    # Create primitives  
    # createPoly(point_indices)
    # createNURBS(point_indices, order=3)
    
    # Set attributes
    # setPointAttrib(point_index, 'attrib_name', value)
    # setPrimAttrib(prim_index, 'attrib_name', value)
    
    # Example: Create custom geometry
    # for i in range(10):
    #     x = i * 0.1
    #     y = math.sin(x * 4.0) * 0.2
    #     z = 0.0
    #     createPoint(x, y, z)

def script_sop_noise_displacement():
    """Script SOP example: Noise-based displacement"""
    import math
    
    # This would run inside Script SOP
    script_op = me
    
    # Parameters (would be actual Script SOP parameters)
    noise_scale = 0.5
    displacement_amount = 0.1
    
    # Process input points
    if script_op.inputs and script_op.inputs[0]:
        input_sop = script_op.inputs[0]
        
        for i, point in enumerate(input_sop.points):
            # Calculate noise based on position
            noise_x = point.x * noise_scale
            noise_y = point.y * noise_scale  
            noise_z = point.z * noise_scale
            
            # Simple noise approximation
            noise_value = math.sin(noise_x) * math.cos(noise_y) * math.sin(noise_z)
            
            # Displace along normal (assuming normal exists)
            if hasattr(point, 'N'):
                new_x = point.x + point.N[0] * noise_value * displacement_amount
                new_y = point.y + point.N[1] * noise_value * displacement_amount
                new_z = point.z + point.N[2] * noise_value * displacement_amount
                
                # Create displaced point (Script SOP function)
                # createPoint(new_x, new_y, new_z)
```

---

## Cross-References

**Related Documentation:**

- [EX_OPS](./EX_OPS.md) - General operator operations
- [EX_NODE_WIRING](./EX_NODE_WIRING.md) - Connection patterns
- [EX_CHOPS](./EX_CHOPS.md) - Channel operator patterns  
- [CLASSES_/CLASS_Point](../CLASSES_/CLASS_Point.md) - Point class reference
- [CLASSES_/CLASS_Prim](../CLASSES_/CLASS_Prim.md) - Primitive class reference
- [PYTHON_/PY_TD_Python_Examples_Reference](../PYTHON_/PY_TD_Python_Examples_Reference.md) - Complete Python patterns

**Performance Notes:**

- Point operations can be expensive with high-resolution geometry
- Use Script SOP for complex procedural operations rather than Python loops
- Attribute access has overhead - batch operations when possible
- Consider using compiled SOPs (C++) for performance-critical geometry processing

---

## File References

**Source Files (16 total):**

- `SOPs__Text__test_Points__td.txt` - Point access and iteration patterns
- `SOPs__Text__test_Prims_Vertices__td.txt` - Primitive and vertex operations
- `SOPs__Text__test_attributes__td.txt` - Attribute system usage
- `SOPs__Text__script1_script__td.txt` - Script SOP implementation patterns
- `SOPs__Text__text4_callbacks__td.py` - SOP callback integration
- `annotation__*__td.*` - Annotation system (3 files)
- `docsHelper__*__td.*` - Documentation helpers (3 files)
- `open_wiki*__*Execute__*__td.py` - Wiki integration (6 files)

**SOP Element Categories:**

- **Points**: 3D position access and manipulation
- **Primitives**: Geometric element iteration and analysis
- **Vertices**: Point-primitive relationship management
- **Attributes**: Data attachment system (normals, colors, UVs)
- **Script Integration**: Procedural geometry generation patterns

---

*This documentation covers TouchDesigner's Surface Operator system for 3D geometry manipulation, providing essential patterns for point operations, primitive analysis, and procedural modeling through Python.*
