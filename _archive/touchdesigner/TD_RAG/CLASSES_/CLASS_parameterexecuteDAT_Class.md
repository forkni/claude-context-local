---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Parameter_Execute_DAT
- Panel_COMP
- Slider_COMP
- Button_COMP
concepts:
- event_driven_programming
- parameter_monitoring
- callback_systems
- parameter_change_detection
- automated_parameter_responses
- event_handling
- python_callbacks
- parameter_automation
- ui_event_handling
prerequisites:
- CLASS_DAT_Class
- Python_fundamentals
- parameter_concepts
- event_handling_concepts
- callback_programming
workflows:
- parameter_monitoring
- event_driven_automation
- ui_control_responses
- parameter_change_automation
- callback_programming
- automated_parameter_responses
- real_time_parameter_tracking
- interactive_systems
keywords:
- parameter execute dat class
- event handling
- parameter callbacks
- onValueChange
- onPulse
- onExpressionChange
- parameter events
- event driven scripting
- parameter automation
- callback functions
- parameter change detection
- automated responses
- ui control monitoring
tags:
- python
- api_reference
- event_driven
- parameter_monitoring
- callback_system
- automation
- ui_control
- real_time_monitoring
- parameter_events
- interactive
relationships:
  CLASS_DAT_Class: strong
  CLASS_Par_Class: strong
  CLASS_OP_Class: medium
  PY_Python_Tips: medium
related_docs:
- CLASS_DAT_Class
- CLASS_Par_Class
- CLASS_OP_Class
- PY_Python_Tips
hierarchy:
  secondary: event_handling
  tertiary: parameter_monitoring
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- parameter_monitoring
- event_driven_automation
- ui_control_responses
- parameter_change_automation
---

# parameterexecuteDAT Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Parameter_Execute_DAT, Panel_COMP, Slider_COMP, Button_COMP]
concepts: [event_driven_programming, parameter_monitoring, callback_systems, parameter_change_detection, automated_parameter_responses, event_handling, python_callbacks, parameter_automation, ui_event_handling]
prerequisites: [CLASS_DAT_Class, Python_fundamentals, parameter_concepts, event_handling_concepts, callback_programming]
workflows: [parameter_monitoring, event_driven_automation, ui_control_responses, parameter_change_automation, callback_programming, automated_parameter_responses, real_time_parameter_tracking, interactive_systems]
related: [CLASS_DAT_Class, CLASS_Par_Class, CLASS_OP_Class, PY_Python_Tips]
relationships: {
  "CLASS_DAT_Class": "strong",
  "CLASS_Par_Class": "strong",
  "CLASS_OP_Class": "medium",
  "PY_Python_Tips": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "event_handling"
  tertiary: "parameter_monitoring"
keywords: [parameter execute dat class, event handling, parameter callbacks, onValueChange, onPulse, onExpressionChange, parameter events, event driven scripting, parameter automation, callback functions, parameter change detection, automated responses, ui control monitoring]
tags: [python, api_reference, event_driven, parameter_monitoring, callback_system, automation, ui_control, real_time_monitoring, parameter_events, interactive]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: parameter_monitoring, event_driven_automation, ui_control_responses

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Class Dat Class] → [Python Fundamentals] → [Parameter Concepts]
**This document**: CLASS reference/guide
**Next steps**: [CLASS DAT Class] → [CLASS Par Class] → [CLASS OP Class]

**Related Topics**: parameter monitoring, event driven automation, ui control responses

## Summary

Event-driven callback system for parameter monitoring. Critical for responsive UI systems and automated parameter-based workflows.

## Relationship Justification

nherits from DAT class and works closely with Par class for parameter access. Connected to OP class for broad operator parameter monitoring. Links to Python Tips for practical callback examples and event-driven programming patterns.

## Content

