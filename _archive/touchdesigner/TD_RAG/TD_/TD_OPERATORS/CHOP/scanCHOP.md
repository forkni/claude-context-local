# CHOP scanCHOP

## Overview

The Scan CHOP converts a SOP or TOP to oscilloscope or laser friendly control waves.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `source` | Source OP |  | Choose the source node family. |
| `rate` | Sample Rate |  | Samples per second, the output sample rate. |
| `swap` | Swap Output |  | Reverse the X and Y channel outputs. |
| `xscale` | X Scale |  | Scale the x amplitude. |
| `yscale` | Y Scale |  | Scale the y amplitude. |
| `rotate` | Rotate |  | Specified in degrees, rotates the output x,y values. |
| `randomize` | Randomize Samples |  | Output all samples in a random order. Creates a fuzzy chaotic image on an oscilloscope. |
| `color` | Output Color |  | If on, r,g,b channels are created.If on, r,g,b channels are created. |
| `redscale` | Red Scale |  | Scale the output r channel. |
| `greenscale` | Green Scale |  | Scale the output g channel. |
| `bluescale` | Blue Scale |  | Scale the output b channel. |
| `blankingcount` | Blanking Count |  | In the case of SOP input, the number of black/off positions to insert between geometry primitives.  In the case of TOP input, the number of black/off positions to insert between full raster scans. ... |
| `top` | TOP |  | Path to the TOP node. |
| `width` | Width |  | The number of columns to resample the image at. |
| `height` | Height |  | The number of rows to resample the image at. |
| `level` | Level |  | The number of brightness levels each pixel can have. |
| `limit` | Auto Reduce |  | Automatically reduce the number of rows and columns dynamically to keep the output frame rate   at a constant level. |
| `layered` | Layered |  | Output the pixels in order of brightness, else they are output left to right for each row. |
| `interleave` | Interleave |  | Controls the order in which rows are output to minimize flicker. |
| `sop` | SOP |  | Path to the SOP node. |
| `vertexorder` | Vertex Order |  | Output the points in the same order as the vertices of each polygon, instead of the order in which the points are defined in the geometry. |
| `limitstep` | Limit Step Size |  | Breakup long x,y jumps into several smaller incremental jumps. |
| `stepsize` | Step Size |  | The distance each x,y can change when above option enabled. |
| `vertexrepeat` | Vertex Repeat |  | Repeat each vertex of the each primitive multiple times. |
| `camera` | Camera |  | Project the geometry onto a 2D plane from this camera, otherwise, only the original x,y components of the geometry are used. |
| `chop` | CHOP |  | Path to the CHOP node. |
| `trigger` | Trigger |  | The output graph will begin where its value exceeds this value. This allows for steady 'frozen' waveforms, analagous to an oscilloscope triggered sweep. |
| `triggerval` | Trigger Value |  | The value to begin the trigger. |
| `trim` | Trim |  | Limit the length of the CHOP to be scanned. |
| `trimval` | Trim Value |  | The length of the CHOP to be scanned. |
| `trimunits` | Trim Units |  | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP scanCHOP operator
scanchop_op = op('scanchop1')

# Get/set parameters
freq_value = scanchop_op.par.active.eval()
scanchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
scanchop_op = op('scanchop1')
output_op = op('output1')

scanchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(scanchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **37** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
