# DAT lookupDAT

## Overview

The Lookup DAT  outputs values from a lookup Table. The first input is an index into the second input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `index` | Index | dropmenu | Select how the index values are interpreted: as values/indices contained in a column or contained in a row. |
| `valueloction` | Value Location | dropmenu | When 'Row Values' or 'Col Values' is selected in the Index Parameter, this parameter lets you select how the lookup row or column where the index value searches will be specified. |
| `valuename` | Value Name | string | Specify the name of the lookup row or column. |
| `valueindex` | Value Index | integer | Specify the index of the lookup row or column. |
| `includeheader` | Include Header | toggle | Include the first row or column. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT lookupDAT operator
lookupdat_op = op('lookupdat1')

# Get/set parameters
freq_value = lookupdat_op.par.active.eval()
lookupdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lookupdat_op = op('lookupdat1')
output_op = op('output1')

lookupdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lookupdat_op)
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
