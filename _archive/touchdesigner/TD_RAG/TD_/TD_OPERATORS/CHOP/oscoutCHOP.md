# CHOP oscoutCHOP

## Overview

The OSC Out CHOP sends all input channels to a specified network address and port.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While On, the CHOP sends information to the network port. When Off, data is not sent. |
| `protocol` | Protocol | Menu | Selects the network protocol to use. Refer to the Network Protocols article for more information. |
| `netaddress` | Network Address | Str | The network address of the server computer. This address is a standard WWW address, such as 'foo' or 'foo.bar.com'. You can put an IP address (e.g. 100.123.45.78). If you put "localhost", it means ... |
| `port` | Network Port | Int | The port which OSC Out will send packets to. |
| `localaddress` | Local Address | StrMenu | Specify an IP address to send from, useful when the system has mulitple NICs (Network Interface Card) and you want to select which one to use. |
| `maxsize` | Max Queue Size | Float | Specifies the maximum number of messages OSC Out will try to send at a single time. |
| `maxsizeunit` | Max Queue Size Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds |
| `cookalways` | Cook Every Frame | Toggle | Specifies that this CHOP should be cooked every frame regardless of CHOPs below it are cooking. |
| `numericformat` | Numeric Format | Menu | Choose the data format to send data between 32-bit integer, 32-bit float, or 64-bit double. |
| `format` | Data Format | Menu | Specify how to format the outgoing messages. |
| `maxbytes` | Max Message Bytes | Int | Limits the size of the outgoing message packets and splits up the message accordingly. |
| `sendevents` | Send Events Every Cook | Toggle | When on, OSC Out will send all channels every cook regardless if the value has changed. When off, OSC Out only sends data which has changed. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP oscoutCHOP operator
oscoutchop_op = op('oscoutchop1')

# Get/set parameters
freq_value = oscoutchop_op.par.active.eval()
oscoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oscoutchop_op = op('oscoutchop1')
output_op = op('output1')

oscoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oscoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **18** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
