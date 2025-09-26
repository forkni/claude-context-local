---
category: GLSL
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- GLSL_TOP
- GLSL_MAT
concepts:
- distance_functions
- signed_distance_fields
- sdf
- procedural_modeling
- ray_marching
- implicit_surfaces
- mathematical_modeling
- primitive_operations
- sdf_combinations
prerequisites:
- GLSL_fundamentals
- vector_math
- 3d_math_concepts
- GLSL_Ray_Marching_Tutorial
workflows:
- procedural_modeling
- ray_marching
- generative_art
- mathematical_visualization
- sdf_modeling
- procedural_animation
- creative_coding
keywords:
- inigo quilez distance functions
- sdf
- signed distance field
- sphere
- box
- torus
- cylinder
- capsule
- cone
- plane
- octahedron
- ellipsoid
- procedural modeling
- ray marching
- implicit surfaces
- primitive combinations
- union
- subtraction
- intersection
- smooth operations
tags:
- glsl
- sdf
- distance_functions
- procedural
- ray_marching
- mathematical
- reference
- inigo_quilez
- primitives
- advanced
relationships:
  GLSL_Ray_Marching_Tutorial: strong
  GLSL_Built_In_Functions_Reference: strong
  CLASS_glslTOP_Class: medium
related_docs:
- GLSL_Ray_Marching_Tutorial
- GLSL_Built_In_Functions_Reference
- CLASS_glslTOP_Class
hierarchy:
  secondary: procedural_techniques
  tertiary: distance_functions
question_patterns:
- How to write GLSL shaders?
- TouchDesigner GLSL examples?
- GPU programming techniques?
- Shader optimization tips?
common_use_cases:
- procedural_modeling
- ray_marching
- generative_art
- mathematical_visualization
---

# Inigo Quilez Distance Functions

<!-- TD-META
category: GLSL
document_type: reference
operators: [GLSL_TOP, GLSL_MAT]
concepts: [distance_functions, signed_distance_fields, sdf, procedural_modeling, ray_marching, implicit_surfaces, mathematical_modeling, primitive_operations, sdf_combinations]
prerequisites: [GLSL_fundamentals, vector_math, 3d_math_concepts, GLSL_Ray_Marching_Tutorial]
workflows: [procedural_modeling, ray_marching, generative_art, mathematical_visualization, sdf_modeling, procedural_animation, creative_coding]
related: [GLSL_Ray_Marching_Tutorial, GLSL_Built_In_Functions_Reference, CLASS_glslTOP_Class]
relationships: {
  "GLSL_Ray_Marching_Tutorial": "strong",
  "GLSL_Built_In_Functions_Reference": "strong",
  "CLASS_glslTOP_Class": "medium"
}
hierarchy:
  primary: "shader_programming"
  secondary: "procedural_techniques"
  tertiary: "distance_functions"
keywords: [inigo quilez distance functions, sdf, signed distance field, sphere, box, torus, cylinder, capsule, cone, plane, octahedron, ellipsoid, procedural modeling, ray marching, implicit surfaces, primitive combinations, union, subtraction, intersection, smooth operations]
tags: [glsl, sdf, distance_functions, procedural, ray_marching, mathematical, reference, inigo_quilez, primitives, advanced]
TD-META -->

## 🎯 Quick Reference

**Purpose**: GLSL shader programming reference for GPU development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: procedural_modeling, ray_marching, generative_art

**Common Questions Answered**:

- "How to write GLSL shaders?" → [See relevant section]
- "TouchDesigner GLSL examples?" → [See relevant section]
- "GPU programming techniques?" → [See relevant section]
- "Shader optimization tips?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Glsl Fundamentals] → [Vector Math] → [3D Math Concepts]
**This document**: GLSL reference/guide
**Next steps**: [GLSL Ray Marching Tutorial] → [GLSL Built In Functions Reference] → [CLASS glslTOP Class]

**Related Topics**: procedural modeling, ray marching, generative art

## Summary

Comprehensive collection of Inigo Quilez's signed distance functions for procedural modeling and ray marching. Includes primitives, combinations, transformations, and deformation techniques essential for mathematical rendering.

## Relationship Justification

Essential companion to Ray Marching Tutorial, providing the mathematical foundation for procedural geometry. Heavily uses built-in functions for mathematical operations. Core reference for advanced procedural graphics techniques.

