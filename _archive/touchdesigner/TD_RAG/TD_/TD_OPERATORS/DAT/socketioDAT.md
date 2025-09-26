# DAT socketioDAT

## Overview

The SocketIO DAT connects to a Socket.IO server at the specified URL.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When enabled, the SocketIO DAT is actively listening for events from the server, and can also emit events. |
| `reset` | Reset | Pulse | Disconnects the connection and then reconnects. |
| `url` | URL | Str | The URL of the socket.io server. |
| `verifycert` | Verify Certificate (TLS) | Toggle | Enables TLS (transport layer security) certificate verification. |
| `delay` | Reconnect Delay | Int | The delay in milliseconds between reconnection attempts. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute once for each message coming in. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The operator whose state change will trigger the DAT to execute its script when Execute from is set to Specified Operator. This operator is also the path that the script will be executed from if th... |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading. To clear with a python script op("opname").par.clear.pulse() |
| `bytes` | Bytes Column | Toggle | Outputs the raw bytes of the message in a separate column. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT socketioDAT operator
socketiodat_op = op('socketiodat1')

# Get/set parameters
freq_value = socketiodat_op.par.active.eval()
socketiodat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
socketiodat_op = op('socketiodat1')
output_op = op('output1')

socketiodat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(socketiodat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
