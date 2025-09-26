# DAT jsonDAT

## Overview

The JSON DAT converts and filters JSON text using JSONPath syntax and outputs the filtered results. It eliminates having to code scripts to parse and manipulate JSON, and keeps the data flow procedural.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `filter` | Filter | Str | A filter string following JSONPath syntax that will be used to filter the input JSON. |
| `output` | Output | Menu | Select the output of the JSON DAT. |
| `expression` | Expression | Str | The custom expression to output |
| `formatoutput` | Format Output | Toggle | When enabled, the output of the DAT will formatted with indents and newlines. |
| `holdlast` | Hold Last Non-Empty Results | Toggle | When enabled, the most recent result will be held if the results become empty, in effect only new non-empty results will update the output. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT jsonDAT operator
jsondat_op = op('jsondat1')

# Get/set parameters
freq_value = jsondat_op.par.active.eval()
jsondat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
jsondat_op = op('jsondat1')
output_op = op('output1')

jsondat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(jsondat_op)
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
