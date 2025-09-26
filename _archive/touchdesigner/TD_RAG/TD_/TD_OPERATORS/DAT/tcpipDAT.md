# DAT tcpipDAT

## Overview

The TCP/IP DAT is used for sending and receiving information over a TCP/IP connection between two remotely located computers.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `mode` | Connection Mode | Menu | Specify if this operator is communicating as a client or a server. |
| `address` | Network Address | Str | If this node is communicating as a client, this should be the IP address of the server. |
| `port` | Port | Int | The network port to listen on or connect to, depending on of the node is the server or client respectively. |
| `shared` | Shared Connection | Toggle | Use the same connection as other networking DATs using the same network protocol. |
| `format` | Row/Callback Format | Menu | Determines how the incoming data is parsed into the table. |
| `active` | Active | Toggle | This check box enables the connection. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute once for each message received. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The component who's state change will trigger the DAT to execute its script when Execute from is set to On Panel Change. This component is also the path that the script will be executed from if the... |
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
# Access the DAT tcpipDAT operator
tcpipdat_op = op('tcpipdat1')

# Get/set parameters
freq_value = tcpipdat_op.par.active.eval()
tcpipdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tcpipdat_op = op('tcpipdat1')
output_op = op('output1')

tcpipdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tcpipdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
