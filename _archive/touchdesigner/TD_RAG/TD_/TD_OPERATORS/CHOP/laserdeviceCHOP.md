# CHOP laserdeviceCHOP

## Overview

The Laser Device CHOP can send laser points to supported laser devices: EtherDream, Helios, and ShowNET. The devices can be connected to a laser using an ILDA cable, except in the case of ShowNET when an onboard DAC is used. Applications of the Laser Device CHOP include displaying computer-generated shape animations or other special effects of a li

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When enabled, the CHOP will connect to the specified device and send points to it. |
| `type` | Type | Menu | Specify the type of laser device. |
| `device` | Device | StrMenu | Menu to select the named devices in the case of Helios and ShowNET. |
| `scan` | Scan | Pulse | Scan for Helios devices. Note: there should not be any active Helios device connections when this scan is performed, otherwise they will be closed by the scanning process. |
| `netaddress` | Network Address | Str | The network address of the EtherDream device to send the packets to. EtherDream IP can be found be polling devices on the network using the EtherDream DAT. |
| `port` | Network Port | Int | The port to send the EtherDream packets to. |
| `localaddress` | Local Address | StrMenu | Specify an IP address to send from. This is useful when the system has multiple NICs (Network Interface Card) and you want to select which one to use. |
| `queuetime` | Queue Time | Float | Determines the queue size of the Helios/EtherDream point buffer and the corresponding time required to drain it. It is often useful to reduce this value when sending fewer points. |
| `queueunits` | Queue Units | Menu | The units of queue time. |
| `xscale` | X Scale | Float | Allows the input x values to be scaled by the specified factor. |
| `yscale` | Y Scale | Float | Allows the input y values to be scaled by the specified factor. |
| `redscale` | Red Scale | Float | Allows the input r values to be scaled by the specified factor. |
| `greenscale` | Green Scale | Float | Allows the input g values to be scaled by the specified factor. |
| `bluescale` | Blue Scale | Float | Allows the input b values to be scaled by the specified factor. |
| `intensityscale` | Intensity Scale | Float | Allows the input intensity values (i) to be scaled by the specified factor. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP laserdeviceCHOP operator
laserdevicechop_op = op('laserdevicechop1')

# Get/set parameters
freq_value = laserdevicechop_op.par.active.eval()
laserdevicechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
laserdevicechop_op = op('laserdevicechop1')
output_op = op('output1')

laserdevicechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(laserdevicechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **21** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
