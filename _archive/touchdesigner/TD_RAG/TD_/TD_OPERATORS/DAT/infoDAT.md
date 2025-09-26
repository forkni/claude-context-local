# DAT infoDAT

## Overview

The Info DAT gives you string information about a node.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `op` | Operator | OP | The path to the operator that the Info DAT is getting information from. You can drag & drop any node onto this path, or type the path directly into the field. |
| `passive` | Passive | Toggle | If this option is off, the Info DAT will update automatically when the information changes. If on, the data may or may not be out-of-date, and the Info DAT may require a forced cook to update its c... |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT infoDAT operator
infodat_op = op('infodat1')

# Get/set parameters
freq_value = infodat_op.par.active.eval()
infodat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
infodat_op = op('infodat1')
output_op = op('output1')

infodat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(infodat_op)
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
