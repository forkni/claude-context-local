# DAT performDAT

## Overview

The Perform DAT logs various performance times in a Table DAT format.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turns logging on/off. The DAT will continuously log while Active is On. |
| `activepulse` | Active Pulse | Pulse | Use resetpulse button to grab a single frame snapshot. |
| `triggermode` | Trigger Mode | Menu | Offers two options for when to trigger a refresh of the logs. |
| `triggerthreshold` | Trigger Threshold | Float | This is the amount of time, in milliseconds, that a frame must exceed to cause the DAT to log and output the frame's timing. For example to see what happens when a frame takes more that 33 ms to co... |
| `logcook` | Cook Time | Toggle | Logs the cook time of operators. |
| `logexport` | Export Time | Toggle | Logs time spent exporting CHOP channels. |
| `logviewport` | Viewport Draw Time | Toggle | Logs time to draw 3D geometry and SOP viewers. |
| `logmovie` | Movie Time | Toggle | Logs time taken to read video and audio from movie files. |
| `logdrawchannels` | Draw Channels Time | Toggle | Logs time to draw channels in CHOP viewers. |
| `logobjectview` | Object View Time | Toggle | Logs time to draw objects in 3D viewers. |
| `logcustompanel` | Custom Panel Time | Toggle | Logs time taken by custom panels build with Panel Components. |
| `logmidi` | MIDI Time | Toggle | Logs time spent on MIDI. |
| `loggraphics` | Graphics Time | Toggle | Logs various graphics system calls, such as time spent waiting for the graphics card, calls to the graphic driver, converting TOP data to CHOPs, etc. |
| `logframelength` | Frame Length | Toggle | Logs total frame time in milliseconds (ms). |
| `logmisc` | Misc | Toggle | Logs miscellaneous times that do not fit into other categories. |
| `logscript` | Script | Toggle | Logs time spent running scripts. |
| `logrender` | Render | Toggle | Logs time spend by Render or Renderpass TOPs. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT performDAT operator
performdat_op = op('performdat1')

# Get/set parameters
freq_value = performdat_op.par.active.eval()
performdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
performdat_op = op('performdat1')
output_op = op('output1')

performdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(performdat_op)
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
