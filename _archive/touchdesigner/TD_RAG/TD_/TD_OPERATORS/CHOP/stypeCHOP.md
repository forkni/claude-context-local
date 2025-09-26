# CHOP stypeCHOP

## Overview

The Stype CHOP reads camera tracking information sent from a Stype device.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `protocol` | Protocol | Menu | The network protocol to use. Refer to the Network Protocols article for more information. |
| `netaddress` | Network Address | Str | When using Multicast, this is the address that Stype will listen for packets on. |
| `port` | Network Port | Int | The port which the Stype CHOP will accept packets on. The default for the protocol is 6301, but this should be set to match the current hardware output settings. |
| `localaddress` | Local Address | StrMenu | When the sending machine is equipped with multiple network adapters, this parameter can be used to choose which adapter to send the data from by specifying its IP address here. |
| `active` | Active | Toggle | While on, the CHOP receives information sent to the network port. While Off, no updating occurs. Data sent to the port is lost. |
| `padding` | Padding | Float | A value from 0 to 1 indicating the percentage to increase the field of view in case the given lens distortion requires samples outside of the normal render area. It is used to calculate the padded ... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP stypeCHOP operator
stypechop_op = op('stypechop1')

# Get/set parameters
freq_value = stypechop_op.par.active.eval()
stypechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
stypechop_op = op('stypechop1')
output_op = op('output1')

stypechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(stypechop_op)
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
