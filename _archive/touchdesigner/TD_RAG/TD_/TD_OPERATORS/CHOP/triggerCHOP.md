# CHOP triggerCHOP

## Overview

The Trigger CHOP starts an audio-style attack/decay/sustain/release (ADSR) envelope to all trigger pulses in the input channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `threshold` | Release = Trigger Threshold | Toggle | If on, the trigger and release thresholds are the same value. |
| `threshup` | Trigger Threshold | Float | The trigger threshold (see above). |
| `threshdown` | Release Threshold | Float | The release threshold (see above). |
| `retrigger` | Re-Trigger Delay | Float | The amount of time after a trigger point that a new trigger may occur. |
| `retriggerunit` | Re-Trigger Delay Unit | Menu |  |
| `mintrigger` | Min Trigger Length | Float | The minimum amount of time that the trigger will remain active. |
| `mintriggerunit` | Min Trigger Length Unit | Menu |  |
| `triggeron` | Trigger On | Menu | Determines whether a trigger occurs on an increasing slope or decreasing slope when passing the trigger threshold. A release will occur on the opposite slope. |
| `triggerpulse` | Trigger Pulse | Pulse | Instantly trigger an envelope (regardless of input). |
| `complete` | Complete Envelope | Toggle | If on, a complete envelope is produced for each trigger point. If off, the envelope may be terminated at any time by a release point. |
| `remainder` | Remainder | Menu | See Remainder Options. What to do with remaining samples at end of the interval: |
| `multitriggeradd` | Multi-Triggers Additive | Toggle | When triggering mulitple envelopes, add their values together. |
| `clamppeak` | Clamp at Peak Level | Toggle | Clamp the additive effect of Multi-Triggers Additive at the level set in Peak Level parameter. |
| `delay` | Delay Length | Float | The amount of time to delay the envelope after the trigger point. |
| `delayunit` | Delay Length Unit | Menu |  |
| `attack` | Attack Length | Float | The amount of rise time from zero to the peak level. |
| `attackunit` | Attack Length Unit | Menu |  |
| `ashape` | Attack Shape | Menu | The shape of the attack ramp. |
| `peak` | Peak Level | Float | The peak level it will rise to in the attack phase. |
| `peaklen` | Peak Length | Float | The length of time of the peak is held before going into the decay phase. |
| `peaklenunit` | Peak Length Unit | Menu |  |
| `decay` | Decay Length | Float | The amount of decay time from the peak level to the sustain level. |
| `decayunit` | Decay Length Unit | Menu |  |
| `dshape` | Decay Shape | Menu | The shape of the decay ramp. |
| `sustain` | Sustain Level | Float | The sustain level. This level is held until a release point is reached (the input goes below the threshold). |
| `minsustain` | Min Sustain Length | Float |  |
| `minsustainunit` | Min Sustain Length Unit | Menu |  |
| `release` | Release Length | Float | The amount of release time from the sustain level to zero. |
| `releaseunit` | Release Length Unit | Menu |  |
| `rshape` | Release Shape | Menu | The shape of the release ramp. |
| `channame` | Channel Name | Str | Name of channels output. |
| `specifyrate` | Specify Rate | Toggle | Allows you to specify the sample rate in the Sample Rate parameter below. |
| `rate` | Sample Rate | Float | Sets the sample rate of the output. Only used when Specify Rate is turned on. |
| `enableremaplength` | Enable Remap Length | Toggle | Enables remapping of the total envelope to a specific length. |
| `remaplength` | Remap Length | Toggle | Sets the total envelope remapped length. |
| `remaplengthunit` | Remap Length Unit | Menu |  |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP triggerCHOP operator
triggerchop_op = op('triggerchop1')

# Get/set parameters
freq_value = triggerchop_op.par.active.eval()
triggerchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
triggerchop_op = op('triggerchop1')
output_op = op('output1')

triggerchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(triggerchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **42** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
