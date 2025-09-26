# DAT mediafileinfoDAT

## Overview

The Media File Info DAT encapsulates the essential metadata for a Media File.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | File | File | The path and name of the image or movie file to load. Image and movie formats are those found in File Types.  You can specify files on the internet using http:// ... |
| `topchop` | TOP/CHOP | CHOP | Reference to a Movie File In TOP or Audio File In CHOP to read file information from. |
| `reloadpulse` | Reload Pulse | Pulse | Change from 0 to 1 to force the file to reload, useful when the file changes or did not exist at first. |
| `opentimeout` | File Open Timeout | Int | The time (in milliseconds) TouchDesigner will wait for a file to open. If the Disk Open Timout is reached, the Media File Info will stop waiting and output nothing. If the file still isn't opened t... |
| `transpose` | Transpose | Toggle | The output will be changed from row per item to column per item. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT mediafileinfoDAT operator
mediafileinfodat_op = op('mediafileinfodat1')

# Get/set parameters
freq_value = mediafileinfodat_op.par.active.eval()
mediafileinfodat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mediafileinfodat_op = op('mediafileinfodat1')
output_op = op('output1')

mediafileinfodat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mediafileinfodat_op)
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
