# DAT fifoDAT

## Overview

The FIFO DAT maintains a user-set maximum number of rows in a table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute once for each row added to the FIFO DAT. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The operator whose state change will trigger the DAT to execute its script when Execute is set to Specified Operator. This operator is also the path that the script will be executed from if the Exe... |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading. To clear with a python script op('opname').par.clear.pulse() |
| `firstrow` | Keep First Row | Toggle | Keeps first row in table. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT fifoDAT operator
fifodat_op = op('fifodat1')

# Get/set parameters
freq_value = fifodat_op.par.active.eval()
fifodat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fifodat_op = op('fifodat1')
output_op = op('output1')

fifodat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fifodat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
