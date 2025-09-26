# DAT artnetDAT

## Overview

The Art-Net DAT polls and lists all devices on the network.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `callbacks` | Callbacks DAT | DAT | Runs this script when polling the network for devices. See artnetDAT_Class for usage. |
| `columns` | Columns | StrMenu | Select which columns are included in the table.  Click the drop menu to the right to see all that are available. |
| `poll` | Poll Devices | Pulse | Poll the network for devices. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT artnetDAT operator
artnetdat_op = op('artnetdat1')

# Get/set parameters
freq_value = artnetdat_op.par.active.eval()
artnetdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
artnetdat_op = op('artnetdat1')
output_op = op('output1')

artnetdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(artnetdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **7** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
