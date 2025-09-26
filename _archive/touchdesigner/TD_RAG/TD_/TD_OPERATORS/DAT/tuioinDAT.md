# DAT tuioinDAT

## Overview

The TUIO In DAT receives and parses TUIO messages (received over network) into columns in the table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `protocol` | Protocol | Menu | Select which protocol to use, refer to the Network Protocols article for more information. |
| `address` | Network Address | Str | For multi-cast protocol, this is the multi-cast address to listen for. |
| `port` | Port | Int | The port which TUIO In will accept packets on. |
| `shared` | Shared Connection | Toggle | Use the same connection as other networking DATs using the same network protocol. |
| `active` | Active | Toggle | While on, the DAT receives information sent to the network port. While Off, no updating occurs. Data sent to the port is lost. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will get callbacks for TUIO events. See tuioinDAT_Class for usage. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The operator whose state change will trigger the DAT to execute its script when Execute from is set to Specified Operator. This operator is also the path that the script will be executed from if th... |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT tuioinDAT operator
tuioindat_op = op('tuioindat1')

# Get/set parameters
freq_value = tuioindat_op.par.active.eval()
tuioindat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tuioindat_op = op('tuioindat1')
output_op = op('output1')

tuioindat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tuioindat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
