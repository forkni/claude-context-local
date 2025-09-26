# DAT opexecuteDAT

## Overview

The OP Execute DAT runs a script when the state of an operator changes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT will respond to the OP that is referenced. |
| `executeloc` | Execute from | Menu | (Tscript only) Determines the location the script is run from. |
| `fromop` | From Operator | OP | The path that the script will be executed from if the Execute From parameter is set to Specified Operator. |
| `op` | Monitor OPs | OP | Specify which operators to monitor to trigger the scripts. |
| `precook` | Pre Cook | Toggle | The onPreCook() method is triggered before the operator is cooked. |
| `postcook` | Post Cook | Toggle | The onPostCook() method is triggered after the operator is cooked. |
| `opdelete` | Destroy | Toggle | The onDestroy() method is triggered when the operator is deleted. |
| `flagchange` | Flag Change | Toggle | The onFlagChange() method is triggered when one of the operator's Flags changes state. This includes all the flags in the Common Flags list of an OP_Class, plus all the python accessible flags list... |
| `wirechange` | Wire Change | Toggle | The onWireChange() method is triggered when the operator's inputs are rewired (connected, disconnected, swapped). |
| `namechange` | Name Change | Toggle | The onNameChange() method is triggered when the name of the operator is changed. |
| `pathchange` | Path Change | Toggle | The onPathChange() method is triggered when the path of the operator is changed. |
| `uichange` | UI Change | Toggle | The onUIChange() method is triggered when operator is resized or moved in the network editor. |
| `numchildrenchange` | Number Children Change | Toggle | The onNumChildrenChange() method is triggered if the number of children an operator has changes. Only works with Component type operators. |
| `childrename` | Child Rename | Toggle | The onChildRename() method is triggered if a child of the operator is renamed. |
| `currentchildchange` | Current Child Change | Toggle | The onCurrentChildChange() method is triggered if a child of the operator is made current in a network. Only works with Component type operators. |
| `extensionchange` | Extension Change | Toggle | The onExtensionChange() method is triggered when an extension of the operator is changed. |
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
# Access the DAT opexecuteDAT operator
opexecutedat_op = op('opexecutedat1')

# Get/set parameters
freq_value = opexecutedat_op.par.active.eval()
opexecutedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
opexecutedat_op = op('opexecutedat1')
output_op = op('output1')

opexecutedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(opexecutedat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **27** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
