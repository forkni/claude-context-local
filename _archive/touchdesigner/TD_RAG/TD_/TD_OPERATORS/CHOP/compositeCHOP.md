# CHOP compositeCHOP

## Overview

The Composite CHOP layers (blends) the channels of one CHOP on the channels of another CHOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `base` | Base Hold | Float | Determines how much of the base to blend into the output at points where the layer has an effect. |
| `match` | Match by | Menu | Matches channels in the base input with ones in the layer input by either index or name. |
| `quatrot` | Quaternion Blend | Toggle | Allows rotations with the quaternion attribute set to use spherical interpolation to produce smooth rotation blending (set in the Attribute CHOP). |
| `shortrot` | Shortest Path Rotation Blending | Toggle | It better-handles the blending from one set of angles to another, taking into account 0 degrees is 360 degrees. |
| `rotscope` | Rotation Scope | Str | Pattern (like *rx*ry *rz) that identifies which channels are rotations that should be handled specially as per the above option. |
| `cyclelen` | Cycle Length | Float | Blend 0 degrees to this angle, generally 360. |
| `effect` | Effect | Float | Note: If the third input is supplied, the Effect page will be overridden by the third input's first channel, which should contain the effect values over the range of the layer. |
| `relative` | Unit Values | Menu | Sets the meaning of the next four parameters - either Absolute values, Relative to the Start/End of the channel, or Relative to the Current Frame. The layer and base are never shifted. |
| `start` | Start | Float | The beginning of the composite interval. Effect is zero at the start. |
| `startunit` | Start Unit | Menu |  |
| `peak` | Peak | Float | Where the composite operation reaches maximum effect. This value is held until the release point. |
| `peakunit` | Peak Unit | Menu |  |
| `release` | Release | Float | The point at which the effect begins to fall back towards zero. |
| `releaseunit` | Release Unit | Menu |  |
| `end` | End | Float | The end of the composite operation's effect. The effect reduces to zero again. |
| `endunit` | End Unit | Menu |  |
| `risefunc` | Rise Shape | Menu | How to interpolate from one CHOP to another. It is the shape of the segment between the Start and Peak indices. |
| `fallfunc` | Fall Shape | Menu | How to interpolate from one CHOP to another. It is the shape of the segment between the Release and End. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP compositeCHOP operator
compositechop_op = op('compositechop1')

# Get/set parameters
freq_value = compositechop_op.par.active.eval()
compositechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
compositechop_op = op('compositechop1')
output_op = op('output1')

compositechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(compositechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
