# DAT tableDAT

## Overview

The Table DAT lets you hand-edit or create a table of rows and columns of cells, each cell containing a text string.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `edit` | Edit.. | Pulse | Clicking this opens a text editor to add/edit/delete text from the DAT. |
| `file` | File | File | The filesystem path and name of the file to load. Accepts .txt and .dat files. |
| `syncfile` | Sync to File | Toggle | When On, loads the file from disk into the DAT when the projects starts.  A filename must be specified.  Turning on the option will load the file from disk immediately.  If the file does not exist,... |
| `defaultreadencoding` | Default Read Encoding | Menu | Sets the expected file encoding format, or auto-detects the format.  UTF8, UTF16-LE, UTF16-BE, CP1252 |
| `loadonstart` | Load on Start | Toggle | When On, reloads the file from disk into the DAT when the projects starts. |
| `write` | Write on Toe Save | Toggle | When On, writes the contents of the DAT out to the file on disk when the project is saved. |
| `removeblank` | Remove Blank Lines | Toggle | When enabled, do not convert blank lines into empty rows when loading files. |
| `fill` | Fill Type | Menu | You can create and fill rows and columns of a table. Fill Type menu gives 5 options: Manual, Set Size, Set Size and Contents, Fill by Column, and Fill by Row. When a Fill option is chosen, you can ... |
| `rows` | Rows | Int | Defines the number of rows in the table, where applicable. |
| `cols` | Columns | Int | Defines the number of columns in the table, where applicable. |
| `cellexpr` | Cell Expression | Str | Expression used to fill each cell if the Fill Type is Set Size and Contents. Can include expressions me.subRow and me.subCol |
| `includenames` | Include Names | Toggle | Creates an extra row at the top, or a column at the left for the names of the columns or rows, filled with the Include Names parameter. |
| `fills` | Fills | Sequence | Sequence of fill information for Fill by Column and Fill by Row Fill Types |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT tableDAT operator
tabledat_op = op('tabledat1')

# Get/set parameters
freq_value = tabledat_op.par.active.eval()
tabledat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tabledat_op = op('tabledat1')
output_op = op('output1')

tabledat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tabledat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
