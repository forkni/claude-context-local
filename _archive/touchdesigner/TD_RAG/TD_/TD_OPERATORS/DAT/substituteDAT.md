# DAT substituteDAT

## Overview

The Substitute DAT changes the cells of the incoming DAT using pattern matching and substitution strings.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `before` | Before | Str | Search term to replace. The following special characters may be used:   * - match any number of characters     ? - match a single character     [] - match any character defined within the brackets ... |
| `after` | After | Str | The replacement term. This replaces everything matched in the search term. Spaces are permitted. |
| `match` | Match | Menu | Specify where to match: |
| `case` | Case Sensitive | Toggle | Respect case sensitivity in search term. |
| `expand` | Expand the From String | Toggle | Expand variables and back quotes in the From string. |
| `expandto` | Expand the To String | Toggle | Expand variables and back quotes in the To string. |
| `first` | First Match Only | Toggle | Replaces only the first instance of the matching string. |
| `xfirstrow` | Exclude First Row | Toggle | Forces the first row to be ignored even if it is not specified by the Select Rows settings. |
| `xfirstcol` | Exclude First Col | Toggle | Forces the first column to be ignored even if it is not specified by the Select Cols settings. |
| `extractrows` | Select Rows | Menu | This parameter allows you to pick different ways of specifying the rows scoped. |
| `rownamestart` | Start Row Name | Str | Specify the row name to start the scope range from. |
| `rowindexstart` | Start Row Index | Int | Specify the row index to start the scope range from. |
| `rownameend` | End Row Name | Str | Specify the row name to end the scope range. |
| `rowindexend` | End Row Index | Int | Specify the row index to end the scope range. |
| `rownames` | Row Select Values | Str | Specify actual row names that you want to scope. You can use pattern matching, for example row[1-4] will scope all the rows names row1 thru row4. |
| `rowexpr` | Row Select Condition | Str | Specify an expression that will be evaluated.  If the expression evaluates to true, the row will be selected.        Expand the parameter and you will see that it is in expression mode.          Fi... |
| `fromcol` | From Column | Int | When selecting rows by values, this parameter selects which column to use when matching cell values to Selected Row Values to determine which rows are scoped. |
| `extractcols` | Select Cols | Menu | This parameter allows you to pick different ways of specifying the columns scoped. |
| `colnamestart` | Start Col Name | Str | Specify the column name to start the scope range from. |
| `colindexstart` | Start Col Index | Int | Specify the column index to start the scope range from. |
| `colnameend` | End Col Name | Str | Specify the column name to end the scope range. |
| `colindexend` | End Col Index | Int | Specify the column index to end the scope range. |
| `colnames` | Col Select Values | Str | Specify actual column names that you want to scope. You can use pattern matching, for example colvalue[1-4] will scope all the columns named colvalue1 thru colvalue4. |
| `colexpr` | Col Select Condition | Str | Specify an expression that will be evaluated. If the expression evaluates to true, the column will be scoped. See Row Select Condition for more details. |
| `fromrow` | From Row | Int | When scoping columns by Specified Names, this parameter selects which row to use when matching cell values to Selected Col Values to determine which columns are scoped. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT substituteDAT operator
substitutedat_op = op('substitutedat1')

# Get/set parameters
freq_value = substitutedat_op.par.active.eval()
substitutedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
substitutedat_op = op('substitutedat1')
output_op = op('output1')

substitutedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(substitutedat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **29** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
