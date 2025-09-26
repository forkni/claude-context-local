# DAT panelexecuteDAT

## Overview

The Panel Execute DAT will run its script when the Panel Values of a specified panel component changes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT will respond to the Panel that is referenced. |
| `executeloc` | Execute from | Menu | (Tscript only) Determines the location the script is run from. |
| `fromop` | From Operator | OP | The path that the script will be executed from if the Execute From parameter is set to Specified Operator. |
| `panels` | Panels | COMP | Select which Panel COMPs to monitor for changes. |
| `panelvalue` | Panel Value | StrMenu | The Panel Value(s) that is monitored to trigger the execution of the script.      Scripts will execute based on a combination of the five trigger events listed below. The script is executed once pe... |
| `offtoon` | Off to On | Toggle | The onOffToOn() method executes when the panel value specified switches from off to on, called at the first "on" frame. |
| `whileon` | While On | Toggle | The whileOn() method executes when the panel value specified is on. It is called once each frame. |
| `ontooff` | On to Off | Toggle | The onOnToOff() method executes when the panel value specified switches from on to off, called at the first "off" frame. |
| `whileoff` | While Off | Toggle | The whileOff() method executes when the panel value specified is off. It is called once each frame. |
| `valuechange` | Value Change | Toggle | The onValueChange() method executes when the panel value specified changes value in any way. It is called once each frame. |
| `edit` | Edit.. | Pulse | Clicking this opens a text editor to edit text in the DAT. |
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
# Access the DAT panelexecuteDAT operator
panelexecutedat_op = op('panelexecutedat1')

# Get/set parameters
freq_value = panelexecutedat_op.par.active.eval()
panelexecutedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
panelexecutedat_op = op('panelexecutedat1')
output_op = op('output1')

panelexecutedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(panelexecutedat_op)
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
