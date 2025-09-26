# DAT fileinDAT

## Overview

The File In DAT reads in .txt text files and .dat table files.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | File | File | The filesystem path and name of the file to load. Accepts .txt files for regular text and .dat files for text in table format. |
| `converttable` | Convert Text to Table | Toggle | Converts the contents of the DAT from regular text to table-formatted text (tab-delimited text, each  is a new column in the table). |
| `refresh` | Refresh | Toggle | Reload the file when this parameter is set to On. |
| `refreshpulse` | Refresh Pulse | Pulse | Instantly reload the file from disk. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT fileinDAT operator
fileindat_op = op('fileindat1')

# Get/set parameters
freq_value = fileindat_op.par.active.eval()
fileindat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fileindat_op = op('fileindat1')
output_op = op('output1')

fileindat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fileindat_op)
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
