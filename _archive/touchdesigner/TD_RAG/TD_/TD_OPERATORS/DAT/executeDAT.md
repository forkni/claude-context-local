# DAT executeDAT

## Overview

The Execute DAT lets you edit scripts and run them based on conditions.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT will respond to the events selected below. |
| `executeloc` | Execute from | Menu | (Tscript only) Determines the location the script is run from. |
| `fromop` | From Operator | OP | This component is also the path that the script will be executed from if the Execute From parameter is set to Specified Operator. |
| `start` | Start | Toggle | The onStart() method is executed when TouchDesigner starts. This method is never called in TouchEngine because components are loaded after TouchEngine has started. |
| `create` | Create | Toggle | The create() method is executed when the node is created. This can be triggered on start, by loading a component from disk, by copying & pasting, or any other way a node can be created. |
| `exit` | Exit | Toggle | The onExit() method is executed when the TouchDesigner process quits. |
| `framestart` | Frame Start | Toggle | The onFrameStart() method is executed at the start of every frame. |
| `frameend` | Frame End | Toggle | The onFrameEnd() method is executed at the end of every frame. |
| `playstatechange` | Play State Change | Toggle | The onPlayStateChange() method is executed each time the play state changes, ie. pause or play is used on the timeline. |
| `devicechange` | Device Change | Toggle | The onDeviceChange() method is executed each time devices are connected or disconnected from the computer. For example, plugging in MIDI devices, cameras, joysticks, etc.      NOTE: When using mult... |
| `edit` | Edit.. | Pulse | Clicking this opens a text editor to edit text in the DAT.      TIP: To direct all "standard output" of python to a Text DAT, put this in the start() method: sys.stdout = op('text1')   To safely to... |
| `file` | File | File | The filesystem path and name of the file to load. Accepts .txt and .dat files. |
| `syncfile` | Sync to File | Toggle | When On, loads the file from disk into the DAT when the projects starts.  A filename must be specified.  Turning on the option will load the file from disk immediately.  If the file does not exist,... |
| `loadonstart` | Load on Start | Toggle | When On, reloads the file from disk into the DAT when the projects starts. |
| `loadonstartpulse` | Load File | Pulse | Instantly reloads the file. |
| `write` | Write on Toe Save | Toggle | When On, writes the contents of the DAT out to the file on disk when the project is saved. |
| `writepulse` | Write File | Pulse | Instantly write the file to disk. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT executeDAT operator
executedat_op = op('executedat1')

# Get/set parameters
freq_value = executedat_op.par.active.eval()
executedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
executedat_op = op('executedat1')
output_op = op('output1')

executedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(executedat_op)
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
