# CHOP pipeinCHOP

## Overview

The Pipe In CHOP allows users to input from custom devices into CHOPs. It is implemented as a TCP/IP network connection.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `mode` | Connection Mode | Menu | Set operation as server or client. |
| `address` | Server Address | Str | The network address of the server computer. This address is a standard WWW address, such as 'foo' or 'foo.bar.com'. You can use an IP address (e.g. 100.123.45.78) or the computer's network name can... |
| `port` | Server Port | Int | The network port of the server. |
| `active` | Active | Toggle | While On, the CHOP receives information from the pipe or server. While Off, no updating occurs. Data sent by a server is lost, but a pipe will store the data until Active is turned on again. If in ... |
| `queued` | Queued | Toggle | When checked on, the network queuing is enabled. See the following parameters. |
| `mintarget` | Minimum Target | Float | The lower end of the queue target range. The Pipe In CHOP will try to maintain a queue length greater than or equal to this value. |
| `mintargetunit` | Min Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `maxtarget` | Maximum Target | Float | The upper end of the queue target range. The Pipe In CHOP will try to maintain a queue length less than or equal to this value. |
| `maxtargetunit` | Max Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `maxqueue` | Maximum Queue | Float | The maximum size of the queue when full. Incoming samples will be dropped if the maximum queue is reached. This also affects the maximum number of script commands that can be queued up before they ... |
| `maxqueueunit` | Max Queue Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `adjusttime` | Queue Adjust Time | Float | Specifies how often to repeat/drop a samples in order to get closer to the queue target range. If the value = 1 and the units = seconds, then it will try to repeat/drop a sample once per second to ... |
| `adjusttimeunit` | Adjust Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `reset` | Reset Channels | Pulse | Discards and clears all channels and incoming data. |
| `allowscripts` | Allow Incoming Scripts | Toggle | Incoming script commands will be ignored unless this parameter is turned On. Turning it Off is more secure. |
| `echo` | Echo Messages to Console | Menu | Print all incoming commands (not channel data) to the Console which can be opened from the Dialogs menu. A good way to test a connection is to put "echo X" commands in the incoming stream. |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callbacks for each event received. See pipeinCHOP_Class for usage. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP pipeinCHOP operator
pipeinchop_op = op('pipeinchop1')

# Get/set parameters
freq_value = pipeinchop_op.par.active.eval()
pipeinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pipeinchop_op = op('pipeinchop1')
output_op = op('output1')

pipeinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pipeinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
