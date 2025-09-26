# SOP captureSOP

## Overview

The Capture SOP is used to weight points in a geometry to capture regions.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Specify the point groups from the first input (input0) to operate on. |
| `rootbone` | Hierarchy | Object | An object hierarchy is traversed to find the Capture Regions with which to do the weighting. This parameter specifies the top of the traversal hierarchy. |
| `weightfrom` | Weight from | Menu | Use this menu to specify where to get the weight from. |
| `captframe` | Capture Frame | Int | Specifies the frame number to do the capture computations. Every time TouchDesigner reaches this frame, the geometry will be re-captured. It is a common practice to set the Capture Frame to an fram... |
| `color` | Point Coloring | Menu | This option colors each point by capture region (using point attributes) according to its capture weight. The points inherit their colors from the Capture Region(s) in which they lie. For example, ... |
| `captfile` | Override File | File | The name of the capture override file (*.ocapt). This file is loaded after TouchDesigner completes its point weighting. Each line of the override file lists a point number, a region (path and primi... |
| `savefile` | Save File | File | The file specified here can be used as a "working file" to save the point weighting of all the points or a selected subset of points. The file format for the capture override files is fairly straig... |
| `autoincr` | Increment Save File | Toggle | This increments the Save File name before saving. Be careful about turning this option off because there is no warning or confirm dialog to prevent you from overwriting an .ocapt file. |
| `savecaptfile` | Save All Data to File | Pulse | This saves the point weighting of all points to the Save File. |
| `savesel` | Save Selected Points to File | Pulse | This saves the point weighting only for the points that are selected in the viewport.      Note: you must be editing this particular SOP in the Viewport for this selection to apply to this SOP. |

## Usage Examples

### Basic Usage

```python
# Access the SOP captureSOP operator
capturesop_op = op('capturesop1')

# Get/set parameters
freq_value = capturesop_op.par.active.eval()
capturesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
capturesop_op = op('capturesop1')
output_op = op('output1')

capturesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(capturesop_op)
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
