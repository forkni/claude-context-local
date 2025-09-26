# DAT reorderDAT

## Overview

The Reorder DAT allows you to reorder the rows and columns of the input table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `reorder` | Reorder | Menu | This parameter allows you to reorder either rows or columns. |
| `method` | Method | Menu | Specify how to reorder the table. |
| `before` | Before | Str | The rows or columns to copy or swap from. |
| `after` | After | Str | The rows or columns to copy or swap to. |
| `order` | Order | Str | The order of input rows and columns to copy. |
| `delete` | Delete Unspecified | Toggle | Only available when Method is 'In Specified Order by Name' or 'In Specified Order by Index'. It will delete any row/column not listed in the Order parameter. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT reorderDAT operator
reorderdat_op = op('reorderdat1')

# Get/set parameters
freq_value = reorderdat_op.par.active.eval()
reorderdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
reorderdat_op = op('reorderdat1')
output_op = op('output1')

reorderdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(reorderdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
