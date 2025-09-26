# DAT insertDAT

## Overview

The Insert DAT allows you to insert a row or column into an exiting table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `insert` | Insert | Menu | Specify what to insert. |
| `at` | At | Menu | Specify where to insert. |
| `index` | Index | Int | Index to insert the row or column. Use "After Last" from the "At" parameter to append at the end of the table. |
| `contents` | Contents | Str | Entries for each cell separated by spaces. Put entries that have spaces in quotes, for example Name Species "Home Planet" will put Name in the first cell, Species in the second, and Home Planet in ... |
| `includenames` | Include Names | Toggle |  |
| `replaceduplicate` | Replace if Duplicate Name | Toggle |  |
| `replace` | Replace | Sequence |  |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT insertDAT operator
insertdat_op = op('insertdat1')

# Get/set parameters
freq_value = insertdat_op.par.active.eval()
insertdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
insertdat_op = op('insertdat1')
output_op = op('output1')

insertdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(insertdat_op)
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
