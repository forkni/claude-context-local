# DAT inDAT

## Overview

The In DAT is used to create a DAT input in a Component.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `label` | Label | Str | Creates a pop-up label when the cursor rolls over this Component input. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT inDAT operator
indat_op = op('indat1')

# Get/set parameters
freq_value = indat_op.par.active.eval()
indat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
indat_op = op('indat1')
output_op = op('output1')

indat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(indat_op)
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