## Content

- [Introduction](#introduction)
- [Primitives](#primitives)
  - [Sphere](#sphere)
  - [Box](#box)
  - [Round Box](#round-box)
  - [Box Frame](#box-frame)
  - [Torus](#torus)
  - [Capped Torus](#capped-torus)
  - [Link](#link)
  - [Infinite Cylinder](#infinite-cylinder)
  - [Cone](#cone)
  - [Cone (bound)](#cone-bound)
  - [Infinite Cone](#infinite-cone)
  - [Plane](#plane)
  - [Hexagonal Prism](#hexagonal-prism)
  - [Triangular Prism](#triangular-prism)
  - [Capsule / Line](#capsule--line)
  - [Vertical Capsule](#vertical-capsule)
  - [Vertical Capped Cylinder](#vertical-capped-cylinder)
  - [Arbitrary Capped Cylinder](#arbitrary-capped-cylinder)
  - [Rounded Cylinder](#rounded-cylinder)
  - [Capped Cone](#capped-cone)
  - [Capped Cone (alternative)](#capped-cone-alternative)
  - [Solid Angle](#solid-angle)
  - [Cut Sphere](#cut-sphere)
  - [Cut Hollow Sphere](#cut-hollow-sphere)
  - [Death Star](#death-star)
  - [Round Cone](#round-cone)
  - [Round Cone (alternative)](#round-cone-alternative)
  - [Ellipsoid](#ellipsoid)
  - [Revolved Vesica](#revolved-vesica)
  - [Rhombus](#rhombus)
  - [Octahedron](#octahedron)
  - [Octahedron (bound)](#octahedron-bound)
  - [Pyramid](#pyramid)
  - [Triangle](#triangle)
  - [Quad](#quad)
- [Creating 3D SDFs from 2D SDFs](#creating-3d-sdfs-from-2d-sdfs)
  - [Revolution](#revolution)
  - [Extrusion](#extrusion)
- [Creating 3D SDFs from 3D SDFs](#creating-3d-sdfs-from-3d-sdfs)
  - [Elongation](#elongation)
  - [Rounding](#rounding)
  - [Onion](#onion)
  - [Change of Metric](#change-of-metric)
- [Primitive Combinations](#primitive-combinations)
  - [Union, Subtraction, Intersection](#union-subtraction-intersection)
  - [Smooth Union, Subtraction and Intersection](#smooth-union-subtraction-and-intersection)
- [Positioning](#positioning)
  - [Rotation/Translation](#rotationtranslation)
  - [Scale](#scale)
- [Symmetry and Repetition](#symmetry-and-repetition)
  - [Symmetry](#symmetry)
  - [Infinite and Limited Repetition](#infinite-and-limited-repetition)
- [Deformations and Distortions](#deformations-and-distortions)
  - [Displacement](#displacement)
  - [Twist](#twist)
  - [Bend](#bend)

## Introduction

This comprehensive reference contains distance functions for basic primitives, plus formulas for combining them together for building more complex shapes, as well as distortion functions for shaping objects. These techniques are useful for rendering scenes with raymarching.

Each primitive, modifier and operator function includes an "exact" or "bound" notation. This refers to the properties of the SDF that is generated or returned by the function. An "exact" SDF retains all qualities of a true SDF in Euclidean space - it measures distance exactly, and its gradient always has unit length. A "bound" SDF is no longer a true SDF and only returns a lower bound to the real SDF, which can still be useful in certain scenarios.

SDFs that are "exact" are generally preferred over "bound" ones because they work better with more algorithms and techniques, producing higher quality results. However, some primitives (like the ellipsoid) or operators (like the smooth minimum) cannot be "exact" because the mathematics that describe them prevent it.

All primitives are centered at the origin. You will need to transform the point to get arbitrarily rotated, translated and scaled objects.

### Helper Functions

Many primitives use `dot2()` or `ndot()` functions:

```glsl
float dot2( in vec2 v ) { return dot(v,v); }
float dot2( in vec3 v ) { return dot(v,v); }
float ndot( in vec2 a, in vec2 b ) { return a.x*b.x - a.y*b.y; }
```

## Primitives

### Sphere

**Type:** exact

```glsl
float sdSphere( vec3 p, float s )
{
  return length(p)-s;
}
```

### Box

**Type:** exact

```glsl
float sdBox( vec3 p, vec3 b )
{
  vec3 q = abs(p) - b;
  return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0);
}
```

### Round Box

**Type:** exact

```glsl
float sdRoundBox( vec3 p, vec3 b, float r )
{
  vec3 q = abs(p) - b + r;
  return length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0) - r;
}
```

### Box Frame

**Type:** exact

```glsl
float sdBoxFrame( vec3 p, vec3 b, float e )
{
       p = abs(p  )-b;
  vec3 q = abs(p+e)-e;
  return min(min(
      length(max(vec3(p.x,q.y,q.z),0.0))+min(max(p.x,max(q.y,q.z)),0.0),
      length(max(vec3(q.x,p.y,q.z),0.0))+min(max(q.x,max(p.y,q.z)),0.0)),
      length(max(vec3(q.x,q.y,p.z),0.0))+min(max(q.x,max(q.y,p.z)),0.0));
}
```

### Torus

**Type:** exact

```glsl
float sdTorus( vec3 p, vec2 t )
{
  vec2 q = vec2(length(p.xz)-t.x,p.y);
  return length(q)-t.y;
}
```

### Capped Torus

**Type:** exact

```glsl
float sdCappedTorus( vec3 p, vec2 sc, float ra, float rb)
{
  p.x = abs(p.x);
  float k = (sc.y*p.x>sc.x*p.y) ? dot(p.xy,sc) : length(p.xy);
  return sqrt( dot(p,p) + ra*ra - 2.0*ra*k ) - rb;
}
```

### Link

**Type:** exact

```glsl
float sdLink( vec3 p, float le, float r1, float r2 )
{
  vec3 q = vec3( p.x, max(abs(p.y)-le,0.0), p.z );
  return length(vec2(length(q.xy)-r1,q.z)) - r2;
}
```

### Infinite Cylinder

**Type:** exact

```glsl
float sdCylinder( vec3 p, vec3 c )
{
  return length(p.xz-c.xy)-c.z;
}
```

### Cone

**Type:** exact

```glsl
float sdCone( vec3 p, vec2 c, float h )
{
  // c is the sin/cos of the angle, h is height
  // Alternatively pass q instead of (c,h),
  // which is the point at the base in 2D
  vec2 q = h*vec2(c.x/c.y,-1.0);
    
  vec2 w = vec2( length(p.xz), p.y );
  vec2 a = w - q*clamp( dot(w,q)/dot(q,q), 0.0, 1.0 );
  vec2 b = w - q*vec2( clamp( w.x/q.x, 0.0, 1.0 ), 1.0 );
  float k = sign( q.y );
  float d = min(dot( a, a ),dot(b, b));
  float s = max( k*(w.x*q.y-w.y*q.x),k*(w.y-q.y)  );
  return sqrt(d)*sign(s);
}
```

### Cone (bound)

**Type:** bound (not exact!)

```glsl
float sdCone( vec3 p, vec2 c, float h )
{
  float q = length(p.xz);
  return max(dot(c.xy,vec2(q,p.y)),-h-p.y);
}
```

### Infinite Cone

**Type:** exact

```glsl
float sdCone( vec3 p, vec2 c )
{
    // c is the sin/cos of the angle
    vec2 q = vec2( length(p.xz), -p.y );
    float d = length(q-c*max(dot(q,c), 0.0));
    return d * ((q.x*c.y-q.y*c.x<0.0)?-1.0:1.0);
}
```

### Plane

**Type:** exact

```glsl
float sdPlane( vec3 p, vec3 n, float h )
{
  // n must be normalized
  return dot(p,n) + h;
}
```

### Hexagonal Prism

**Type:** exact

```glsl
float sdHexPrism( vec3 p, vec2 h )
{
  const vec3 k = vec3(-0.8660254, 0.5, 0.57735);
  p = abs(p);
  p.xy -= 2.0*min(dot(k.xy, p.xy), 0.0)*k.xy;
  vec2 d = vec2(
       length(p.xy-vec2(clamp(p.x,-k.z*h.x,k.z*h.x), h.x))*sign(p.y-h.x),
       p.z-h.y );
  return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}
```

### Triangular Prism

**Type:** bound

```glsl
float sdTriPrism( vec3 p, vec2 h )
{
  vec3 q = abs(p);
  return max(q.z-h.y,max(q.x*0.866025+p.y*0.5,-p.y)-h.x*0.5);
}
```

### Capsule / Line

**Type:** exact

```glsl
float sdCapsule( vec3 p, vec3 a, vec3 b, float r )
{
  vec3 pa = p - a, ba = b - a;
  float h = clamp( dot(pa,ba)/dot(ba,ba), 0.0, 1.0 );
  return length( pa - ba*h ) - r;
}
```

### Vertical Capsule

**Type:** exact

```glsl
float sdVerticalCapsule( vec3 p, float h, float r )
{
  p.y -= clamp( p.y, 0.0, h );
  return length( p ) - r;
}
```

### Vertical Capped Cylinder

**Type:** exact

```glsl
float sdCappedCylinder( vec3 p, float h, float r )
{
  vec2 d = abs(vec2(length(p.xz),p.y)) - vec2(r,h);
  return min(max(d.x,d.y),0.0) + length(max(d,0.0));
}
```

### Arbitrary Capped Cylinder

**Type:** exact

```glsl
float sdCappedCylinder( vec3 p, vec3 a, vec3 b, float r )
{
  vec3  ba = b - a;
  vec3  pa = p - a;
  float baba = dot(ba,ba);
  float paba = dot(pa,ba);
  float x = length(pa*baba-ba*paba) - r*baba;
  float y = abs(paba-baba*0.5)-baba*0.5;
  float x2 = x*x;
  float y2 = y*y*baba;
  float d = (max(x,y)<0.0)?-min(x2,y2):(((x>0.0)?x2:0.0)+((y>0.0)?y2:0.0));
  return sign(d)*sqrt(abs(d))/baba;
}
```

### Rounded Cylinder

**Type:** exact

```glsl
float sdRoundedCylinder( vec3 p, float ra, float rb, float h )
{
  vec2 d = vec2( length(p.xz)-2.0*ra+rb, abs(p.y) - h );
  return min(max(d.x,d.y),0.0) + length(max(d,0.0)) - rb;
}
```

### Capped Cone

**Type:** exact

```glsl
float sdCappedCone( vec3 p, float h, float r1, float r2 )
{
  vec2 q = vec2( length(p.xz), p.y );
  vec2 k1 = vec2(r2,h);
  vec2 k2 = vec2(r2-r1,2.0*h);
  vec2 ca = vec2(q.x-min(q.x,(q.y<0.0)?r1:r2), abs(q.y)-h);
  vec2 cb = q - k1 + k2*clamp( dot(k1-q,k2)/dot2(k2), 0.0, 1.0 );
  float s = (cb.x<0.0 && ca.y<0.0) ? -1.0 : 1.0;
  return s*sqrt( min(dot2(ca),dot2(cb)) );
}
```

### Capped Cone (alternative)

**Type:** exact

```glsl
float sdCappedCone( vec3 p, vec3 a, vec3 b, float ra, float rb )
{
  float rba  = rb-ra;
  float baba = dot(b-a,b-a);
  float papa = dot(p-a,p-a);
  float paba = dot(p-a,b-a)/baba;
  float x = sqrt( papa - paba*paba*baba );
  float cax = max(0.0,x-((paba<0.5)?ra:rb));
  float cay = abs(paba-0.5)-0.5;
  float k = rba*rba + baba;
  float f = clamp( (rba*(x-ra)+paba*baba)/k, 0.0, 1.0 );
  float cbx = x-ra - f*rba;
  float cby = paba - f;
  float s = (cbx<0.0 && cay<0.0) ? -1.0 : 1.0;
  return s*sqrt( min(cax*cax + cay*cay*baba,
                     cbx*cbx + cby*cby*baba) );
}
```

### Solid Angle

**Type:** exact

```glsl
float sdSolidAngle( vec3 p, vec2 c, float ra )
{
  // c is the sin/cos of the angle
  vec2 q = vec2( length(p.xz), p.y );
  float l = length(q) - ra;
  float m = length(q - c*clamp(dot(q,c),0.0,ra) );
  return max(l,m*sign(c.y*q.x-c.x*q.y));
}
```

### Cut Sphere

**Type:** exact

```glsl
float sdCutSphere( vec3 p, float r, float h )
{
  // sampling independent computations (only depend on shape)
  float w = sqrt(r*r-h*h);

  // sampling dependant computations
  vec2 q = vec2( length(p.xz), p.y );
  float s = max( (h-r)*q.x*q.x+w*w*(h+r-2.0*q.y), h*q.x-w*q.y );
  return (s<0.0) ? length(q)-r :
         (q.x<w) ? h - q.y     :
                   length(q-vec2(w,h));
}
```

### Cut Hollow Sphere

**Type:** exact

```glsl
float sdCutHollowSphere( vec3 p, float r, float h, float t )
{
  // sampling independent computations (only depend on shape)
  float w = sqrt(r*r-h*h);
  
  // sampling dependant computations
  vec2 q = vec2( length(p.xz), p.y );
  return ((h*q.x<w*q.y) ? length(q-vec2(w,h)) : 
                          abs(length(q)-r) ) - t;
}
```

### Death Star

**Type:** exact

```glsl
float sdDeathStar( vec3 p2, float ra, float rb, float d )
{
  // sampling independent computations (only depend on shape)
  float a = (ra*ra - rb*rb + d*d)/(2.0*d);
  float b = sqrt(max(ra*ra-a*a,0.0));
 
  // sampling dependant computations
  vec2 p = vec2( p2.x, length(p2.yz) );
  if( p.x*b-p.y*a > d*max(b-p.y,0.0) )
    return length(p-vec2(a,b));
  else
    return max( (length(p            )-ra),
               -(length(p-vec2(d,0.0))-rb));
}
```

### Round Cone

**Type:** exact

```glsl
float sdRoundCone( vec3 p, float r1, float r2, float h )
{
  // sampling independent computations (only depend on shape)
  float b = (r1-r2)/h;
  float a = sqrt(1.0-b*b);

  // sampling dependant computations
  vec2 q = vec2( length(p.xz), p.y );
  float k = dot(q,vec2(-b,a));
  if( k<0.0 ) return length(q) - r1;
  if( k>a*h ) return length(q-vec2(0.0,h)) - r2;
  return dot(q, vec2(a,b) ) - r1;
}
```

### Round Cone (alternative)

**Type:** exact

```glsl
float sdRoundCone( vec3 p, vec3 a, vec3 b, float r1, float r2 )
{
  // sampling independent computations (only depend on shape)
  vec3  ba = b - a;
  float l2 = dot(ba,ba);
  float rr = r1 - r2;
  float a2 = l2 - rr*rr;
  float il2 = 1.0/l2;
    
  // sampling dependant computations
  vec3 pa = p - a;
  float y = dot(pa,ba);
  float z = y - l2;
  float x2 = dot2( pa*l2 - ba*y );
  float y2 = y*y*l2;
  float z2 = z*z*l2;

  // single square root!
  float k = sign(rr)*rr*rr*x2;
  if( sign(z)*a2*z2>k ) return  sqrt(x2 + z2)        *il2 - r2;
  if( sign(y)*a2*y2<k ) return  sqrt(x2 + y2)        *il2 - r1;
                        return (sqrt(x2*a2*il2)+y*rr)*il2 - r1;
}
```

### Ellipsoid

**Type:** bound (not exact!)

```glsl
float sdEllipsoid( vec3 p, vec3 r )
{
  float k0 = length(p/r);
  float k1 = length(p/(r*r));
  return k0*(k0-1.0)/k1;
}
```

### Revolved Vesica

**Type:** exact

```glsl
float sdVesicaSegment( in vec3 p, in vec3 a, in vec3 b, in float w )
{
    vec3  c = (a+b)*0.5;
    float l = length(b-a);
    vec3  v = (b-a)/l;
    float y = dot(p-c,v);
    vec2  q = vec2(length(p-c-y*v),abs(y));
    
    float r = 0.5*l;
    float d = 0.5*(r*r-w*w)/w;
    vec3  h = (r*q.x<d*(q.y-r)) ? vec3(0.0,r,0.0) : vec3(-d,0.0,d+w);
 
    return length(q-h.xy) - h.z;
}
```

### Rhombus

**Type:** exact

```glsl
float sdRhombus( vec3 p, float la, float lb, float h, float ra )
{
  p = abs(p);
  vec2 b = vec2(la,lb);
  float f = clamp( (ndot(b,b-2.0*p.xz))/dot(b,b), -1.0, 1.0 );
  vec2 q = vec2(length(p.xz-0.5*b*vec2(1.0-f,1.0+f))*sign(p.x*b.y+p.z*b.x-b.x*b.y)-ra, p.y-h);
  return min(max(q.x,q.y),0.0) + length(max(q,0.0));
}
```

### Octahedron

**Type:** exact

```glsl
float sdOctahedron( vec3 p, float s )
{
  p = abs(p);
  float m = p.x+p.y+p.z-s;
  vec3 q;
       if( 3.0*p.x < m ) q = p.xyz;
  else if( 3.0*p.y < m ) q = p.yzx;
  else if( 3.0*p.z < m ) q = p.zxy;
  else return m*0.57735027;
    
  float k = clamp(0.5*(q.z-q.y+s),0.0,s); 
  return length(vec3(q.x,q.y-s+k,q.z-k)); 
}
```

### Octahedron (bound)

**Type:** bound (not exact)

```glsl
float sdOctahedron( vec3 p, float s)
{
  p = abs(p);
  return (p.x+p.y+p.z-s)*0.57735027;
}
```

### Pyramid

**Type:** exact

```glsl
float sdPyramid( vec3 p, float h )
{
  float m2 = h*h + 0.25;
    
  p.xz = abs(p.xz);
  p.xz = (p.z>p.x) ? p.zx : p.xz;
  p.xz -= 0.5;

  vec3 q = vec3( p.z, h*p.y - 0.5*p.x, h*p.x + 0.5*p.y);
   
  float s = max(-q.x,0.0);
  float t = clamp( (q.y-0.5*p.z)/(m2+0.25), 0.0, 1.0 );
    
  float a = m2*(q.x+s)*(q.x+s) + q.y*q.y;
  float b = m2*(q.x+0.5*t)*(q.x+0.5*t) + (q.y-m2*t)*(q.y-m2*t);
    
  float d2 = min(q.y,-q.x*m2-q.y*0.5) > 0.0 ? 0.0 : min(a,b);
    
  return sqrt( (d2+q.z*q.z)/m2 ) * sign(max(q.z,-p.y));
}
```

### Triangle

**Type:** exact

```glsl
float udTriangle( vec3 p, vec3 a, vec3 b, vec3 c )
{
  vec3 ba = b - a; vec3 pa = p - a;
  vec3 cb = c - b; vec3 pb = p - b;
  vec3 ac = a - c; vec3 pc = p - c;
  vec3 nor = cross( ba, ac );

  return sqrt(
    (sign(dot(cross(ba,nor),pa)) +
     sign(dot(cross(cb,nor),pb)) +
     sign(dot(cross(ac,nor),pc))<2.0)
     ?
     min( min(
     dot2(ba*clamp(dot(ba,pa)/dot2(ba),0.0,1.0)-pa),
     dot2(cb*clamp(dot(cb,pb)/dot2(cb),0.0,1.0)-pb) ),
     dot2(ac*clamp(dot(ac,pc)/dot2(ac),0.0,1.0)-pc) )
     :
     dot(nor,pa)*dot(nor,pa)/dot2(nor) );
}
```

### Quad

**Type:** exact

```glsl
float udQuad( vec3 p, vec3 a, vec3 b, vec3 c, vec3 d )
{
  vec3 ba = b - a; vec3 pa = p - a;
  vec3 cb = c - b; vec3 pb = p - b;
  vec3 dc = d - c; vec3 pc = p - c;
  vec3 ad = a - d; vec3 pd = p - d;
  vec3 nor = cross( ba, ad );

  return sqrt(
    (sign(dot(cross(ba,nor),pa)) +
     sign(dot(cross(cb,nor),pb)) +
     sign(dot(cross(dc,nor),pc)) +
     sign(dot(cross(ad,nor),pd))<3.0)
     ?
     min( min( min(
     dot2(ba*clamp(dot(ba,pa)/dot2(ba),0.0,1.0)-pa),
     dot2(cb*clamp(dot(cb,pb)/dot2(cb),0.0,1.0)-pb) ),
     dot2(dc*clamp(dot(dc,pc)/dot2(dc),0.0,1.0)-pc) ),
     dot2(ad*clamp(dot(ad,pd)/dot2(ad),0.0,1.0)-pd) )
     :
     dot(nor,pa)*dot(nor,pa)/dot2(nor) );
}
```

## Creating 3D SDFs from 2D SDFs

One simple way to create 3D SDFs is to take any 2D SDF and either revolve it or extrude it. This approach has the advantage that if the 2D SDF is exact, the resulting 3D volume is exact as well. This is interesting because creating shapes through 3D boolean operations of basic forms does not produce exact SDFs, while revolution or extrusion of 2D shapes does produce correct SDFs.

### Revolution

```glsl
float opRevolution( in vec3 p, in sdf2d primitive, float o )
{
    vec2 q = vec2( length(p.xz) - o, p.y );
    return primitive(q);
}
```

### Extrusion

```glsl
float opExtrusion( in vec3 p, in sdf2d primitive, in float h )
{
    float d = primitive(p.xy);
    vec2 w = vec2( d, abs(p.z) - h );
    return min(max(w.x,w.y),0.0) + length(max(w,0.0));
}
```

## Creating 3D SDFs from 3D SDFs

It is also possible to create new types of 3D primitives from other 3D primitives.

### Elongation

**Type:** exact

Elongating is a useful way to construct new shapes. It basically splits a primitive in two (four or eight), moves the pieces apart and connects them. It is a perfect distance preserving operation that does not introduce any artifacts in the SDF.

```glsl
float opElongate( in sdf3d primitive, in vec3 p, in vec3 h )
{
    vec3 q = p - clamp( p, -h, h );
    return primitive( q );
}

float opElongate( in sdf3d primitive, in vec3 p, in vec3 h )
{
    vec3 q = abs(p)-h;
    return primitive( max(q,0.0) ) + min(max(q.x,max(q.y,q.z)),0.0);
}
```

For 1D elongations, the first function works perfectly and gives exact exterior and interior distances. The first implementation produces a small core of zero distances inside the volume for 2D and 3D elongations.

### Rounding

**Type:** exact

Rounding a shape is as simple as subtracting some distance (jumping to a different isosurface). If you want to preserve the overall volume of the shape, you can shrink the source primitive by the same amount you are rounding it by.

```glsl
float opRound( in sdf3d primitive, float rad )
{
    return primitive(p) - rad;
}
```

### Onion

**Type:** exact

For carving interiors or giving thickness to primitives, without performing expensive boolean operations and without distorting the distance field into a bound, one can use "onioning". You can use it multiple times to create concentric layers in your SDF.

```glsl
float opOnion( in float sdf, in float thickness )
{
    return abs(sdf)-thickness;
}
```

### Change of Metric

**Type:** bound

Most functions can be modified to use other norms than the euclidean. By replacing `length(p)`, which computes `(x²+y²+z²)^(1/2)`, by `(x^n+y^n+z^n)^(1/n)` one can get variations of the basic primitives that have rounded edges rather than sharp ones. This technique is not recommended as these primitives require more raymarching steps and only give a bound to the real SDF.

```glsl
float length2( vec3 p ) { p=p*p; return sqrt( p.x+p.y+p.z); }

float length6( vec3 p ) { p=p*p*p; p=p*p; return pow(p.x+p.y+p.z,1.0/6.0); }

float length8( vec3 p ) { p=p*p; p=p*p; p=p*p; return pow(p.x+p.y+p.z,1.0/8.0); }
```

## Primitive Combinations

When you cannot simply elongate, round or onion a primitive, you need to combine, carve or intersect basic primitives.

### Union, Subtraction, Intersection

**Union:** exact/bound, **Subtraction:** bound, **Intersection:** bound

These are the most basic combinations of pairs of primitives corresponding to basic boolean operations. The Union and Xor of two SDFs produces a true SDF, but not the Subtraction or Intersection. This is only true in the exterior of the SDF (where distances are positive) and not in the interior.

**Note:** `opSubtraction()` is not commutative and depending on the order of the operands it will produce different results.

```glsl
float opUnion( float d1, float d2 )
{
    return min(d1,d2);
}

float opSubtraction( float d1, float d2 )
{
    return max(-d1,d2);
}

float opIntersection( float d1, float d2 )
{
    return max(d1,d2);
}

float opXor(float d1, float d2 )
{
    return max(min(d1,d2),-max(d1,d2));
}
```

### Smooth Union, Subtraction and Intersection

**Type:** bound, bound, bound

Blending primitives is a powerful tool that allows constructing complex and organic shapes without the geometrical seams that normal boolean operations produce. These operations replace the `min()` and `max()` functions with smooth versions. They all accept an extra parameter `k` that defines the size of the smooth transition between primitives, given in actual distance units.

```glsl
float opSmoothUnion( float d1, float d2, float k )
{
    float h = clamp( 0.5 + 0.5*(d2-d1)/k, 0.0, 1.0 );
    return mix( d2, d1, h ) - k*h*(1.0-h);
}

float opSmoothSubtraction( float d1, float d2, float k )
{
    float h = clamp( 0.5 - 0.5*(d2+d1)/k, 0.0, 1.0 );
    return mix( d2, -d1, h ) + k*h*(1.0-h);
}

float opSmoothIntersection( float d1, float d2, float k )
{
    float h = clamp( 0.5 - 0.5*(d2-d1)/k, 0.0, 1.0 );
    return mix( d2, d1, h ) + k*h*(1.0-h);
}
```

## Positioning

Placing primitives in different locations and orientations in space is a fundamental operation in designing SDFs.

### Rotation/Translation

**Type:** exact

Since rotations and translations don't compress nor dilate space, all we need to do is transform the point being sampled with the inverse of the transformation used to place an object in the scene.

```glsl
vec3 opTx( in vec3 p, in transform t, in sdf3d primitive )
{
    return primitive( invert(t)*p );
}
```

### Scale

**Type:** exact

Scaling an object compresses/dilates space, so we have to take that into account on the resulting distance estimation. This only works with uniform scaling. Non-uniform scaling is not possible while still getting a correct SDF.

```glsl
float opScale( in vec3 p, in float s, in sdf3d primitive )
{
    return primitive(p/s)*s;
}
```

## Symmetry and Repetition

Creating multiple copies of the same object can be done easily at no memory or performance cost by making the SDF function itself symmetric or periodic.

### Symmetry

**Type:** bound and exact

Symmetry is useful since many things around us are symmetric. Often, one can model only half or a quarter of the desired shape and get it duplicated automatically by using the absolute value of the domain coordinates before evaluation. The resulting SDF might not be exact but a bound if the object crosses the mirroring plane.

```glsl
float opSymX( in vec3 p, in sdf3d primitive )
{
    p.x = abs(p.x);
    return primitive(p);
}

float opSymXZ( in vec3 p, in sdf3d primitive )
{
    p.xz = abs(p.xz);
    return primitive(p);
}
```

### Infinite and Limited Repetition

Domain repetition allows creating infinitely many primitives with a single object evaluation:

```glsl
float opRepetition( in vec3 p, in vec3 s, in sdf3d primitive )
{
    vec3 q = p - s*round(p/s);
    return primitive( q );
}
```

In this code `s` is the spacing between instances. This function will only work for symmetric shapes. For limited repetition:

```glsl
vec3 opLimitedRepetition( in vec3 p, in float s, in vec3 l, in sdf3d primitive )
{
    vec3 q = p - s*clamp(round(p/s),-l,l);
    return primitive( q );
}
```

## Deformations and Distortions

Deformations and distortions allow enhancing the shape of primitives or fusing different primitives together. These operations usually distort the distance field and make it non-euclidean, so care must be taken when raymarching them.

### Displacement

The displacement example below uses `sin(20*p.x)*sin(20*p.y)*sin(20*p.z)` as displacement pattern, but you can use anything you might imagine.

```glsl
float opDisplace( in sdf3d primitive, in vec3 p )
{
    float d1 = primitive(p);
    float d2 = displacement(p);
    return d1+d2;
}
```

### Twist

```glsl
float opTwist( in sdf3d primitive, in vec3 p )
{
    const float k = 10.0; // or some other amount
    float c = cos(k*p.y);
    float s = sin(k*p.y);
    mat2  m = mat2(c,-s,s,c);
    vec3  q = vec3(m*p.xz,p.y);
    return primitive(q);
}
```

### Bend

```glsl
float opCheapBend( in sdf3d primitive, in vec3 p )
{
    const float k = 10.0; // or some other amount
    float c = cos(k*p.x);
    float s = sin(k*p.x);
    mat2  m = mat2(c,-s,s,c);
    vec3  q = vec3(m*p.xy,p.z);
    return primitive(q);
}
```
