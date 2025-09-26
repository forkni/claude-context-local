# CHOP touchoutCHOP

## Overview

The Touch Out CHOP can be used to create high speed connection between two TouchDesigner processes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `protocol` | Protocol | Menu | Selects which network protocol to use to transfer data. Different protocol's have methods of connecting and using the address parameter. For more information refer to the Network Protocols article. |
| `address` | Address | Str | The address to use, not all protocls require an address to be specified on the sending side. |
| `port` | Network Port | Int | The network port to use. |
| `active` | Active | Toggle | When Off, data is not sent. |
| `maxsize` | Max Queue Size | Float | Limits the number of events waiting to be sent. This prevents overflows if the connection is too slow. |
| `maxsizeunit` | Max Queue Size Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for the Max Queue Size parameter. |
| `cookalways` | Cook Every Frame | Toggle | Specifies that this CHOP should be cooked every frame regardless of CHOPs below it are cooking. |
| `resendnames` | Resend Names | Pulse | Resends all the channel names. Generally you don't need to use this parameter, but it is provided just in-case. |
| `syncports` | Use Synced Ports | Menu | This parameter lets you send the the data in a single global pipe if required. This can be important if various data streams must be sent in frame sync. For more information, refer to Touch In/Out ... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP touchoutCHOP operator
touchoutchop_op = op('touchoutchop1')

# Get/set parameters
freq_value = touchoutchop_op.par.active.eval()
touchoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
touchoutchop_op = op('touchoutchop1')
output_op = op('output1')

touchoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(touchoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
