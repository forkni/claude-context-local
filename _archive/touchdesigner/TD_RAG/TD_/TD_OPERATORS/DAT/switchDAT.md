# DAT switchDAT

## Overview

The Switch DAT is a multi-input operator which lets you choose which input is output by using the Input parameter.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `index` | Index | Int | Selects which input to pass though to the output. The first input is 0. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT switchDAT operator
switchdat_op = op('switchdat1')

# Get/set parameters
freq_value = switchdat_op.par.active.eval()
switchdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
switchdat_op = op('switchdat1')
output_op = op('output1')

switchdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(switchdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **5** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
