# CHOP freedCHOP

## Overview

The FreeD CHOP reads incoming camera tracking data sent over a network using the FreeD protocol and outputs CHOP channels that can be used to control a virtual 3D camera.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While On, the CHOP receives FreeD information sent to the network port. While Off, no updating occurs. |
| `protocol` | Protocol | Menu | The network protocol to use. Refer to the Network Protocols article for more information. |
| `netaddress` | Network Address | Str | When using Multicast, this is the address that FreeD will listen for packets on. |
| `port` | Network Port | Int | The port which FreeD will accept packets on. |
| `localaddress` | Local Address | StrMenu | Specify an IP address to receive on, useful when the system has mulitple NICs (Network Interface Card) and you want to select which one to use. |
| `cameraid` | Camera ID | Str | This parameter can be used to select a specific camera when there are multiple streams of incoming data. To select the camera, the parameter value should match the incoming value in the camera_id c... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP freedCHOP operator
freedchop_op = op('freedchop1')

# Get/set parameters
freq_value = freedchop_op.par.active.eval()
freedchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
freedchop_op = op('freedchop1')
output_op = op('output1')

freedchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(freedchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
