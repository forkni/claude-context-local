# datexecuteDAT

## Overview

The DAT Execute DAT monitors another DAT's contents and runs a script when those contents change. The other DAT is usually a table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT will respond to the CHOP that is referenced. |
| `executeloc` | Execute from | Menu | (Tscript only) Determines the location the script is run from. |
| `fromop` | From Operator | OP | The path that the script will be executed from if the Execute From parameter is set to Specified Operator. |
| `dat` | DAT | DAT | The DAT which is monitored and will trigger the script to execute when its contents change. |
| `tablechange` | Table Change | Toggle | The onTableChange() method is called if the table changes in any way since the last cook. |
| `rowchange` | Row Change | Toggle | The onRowChange() method is called once for every row that changed (since its last cook). |
| `colchange` | Column Change | Toggle | The onColChange() method is called once for every column that changed (since its last cook). |
| `cellchange` | Cell Change | Toggle | The onCellChange() method is called for every cell that changed since the last cook. |
| `sizechange` | Size Change | Toggle | The onSizeChange() method is called for every table size change since the last cook. |
| `execute` | Execute | Menu | Determines if the methods are executed at the start of the frame or end of the frame. |
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
# Access the datexecuteDAT operator
datexecutedat_op = op('datexecutedat1')

# Get/set parameters
freq_value = datexecutedat_op.par.active.eval()
datexecutedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
datexecutedat_op = op('datexecutedat1')
output_op = op('output1')

datexecutedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(datexecutedat_op)
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
