# DAT sortDAT

## Overview

The Sort DAT will sort table DAT data by row or column.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sortmethod` | Sort | Menu | Determines how the table will be sorted. |
| `name` | Name | Str | When using Sort Specify Row/Column Name, specify the name in this parameter. If the sort name does not find a match, the output will be unsorted. |
| `index` | Index | Int | When using Sort Specify Row/Column Index, specify the index in this parameter. If the sort index is -1 or out of bounds, the output will be unsorted. |
| `order` | Order | Menu | Determines the type of sorting. |
| `seed` | Seed | Float | The random seed when Sort Order is set to Random. |
| `ignorecase` | Ignore Case | Toggle | Ignores case sensitivity when Sort Order is set to Alphabetical or Alphabetical with Numbers. |
| `preservefirst` | Preserve First | Toggle | Does not resort the first row or column (depending if Sort is set to Rows or Columns). |
| `unique` | Unique Output | Menu | Remove duplicate rows/column entries in the sorted row/column. |
| `reverse` | Reverse Output | Toggle | Reverses the sort order. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT sortDAT operator
sortdat_op = op('sortdat1')

# Get/set parameters
freq_value = sortdat_op.par.active.eval()
sortdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sortdat_op = op('sortdat1')
output_op = op('output1')

sortdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sortdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
