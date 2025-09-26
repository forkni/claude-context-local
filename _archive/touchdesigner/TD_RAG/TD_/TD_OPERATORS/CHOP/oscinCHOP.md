# CHOP oscinCHOP

## Overview

The OSC In CHOP is used to accept Open Sound Control Messages.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the CHOP receives information sent to the network port. While Off, no updating occurs. Data sent to the port is lost. |
| `protocol` | Protocol | Menu | The network protocol to use. Refer to the Network Protocols article for more information. |
| `netaddress` | Network Address | Str | When using Multicast, this is the address that OSC In will listen for packets on. |
| `port` | Network Port | Int | The port which OSC-In will accept packets on. |
| `localaddress` | Local Address | StrMenu | Specify an IP address to receive on, useful when the system has mulitple NICs (Network Interface Card) and you want to select which one to use. |
| `oscaddressscope` | OSC Address Scope | Str | To reduce which channels are generated, you can use channel name patterns to include or exclude channels. For example, ^*accel* will exclude accelerometer channels coming in from an iPhone or iOS a... |
| `useglobalrate` | Use Global Rate | Toggle | When on, the CHOP will sample at the global sample rate specified by TouchDesigner. |
| `samplerate` | Default Sample Rate | Int | When Use Global Rate is off, this parameter is used to determine the sample rate of this CHOP. |
| `queued` | Queued | Toggle | Turn this on to enable queuing to help avoid lost messages. Use the parameters below to setup the queue behavior. |
| `queuevariance` | Queue Variance | Float | The range around the Queue Target that's acceptable. If the queue's length is within the target and variance range, the CHOP will not bother to adjust the queue length. |
| `queuevarianceunit` | Queue Variance Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `maxqueue` | Maximum Queue |  | The maximum size of the queue when full. Incoming samples will be dropped if the maximum queue is reached. |
| `maxqueueunit` | Max Queue Unit |  | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `adjusttime` | Queue Adjust Time | Float | Specifies how often to repeat/drop a samples in order to get closer to the queue target range. If the value = 1 and the units = seconds, then it will try to repeat/drop a sample once per second to ... |
| `adjusttimeunit` | Adjust Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `stripsegments` | Strip Prefix Segments | Int | Strip a number of prefixes from the incoming address. Example:  An address of /a/b/c/d/e  with 3 segments removed would show d/e (or d_e as a final channel name). |
| `resetchannels` | Reset Channels | Toggle | Deletes all channels when set to On, new channels will not be added until Reset Channels is turned Off. |
| `resetchannelspulse` | Reset Channels Pulse | Pulse | Instantly resets all channels to 0. |
| `resetvalues` | Reset Values | Toggle | Resets all channel values to 0 when On, channel values will not be updated until Reset Values is turned Off. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP oscinCHOP operator
oscinchop_op = op('oscinchop1')

# Get/set parameters
freq_value = oscinchop_op.par.active.eval()
oscinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oscinchop_op = op('oscinchop1')
output_op = op('output1')

oscinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oscinchop_op)
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
