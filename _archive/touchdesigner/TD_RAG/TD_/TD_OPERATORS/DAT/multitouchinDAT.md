# DAT multitouchinDAT

## Overview

The Multi Touch In DAT is used for receiving messages and events from the Windows 7+ standard multi-touch API.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Registers event when Active is On. |
| `outputtype` | Output | Menu | Sets how the output is displayed in the table. |
| `panel` | Panel | PanelCOMP | The Panel Component to capture the touch events from. |
| `relativeid` | Relative IDs | Toggle | Reorder the touch ids so only the ones within the specified panel are counted. |
| `relativepos` | Relative Position | Toggle | Output position and normalized coordinates relative to lower left corner of the specified panel. |
| `mouse` | Include Mouse | Toggle | When on, the mouse add a touch event when clicked. This event always shares ID 1 with the first touch. Using mouse and multitouch at the same time may result in unexpected behaviours. |
| `posthresh` | Position Threshold | Float | A new message will not be added if a finger has moved less than this number of units. The units are determined by the input device, not necessarily the resolution of the screen that it is associate... |
| `contactthresh` | Contact Threshold | Float | Some touch devices have a width and height of a press, representing pressure of amount of finger contact. This is a minimum threshold below which no events are recognized. |
| `minrows` | Min Rows Displayed | Int | The minimum number of rows always displayed in the table. |
| `doubleclickthresh` | Double Click (secs) | Float | The maximum time allowed between clicks to be registered as a 'double-click'. |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callbacks. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The path that the script will be executed from if the Execute From parameter is set to Specified Operator. |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading. To clear with a script command, here is an example: opparm -c /serial1 clear |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT multitouchinDAT operator
multitouchindat_op = op('multitouchindat1')

# Get/set parameters
freq_value = multitouchindat_op.par.active.eval()
multitouchindat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
multitouchindat_op = op('multitouchindat1')
output_op = op('output1')

multitouchindat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(multitouchindat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
