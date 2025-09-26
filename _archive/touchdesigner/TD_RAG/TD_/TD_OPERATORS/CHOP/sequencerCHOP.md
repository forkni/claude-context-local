# CHOP sequencerCHOP

## Overview

NOTE: The Timer CHOP replaces the Sequencer CHOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `datlist` | DAT List | DAT | The table of CHOPs to sequence, the table contains the paths to the CHOPs to be sequenced. |
| `blendscope` | Blend Scope | Str | Specifies which channels should blend between transitions, otherwise they add or jump. |
| `addscope` | Add Scope | Str | Specifies which channels should add during transitions, otherwise they blend or jump. |
| `queue` | Queue | Str | Specifies the channel that controls when to queue (pause). |
| `trigger` | Trigger | Pulse | Begin transitioning immediately, instead of waiting until the end of the current CHOP channels. |
| `reset` | Reset | Toggle | While On, resets the sequence to the default CHOP. |
| `resetpulse` | Reset Pulse | Pulse | Instantly resets the sequence. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP sequencerCHOP operator
sequencerchop_op = op('sequencerchop1')

# Get/set parameters
freq_value = sequencerchop_op.par.active.eval()
sequencerchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sequencerchop_op = op('sequencerchop1')
output_op = op('output1')

sequencerchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sequencerchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
