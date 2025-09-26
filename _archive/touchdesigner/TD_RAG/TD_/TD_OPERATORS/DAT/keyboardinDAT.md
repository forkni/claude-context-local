# DAT keyboardinDAT

## Overview

The Keyboard In DAT lists the most recent key events in its FIFO (first in/first out) table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Inhibits and allows message to be added to log. |
| `perform` | Perform Window Only | Toggle | When on, key events are only detected while in perform mode. |
| `keys` | Keys | Str | List of keys to allow through the filter. Just put the characters in the list, space-separated. Eg. '1 2 g h' for the 1, 2, g and h keys. Only these keys will be added to the log and generate an ev... |
| `shortcuts` | Shortcuts | Str | List of shortcuts to watch for. See "Shortcuts" in the notes for defining shortcuts. |
| `panels` | Panels | PanelCOMP | Optional list of references to panels to detect events from. Events will only be fired when any of the listed panels has focus. |
| `lrmodifiers` | Left/Right Modifiers | Toggle | When on, the states of the left and right modifier keys (see Notes) will be added to the table. Switching the state of this parameter will reset the table's contents. |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callbacks for each keyboard event received. See keyboardinDAT_Class for usage. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The operator whose state change will trigger the DAT to execute its script when Execute is set to Specified Operator. This operator is also the path that the script will be executed from if the Exe... |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading.  To clear with a python script op("opname").par.clear.pulse() |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT keyboardinDAT operator
keyboardindat_op = op('keyboardindat1')

# Get/set parameters
freq_value = keyboardindat_op.par.active.eval()
keyboardindat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
keyboardindat_op = op('keyboardindat1')
output_op = op('output1')

keyboardindat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(keyboardindat_op)
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
