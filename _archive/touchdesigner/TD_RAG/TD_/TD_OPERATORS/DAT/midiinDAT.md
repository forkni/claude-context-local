# DAT midiinDAT

## Overview

The MIDI In DAT logs all MIDI messages coming into TouchDesigner from a specified MIDI device.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Logs MIDI events when turned on. |
| `device` | Device Table | DAT | Path to the MIDI device Table DAT |
| `id` | Device ID | Str | Path to the MIDI device Table DAT |
| `skipsense` | Skip Sense | Toggle | Does not log sense messages when this is turned on. |
| `skiptiming` | Skip Timing | Toggle | Does not report timing messages when this is turned on. |
| `filter` | Filter Messages | Toggle | Turning this on enables the message filtering parameters below. |
| `message` | Message | Str | Filter by the MIDI message content. Example "Control Change" |
| `channel` | Channel | Str | Filter by the MIDI message channel. Channels range from 1 to 16. |
| `index` | Index | Str | Filter by the MIDI message index. Indices range from 1 to 128. |
| `value` | Value | Str | Filter by the MIDI message value. Values range from 0 to 127. |
| `callbacks` | Callbacks DAT | DAT | Runs this script once for each row added to the table (ie. each MIDI event received). See midiinDAT_Class for usage. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `fromop` | From Operator | OP | The operator whose state change will trigger the DAT to execute its script when Execute from is set to Specified Operator. This operator is also the path that the script will be executed from if th... |
| `clamp` | Clamp Output | Toggle | The DAT is limited to 100 messages by default but with Clamp Output, this can be set to anything including unlimited. |
| `maxlines` | Maximum Lines | Int | Limits the number of messages, older messages are removed from the list first. |
| `clear` | Clear Output | Pulse | Deletes all lines except the heading. To clear with a python script op("opname").par.clear.pulse() |
| `bytes` | Bytes Column | Toggle | Outputs the raw bytes of the message in a separate column. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT midiinDAT operator
midiindat_op = op('midiindat1')

# Get/set parameters
freq_value = midiindat_op.par.active.eval()
midiindat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
midiindat_op = op('midiindat1')
output_op = op('output1')

midiindat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(midiindat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **21** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
