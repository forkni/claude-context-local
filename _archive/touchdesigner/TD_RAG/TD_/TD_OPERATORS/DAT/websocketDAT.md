# DAT websocketDAT

## Overview

The WebSocket DAT receives and parses WebSocket messages.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT receives information sent to the network port. While Off, no updating occurs. Data sent to the port is lost. |
| `netaddress` | Network Address | Str | The network address of the server computer. This address is a standard WWW address, such as foo or foo.bar.com. You can put an IP address (e.g. 100.123.45.78). If you put localhost, it means the ot... |
| `port` | Network Port | Int | The port in which the DAT will accept messages. Port 443 implies a secure connection. If attempting a secure connection not using port 443 then a "wss://" prefix is required on the Network Address ... |
| `timeout` | Connection Timeout | Int | Time in milliseconds the WebSocket DAT will wait to connect to the server. |
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
# Access the DAT websocketDAT operator
websocketdat_op = op('websocketdat1')

# Get/set parameters
freq_value = websocketdat_op.par.active.eval()
websocketdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
websocketdat_op = op('websocketdat1')
output_op = op('output1')

websocketdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(websocketdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
