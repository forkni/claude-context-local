# CHOP oculusaudioCHOP

## Overview

The Oculus Audio CHOP uses the Oculus Audio SDK to take a mono sound channel and create a spatialized stereo pair or channels for that sound.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When enabled, will actively spatialize the audio input. |
| `headobject` | Head Object COMP | Object | A COMP that represents the listener's (ie. head) transform. Must be a COMP that contains transform data, such as a Geometry or Camera COMP. |
| `sourceobject` | Source Object COMP | Object | A COMP that represents the audio source's transform. Must be a COMP that contains transform data, such as a Geometry or Camera COMP. |
| `minrange` | Minimum Range | Float | The minimum attenuation range of the audio source (in meters). |
| `maxrange` | Maximum Range | Float | The maximum attenuation range of the audio source (in meters) |
| `diameter` | Diameter | Float | The virtual diameter of the audio source. By default the diameter is 0 which means the audio source is just a point in space. |
| `bandhint` | Band Hint | Menu | If the audio source content is known, this parameter can be set to improve overall sound quality. |
| `reflectrevert` | Reflections and Reverb | Toggle | When enabled, audio reflection and reverb will be enabled. |
| `attenuation` | Attenuation | Menu | Select attentuation calculation between the audio source and listener (head). |
| `attenuationscale` | Attenuation Scale | Float | Set the fixed attenuation value when in Fixed Attenuation mode. |
| `boxroommode` | Box Room Mode | Toggle | Enables box room calculations for reverberation. |
| `roomsize` | Room Size | XYZ | Sets the size of the box room. |
| `roomleftrelfect` | Room Left Reflect | Float | Reflection level for the left of the box (ie. what percentage of the audio is reflected back). |
| `roomrightrelfect` | Room Right Reflect | Float | Reflection level for the right of the box (ie. what percentage of the audio is reflected back). |
| `roombottomrelfect` | Room Bottom Reflect | Float | Reflection level for the bottom of the box (ie. what percentage of the audio is reflected back). |
| `roomtoprelfect` | Room Top Reflect | Float | Reflection level for the top of the box (ie. what percentage of the audio is reflected back). |
| `roomfrontrelfect` | Room Front Reflect | Float | Reflection level for the front of the box (ie. what percentage of the audio is reflected back). |
| `roombackrelfect` | Room Back Reflect | Float | Reflection level for the back of the box (ie. what percentage of the audio is reflected back). |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP oculusaudioCHOP operator
oculusaudiochop_op = op('oculusaudiochop1')

# Get/set parameters
freq_value = oculusaudiochop_op.par.active.eval()
oculusaudiochop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oculusaudiochop_op = op('oculusaudiochop1')
output_op = op('output1')

oculusaudiochop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oculusaudiochop_op)
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
