# CHOP serialCHOP

## Overview

The Serial CHOP is used for serial communication through an external port, using the RS-232 protocol.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | This check box enables the serial connection. |
| `state` | State | Menu | The type of input transition to monitor. |
| `port` | Port | StrMenu | Selects the COM port that the serial connection will use. |
| `baudrate` | Baud Rate | Int | The maximum number of bits of information, including "control" bits, that are transmitted per second. Check your input device's default baud rate and set accordingly. |
| `baudmenu` | Baud Rate Menu | Pulse | Use this menu to select from some commonly used baud rates. |
| `databits` | Data Bits | Menu | This parameter sets the number of data bits sent in each. Data bits are transmitted "backwards". Backwards refers to the order of transmission, which is from least significant bit (LSB) to most sig... |
| `parity` | Parity | Menu | This parameter can be set to none, even, or odd. The optional parity bit follows the data bits and is included as a simple means of error checking. Parity bits work by specifying ahead of time whet... |
| `stopbits` | Stop Bits | Menu | The last part of transmission packet consists of 1 or 2 Stop bits. The connection will now wait for the next Start bit. |
| `script` | Script | Sequence | Sequence of scripts corresponding to input channels. These strings are sent out the serial port when the corresponding channel change is detected. For example, Script 2 is sent to the serial port w... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP serialCHOP operator
serialchop_op = op('serialchop1')

# Get/set parameters
freq_value = serialchop_op.par.active.eval()
serialchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
serialchop_op = op('serialchop1')
output_op = op('output1')

serialchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(serialchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
