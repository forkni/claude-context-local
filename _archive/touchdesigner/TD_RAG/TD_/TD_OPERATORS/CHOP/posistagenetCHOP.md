# CHOP posistagenetCHOP

## Overview

This operator decodes PosiStageNet protocol data into CHOP channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | If turned off, the PosiStageNet CHOP will stop receiving data. |
| `netaddress` | Network Address | Str | Set this parameter to the network address of the PosiStageNet server, device, or software. |
| `port` | Port | Int | By default, TCP Port uses 56565. Firewall settings may need to be adjusted to allow for the PosiStageNet CHOP to communicate properly. |
| `samplerate` | Sample Rate | Int | Specify the rate at which the incoming data is sampled. |
| `pos` | Position | Toggle | Include position channels. |
| `ori` | Orientation | Toggle | Include orientation channels as Euler angles. |
| `speed` | Speed | Toggle | Include speed channels. |
| `accel` | Acceleration | Toggle | Include acceleration channels. |
| `targetpos` | Target Position | Toggle | Include the target position as channels. |
| `resetpulse` | Reset Pulse |  | This button resets the channels. This will clear all the data channels in the CHOP, so any untracked data will be removed |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP posistagenetCHOP operator
posistagenetchop_op = op('posistagenetchop1')

# Get/set parameters
freq_value = posistagenetchop_op.par.active.eval()
posistagenetchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
posistagenetchop_op = op('posistagenetchop1')
output_op = op('output1')

posistagenetchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(posistagenetchop_op)
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
