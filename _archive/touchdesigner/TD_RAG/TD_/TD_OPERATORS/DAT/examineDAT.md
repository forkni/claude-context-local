# DAT examineDAT

## Overview

The Examine DAT lets you inspect an operator's python storage, locals, globals, expressions, and extensions.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `op` | Operator | OP | Path to the operator to examine. |
| `source` | Source | Menu | Specifies what part of the operator to examine. |
| `subkey` | Subkey | Str | If the object to be examined is a dictionary you can specify which element to examine here. |
| `expression` | Expression | Str | When source is set to Expression, enter your expression in this parameter. |
| `level` | Level | Str | Clamp the maximum depth level. |
| `key` | Key | Str | Filter Key results. |
| `type` | Type | Str | Filter Type results. |
| `value` | Value | Str | Filter Value results. |
| `expandclasses` | Expand Classes | Toggle | When true, complex object structures (example OP) are further expanded. |
| `maxlevels` | Max Levels | Int | Specify the maximum depth in which to expand a python object. |
| `format` | Format | Menu | Determines whether the output is raw text or in table format. |
| `outputheaders` | Output Headers | Toggle | Turn this on to display the column names when Format is set to Table. |
| `outputlevel` | Output Level | Toggle | Turn this on to output the Level column of the results. |
| `outputkey` | Output Key | Toggle | Turn this on to output the Key column of the results. |
| `outputtype` | Output Type | Toggle | Turn this on to output the Type column of the results. |
| `outputvalue` | Output Value | Toggle | Turn this on to output the Value column of the results. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT examineDAT operator
examinedat_op = op('examinedat1')

# Get/set parameters
freq_value = examinedat_op.par.active.eval()
examinedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
examinedat_op = op('examinedat1')
output_op = op('output1')

examinedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(examinedat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
