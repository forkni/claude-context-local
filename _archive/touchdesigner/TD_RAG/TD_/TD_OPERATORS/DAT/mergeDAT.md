# DAT mergeDAT

## Overview

The Merged DAT is a multi-input DAT which merges the text or tables from the input DATs together.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `dat` | DAT | DAT | Specifies the path to DATs to be merged. Can be used in conjunction with the operator's wired inputs. |
| `how` | How | Menu | Sets how tables are merged together. |
| `byname` | By Name | Toggle | Specifies if you are appending columns and rows by name. |
| `spacer` | Concatenate with | Str | Allows you to separate the cell data with a string when concatenating. The default is a space. |
| `unmatched` | Append Unmatched | Toggle | If the subsequent tables have rows or columns that are not found in the first table, these will be added to the output. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT mergeDAT operator
mergedat_op = op('mergedat1')

# Get/set parameters
freq_value = mergedat_op.par.active.eval()
mergedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mergedat_op = op('mergedat1')
output_op = op('output1')

mergedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mergedat_op)
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
