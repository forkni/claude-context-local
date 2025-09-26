# DAT choptoDAT

## Overview

The CHOP to DAT allows you to get CHOP channel values into a DAT in table format.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `chop` | CHOP | CHOP | The CHOP to be used to retrieve values. A row is created for each channel's value. |
| `names` | Include Names | Toggle | When checked on, an extra column will be created in every row for the channel's name. |
| `latestsample` | Latest Sample when Time Slice | Toggle | When on and the CHOP is time sliced, only the latest sample of the CHOP will be used to create the DAT output. This prevents the table size from fluctuating as frames are dropped. |
| `output` | Output | Menu | Create a row per channel or column per channel. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT choptoDAT operator
choptodat_op = op('choptodat1')

# Get/set parameters
freq_value = choptodat_op.par.active.eval()
choptodat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
choptodat_op = op('choptodat1')
output_op = op('output1')

choptodat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(choptodat_op)
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
