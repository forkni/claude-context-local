# DAT indicesDAT

## Overview

The Indices DAT creates a series of numbers in a table, ranging between the start and end values.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `start` | Start |  | The start of the number range. |
| `end` | End |  | The end of the number range. |
| `level` | Level |  | Determines how the range is divided. Coarse = 0, Medium = 1, Fine = 2. |
| `origin` | Origin |  | The first number in the series. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT indicesDAT operator
indicesdat_op = op('indicesdat1')

# Get/set parameters
freq_value = indicesdat_op.par.active.eval()
indicesdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
indicesdat_op = op('indicesdat1')
output_op = op('output1')

indicesdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(indicesdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **8** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
