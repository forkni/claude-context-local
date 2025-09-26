# DAT oscinDAT

## Overview

The OSC In DAT receives and parses full Open Sound Control packets using UDP by default.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT receives information sent to the network port. While Off, no updating occurs. Data sent to the port is lost. |
| `protocol` | Protocol | Menu | Select which protocol to use, refer to the Network Protocols article for more information. |
| `address` | Network Address | Str | For multi-cast protocol, this is the multi-cast address to listen for. For UDT protocol this is the IP address of the server. |
| `port` | Port | Int | The port which OSC-In will accept packets on. |
| `localaddress` | Local Address | StrMenu | Specify an IP address to receive on, useful when the system has mulitple NICs (Network Interface Card) and you want to select which one to use. |
| `shared` | Shared Connection | Toggle | Use the same connection as other networking DATs using the same network protocol. |
| `addscope` | OSC Address Scope | Str | To reduce which message are generated, you can use message address name patterns to include or exclude messages. For example, ^*accel* will exclude accelerometer messages coming in from an iOS or i... |
| `typetag` | Include Type Tag | Toggle | Includes the argument list type tag in each message. It includes the parameter type keywords (in case the parsing application needs to identify parameter types). |
| `splitbundle` | Split Bundle into Messages | Toggle | When On, each message contained within a bundle is given its own row. |
| `splitmessage` | Split Message into Columns | Toggle | When On, OSC address and arguments are given individual columns, otherwise they are included in the message column. |
| `bundletimestamp` | Bundle Timestamp Column | Toggle | When On, each bundle timestamp value is included in a column. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute once for each message received. See oscinDAT_Class for usage. |
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
# Access the DAT oscinDAT operator
oscindat_op = op('oscindat1')

# Get/set parameters
freq_value = oscindat_op.par.active.eval()
oscindat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oscindat_op = op('oscindat1')
output_op = op('output1')

oscindat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oscindat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
