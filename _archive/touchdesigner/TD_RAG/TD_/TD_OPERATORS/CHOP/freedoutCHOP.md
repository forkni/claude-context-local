# CHOP freedoutCHOP

## Overview

The FreeD Out CHOP sends camera tracking information, including position and orientation, to an external device or program over the network using the popular device-indepedent FreeD protocol. This can be used to emulate a physical camera or to send data to another program/device that can process FreeD tracking data. Data packets are sent out once p

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turn this parameter off to stop sending out data packets. |
| `protocol` | Protocol | Menu | Selects the network protocol to use. Refer to the Network Protocols article for more information. |
| `netaddress` | Network Address | Str | The network address of the computer to send the Stype data to. The address can be a domain name, an IP address (e.g. 100.123.45.78), or "localhost" to target the packets at another program on the s... |
| `port` | Network Port | Int | The port to send the data packets to. |
| `localaddress` | Local Address | StrMenu | Specify an IP address to send from. This is useful when the system has multiple NICs (Network Interface Card) and you want to select which one to use. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP freedoutCHOP operator
freedoutchop_op = op('freedoutchop1')

# Get/set parameters
freq_value = freedoutchop_op.par.active.eval()
freedoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
freedoutchop_op = op('freedoutchop1')
output_op = op('output1')

freedoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(freedoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
