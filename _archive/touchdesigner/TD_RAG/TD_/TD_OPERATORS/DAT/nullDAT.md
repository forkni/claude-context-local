# DAT nullDAT

## Overview

The Null DAT has no effect on the data. It is an instance of the DAT connected to its input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT nullDAT operator
nulldat_op = op('nulldat1')

# Get/set parameters
freq_value = nulldat_op.par.active.eval()
nulldat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
nulldat_op = op('nulldat1')
output_op = op('output1')

nulldat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(nulldat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **4** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
