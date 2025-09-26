# DAT convertDAT

## Overview

The Convert DAT changes the text format from simple text to table form and vice-versa.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `how` | How | Menu | Convert text format. |
| `removeblank` | Remove Blank Lines | Toggle | When enabled, do not convert blank lines into empty rows. |
| `delimiters` | Split Cells at | Str | A list of individual characters to use to split the string into cells. The delimiters are used independently. That is, if $% is used in this parameter, the cells will be split at $ OR %, not only a... |
| `spacers` | Concatenate with | Str | Insert this string between each cell when converting from a table to text. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT convertDAT operator
convertdat_op = op('convertdat1')

# Get/set parameters
freq_value = convertdat_op.par.active.eval()
convertdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
convertdat_op = op('convertdat1')
output_op = op('output1')

convertdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(convertdat_op)
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
