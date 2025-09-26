# CHOP pangolinCHOP

## Overview

The Pangolin CHOP interfaces with Pangolin's Beyond.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When disabled, the CHOP will no longer send to Beyond. The corresponding image in Beyond will also be cleared. |
| `source` | Source | Menu | Select the source operator. |
| `sop` | SOP | SOP | Path to the SOP. |
| `chop` | CHOP | CHOP | Path to the CHOP. The input CHOP must have x, y channels for the point positions. In addition, it also supports z, r, g, b, and id channels. The id channel is used for grouping points together as a... |
| `zone` | Zone | Int | The index of the zone to send to in Beyond. |
| `ratemode` | Rate Mode | Menu | Select the mode for calculating the rate of the image in Beyond. Note: this is not the rate of the CHOP. |
| `percent` | Percent | Int | Specify the sample rate as a percent of the projector default sample rate. |
| `rate` | Sample Rate | Int | Specify the sample rate of the image in Beyond |
| `repeat` | Vertex Repeat | Int | How often to repeat each point in the image (not including blanked points). |
| `vector` | Vector Frame | Toggle | When enabled, the image will be sent to Beyond as a vector frame. A vector frame will have extra computation done in Beyond, such as the addition of blanking points. When disabled, the image will b... |
| `resend` | Resend Image | Pulse | Resend the image to Beyond. |
| `enableout` | Enable Laser Output | Pulse | Enables laser output in Beyond. Has the same effect as hitting the "Enable Laser Output" button in Beyond. |
| `disableout` | Disable Laser Output | Pulse | Disables laser output in Beyond. Has the same effect as hitting the "Disable Laser Output" button in Beyond. |
| `blackout` | Blackout | Pulse | Sends a blackout command to Beyond. Has the effect as hitting the "Blackout" button in Beyond. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP pangolinCHOP operator
pangolinchop_op = op('pangolinchop1')

# Get/set parameters
freq_value = pangolinchop_op.par.active.eval()
pangolinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pangolinchop_op = op('pangolinchop1')
output_op = op('output1')

pangolinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pangolinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
