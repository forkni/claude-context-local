# SOP polysplineSOP

## Overview

The Polyspline SOP fits a spline curve to a polygon or hull and outputs a polygonal approximation of that spline.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Subset of faces to use. Accepts patterns, as described in Pattern Matching. |
| `basis` | Spline Type | Menu | Spline type to use. There are seven choices: |
| `closure` | Close | Menu | Determines if the output spline is open or closed. |
| `divide` | Division Method | Menu | Settings for refining the spline by adding extra divisions. |
| `segsize` | Segment Length | Float | The length of the segments in the resampled curve.     Division Method Standard   If Even Length Segments are selected, Segment Length sets the length of output segments. The number of output segme... |
| `polydivs` | Output Divisions | Int | Number of segments in the resampled curve.     If Division Method = Standard is selected, this has no effect. If Even Length Segments is selected, this parameter sets the number of edges that is cr... |
| `edgedivs` | Sample Divisions | Int | Number of spline divisions before resampling.     If Division Method = Standard is selected, this is the number of subdivisions for every edge. If Even Length Segments is chosen, it has the subtle ... |
| `first` | First CV Count | Int | Number of times to repeat the first control vertex, determining its multiplicity. This determines the number of times to replicate the first vertex of the Source polygon(s). This is most useful whe... |
| `last` | Last CV Count | Int | This determines the number of times to repeat the last control vertex, determining its multiplicity. This determines the number of times to replicate the last vertex of the Source polygon(s). This ... |
| `tension` | CV Tension | Float | The tension exerted by the points from the Source polygons. The greater the tension, the closer the resulting shape will be to the original shape. |

## Usage Examples

### Basic Usage

```python
# Access the SOP polysplineSOP operator
polysplinesop_op = op('polysplinesop1')

# Get/set parameters
freq_value = polysplinesop_op.par.active.eval()
polysplinesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
polysplinesop_op = op('polysplinesop1')
output_op = op('output1')

polysplinesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(polysplinesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
