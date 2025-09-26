# CHOP dattoCHOP

## Overview

The DAT to CHOP will create a set of CHOP channels with values derived from a DAT.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `dat` | DAT | DAT | The DAT to be used to retrieve values. This DAT should be in table format. For table format, use either a Table DAT or a Convert DAT set to To Table. |
| `extractrows` | Select Rows | Menu | This parameter allows you to pick different ways of specifying the rows selected. |
| `rownamestart` | Start Row Name | Str | Specify the row name to start the selection range from. |
| `rowindexstart` | Start Row Index | Int | Specify the row index to start the selection range from. |
| `rownameend` | End Row  Name | Str | Specify the row name to end the selection range. |
| `rowindexend` | End Row Index | Int | Specify the row index to end the selection range. |
| `rownames` | Row Select Values | Str | Specify actual row names that you want to select. You can use pattern matching, for example row[1-4] will select all the rows names row1 thru row4. |
| `rowexpr` | Row Select Condition | Str | Specify an expression that will be evaluated. If the expression evaluates to true, the row will be selected. Expand the parameter and you will see that it is in expression mode.  File:SelectDAT_row... |
| `fromcol` | From Column | Int | When selecting rows by values, this parameter selects which column to use when matching cell values to Selected Row Values to determine which rows are selected. |
| `extractcols` | Select Cols | Menu | This parameter allows you to pick different ways of specifying the columns selected. |
| `colnamestart` | Start Col Name | Str | Specify the column name to start the selection range from. |
| `colindexstart` | Start Col Index | Int | Specify the column index to start the selection range from. |
| `colnameend` | End Col Name | Str | Specify the column name to end the selection range. |
| `colindexend` | End Col Index | Int | Specify the column index to end the selection range. |
| `colnames` | Col Select Values | Str | Specify actual column names that you want to select. You can use pattern matching, for example colvalue[1-4] will select all the columns named colvalue1 thru colvalue4. |
| `colexpr` | Col Select Condition | Str | Specify an expression that will be evaluated. If the expression evaluates to true, the column will be selected. See Row Select Condition for more details. |
| `fromrow` | From Row | Int | When extracting columns by Specified Names, this parameter selects which row to use when matching cell values to Selected Col Values to determine which columns are selected. |
| `output` | Output | Menu | Specify the form of the channels output. |
| `firstrow` | First Row is | Menu | Specifies whether the first row is ignored, names, or values. |
| `firstcolumn` | First Column is | Menu | Specifies whether the first columnn is ignored, names, or values. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP dattoCHOP operator
dattochop_op = op('dattochop1')

# Get/set parameters
freq_value = dattochop_op.par.active.eval()
dattochop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
dattochop_op = op('dattochop1')
output_op = op('output1')

dattochop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(dattochop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
