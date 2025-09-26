# CHOP laserCHOP

## Overview

The Laser CHOP produces channels that can drive a laser projector. It uses the points and lines of a SOP or CHOP and outputs the channels at a specified sample rate.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When disabled, the CHOP will zero out all channels. |
| `source` | Source OP | Menu | Select the source operator type for the laser image. |
| `sop` | SOP | SOP | Path to the SOP. |
| `chop` | CHOP | CHOP | Path to the CHOP. The input CHOP must have x, y channels for the point positions. In addition, it also supports z, r, g, b, and id channels. The id channel is used for grouping points together as a... |
| `outputrate` | Output Sample Rate | Float | The sample rate of the Laser CHOP, and the sample rate at which it will output to the laser. With the default 48000 samples per second and a 60fps frame rate, the Laser CHOP can output 800 position... |
| `swap` | Swap Output | Toggle | Lets you swap the x and y axis of the output. |
| `xscale` | X Scale | Float | Control the horizontal scale of the output. |
| `yscale` | Y Scale | Float | Control the vertical scale of the output. |
| `rotate` | Rotate | Float | Control the rotation of the output. |
| `camera` | Camera | OBJ | Specify the path to a Camera COMP used to draw a SOP from the cameras view. |
| `updatemethod` | Update Method | Menu | Control how the Laser CHOP pulls data from its source.      In most cases you will want to keep this at the default setting "When All Points Drawn".   There is a specific usage case that requires t... |
| `startpulse` | Frame Start Pulse | Toggle | When enabled, will insert a sample with all colors set to -1 at the beginning of the laser frame. |
| `debugchan` | Debug Channel | Toggle | When enabled, an extra channel with point state will be included:  -1 : Frame Start Pulse  0 : Color  1 : Corner Hold Point  2 : Start Point Hold Time  3 : Pre Blank On  4 : Post Blank On  5 : Blan... |
| `stepsize` | Step Size | Float | The distance each x,y can change while outputing color. |
| `bstepsize` | Blanking Step Size | Float | The distance each x,y can change while not outputing color (blanking). |
| `mincornerhold` | Minimum Corner Hold | Float | The minimum value of the corner hold of a point. The value of the corner hold of a point is calculated linearly in the range from the minimum to maximum corner hold, based on the steepness of the a... |
| `maxcornerhold` | Maximum Corner Hold | Float | The maximum value of the corner hold of a point. See Minimum corner Hold for more details. When the angle at the point is 0 degrees, then the corner hold will be the maximum value. If the maximum v... |
| `cornerholdchop` | Corner Hold Lookup CHOP | CHOP | Reference to a CHOP to use as the custom lookup curve when interpolating from min to max hold. By default (ie. when no CHOP is specified), then it is linearly interpolated. |
| `closedoverlap` | Closed Shape Overlap | CHOP | For closed shapes, the number of points (specified in milliseconds) to overlap the start/end, to utilize color interpolation and get a more uniform shape. |
| `redscale` | Red Scale | Float | Set the intensity of the Red Channel. |
| `greenscale` | Green Scale | Float | Set the intensity of the Green Channel. |
| `bluescale` | Blue Scale | Float | Set the intensity of the Blue Channel. |
| `preblankon` | Pre Blanking On Delay | Float | Set the time in ms the Laser should wait at a position before turning the color output off. |
| `postblankon` | Post Blanking On Delay | Float | Set the time in ms the Laser should wait at a position after turning the color output off. |
| `preblankoff` | Pre Blanking Off Delay | Float | Set the time in ms the Laser should wait at a position before turning the color output on. |
| `postblankoff` | Post Blanking Off Delay | Float | Set the time in ms the Laser should wait at a position after turning the color output on. |
| `starthold` | Start-Point Hold Time | Float | Set the time in ms the Laser should wait at the first point of a new data frame before continuing on. |
| `colordelay` | Color Delay | Float | Set the delay in ms of the color channels in the output. |
| `interpcolors` | Interpolate Colors | CHOP | When enabled, interpolates colors between points. |
| `brightnesscurvechop` | Brightness Curve Lookup CHOP | CHOP | Reference a CHOP to use as a custom look-up for soft-edge blending of closed shapes. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP laserCHOP operator
laserchop_op = op('laserchop1')

# Get/set parameters
freq_value = laserchop_op.par.active.eval()
laserchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
laserchop_op = op('laserchop1')
output_op = op('output1')

laserchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(laserchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **36** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
