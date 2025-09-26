# DAT serialDAT

## Overview

The Serial DAT is used for serial communication through an external port, using the RS-232 protocol.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | This check box enables the serial connection. |
| `format` | Row/Callback Format | Menu | Interpret the incoming data as binary or ASCII data. If the format is Per Byte, one row is appended for each binary byte received. If the format is Per Line, one row is appended for each null or ne... |
| `port` | Port | StrMenu | Selects the COM port that the serial connection will use.  Default port names 1 through 8 are available in the popup menu, though any name can be manually entered in this field. |
| `baudrate` | Baud Rate | Int | The maximum number of bits of information, including "control" bits, that are transmitted per second. Check your input device's default baud rate and set accordingly. |
| `databits` | Data Bits | Menu | This parameter sets the number of data bits sent in each. Data bits are transmitted "backwards". Backwards refers to the order of transmission, which is from least significant bit (LSB) to most sig... |
| `parity` | Parity | Menu | This parameter can be set to none, even, or odd. The optional parity bit follows the data bits and is included as a simple means of error checking. Parity bits work by specifying ahead of time whet... |
| `stopbits` | Stop Bits | Menu | The last part of transmission packet consists of 1 or 2 Stop bits. The connection will now wait for the next Start bit. |
| `dtr` | DTR | Menu | The DTR (data-terminal-ready) flow control. (Windows Only). |
| `rts` | RTS | Menu | The RTS (request-to-send) flow control. (Windows Only). |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute once for each message received. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The path that the script will be executed from if the Execute From parameter is set to Specified Operator. |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading. To clear with a script command, here is an example: opparm -c /serial1 clear |
| `bytes` | Bytes Column | Toggle | Outputs the raw bytes of the message in a separate column. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT serialDAT operator
serialdat_op = op('serialdat1')

# Get/set parameters
freq_value = serialdat_op.par.active.eval()
serialdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
serialdat_op = op('serialdat1')
output_op = op('output1')

serialdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(serialdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
