# CHOP dmxoutCHOP

## Overview

The DMX Out CHOP sends channels to DMX, Art-Net, or sACN devices.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Connects to the device while On. |
| `interface` | Interface | Menu | Select the type of interface to connect to the device with. |
| `kinetversion` | KiNET Version | Menu | Set the version of the KiNET protocol to use. |
| `format` | Format | Menu | Select between sending Packet Per Sample or Packet Per Channel. |
| `routingtable` | Routing Table | DAT | Available when using Packet Per Channel Format for Art-Net or sACN. Use the docked Table DAT to route channels to the appropriate universes. Addresses can be specified by adding rows for each chann... |
| `sendartsync` | Send ArtSync | Toggle | When enabled will send out ArtSync packets. ArtSync packets are used to synchronize multiple universes together. |
| `device` | Device | StrMenu | Select a DMX device from the menu. |
| `serialport` | Serial Port | StrMenu | When the Interface parameter is set to Generic Serial this parameter lets you select which Serial (COM) port to use. |
| `rate` | Rate | Int | How often data is sent to the device (per second).                  WARNING: DMX512 devices have a maximum refresh rate of 44Hz. It is recommended that Rate <= 44 for reliable performance. |
| `net` | Net (0-127) | Int | When the Interface parameter is set to Art-Net, this sets the net address. A net is a groups of 16 consecutive subnets or 256 consecutive universes. The range for this parameter is 0-127. This is n... |
| `subnet` | Subnet (0-15) | Int | When the Interface parameter is set to Art-Net, this sets the subnet address. A subnet is a group of 16 consecutive universes. The range for this parameter is 0-15. This is not a network subnet mask. |
| `universe` | Universe | Int | When the Interface parameter is set to Art-Net, this sets the universe address. A single DMX512 frame of 512 channels is referred to as a universe. The range for this parameter is 0-15. |
| `cid` | CID | Str | The unique ID of the sender. |
| `source` | Source | Str | User assigned name of source (for informative purposes). |
| `priority` | Priority | Int | The priority of the data being sent, if there are multiple sources. |
| `customkinetport` | Custom KiNET Port | Toggle | When enabled, can specify a custom port for the KiNET v2 interface. When disabled, the port will be the broadcast port: 255. |
| `kinetport` | KiNET Port | Int | Specifies the port for KiNET v2 interface. |
| `multicast` | Multicast | Toggle | Enable multicast for sACN. Multicast automatically builds the IP based on Net, Subnet, and Universe of the device. This allows for sending to multiple devices at once by specifying multiple universes. |
| `netaddress` | Network Address | Str | Specify the IP address to use when Interface is set to Art-Net. This address corresponds to the receiving device address.  When the address is set to its default 255.255.255.255, the messages are i... |
| `localaddress` | Local Address | StrMenu | When the sending machine is equipped with multiple network adapters, this parameter can be used to choose which adapter to send the data from by specifying its IP address here. |
| `localport` | Local Port | Int | In rare cases it can be necessary to supply a custom port from which the data should be sent. The default of -1 means the O/S assigned port is being used. |
| `customport` | Use Custom Port | Toggle | Enable the Network Port parameter to specify the port of the receiving hardware. |
| `netport` | Network Port | Int | Let's you specify the port of the receiving hardware. By default and the spec of ArtNet this is set to 6454 and should only be changed in rare cases. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP dmxoutCHOP operator
dmxoutchop_op = op('dmxoutchop1')

# Get/set parameters
freq_value = dmxoutchop_op.par.active.eval()
dmxoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
dmxoutchop_op = op('dmxoutchop1')
output_op = op('output1')

dmxoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(dmxoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **29** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
