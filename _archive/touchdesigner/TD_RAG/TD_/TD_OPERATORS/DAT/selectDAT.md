# DAT selectDAT

## Overview

The Select DAT allows you to fetch a DAT from any other location in the project, and to select any subset of rows and columns if it is a table.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `dat` | DAT | DAT | The path of the DAT being referenced. |
| `firstrow` | Include First Row | Toggle | Forces the first row to be selected even if it is not specified by the Select Rows settings. |
| `firstcol` | Include First Col | Toggle | Forces the first column to be selected even if it is not specified by the Select Cols settings. |
| `extractrows` | Select Rows | Menu | This parameter allows you to pick different ways of specifying the rows selected. |
| `rownamestart` | Start Row Name | Str | Specify the row name to start the selection range from. |
| `rowindexstart` | Start Row Index | Int | Specify the row index to start the selection range from. |
| `rownameend` | End Row  Name | Str | Specify the row name to end the selection range. |
| `rowindexend` | End Row Index | Int | Specify the row index to end the selection range. |
| `rownames` | Row Select Values | Str | Specify actual row names that you want to select. You can use TouchDesigner's pattern matching (see wiki page Pattern Matching), for example row[1-4] will select all the rows names row1 thru row4. ... |
| `rowexpr` | Row Select Condition | Str | Specify an expression that will be evaluated.  If the expression evaluates to true, the row will be selected.        Expand the parameter and you will see that it is in expression mode.          Fi... |
| `fromcol` | From Column | Int | When selecting rows by values, this parameter selects which column to use when matching cell values to Selected Row Values to determine which rows are selected. |
| `extractcols` | Select Cols | Menu | This parameter allows you to pick different ways of specifying the columns selected. |
| `colnamestart` | Start Col Name | Str | Specify the column name to start the selection range from. |
| `colindexstart` | Start Col Index | Int | Specify the column index to start the selection range from. |
| `colnameend` | End Col Name | Str | Specify the column name to end the selection range. |
| `colindexend` | End Col Index | Int | Specify the column index to end the selection range. |
| `colnames` | Col Select Values | Str | Specify actual column names that you want to select. You can use TouchDesigner's pattern matching  (see wiki page Pattern Matching), for example colvalue[1-4] will select all the columns named colv... |
| `colexpr` | Col Select Condition | Str | Specify an expression that will be evaluated. If the expression evaluates to true, the column will be selected. See Row Select Condition for more details. |
| `fromrow` | From Row | Int | When extracting columns by Specified Names, this parameter selects which row to use when matching cell values to Selected Col Values to determine which columns are selected. |
| `output` | Output | Menu | Determines what format will be used for output from the DAT. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT selectDAT operator
selectdat_op = op('selectdat1')

# Get/set parameters
freq_value = selectdat_op.par.active.eval()
selectdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
selectdat_op = op('selectdat1')
output_op = op('output1')

selectdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(selectdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
