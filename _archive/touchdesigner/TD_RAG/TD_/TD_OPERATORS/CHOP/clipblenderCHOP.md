# CHOP clipblenderCHOP

## Overview

The Clip Blender CHOP can be used as an animation system that blends between different animation clips, preserving rotation, changing target positions etc.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `default` | Default Clip CHOP | CHOP | Operator path to a valid Clip CHOP. |
| `datlist` | DAT List | DAT | Operator path to a valid Table DAT. |
| `target` | Target | XYZ | This parameter works in conjunction with the root transform channels as defined on the Channels page of the clpblender CHOP as well as the Clip CHOP parameter called Position Type. When Position Ty... |
| `playspeed` | Play Speed | Float | Provides a scale value to slow down or speed up the playback of the animation sequence. |
| `stepforward` | Step Forward | Toggle | Unknown |
| `stepbackward` | Step Backward | Toggle | Unknown |
| `aend` | A End Script | Str | Broken |
| `delay` | Delay Samples | Int | Delays the output of animation data by the specified number of samples. |
| `reset` | Reset | Toggle | When On, resets the clipblender and holds it ready to play the clip defined by the Default Clip CHOP parameter. |
| `resetpulse` | Reset Pulse | Pulse | Instantly reset the cliblender and start playing the clip defined by the Default Clip CHOP parameter. |
| `timeremaining` | Output Time Remaining | Str | A channel of the name defined in this parameter will return the time remaining in the current clip. |
| `timechannel` | Time Channel | Str | A channel of the name defined in this parameter will return the time elapsed in the current clip. |
| `xtrans` | X Root Trans | StrMenu | The translate X channel of the animation hierarchy that defines the Clipblender Motion Root. |
| `ytrans` | Y Root Trans | StrMenu | The translate Y channel of the animation hierarchy that defines the Clipblender Motion Root. |
| `ztrans` | Z Root Trans | StrMenu | The translate Z channel of the animation hierarchy that defines the Clipblender Motion Root. |
| `xrot` | X Root Rot | StrMenu | The rotate X channel of the animation hierarchy that defines the Clipblender Motion Root. |
| `yrot` | Y Root Rot | StrMenu | The rotate Y channel of the animation hierarchy that defines the Clipblender Motion Root. |
| `zrot` | Z Root Rot | StrMenu | The rotate Z channel of the animation hierarchy that defines the Clipblender Motion Root. |
| `qenable` | Queue Enable | Str | Specifies the name of the queue enable channel that may be added to all animation clips that will be loaded into this clipblender. A "Queue Enable" channel may be added to the animation clip to def... |
| `qtrigger` | Queue Trigger | Toggle | Unknown |
| `prerotate` | Pre-Rotate Adds | Toggle | Unknown |
| `doxform` | Transform Next Clip | Toggle |  |
| `t` | Translate | XYZ |  |
| `r` | Rotate | XYZ |  |
| `printstate` | Print State | Toggle |  |
| `logjumps` | Log Jumps | Toggle |  |
| `jumpmin` | Jump Min | XYZ |  |
| `jumpmax` | Jump Max | XYZ |  |
| `jumpxy` | Jump Area XY | XYZ |  |
| `fixjump` | Fix Jump | Toggle |  |
| `logpulse` | Log | Pulse |  |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP clipblenderCHOP operator
clipblenderchop_op = op('clipblenderchop1')

# Get/set parameters
freq_value = clipblenderchop_op.par.active.eval()
clipblenderchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
clipblenderchop_op = op('clipblenderchop1')
output_op = op('output1')

clipblenderchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(clipblenderchop_op)
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
