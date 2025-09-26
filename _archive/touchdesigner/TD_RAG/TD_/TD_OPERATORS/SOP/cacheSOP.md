# SOP cacheSOP

## Overview

The Cache SOP collects its input geometry in a cache for faster random-access playback of multiple SOPs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While On, this node will cache a single snapshot of it's input's geometry each cook. |
| `prefill` | Pre-Fill | Toggle | Cooks 'Cache Size' number of times to fill the Cache SOP with geometry. When set > 0, it will fill the cache. If set > 0 during playback, it will fill immediately. If set > 0 and saved out, then ne... |
| `cachesize` | Cache Size | Int | The size of the cache. |
| `step` | Step Size | Int | The number of frames that the node will cook before it caches another geometry. When set to 1, it will cache every cook, when set to 2, it will cache every two cooks, etc. |
| `outputindex` | Output Index | Float | Determines which cached geometry to output. 0 is the most recent cached geometry. Valid values are between 0 and cachesize - 1. |
| `cachepoints` | Cache Points Only | Toggle | Store a single topology for the first cached geometry and only point data for the remaining geometries. |
| `blendpos` | Blend Position | Toggle | Interpolate points between geometries. |
| `reset` | Reset | Toggle | When On, clears out all of the cached geometry. |
| `resetpulse` | Reset Pulse | Pulse | Instantly clears out all of the cached geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP cacheSOP operator
cachesop_op = op('cachesop1')

# Get/set parameters
freq_value = cachesop_op.par.active.eval()
cachesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
cachesop_op = op('cachesop1')
output_op = op('output1')

cachesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(cachesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
