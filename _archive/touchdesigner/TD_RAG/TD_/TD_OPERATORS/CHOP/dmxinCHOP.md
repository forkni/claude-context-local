# CHOP dmxinCHOP

## Overview

The DMX In CHOP receives channels from DMX, Art-Net  or sACN devices.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Connects to the device while On. |
| `interface` | Interface | Menu | Select the type of interface to connect to the device with. |
| `kinetversion` | KiNET Version | Menu | Set the version of the KiNET protocol to use. |
| `device` | Device | StrMenu | Select a DMX device from the menu. |
| `serialport` | Serial Port | StrMenu | When the Interface parameter is set Generic Serial this parameter lets you select which Serial (COM) port to use. |
| `format` | Format | Menu | Select between receiving Packet Per Sample (Timesliced), Packet Per Channel (Latest) or Packet Per Channel (All). When selecting Packet Per Channel (Latest), any messages outside the last cook are ... |
| `net` | Art-Net Net (0-127) | Int | When the Interface parameter is set to Art-Net, this sets the net address. A net is a groups of 16 consecutive subnets or 256 consecutive universes. The range for this parameter is 0-127. This is n... |
| `subnet` | Art-Net Subnet (0-15) | Int | When the Interface parameter is set to Art-Net, this sets the subnet address. A subnet is a group of 16 consecutive universes. The range for this parameter is 0-15. This is not a network subnet mask. |
| `universe` | Art-Net Universe (0-15) | Int | When the Interface parameter is set to Art-Net, this sets the universe address. A single DMX512 frame of 512 channels is referred to as a universe. The range for this parameter is 0-15. |
| `filterdat` | Filter Table | DAT | Available when using Packet Per Channel Format for Art-Net or sACN. Use the docked Table DAT to specify which net, subnet, universe channels are being received from.      Note: For sACN the first a... |
| `netname` | Net Name | Str | Specify the channel prefix for the net part of the address. |
| `subnetname` | Subnet Name | Str | Specify the channel prefix for the subnet part of the address. |
| `universename` | Universe Name | Str | Specify the channel prefix for the universe part of the address. |
| `kinetportname` | KiNET Port Name | Str | Specify the channel prefix for the KiNET port part of the address. |
| `startcodes` | Start Codes | Str | A list of accepted start codes when using sACN. If the DMX In CHOP receives an sACN packet with a start code not in the list then it will discard it. |
| `multicast` | Multicast | Toggle | Enable multicast for sACN. Multicast automatically builds the IP based on Net, Subnet, and Universe of the device. This allows for the DMX In CHOP to automatically receive from a sender without kno... |
| `queuesize` | Queue Size | Int | When using interface Art-Net or sACN, this will set the size of the incoming packets queue.  This can be used to smooth data, though latency will be higher.  In the case of Packet Per Channel (All)... |
| `rate` | Rate | Int | Resample the incoming data to this rate. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP dmxinCHOP operator
dmxinchop_op = op('dmxinchop1')

# Get/set parameters
freq_value = dmxinchop_op.par.active.eval()
dmxinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
dmxinchop_op = op('dmxinchop1')
output_op = op('output1')

dmxinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(dmxinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
