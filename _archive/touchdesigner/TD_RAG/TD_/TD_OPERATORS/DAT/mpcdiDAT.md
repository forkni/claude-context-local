# DAT mpcdiDAT

## Overview

The MPCDI DAT lets you load calibration data stored in the MPCDI format.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | Configuration File | File | Specify the location of the .mpcdi file. |
| `reloadpulse` | Reload Pulse | Pulse | Instantly reloads the file. |
| `outputby` | Output by | Menu | The menu determines how to fill the DAT rows, with a single region or full buffers. |
| `bufferid` | Buffer ID | Menu | Buffer ID to output. |
| `regionid` | Region ID | Menu | Region ID to output. |
| `near` | Near | Float | Sets the near value. |
| `far` | Far | Float | Sets the far value. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT mpcdiDAT operator
mpcdidat_op = op('mpcdidat1')

# Get/set parameters
freq_value = mpcdidat_op.par.active.eval()
mpcdidat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mpcdidat_op = op('mpcdidat1')
output_op = op('output1')

mpcdidat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mpcdidat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
