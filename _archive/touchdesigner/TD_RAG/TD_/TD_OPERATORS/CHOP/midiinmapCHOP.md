# CHOP midiinmapCHOP

## Overview

See first the MIDI In DAT. The MIDI In Map CHOP reads in specified channels from the MIDI Device Mapper which prepares slider channels starting from s1, s2, etc.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `device` | Device Table | DAT | Path to the MIDI device Table DAT. |
| `id` | Device ID | Str | Specify the id of which device to use. |
| `sliders` | Sliders | Str | The slider controllers to import from the MIDI Mapper. For example to import the first 16 sliders, slider 20 and sliders 32 to 40, type:    s[1-16] s20 s[32-40] |
| `buttons` | Buttons | Str | The buttons to import from the MIDI Mapper. For example to import the first 16 buttons, button 20 and buttons 32 to 40, type:     b[1-16] b20 b[32-40] |
| `bvelocity` | Include Velocity in Buttons | Toggle | Enable velocity on button inputs if available. |
| `squeue` | Queue Slider Events | Toggle |  |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left extend conditions (before range). |
| `right` | Extend Right | Menu | The right extend conditions (after range). |
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
# Access the CHOP midiinmapCHOP operator
midiinmapchop_op = op('midiinmapchop1')

# Get/set parameters
freq_value = midiinmapchop_op.par.active.eval()
midiinmapchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
midiinmapchop_op = op('midiinmapchop1')
output_op = op('output1')

midiinmapchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(midiinmapchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
