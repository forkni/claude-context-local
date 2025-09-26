# DAT errorDAT

## Overview

The Error DAT lists the most recent TouchDesigner errors in its FIFO (first in/first out) table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Inhibits and allows message to be added to log. |
| `severity` | Severity | Str | Filter pattern for the output. Can be a combination or one of: message, warning or abort |
| `type` | Type | Str | Filter pattern for the output where the source operator family is specified. Can be a combination or one of the operator families. |
| `source` | Source | Str | Filter pattern for the output where the logging of errors can be limited to specific locations in the project. |
| `message` | Message | Str | Filter pattern for the output applied to the error message. |
| `logcurrent` | Log Current Errors | Pulse | Traverse through all nodes and captures all current errors. |
| `callbacks` | Callbacks DAT | DAT | The DAT's script will execute once for each message coming in. See errorDAT_Class for usage. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The path that the script will be executed from if the Execute From parameter is set to Specified Operator. |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT errorDAT operator
errordat_op = op('errordat1')

# Get/set parameters
freq_value = errordat_op.par.active.eval()
errordat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
errordat_op = op('errordat1')
output_op = op('output1')

errordat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(errordat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
