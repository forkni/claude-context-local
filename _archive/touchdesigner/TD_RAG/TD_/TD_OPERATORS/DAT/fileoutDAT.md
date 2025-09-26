# DAT fileoutDAT

## Overview

The File Out DAT allows you to write out DAT contents to a .dat file or a .txt file.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | File | File | The filesystem path and name of the file to be written. |
| `n` | N | Int | Using me.par.n (or $N in Tscript) in the filename (in the File parameter) in conjuction with the N parameter here gives a method of incrementing file names. The N parameter must manually be increme... |
| `write` | Write File | Pulse | Press this button to write the file once. |
| `append` | Append (txt Only) | Toggle | Appends the text into the file instead of overwriting the file contents completely. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT fileoutDAT operator
fileoutdat_op = op('fileoutdat1')

# Get/set parameters
freq_value = fileoutdat_op.par.active.eval()
fileoutdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fileoutdat_op = op('fileoutdat1')
output_op = op('output1')

fileoutdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fileoutdat_op)
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
