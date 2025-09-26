# CHOP touchinCHOP

## Overview

The Touch In CHOP can be used to create a high speed connection between two TouchDesigner processes via CHOPs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `protocol` | Protocol | Menu | Selects which network protocol to use to transfer data. Different protocol's have methods of connecting and using the address parameter. For more information refer to the Network Protocols article. |
| `address` | Address | Str | The computer name or IP address of the server computer. You can use an IP address (e.g. 100.123.45.78) or the computer's network name can be used directly. If you put "localhost", it means the othe... |
| `port` | Network Port | Int | The network port of the server. |
| `active` | Active | Toggle | While on, the CHOP receives information from the pipe or server. While off, no updating occurs. Data sent by a server is lost, but a pipe will store the data until Active is turned on again. If in ... |
| `queuetarget` | Queue Target | Float | The target queue length the CHOP will attempt to maintain. |
| `queuetargetunit` | Queue Target Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `queuevariance` | Queue Variance | Float | The range around the Queue Target that's acceptable. If the queue's length is within the target and variance range, the CHOP will not bother to adjust the queue length. |
| `queuevarianceunit` | Queue Variance Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `maxqueue` | Maximum Queue | Float | The maximum size of the queue when full. Incoming samples will be dropped if the maximum queue is reached. |
| `maxqueueunit` | Max Queue Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `adjusttime` | Queue Adjust Time | Float | Specifies how often to repeat/drop a samples in order to get closer to the queue target range. If the value = 1 and the units = seconds, then it will try to repeat/drop a sample once per second to ... |
| `adjusttimeunit` | Adjust Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `recover` | Recover Outside Range | Toggle | If the queue size goes outside of the target size range for more than the 'adjust time', then if this option is on it will stop delivering new data or throw away a lot of data, until queue size is ... |
| `syncports` | Use Synced Ports | Menu | This parameter lets you send the the data in a single global pipe if required. This can be important if various data streams must be sent in frame sync. For more information, refer to Touch In/Out ... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP touchinCHOP operator
touchinchop_op = op('touchinchop1')

# Get/set parameters
freq_value = touchinchop_op.par.active.eval()
touchinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
touchinchop_op = op('touchinchop1')
output_op = op('output1')

touchinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(touchinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
