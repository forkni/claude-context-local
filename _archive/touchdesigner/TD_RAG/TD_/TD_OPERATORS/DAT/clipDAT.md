# DAT clipDAT

## Overview

The Clip DAT contains information about motion clips that are manipulated by a Clip CHOP and Clip Blender CHOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `edit` | Edit.. | Pulse | Clicking this opens a text editor to add/edit/delete text from the DAT. |
| `file` | File | File | The path and name of the file to load. Accepts .txt and .dat files. The file can be read in from disk or from the web. Use http:// when specifying a URL. |
| `reload` | Reload File | Pulse | When set to 1, reloads the file into the DAT. |
| `executeloc` | Execute from | Menu | Determines the location the script is run from. |
| `clip` | Clip | CHOP | Points to the Clip CHOP which will trigger the script when run in a Clip Blender CHOP. |
| `component` | Component | OP | The path that the script will be executed from if the Execute From parameter is set to Specified Component. |
| `framefirst` | Execute on Frame (First) | Int | Executes the script once, the first time the specified index of the clip is played in a clipblender. Even if the clip is looping in a clipblender, the script will only be executed once. |
| `frameloop` | Execute on Frame (Loop) | Int | Executes the script everytime the specified index of the clip is played in a clipblender. When a clip is looping, the script will run each time through the loop. |
| `exit` | Execute on Exit | Toggle | Executes the script when a clipblender exits the specified clip. |
| `printstate` | Print State | Toggle | Print debug information to the textport. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT clipDAT operator
clipdat_op = op('clipdat1')

# Get/set parameters
freq_value = clipdat_op.par.active.eval()
clipdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
clipdat_op = op('clipdat1')
output_op = op('output1')

clipdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(clipdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
