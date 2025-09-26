# CHOP beatCHOP

## Overview

The Beat CHOP generates a variety of ramps, pulses and counters that are timed to the beats per minute and the sync produced by the Beat Dialog or the beat Command.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `op` | Reference Operator | OP | This node is used to specify the time settings referenced by the Beat CHOP. The time is defined by the Time COMP found at timepath("reference_node") |
| `reftimeslice` | Use Reference Time Slice | Toggle | Turn on this checkbox to use the Time Slicing used by the Reference Node. |
| `playmode` | Play Mode | Menu | Specifies the method used to playback the output. |
| `period` | Period | Float | Number of beats it takes to generate one cycle of ramp. Use the drop down menu to select from some commonly used Period lengths. |
| `multiples` | Multiples | Int | The number of channels to create. |
| `shiftoffset` | Shift Offset | Float | Delays all channels by this amount. 0 = no change, .5 means 50% of one period later. |
| `shiftstep` | Shift Step | Float | When set to 1, and Multiples is 5, each ramp channel is 1/5 cycle later than the previous channel. When set to .1, the delay is 1/50 cycle. This is a way to stagger the channels. |
| `randoffset` | Random Offset | Float | The amount that each ramp is randomly time-shifted relative to a perfect ramp. |
| `randseed` | Random Seed | Float | Changing this generates a different set of random offsets. |
| `resetcondition` | Reset Condition | Menu | This menu determines how the Reset input triggers a reset of the channel(s). |
| `resetbarvalue` | Reset Bar Value | Float | Specifies which Bar the Beat CHOP will jump to when the Reset Condition is met. Beat values are derived from the fractional part of this value. |
| `resetwait` | Wait after Reset | Toggle | When using the While On Reset Condition, Wait After Reset will hold the channels at zero until the next bar is started, after which the output will continue. When Wait After Reset is off, the chann... |
| `reset` | Reset | Toggle | This button resets the ramps to zero when On. The ramp is also zero when the Beat CHOP's input is above 0. |
| `resetpulse` | Reset Pulse | Pulse | Instantly resets the ramps to zero. |
| `updateglobal` | Update Global | Toggle | Any Beat CHOP can be made the "global beat source" by turning on Update Global. A reference Beat CHOP is created at /local/master_beat (if it doesn't already exist) and all Beat CHOPs can synchroni... |
| `ramp` | Ramp | Toggle | Outputs a 0-1 ramp each period. |
| `pulse` | Pulse | Toggle | Outputs a pulse each period. |
| `sine` | Sine | Toggle | Outputs a sine wave each period. |
| `count` | Count | Toggle | Increases the count each period. |
| `countramp` | Count+Ramp | Toggle | A ramp that counts up until the bar is reset. |
| `bar` | Bar | Toggle | Output the current bar. |
| `beat` | Beat | Toggle | Output the current beat. |
| `sixteenths` | Sixteenths | Toggle | Output the current sixteenths. |
| `rampbar` | Ramp Bar | Toggle | Outputs a 0-1 ramp each bar. |
| `rampbeat` | Ramp Beat | Toggle | Outputs a 0-1 ramp each beat. |
| `bpm` | BPM | Toggle | Outputs the current BPM. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP beatCHOP operator
beatchop_op = op('beatchop1')

# Get/set parameters
freq_value = beatchop_op.par.active.eval()
beatchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
beatchop_op = op('beatchop1')
output_op = op('output1')

beatchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(beatchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **32** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
