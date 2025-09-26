# DAT udtoutDAT

## Overview

The UDT Out DAT is used for sending information over a UDT connection between remotely located computers.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `protocol` | Protocol |  | Selects the network protocol to use. Refer to the Network Protocols article for more information. |
| `port` | Port |  | The network port to send to. |
| `shared` | Shared Connection |  | Use the same connection as other networking DATs using the same network protocol. |
| `format` | Row/Callback Format |  | Determines how the incoming data is parsed. |
| `active` | Active |  | This check box enables the connection. |
| `callbacks` | Callbacks DAT |  | The Callbacks DAT will execute once for each message coming in. |
| `executeloc` | Execute from |  | Determines the location the script is run from. |
| `fromop` | From Operator |  | The operator whose state change will trigger the DAT to execute its script when Execute from is set to Specified Operator. This operator is also the path that the script will be executed from if th... |
| `clamp` | Clamp Output |  | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines |  | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output |  | Deletes all lines except the heading. To clear with a python script op("opname").par.clear.pulse() |
| `bytes` | Bytes Column |  | Outputs the raw bytes of the message in a separate column. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT udtoutDAT operator
udtoutdat_op = op('udtoutdat1')

# Get/set parameters
freq_value = udtoutdat_op.par.active.eval()
udtoutdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
udtoutdat_op = op('udtoutdat1')
output_op = op('output1')

udtoutdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(udtoutdat_op)
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
