---
title: "ArcBall Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
user_personas: ["script_developer", "3d_developer"]
operators: []
concepts: ["3d_interaction", "arcball", "camera_manipulation"]
prerequisites: ["Python_fundamentals", "3d_transforms"]
workflows: ["interactive_3d_viewers", "camera_control_systems"]
keywords: ["arcball", "3d", "viewer", "interaction", "camera", "matrix"]
tags: ["python", "api", "3d", "camera"]
related_docs:
- CLASS_Matrix
- MODULE_tdu
---

# ArcBall Class

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods](#methods)

## Introduction

Encapsulates many aspects of 3D viewer interaction. Rotation via arcball, translation and scale.

```python
a = tdu.ArcBall(forCamera=False)
```

The `forCamera` argument controls whether matrices used by the `tranform` and `setTransform` methods are from the world or camera perspective. When `forCamera` is true, the world matrices are inverted before being returned or used.

## Members

No operator specific members.

## Methods

### beginPan()

`beginPan(u, v)→ None:`

Begin a pan at at the given u and v.

- `u`, `v` - The coordinates to begin the pan at.

Example:

```python
m.beginPan(.1, .2)
```

### beginRotate()

`beginRotate(u, v)→ None:`

Begin an arcball rotation at the given u and v.

- `u`, `v` - The coordinates to begin the rotation at.

Example:

```python
m.beginRotate(.1, .2)
```

### beginDolly()

`beginDolly(u, v)→ None:`

Begin a dolly at at the given u and v.

- `u`, `v` - The coordinates to begin the dolly at.

Example:

```python
m.beginDolly(.1, .2)
```

### pan()

`pan(u, v)→ None:`

Pan the view by the given x and y.

- `u`, `v` - The amount to pan the view by.

Example:

```python
m.pan(.1, .2)
```

### panTo()

`panTo(u, v, scale=1.0)→ None:`

Pan from the u,v given in the last call to `beginPan()` to the given u and v, applying a scale as well to the pan amount.

- `u`, `v` - The coordinates to pan to.
- `scale` - (Keyword, Optional) Scale the operation by this amount.

Example:

```python
m.panTo(.1, .2)
```

### rotateTo()

`rotateTo(u, v, scale=1.0)→ None:`

Rotates the arcball to the given u and v position.

- `u`, `v` - The coordinates to rotate to.
- `scale` - (Keyword, Optional) Scale the operation by this amount.

Example:

```python
m.rotateTo(.1, .2)
```

### dolly()

`dolly(z)→ None:`

Dolly the view by the given z value.

- `z` - The amount to dolly the view by.

Example:

```python
m.dolly(.3)
```

### dollyTo()

`dollyTo(u, v, scale=1.0)→ None:`

Dolly from the u,v given in the last call to `beginDolly()` to the given u and v, applying a scale as well to the dolly amount.

- `u`, `v` - The coordinates to dolly to.
- `scale` - (Keyword, Optional) Scale the operation by this amount.

Example:

```python
m.dollyTo(.1, .2)
```

### transform()

`transform()→ tdu.Matrix:`

Gets the current transform matrix for the arcball.

Example:

```python
m.transform()
```

### setTransform()

`setTransform(matrix)→ None:`

Sets the current transform matrix for the arcball. Scales in the given matrix will be ignored.

- `matrix` - The [CLASS_Matrix] to set the transform to.

Example:

```python
m.setTransform(m)
```

### identity()

`identity()→ None:`

Resets all values of the ArcBall to the default state.

Example:

```python
m.identity()
```
