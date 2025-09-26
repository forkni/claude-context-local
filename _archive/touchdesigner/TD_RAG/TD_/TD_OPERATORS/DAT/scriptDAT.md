# DAT scriptDAT

## Overview

The Script DAT runs a script each time the DAT cooks and can build/modify the output table based in the optional input tables.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `callbacks` | Callbacks DAT | DAT | Specifies the DAT which holds the callbacks. See scriptDAT_Class for usage. |
| `setuppars` | Setup Parameters | Pulse | Clicking the button runs the setupParameters() callback function. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT scriptDAT operator
scriptdat_op = op('scriptdat1')

# Get/set parameters
freq_value = scriptdat_op.par.active.eval()
scriptdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
scriptdat_op = op('scriptdat1')
output_op = op('output1')

scriptdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(scriptdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **6** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