- [Introduction](#introduction)
- [parameterexecuteDAT Specific](#parameterexecutedat-specific)
  - [Members](#members)
  - [Methods](#methods)
  - [Callbacks](#callbacks)
- [DAT Class](#dat-class)
  - [Members](#dat-members)
  - [Methods](#dat-methods)
    - [Script Execution](#script-execution)
    - [File Operations](#file-operations)
    - [Content Modification](#content-modification)
    - [Text Content](#text-content)
    - [Single Cell Modification](#single-cell-modification)
    - [Table Content Modification](#table-content-modification)
    - [Table Content Access](#table-content-access)
- [OP Class](#op-class)
  - [Members](#op-members)
    - [General](#general)
    - [Common Flags](#common-flags)
    - [Appearance](#appearance)
    - [Connection](#connection)
    - [Cook Information](#cook-information)
    - [Type](#type)
  - [Methods](#op-methods)
    - [General](#op-general)
    - [Errors](#errors)
    - [Appearance](#op-appearance)
    - [Viewers](#viewers)
    - [Storage](#storage)
    - [Miscellaneous](#miscellaneous)

## Introduction

This class inherits from the [CLASS_DAT] class. It references a specific [CLASS_ParameterExecuteDAT].

## parameterexecuteDAT Specific

### Members

No operator specific members.

### Methods

No operator specific methods.

### Callbacks

The following python callbacks are associated with this operator.

```python
# me - this DAT
# par - the Par object that has changed
# val - the current value
# prev - the previous value
# 
# Make sure the corresponding toggle is enabled in the Parameter Execute DAT.

def onValueChange(par, val, prev):
    return

def onPulse(par):
    return

def onExpressionChange(par, val, prev):
    return

def onExportChange(par, val, prev):
    return

def onEnableChange(par, val, prev):
    return

def onModeChange(par, val, prev):
    return
```

## DAT Class

### Members

#### export

export → bool:

Get or set Export Flag.

#### module

module → 'module' (Read Only):

Retrieve the contents of the DAT as a module. This allows for functions in the module to be called directly. E.g `n.module.function(arg1, arg2)`

#### numRows

numRows → int (Read Only):

Number of rows in the DAT table.

#### numCols

numCols → int (Read Only):

Number of columns in the DAT table.

#### text

text → str:

Get or set contents. Tables are treated as tab delimited columns, newline delimited rows.

#### editingFile

editingFile → str (Read Only):

The path to the current file used by external editors.

#### isTable

isTable → bool (Read Only):

True if the DAT contains table formatted data.

#### isText

isText → bool (Read Only):

True if the DAT contains text formatted data. (ie, not table formatted).

#### isEditable

isEditable → bool (Read Only):

True if the DAT contents can be edited (Text DATs, Table DATs, locked DATs etc).

#### isDAT

isDAT → bool (Read Only):

True if the operator is a DAT.

#### locals

locals → dict (Read Only):

Local dictionary used during python execution of scripts in this DAT. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with scripts, or with an Examine DAT.

#### jsonObject

jsonObject → dict (Read Only):

Parses the DAT as json and returns a python object.

#### I/O Methods

**flush()→ None**: Dummy function required to redirect stdout to DATs.

**isatty()→ False**: Required to redirect stdout to DATs.

### Methods

#### Script Execution

##### run()

run(arg1, arg2..., endFrame=False, fromOP=None, asParameter=False, group=None, delayFrames=0, delayMilliSeconds=0, delayRef=me)→ [CLASS_Run]:

Run the contents of the DAT as a script, returning a [CLASS_Run] object which can be used to optionally modify its execution.

- `arg` - (Optional) Arguments that will be made available to the script in a local tuple named args.
- `endFrame` - (Keyword, Optional) If set to True, the execution will be delayed until the end of the current frame.
- `fromOP` - (Keyword, Optional) Specifies an optional operator from which the execution will be run relative to.
- `asParameter` - (Keyword, Optional) When fromOP used, run relative to a parameter of fromOP.
- `group` - (Keyword, Optional) Can be used to specify a group label string. This label can then be used with the td.runs object to modify its execution.
- `delayFrames` - (Keyword, Optional) Can be used to delay the execution a specific amount of frames.
- `delayMilliSeconds` - (Keyword, Optional) Can be used to delay the execution a specific amount of milliseconds. This value is rounded to the nearest frame.
- `delayRef` - (Keyword, Optional) Specifies an optional operator which is controlled by a different Time Component. If your own local timeline is paused, you can point to another timeline to ensure this script will still execute for example.

```python
# grab DAT
n = op('text1')
# run the DAT
n.run()
# run the data with some arguments
r.run('firstArgIsString', secondArgIsVariable)
```

#### File Operations

##### save()

save(filepath, append=False, createFolders=False)→ str:

Saves the content of the DAT to the file system. Returns the file path that it was saved to.

- `filepath` - (Optional) The path and filename to save the file to. If this is not given then a default named file will be saved to project.folder
- `append` - (Keyword, Optional) If set to True and the format is txt, then the contents are appended to the existing file.
- `createFolders` - (Keyword, Optional) If True, it creates the not existent directories provided by the filepath.

```python
name = n.save() #save in native format with default name
n.save('output.txt') #human readable format without channel names
n.save('C:/Desktop/myFolder/output.txt', createFolders=True)  # supply file path and createFolder flag
```

##### write()

write(args)→ str:

Append content to this DAT. Can also be used to implement DAT printing functions.

```python
# grab DAT
n = op('text1')
# append message directly to DAT
n.write('Hello World')
# use print method
print('Hello World', file=n)
```

##### detectLanguage()

detectLanguage(setLanguage=False)→ str:

Returns the result of attempting to auto-detect the programming language in the DAT based on the contained text.

- `setLanguage` - (Keyword, Optional) If True sets the language parameters on the DAT appropriately

#### Content Modification

##### clear()

clear(keepSize=False, keepFirstRow=False, keepFirstCol=False)→ None:

Remove all rows and columns from the table.

- `keepSize` - (Keyword, Optional) If set to True, size is unchanged, but entries will be set to blank, dependent on other options below.
- `keepFirstRow` - (Keyword, Optional) If set to True, the first row of cells are retained.
- `keepFirstCol` - (Keyword, Optional) If set to True, the first column of cells are retained.

```python
n.clear() #remove all rows and columns
n.clear(keepSize=True) #set all table cells to blank
n.clear(keepFirstRow=True) #remove all rows, but keep the first
n.clear(keepFirstRow=True, keepFirstCol=True) #keep the first row, first column, and set remaining cells to blank
```

##### copy()

copy(DAT)→ None:

Copy the text or table from the specified DAT operator.

- `OP` - The DAT operator whose contents should be copied into the DAT.

#### Text Content

When the DAT is not a table, but a block of text, its contents can be simply accessed through its text member.

```python
t = op('merge1').text
op('text2').text = 'merge1 contains:' + t
op('text3').text = "Hello there!"
```

#### Single Cell Modification

Using DAT[row, column] where row, column specifies which cell to modify. The row and column may be integer numbers starting at 0, or strings which are the column names or row names (in row 0 or column 0 respectively):

```python
op('table1')['Monday',1] = 'day1'

tab = op('table1')
tab[0,0] = 'corner'
tab[1,'select'] = 'yes'
tab['Monday',1] = 'day1'
```

#### Table Content Modification

##### appendRow()

appendRow(vals, nameOrIndex, sort=None)→ int:

Append a row to the end of the table, or after the specified row name/index. Returns the integer index of the new row.

- `vals` - (Optional) If specified, will fill the row with the given values. It should be a list of items that can be expressed as strings. Each item will be copied to one cell.
- `nameOrIndex` - (Optional) If specified will determine where the new row will be appended. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
- `sort` - (Keyword, Optional) If specified will determine the column to keep sorted after the insertion. If it's a numeric value it represents the numeric index of the column. If it is a string it represents a column label.

```python
n.appendRow()
n.appendRow( [1,2,3], 'January' )  #append with values (1,2,3) after the row labelled 'January'
n.appendRow( [1,2,3], 5 )  #append row with values (1,2,3) after the row 5.
n.appendRow( [1,2,3], sort='Month' )  #append row with values (1,2,3) keeping column 'Month' sorted.
```

##### appendRows()

appendRows(vals, nameOrIndex, sort=None)→ int:

Append rows to the end of the table, or after the specified row name/index. Returns the integer of the last row appended.

- `vals` - (Optional) If specified, will fill the rows with the given values. It should be a list of lists of items that can be expressed as strings. Each item will be copied to one cell.
- `nameOrIndex` - (Optional) If specified will determine where the new row will be appended. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
- `sort` - (Keyword, Optional) If specified will determine the column to keep sorted after the insertion. If it's a numeric value it represents the numeric index of the column. If it is a string it represents a column label.

```python
n.appendRows()
n.appendRows( [[1,2,3],[4,5,6,7]], 'January' )  #after the row labelled 'January append 2 rows: first one with values (1,2,3), then one with values (4,5,6,7)
n.appendRows( [[1,2,3]], 5 )  # after row 5 append one row with values (1,2,3).
n.appendRows( [1,2,3] )  # append 3 rows with values 1, 2, 3 respectively.
```

##### appendCol()

appendCol(vals, nameOrIndex, sort=None)→ int:

Append a column to the end of the table. See appendRow for similar usage.

##### appendCols()

appendCols(vals, nameOrIndex, sort=None)→ int:

Append columns to the end of the table. See appendRows for similar usage.

##### insertRow()

insertRow(vals, nameOrIndex, sort=None)→ int:

Insert a row to the beginning of the table or before the specified row name/index. See [CLASS_DAT].appendRow() for similar usage.

##### insertCol()

insertCol(vals, nameOrIndex, sort=None)→ int:

Insert a column to the beginning of the table or before the specified row name/index. See [CLASS_DAT].appendRow() for similar usage.

##### replaceRow()

replaceRow(nameOrIndex, vals, entireRow=True)→ int:

Replaces the contents of an existing row.

- `nameOrIndex` - Specifies the row that will be replaced. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
- `vals` - (Optional) If specified, will overwrite the row with the given values. It should be a list of lists of items that can be expressed as strings. Each item will be copied to one cell.
- `entireRow` - (Keyword, Optional) If True, overwrites every cell in the specified row. If False, will only overwrite as many cells in the row as there are items in vals.

```python
n.replaceRow(0) # will empty all the cells in row 0 (ie. replaced with nothing)
n.replaceRow('January', ['January', 1,2,3])  # the row 'January' will be replaced with the list of 4 items.
n.replaceRow(2, [1,2,3], entireRow=False)  # at row 2 the 3 items will replace the first 3 items in the row.
```

##### replaceCol()

replaceCol(nameOrIndex, vals, entireCol=True)→ int:

Replaces the contents of an existing column. See [CLASS_DAT].replaceRow for similar usage.

##### deleteRow()

deleteRow(nameOrIndex)→ None:

Delete a single row at the specified row name or index.

- `nameOrIndex` - May be a string for a row name, or numeric index for rowindex.

##### deleteRows()

deleteRows(vals)→ None:

Deletes multiple rows at the row names or indices specified in vals.

- `vals` - If specified, will delete each row given. It should be a list of items that can be expressed as strings. If no vals is provided deleteRows does nothing.

##### deleteCol()

deleteCol(nameOrIndex)→ None:

Delete a single column at the specified column name or index.

- `nameOrIndex` - May be a string for a column name, or numeric index for column index.

##### deleteCols()

deleteCols(vals)→ None:

Deletes multiple columns at the column names or indices specified in vals.

- `vals` - If specified, will delete each column given. It should be a list of items that can be expressed as strings. If no vals is provided deleteCols does nothing.

##### setSize()

setSize(numrows, numcols)→ None:

Set the exact size of the table.

- `numrows` - The number of rows the table should have.
- `numcols` - The number of columns the table should have.

##### scroll()

scroll(row, col)→ None:

Bring current DAT viewers to the specified row and column.

- `row` - Row to scroll to.
- `col` - (Optional) Column to scroll to for tables.

#### Table Content Access

##### [rowNameOrIndex, colNameOrIndex]

[rowNameOrIndex, colNameOrIndex]→ [CLASS_Cell]:

Cells in a table may be accessed with the [] subscript operator.

The NameOrIndex may be an exact string name, or it may be a numeric index value. [REF_PatternMatching] is not supported.

- `rowNameOrIndex` - If a string it specifies a row name, if it's numeric it specifies a row index.
- `colNameOrIndex` - If a string it specifies a column name, if it's numeric it specifies a column index.

```python
c = n[4, 'June']
c = n[3, 4]
```

##### cell()

cell(rowNameOrIndex, colNameOrIndex, caseSensitive=True, val=False)→ [CLASS_Cell] | str | None:

Find a single cell in the table, or None if none are found.

- `rowNameOrIndex`/`colNameOrIndex` - If a string it specifies a row/column name. If it's numeric it specifies a row/column index. [REF_PatternMatching] is supported for strings.
- `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
- `val` - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of [CLASS_Cell] items.

```python
c = n.cell(5, 'June') #Return a cell under row 5, column 'June'.
c = n.cell('A*', 2) #Find a cell under any row beginning with an A, in column 2.
c = n.cell('A*', 2, val=True) #Return the str type of the found cell
```

##### cells()

cells(rowNameOrIndex, colNameOrIndex, caseSensitive=True, val=False)→ list:

Returns a (possibly empty) list of cells that match the given row/column names or indices. See [CLASS_DAT].cell method for similar usage.

##### findCell()

findCell(pattern, rows=None, cols=None, valuePattern=True, rowPattern=True, colPattern=True, caseSensitive=False, val=False)→ [CLASS_Cell] | str | None:

Returns a cell that matches the given pattern and row/column names or indices or None if no match is found.

- `pattern` - The pattern to match a cell.
- `rows` - (Keyword, Optional) If specified, looks for cell only in the specified rows. Must be specified as a list.
- `cols` - (Keyword, Optional) If specified, looks for cell only in the specified columns. Must be specified as a list.
- `valuePattern`, `rowPattern`, `colPattern` - (Keyword, Optional) If specified and set to False, disables pattern matching for a cell, rows or columns.
- `caseSensitive` - (Keyword, Optional) Cell matching is case sensitive if set to true.
- `val` - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of [CLASS_Cell] items.

##### findCells()

findCells(pattern, rows=None, cols=None, valuePattern=True, rowPattern=True, colPattern=True, val=False)→ list:

Returns a (possibly empty) list of cells that match the given patterns and row/column names or indices.

##### row()

row(*nameOrIndexes, caseSensitive=True, val=False)→ List[[CLASS_Cell]]:

Returns a list of cells from the first row matching the name/index, or None if nothing is found.

- `nameOrIndexes` - Include any number of these. If a string it specifies a row name, if it's numeric it specifies a row index. [REF_PatternMatching] is supported.
- `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
- `val` - (Optional) If set to true, returns list of cell item strings instead of list of [CLASS_Cell] items.

```python
r = op('table1').row(3, caseSensitive=False)
r = op('table1').row('June')
r = op('table1').row('A*', 'B*') #returns first row beginning with A or B
r = op('table1').row('June', val=True) #returns list of all strings stored under the row 'June'
```

##### rows()

rows(*nameOrIndexes, caseSensitive=True, val=False)→ List[List[[CLASS_Cell]]]:

Returns a (possibly empty) list of rows (each row being a list of cells). If no arguments are given it returns all rows in the table.

- `nameOrIndexes` - (Optional) Include any number of these. If a string it specifies a row name, if it's numeric it specifies a row index. [REF_PatternMatching] is supported.
- `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
- `val` - (Optional) If set to true, returns list of cell item strings instead of list of [CLASS_Cell] items.

```python
for r in op('table1').rows():
    # do something with row 'r'

for r in op('table1').rows(val=True):
    # do something with the strings values of the row 'r'
```

##### col()

col(*nameOrIndexes, caseSensitive=True, val=False)→ list:

Returns a list of cells from the first col matching the name/index, or None if nothing is found.

- `nameOrIndexes` - Include any number of these. If a string it specifies a column name, if it's numeric it specifies a column index. [REF_PatternMatching] is supported.
- `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
- `val` - (Optional) If set to true, returns list of cell item strings instead of list of [CLASS_Cell] items.

```python
r = op('table1').col(3, caseSensitive=False)
r = op('table1').col('June')
r = op('table1').col('A*', 'B*') #returns first column beginning with A or B
r = op('table1').col('June', val=True) #returns list of all strings stored under the column 'June'
```

##### cols()

cols(*nameOrIndexes, caseSensitive=True, val=False)→ List[List[[CLASS_Cell]]]:

Returns a (possibly empty) list of columns (each being a list themselves). If no arguments are given then all columns in the table are returned.

- `nameOrIndexes` - (Optional) Include any number of these. If a string it specifies a column name, if it's numeric it specifies a column index. [REF_PatternMatching] is supported.
- `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
- `val` - (Optional) If set to true, returns list of cell item strings instead of list of [CLASS_Cell] items.

```python
for c in op('table1').cols():
    # do something with each column 'c'

for c in op('table1').cols(val=True):
    # do something with the string values in each column 'c'
```

## OP Class

### Members

#### General

**valid** → bool (Read Only): True if the referenced operator currently exists, False if it has been deleted.

**id** → int (Read Only): Unique id for the operator. This id can also be passed to the op() and ops() methods. Id's are not consistent when a file is re-opened, and will change if the OP is copied/pasted, changes OP types, deleted/undone. The id will not change if the OP is renamed though. Its data type is integer.

**name** → str: Get or set the operator name.

**path** → str (Read Only): Full path to the operator.

**digits** → int (Read Only): Returns the numeric value of the last consecutive group of digits in the name, or None if not found. The digits can be in the middle of the name if there are none at the end of the name.

**base** → str (Read Only): Returns the beginning portion of the name occurring before any digits.

**passive** → bool (Read Only): If true, operator will not cook before its access methods are called. To use a passive version of an operator n, use passive(n).

**curPar** → [CLASS_Par] (Read Only): The parameter currently being evaluated. Can be used in a parameter expression to reference itself. An easy way to see this is to put the expression curPar.name in any string parameter.

**curBlock** → (Read Only): The SequenceBlock of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

**curSeq** → [CLASS_Sequence] (Read Only): The Sequence of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

**time** → [CLASS_OP] (Read Only): Time Component that defines the operator's time reference.

**ext** → class (Read Only): The object to search for parent extensions. Example: `me.ext.MyClass`

**fileFolder** → str (Read Only): Returns the folder where this node is saved.

**filePath** → str (Read Only): Returns the file location of this node.

**mod** → mod (Read Only): Get a module on demand object that searches for DAT modules relative to this operator.

**pages** → list (Read Only): A list of all built-in pages.

**parGroup** → tuple (Read Only): An intermediate parameter collection object, from which a specific parameter group can be found. Example: `n.parGroup.t` or `n.parGroup['t']`

**par** → [CLASS_Par] (Read Only): An intermediate parameter collection object, from which a specific parameter can be found. Example: `n.par.tx` or `n.par['tx']`

**builtinPars** → list or par (Read Only): A list of all built-in parameters.

**customParGroups** → list of parGroups (Read Only): A list of all ParGroups, where a ParGroup is a set of parameters all drawn on the same line of a dialog, sharing the same label.

**customPars** → list of par (Read Only): A list of all custom parameters.

**customPages** → list (Read Only): A list of all custom pages.

**replicator** → [CLASS_OP] or None (Read Only): The replicatorCOMP that created this operator, if any.

**storage** → dict (Read Only): Storage is dictionary associated with this operator. Values stored in this dictionary are persistent, and saved with the operator. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with methods such as [CLASS_OP].fetch() or [CLASS_OP].store() described below, or examined with an Examine DAT.

**tags** → list: Get or set a set of user defined strings. Tags can be searched using [CLASS_OP].findChildren() and the OP Find DAT.

**children** → list (Read Only): A list of operators contained within this operator. Only component operators have children, otherwise an empty list is returned.

**numChildren** → int (Read Only): Returns the number of children contained within the operator. Only component operators have children.

**numChildrenRecursive** → int (Read Only): Returns the number of operators contained recursively within this operator. Only component operators have children.

**op** → [CLASS_OP] or None (Read Only): The operator finder object, for accessing operators through paths or shortcuts.

**opex** → [CLASS_OP] (Read Only): An operator finder object, for accessing operators through paths or shortcuts. Works like the op() shortcut method, except it will raise an exception if it fails to find the node instead of returning None as op() does.

**parent** → Shortcut (Read Only): The Parent Shortcut object, for accessing parent components through indices or shortcuts.

**iop** → [CLASS_OP] (Read Only): The Internal Operator Shortcut object, for accessing internal shortcuts. See also [REF_InternalOperators].

**ipar** → ParCollection (Read Only): The Internal Operator Parameter Shortcut object, for accessing internal shortcuts. See also [REF_InternalParameters].

**currentPage** → [CLASS_Page]: Get or set the currently displayed parameter page. It can be set by setting it to another page or a string label.

#### Common Flags

**activeViewer** → bool: Get or set Viewer Active Flag.

**allowCooking** → bool: Get or set Cooking Flag. Only COMPs can disable this flag.

**bypass** → bool: Get or set Bypass Flag.

**cloneImmune** → bool: Get or set Clone Immune Flag.

**current** → bool: Get or set Current Flag.

**display** → bool: Get or set Display Flag.

**expose** → bool: Get or set the Expose Flag which hides a node from view in a network.

**lock** → bool: Get or set Lock Flag.

**selected** → bool: Get or set Selected Flag. This controls if the node is part of the network selection. (yellow box around it).

**seq** → (Read Only): An intermediate sequence collection object, from which a specific sequence group can be found.

**python** → bool: Get or set parameter expression language as python.

**render** → bool: Get or set Render Flag.

**showCustomOnly** → bool: Get or set the Show Custom Only Flag which controls whether or not non custom parameters are display inparameter dialogs.

**showDocked** → bool: Get or set Show Docked Flag. This controls whether this node is visible or hidden when it is docked to another node.

**viewer** → bool: Get or set Viewer Flag.

#### Appearance

**color** → tuple(r, g, b): Get or set color value, expressed as a 3-tuple, representing its red, green, blue values. To convert between color spaces, use the built in colorsys module.

**comment** → str: Get or set comment string.

**nodeHeight** → int: Get or set node height, expressed in network editor units.

**nodeWidth** → int: Get or set node width, expressed in network editor units.

**nodeX** → int: Get or set node X value, expressed in network editor units, measured from its left edge.

**nodeY** → int: Get or set node Y value, expressed in network editor units, measured from its bottom edge.

**nodeCenterX** → int: Get or set node X value, expressed in network editor units, measured from its center.

**nodeCenterY** → int: Get or set node Y value, expressed in network editor units, measured from its center.

**dock** → [CLASS_OP]: Get or set the operator this operator is docked to. To clear docking, set this member to None.

**docked** → list (Read Only): The (possibly empty) list of operators docked to this node.

#### Connection

**inputs** → list (Read Only): List of input operators (via left side connectors) to this operator. To get the number of inputs, use len(OP.inputs).

**outputs** → list (Read Only): List of output operators (via right side connectors) from this operator.

**inputConnectors** → list (Read Only): List of input connectors (on the left side) associated with this operator.

**outputConnectors** → list (Read Only): List of output connectors (on the right side) associated with this operator.

#### Cook Information

**cookFrame** → float (Read Only): Last frame at which this operator cooked.

**cookTime** → float (Read Only): Deprecated Duration of the last measured cook (in milliseconds).

**cpuCookTime** → float (Read Only): Duration of the last measured cook in CPU time (in milliseconds).

**cookAbsFrame** → float (Read Only): Last absolute frame at which this operator cooked.

**cookStartTime** → float (Read Only): Last offset from frame start at which this operator cook began, expressed in milliseconds.

**cookEndTime** → float (Read Only): Last offset from frame start at which this operator cook ended, expressed in milliseconds. Other operators may have cooked between the start and end time. See the cookTime member for this operator's specific cook duration.

**cookedThisFrame** → bool (Read Only): True when this operator has cooked this frame.

**cookedPreviousFrame** → bool (Read Only): True when this operator has cooked the previous frame.

**childrenCookTime** → float (Read Only): Deprecated The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenCPUCookTime** → float (Read Only): The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenCookAbsFrame** → float (Read Only): Deprecated The absolute frame on which childrenCookTime is based.

**childrenCPUCookAbsFrame** → float (Read Only): The absolute frame on which childrenCPUCookTime is based.

**gpuCookTime** → float (Read Only): Duration of GPU operations during the last measured cook (in milliseconds).

**childrenGPUCookTime** → float (Read Only): The total accumulated GPU cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenGPUCookAbsFrame** → float (Read Only): The absolute frame on which childrenGPUCookTime is based.

**totalCooks** → int (Read Only): Number of times the operator has cooked.

**cpuMemory** → int (Read Only): The approximate amount of CPU memory this Operator is using, in bytes.

**gpuMemory** → int (Read Only): The amount of GPU memory this OP is using, in bytes.

#### Type

**type** → str (Read Only): Operator type as a string. Example: 'oscin'.

**subType** → str (Read Only): Operator subtype. Currently only implemented for components. May be one of: 'panel', 'object', or empty string in the case of base components.

**OPType** → str (Read Only): Python operator class type, as a string. Example: 'oscinCHOP'. Can be used with COMP.create() method.

**label** → str (Read Only): Operator type label. Example: 'OSC In'.

**icon** → str (Read Only): Get the letters used to create the operator's icon.

**family** → str (Read Only): Operator family. Example: CHOP. Use the global dictionary families for a list of each operator type.

**isFilter** → bool (Read Only): True if operator is a filter, false if it is a generator.

**minInputs** → int (Read Only): Minimum number of inputs to the operator.

**maxInputs** → int (Read Only): Maximum number of inputs to the operator.

**isMultiInputs** → bool (Read Only): True if inputs are ordered, false otherwise. Operators with an arbitrary number of inputs have unordered inputs, example Merge CHOP.

**visibleLevel** → int (Read Only): Visibility level of the operator. For example, expert operators have visibility level 1, regular operators have visibility level 0.

**isBase** → bool (Read Only): True if the operator is a Base (miscellaneous) component.

**isCHOP** → bool (Read Only): True if the operator is a CHOP.

**isCOMP** → bool (Read Only): True if the operator is a component.

**isDAT** → bool (Read Only): True if the operator is a DAT.

**isMAT** → bool (Read Only): True if the operator is a Material.

**isObject** → bool (Read Only): True if the operator is an object.

**isPanel** → bool (Read Only): True if the operator is a Panel.

**isSOP** → bool (Read Only): True if the operator is a SOP.

**isTOP** → bool (Read Only): True if the operators is a TOP.

**licenseType** → str (Read Only): Type of License required for the operator.

### Methods

#### General

**NOTE**: create(), copy() and copyOPs() is done by the parent operator (a component). For more information see [CLASS_COMP].create, [CLASS_COMP].copy and [CLASS_COMP].copyOPs methods.

**pars(pattern)→ list**: Returns a (possibly empty) list of parameter objects that match the pattern.

**cook(force=False, recurse=False, includeUtility=False)→ None**: Cook the contents of the operator if required.

**copyParameters(OP, custom=True, builtin=True)→ None**: Copy all of the parameters from the specified operator. Both operators should be the same type.

**changeType(OPtype)→ OP**: Change referenced operator to a new operator type. After this call, this OP object should no longer be referenced. Instead use the returned OP object.

**dependenciesTo(OP)→ list**: Returns a (possibly empty) list of operator dependency paths between this operator and the specified operator. Multiple paths may be found.

**evalExpression(str)→ value**: Evaluate the expression from the context of this OP. Can be used to evaluate arbitrary snippets of code from arbitrary locations.

**destroy()→ None**: Destroy the operator referenced by this OP. An exception will be raised if the OP's operator has already been destroyed.

**var(name, search=True)→ str**: Evaluate avariable. This will return the empty string, if not found. Most information obtained from variables (except for Root and Component variables) are accessible through other means in Python, usually in the global td module.

**openMenu(x=None, y=None)→ None**: Open a node menu for the operator at x, y. Opens at mouse if x & y are not specified.

**relativePath(OP)→ str**: Returns the relative path from this operator to the OP that is passed as the argument. See [CLASS_OP].shortcutPath for a version using expressions.

**setInputs(listOfOPs)→ None**: Set all the operator inputs to the specified list.

**shortcutPath(OP, toParName=None)→ str**: Returns an expression from this operator to the OP that is passed as the argument. See [CLASS_OP].relativePath for a version using relative path constants.

**ops(pattern1, pattern2.., includeUtility=False)→ list of OPs**: Returns a (possibly empty) list of OPs that match the patterns, relative to the inside of this OP.

**resetPars(parNames='*', parGroupNames='*', pageNames='*', includeBuiltin=True, includeCustom=True)→ bool**: Resets the specified parameters in the operator.

#### Errors

**addScriptError(msg)→ None**: Adds a script error to a node.

**addError(msg)→ None**: Adds an error to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

**addWarning(msg)→ None**: Adds a warning to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

**errors(recurse=False)→ str**: Get error messages associated with this OP.

**warnings(recurse=False)→ str**: Get warning messages associated with this OP.

**scriptErrors(recurse=False)→ str**: Get script error messages associated with this OP.

**clearScriptErrors(recurse=False, error='*')→ None**: Clear any errors generated during script execution. These may be generated during execution of DATs, Script Nodes, Replicator COMP callbacks, etc.

**childrenCPUMemory()→ int**: Returns the total CPU memory usage for all the children from this COMP.

**childrenGPUMemory()→ int**: Returns the total GPU memory usage for all the children from this COMP.

#### Appearance

**resetNodeSize()→ None**: Reset the node tile size to its default width and height.

#### Viewers

**closeViewer(topMost=False)→ None**: Close the floating content viewers of the OP.

**openViewer(unique=False, borders=True)→ None**: Open a floating content viewer for the OP.

**resetViewer(recurse=False)→ None**: Reset the OP content viewer to default view settings.

**openParameters()→ None**: Open a floating dialog containing the operator parameters.

#### Storage

Storage can be used to keep data within components. Storage is implemented as one python dictionary per node.

When an element of storage is changed by using n.store() as explained below, expressions and operators that depend on it will automatically re-cook. It is retrieved with the n.fetch() function.

Storage is saved in .toe and .tox files and restored on startup.

Storage can hold any python object type (not just strings as in Tscript variables). Storage elements can also have optional startup values, specified separately. Use these startup values for example, to avoid saving and loading some session specific object, and instead save or load a well defined object like None.

See the Examine DAT for procedurally viewing the contents of storage.

**fetch(key, default, search=True, storeDefault=False)→ value**: Return an object from the OP storage dictionary. If the item is not found, and a default it supplied, it will be returned instead.

**fetchOwner(key)→ OP**: Return the operator which contains the stored key, or None if not found.

**store(key, value)→ value**: Add the key/value pair to the OP's storage dictionary, or replace it if it already exists. If this value is not intended to be saved and loaded in the toe file, it can be be given an alternate value for saving and loading, by using the method storeStartupValue described below.

**unstore(keys1, keys2..)→ None**: For key, remove it from the OP's storage dictionary. Pattern Matching is supported as well.

**storeStartupValue(key, value)→ None**: Add the key/value pair to the OP's storage startup dictionary. The storage element will take on this value when the file starts up.

**unstoreStartupValue(keys1, keys2..)→ None**: For key, remove it from the OP's storage startup dictionary. Pattern Matching is supported as well. This does not affect the stored value, just its startup value.

#### Miscellaneous

****getstate**()→ dict**: Returns a dictionary with persistent data about the object suitable for pickling and deep copies.

****setstate**()→ dict**: Reads the dictionary to update persistent details about the object, suitable for unpickling and deep copies.
