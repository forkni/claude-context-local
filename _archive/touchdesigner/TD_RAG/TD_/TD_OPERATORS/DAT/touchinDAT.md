# DAT touchinDAT

## Overview

The Touch In DAT receives full tables across the network from the Touch Out DAT, as opposed to messages with the other network based DATs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `protocol` | Protocol | Menu | Select which protocol to use, refer to the Network Protocols article for more information. |
| `address` | Network Address | Str | For multi-cast protocol, this is the multi-cast address to listen for. For UDT protocol this is the IP address of the server. |
| `port` | Port | Int | The port receiving the packets. |
| `shared` | Shared Connection | Toggle | Use the same connection as other networking DATs using the same network protocol. |
| `active` | Active | Toggle | While on, the DAT receives information sent to the network port. While Off, no updating occurs. Data sent to the port is lost. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT touchinDAT operator
touchindat_op = op('touchindat1')

# Get/set parameters
freq_value = touchindat_op.par.active.eval()
touchindat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
touchindat_op = op('touchindat1')
output_op = op('output1')

touchindat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(touchindat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
