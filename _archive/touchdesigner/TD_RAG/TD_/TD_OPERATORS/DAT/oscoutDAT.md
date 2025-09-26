# DAT oscoutDAT

## Overview

The OSC Out DAT is used for sending information over a OSC connection between remotely located computers.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT receives/sends information from/to the network port. While Off, no updating occurs. Data sent to the port is lost. |
| `protocol` | Protocol | Menu | Selects the network protocol to use. Refer to the Network Protocols article for more information. |
| `address` | Network Address | Str | The network address of the target computer when using UDP. For multi-cast this is the multi-cast address to send to. This address is a standard WWW address, such as 'foo' or 'foo.bar.com'. You can ... |
| `port` | Port | Int | The network port to send to. |
| `localaddress` | Local Address | Str | Specify an IP address to send from, useful when the system has mulitple NICs (Network Interface Card) and you want to select which one to use. |
| `shared` | Shared Connection | Toggle | Use the same connection as other networking DATs using the same network protocol. |
| `addscope` | OSC Address Scope | Toggle | To reduce which channels are generated, you can use channel name patterns to include or exclude channels. For example, ^*accel* will exclude accelerometer channels coming in from an iOS or iPhone a... |
| `typetag` | Include Type Tag | Toggle | Includes the argument list type tag in each message. It includes the parameter type keywords (in case the parsing application needs to identify parmameter types). |
| `splitbundle` | Split Bundle into Messages | Toggle | When On, each message contained within a bundle is given its own row. |
| `splitmessage` | Split Message into Columns | Toggle | When On, OSC address and arguments are given individual columns, otherwise they are included in the message column. |
| `bundletimestamp` | Bundle Timestamp Column | Toggle | When On, each bundle timestamp value is included in a column. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute once for each message received. |
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
# Access the DAT oscoutDAT operator
oscoutdat_op = op('oscoutdat1')

# Get/set parameters
freq_value = oscoutdat_op.par.active.eval()
oscoutdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oscoutdat_op = op('oscoutdat1')
output_op = op('output1')

oscoutdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oscoutdat_op)
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
