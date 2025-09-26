# CHOP abletonlinkCHOP

## Overview

The Ableton Link CHOP retrieves timing information from an Ableton Link supported network. For more information see:  http://www.ableton.com/en/link/

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turns the CHOP's output on or off. |
| `enable` | Enable | Toggle | Initializes the connection to the Ableton Link session. |
| `startstopsync` | Start Stop Sync Enable | Toggle | Enables start stop synchronization for the entire Ableton Link session. Start stop synchronization allows for sharing of start or stop signals between subgroups of peers in a Link session. |
| `signature` | Signature | Int | Specifies the time signature. The first number is the number of beats per measure and the second number indicates the type of note that constitutes one beat. See Time Signature - Wikipedia for addi... |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callbacks for each event received. |
| `status` | Status Channels | Toggle | Enables the following status channels  numpeers - number of Ableton Link enabled devices or app found on the network.  linked - if the Ableton Link CHOP is connected to the Link network.  waiting -... |
| `ramp` | Ramp | Toggle | Outputs a 0-1 ramp each bar. |
| `pulse` | Pulse | Toggle | Outputs a pulse each bar. |
| `sine` | Sine | Toggle | Outputs a sine wave each bar. |
| `count` | Count | Toggle | Increases the count each bar. |
| `countramp` | Count+Ramp | Toggle | A ramp that counts up until the bar is reset. |
| `bar` | Bar | Toggle | Output the current bar. |
| `beat` | Beat | Toggle | Output the current beat. |
| `sixteenths` | Sixteenths | Toggle | Output the current sixteenths. |
| `rampbar` | Ramp Bar | Toggle | Outputs a 0-1 ramp each bar. |
| `rampbeat` | Ramp Beat | Toggle | Outputs a 0-1 ramp each beat. |
| `tempo` | Tempo | Toggle | Outputs the current tempo (also known as BPM). |
| `beats` | Beats | Toggle | Outputs the total number of beats. |
| `phase` | Phase | Toggle | Outputs the current phase in the bar. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP abletonlinkCHOP operator
abletonlinkchop_op = op('abletonlinkchop1')

# Get/set parameters
freq_value = abletonlinkchop_op.par.active.eval()
abletonlinkchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
abletonlinkchop_op = op('abletonlinkchop1')
output_op = op('output1')

abletonlinkchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(abletonlinkchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **25** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
