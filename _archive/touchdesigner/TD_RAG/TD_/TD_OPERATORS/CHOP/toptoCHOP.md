# CHOP toptoCHOP

## Overview

The TOP to CHOP converts pixels in a TOP image to CHOP channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `top` | TOP | TOP | Specify the TOP operator whose image will be sampled. |
| `downloadtype` | Download Type | Menu | Gives the option for a delayed data download from the GPU, which is much faster and does not stall the render. |
| `r` | Red | Str | The prefix for channels created from the red pixels of the source image. If multiple red channels are created, they will have a numeric suffix that matches the vertical scanline number of the image... |
| `g` | Green | Str | The prefix for channels created from the green pixels of the source image. If multiple green channels are created, they will have a numeric suffix that matches the scanline number of the image e.g.... |
| `b` | Blue | Str | The prefix for channels created from the blue pixels of the source image. If multiple blue channels are created, they will have a numeric suffix that matches the scanline number of the image e.g. b... |
| `a` | Alpha | Str | The prefix for channels created from the alpha pixels of the source image. If multiple alpha channels are created, they will have a numeric suffix that matches the scanline number of the image e.g.... |
| `singleset` | Output as Single Channel Set | Toggle | Controls whether a channel is created for each scanline, or whether all scanlines are appended into a single channel set. A channel set refers to one CHOP channel per color channel of the source im... |
| `excludenans` | Exclude NaNs | Toggle | When enabled, pixels that have a NaN value in any of their channels will be skipped and not added to the CHOP channel. |
| `activechannel` | Active Channel | Menu | When enabled, only pixels that have a non-zero value in the selected active channel will be added to the CHOP channel. |
| `rgbaunit` | RGBA Units | Menu | Scales the output to lie in the range 0-1, 0-255 or 0-65535. |
| `crop` | Crop | Menu | Specifies what to extract from the image. |
| `uvunits` | UV Units | Menu | Specifies the units for the following 4 parameters. The parameters can use the local variables $NR and $NC for the number of rows and columns. |
| `ustart` | U Start | Float | Starting point for sampling in U. Values outside the range of the image are determined by the image's extend conditions, in the extend page. |
| `uend` | U End | Float | Ending point for sampling in U. |
| `vstart` | V Start | Float | Starting point for sampling in V. |
| `vend` | V End | Float | Ending point for sampling in V. |
| `interp` | Interpolate | Menu | Determines the interpolation method when UV sampling with an input CHOP. |
| `imageleft` | Image Left | Menu | The image extend conditions when sampling the image with U less than 0. |
| `imageright` | Image Right | Menu | The image extend conditions for U greater than 1. |
| `imagebottom` | Image Bottom | Menu | The image extend conditions for V less than 0. |
| `imagetop` | Image Top | Menu | The image extend conditions for V greater than 1.      The extend conditions are: |
| `defcolor` | Default Color | RGBA | The color to use when outside the bounds of the image, and the Default Color extend condition is set. |
| `start` | Start | Float | The start position of the channel, expressed in units set by the units menu to the right (samples, frames or seconds). The channel length is determined by the number of pixels in each scanline that... |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left extend conditions (before/after range). |
| `right` | Extend Right | Menu | The right extend conditions (before/after range). |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP toptoCHOP operator
toptochop_op = op('toptochop1')

# Get/set parameters
freq_value = toptochop_op.par.active.eval()
toptochop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
toptochop_op = op('toptochop1')
output_op = op('output1')

toptochop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(toptochop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **34** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
