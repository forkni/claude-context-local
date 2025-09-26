---
title: "scriptDAT Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "automation_specialist", "technical_artist", "intermediate_user"]
completion_signals: ["can_access_scriptdat_properties", "understands_python_scripting", "can_implement_callback_functions", "manages_custom_parameters"]

operators:
- Script_DAT
- Text_DAT
- Table_DAT
- Parameter_Execute_DAT
- Examine_DAT
concepts:
- python_scripting
- data_manipulation
- table_operations
- custom_parameters
- callback_functions
- script_execution
- data_containers
- parameter_pages
prerequisites:
- Python_fundamentals
- CLASS_DAT_Class
- MODULE_td_Module
workflows:
- data_processing
- custom_parameter_creation
- table_manipulation
- script_execution
- callback_programming
- data_generation
- custom_component_development
keywords:
- scriptDAT
- python api
- dat scripting
- table manipulation
- custom parameters
- callbacks
- onCook
- onSetupParameters
- onPulse
- script execution
- data containers
- appendCustomPage
tags:
- python
- class_inheritance
- api_documentation
- data_structures
- callbacks
- real_time
- script_dat
- custom_parameters
relationships:
  CLASS_DAT_Class: strong
  CLASS_Page_Class: strong
  PY_Working_with_DATs_in_Python: strong
  MODULE_td_Module: strong
related_docs:
- CLASS_DAT_Class
- CLASS_Page_Class
- PY_Working_with_DATs_in_Python
- MODULE_td_Module
# Enhanced search optimization
search_optimization:
  primary_keywords: ["scriptdat", "python", "script", "callback"]
  semantic_clusters: ["python_scripting", "data_manipulation", "callback_programming"]
  user_intent_mapping:
    beginner: ["what is scriptdat", "basic dat scripting", "how to use script dat"]
    intermediate: ["callback functions", "custom parameters", "data processing"]
    advanced: ["complex scripting", "advanced callbacks", "custom component development"]

hierarchy:
  secondary: operator_classes
  tertiary: script_dat
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- data_processing
- custom_parameter_creation
- table_manipulation
- script_execution
---

# scriptDAT Class, DAT Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_DAT, Text_DAT, Table_DAT, Parameter_Execute_DAT, Examine_DAT]
concepts: [python_scripting, data_manipulation, table_operations, custom_parameters, callback_functions, script_execution, data_containers, parameter_pages]
prerequisites: [Python_fundamentals, CLASS_DAT_Class, MODULE_td_Module]
workflows: [data_processing, custom_parameter_creation, table_manipulation, script_execution, callback_programming, data_generation, custom_component_development]
related: [CLASS_DAT_Class, CLASS_Page_Class, PY_Working_with_DATs_in_Python, MODULE_td_Module]
relationships: {
  "CLASS_DAT_Class": "strong",
  "CLASS_Page_Class": "strong",
  "PY_Working_with_DATs_in_Python": "strong",
  "MODULE_td_Module": "strong"
}
hierarchy:
  primary: "scripting"
  secondary: "operator_classes"
  tertiary: "script_dat"
keywords: [scriptDAT, python api, dat scripting, table manipulation, custom parameters, callbacks, onCook, onSetupParameters, onPulse, script execution, data containers, appendCustomPage]
tags: [python, class_inheritance, api_documentation, data_structures, callbacks, real_time, script_dat, custom_parameters]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: data_processing, custom_parameter_creation, table_manipulation

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Class Dat Class] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [CLASS DAT Class] → [CLASS Page Class] → [PY Working with DATs in Python]

**Related Topics**: data processing, custom parameter creation, table manipulation

## Summary

Specialized class documentation for Script DATs extending the base DAT class. Essential for understanding callback-based programming and custom parameter creation.

## Relationship Justification

Strong connections to base DAT class, Page class for custom parameters, and practical DAT usage guide. Links to td module as foundational requirement. This class inherits from the DAT class. It references a specific Script DAT.

## Contents

- [1. Members](#members)
- [2. Methods](#methods)
- [3. Callbacks](#callbacks)
- [4. DAT Class](#dat-class)
  - [4.1. Members](#members-1)
  - [4.2. Methods](#methods-1)
    - [4.2.1. Modifying Content](#modifying-content)
    - [4.2.2. Modifying Text Content](#modifying-text-content)
    - [4.2.3. Modifying a Single Cell of a Table](#modifying-a-single-cell-of-a-table)
    - [4.2.4. Modifying Table Content](#modifying-table-content)
    - [4.2.5. Accessing Table Content](#accessing-table-content)

## Members

No operator specific members.

## Methods

These methods can be used by including them in the onCook() callback of the Script DAT. Using them outside the callback may cause unexpected results.

appendCustomPage(name)→ Page:

Add a new page of custom parameters. See Page Class for more details.

page = scriptOp.appendCustomPage('Custom1')
page.appendFloat('X1')
destroyCustomPars()→ int:

Remove all custom parameters from the Script DAT. Returns number of destroyed pars.

sortCustomPages(*pages)→ None:

Reorder custom parameter pages.

pages - any number of page names in their new order
scriptOp.sortPages('Definition','Controls')

## Callbacks

The following python callbacks are associated with this operator.

```python
# me - this DAT
# scriptOp - the OP which is cooking
# press 'Setup Parameters' in the OP to call this function to re-create the parameters

def onSetupParameters(scriptOp):
 page = scriptOp.appendCustomPage('Custom')
 p = page.appendFloat('Valuea', label='Value A')
 p = page.appendFloat('Valueb', label='Value B')
 return

# called whenever custom pulse parameter is pushed
def onPulse(par):
 return

def onCook(scriptOp):
 scriptOp.clear()

 #scriptOp.copy(scriptOp.inputs[0]) # no need to call .clear() above when copying
 #scriptOp.insertRow(['color', 'size', 'shape'], 0)
 #scriptOp.appendRow(['red', '3', 'square'])
 #scriptOp[1,0] += '**'

 return
```

## DAT Class

### Members

export → bool :

Get or set Export Flag

module → 'module' (Read Only):

Retrieve the contents of the DAT as a module. This allows for functions in the module to be called directly. E.g n.module.function(arg1, arg2)

numRows → int (Read Only):

Number of rows in the DAT table.

numCols → int (Read Only):

Number of columns in the DAT table.

text → str :

Get or set contents. Tables are treated as tab delimited columns, newline delimited rows.

editingFile → str (Read Only):

The path to the current file used by external editors.

isTable → bool (Read Only):

True if the DAT contains table formatted data.

isText → bool (Read Only):

True if the DAT contains text formatted data. (ie, not table formatted).

isEditable → bool (Read Only):

True if the DAT contents can be edited (Text DATs, Table DATs, locked DATs etc).

isDAT → bool (Read Only):

True if the operator is a DAT.

locals → dict (Read Only):

Local dictionary used during python execution of scripts in this DAT. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with scripts, or with an Examine DAT.

jsonObject → dict (Read Only):

Parses the DAT as json and returns a python object.

flush()→ None:

Dummy function required to redirect stdout to DATs.

isatty()→ False:

Required to redirect stdout to DATs.

Methods
run(arg1, arg2..., endFrame=False, fromOP=None, asParameter=False, group=None, delayFrames=0, delayMilliSeconds=0, delayRef=me)→ td.Run:

Run the contents of the DAT as a script, returning a Run object which can be used to optionally modify its execution.

arg - (Optional) Arguments that will be made available to the script in a local tuple named args.
endFrame - (Keyword, Optional) If set to True, the execution will be delayed until the end of the current frame.
fromOP - (Keyword, Optional) Specifies an optional operator from which the execution will be run relative to.
asParameter - (Keyword, Optional) When fromOP used, run relative to a parameter of fromOP.
group - (Keyword, Optional) Can be used to specify a group label string. This label can then be used with the td.runs object to modify its execution.
delayFrames - (Keyword, Optional) Can be used to delay the execution a specific amount of frames.
delayMilliSeconds - (Keyword, Optional) Can be used to delay the execution a specific amount of milliseconds. This value is rounded to the nearest frame.
delayRef - (Keyword, Optional) Specifies an optional operator which is controlled by a different Time Component. If your own local timeline is paused, you can point to another timeline to ensure this script will still execute for example.

# grab DAT

n = op('text1')

# run the DAT

n.run()

# run the data with some arguments

r.run('firstArgIsString', secondArgIsVariable)
save(filepath, append=False, createFolders=False)→ str:

Saves the content of the DAT to the file system. Returns the file path that it was saved to.

filepath - (Optional) The path and filename to save the file to. If this is not given then a default named file will be saved to project.folder
append - (Keyword, Optional) If set to True and the format is txt, then the contents are appended to the existing file.
createFolders - (Keyword, Optional) If True, it creates the not existent directories provided by the filepath.
name = n.save() #save in native format with default name
n.save('output.txt') #human readable format without channel names
n.save('C:/Desktop/myFolder/output.txt', createFolders=True)  # supply file path and createFolder flag
write(args)→ str:

Append content to this DAT. Can also be used to implement DAT printing functions.

# grab DAT

n = op('text1')

# append message directly to DAT

n.write('Hello World')

# use print method

print('Hello World', file=n)
detectLanguage(setLanguage=False)→ str:

Returns the result of attempting to auto-detect the programming language in the DAT based on the contained text.

setLanguage - (Keyword, Optional) If True sets the language parameters on the DAT appropriately

### Modifying Content

The following methods can be used to modify the contents of a DAT. This can be done when the DAT is a Text DAT, or Script DAT for example, or a DAT that is Locked.

clear(keepSize=False, keepFirstRow=False, keepFirstCol=False)→ None:

Remove all rows and columns from the table.

keepSize - (Keyword, Optional) If set to True, size is unchanged, but entries will be set to blank, dependent on other options below.
keepFirstRow - (Keyword, Optional) If set to True, the first row of cells are retained.
keepFirstCol - (Keyword, Optional) If set to True, the first column of cells are retained.
n.clear() #remove all rows and columns
n.clear(keepSize=True) #set all table cells to blank
n.clear(keepFirstRow=True) #remove all rows, but keep the first
n.clear(keepFirstRow=True, keepFirstCol=True) #keep the first row, first column, and set remaining cells to blank
copy(DAT)→ None:

Copy the text or table from the specified DAT operator.

OP - The DAT operator whose contents should be copied into the DAT.

### Modifying Text Content

When the DAT is not a table, but a block of text, its contents can be simply accessed through its text member.

t = op('merge1').text
op('text2').text = 'merge1 contains:' + t

op('text3').text = "Hello there!"

### Modifying a Single Cell of a Table

Using DAT[row, column] where row, column specifies which cell to modify. The row and column may be integer numbers starting at 0, or strings which are the column names or row names (in row 0 or column 0 respectively):

op['table1']('Monday',1) = 'day1'

tab = op('table1')
tab[0,0] = 'corner'
tab[1,'select'] = 'yes'
tab['Monday',1] = 'day1'

### Modifying Table Content

The following methods can be used to modify the contents of a table type DAT containing rows and columns. This can be done when the DAT is a basic Table DAT, or Script DAT. It can also be used to append rows to FIFO-style DATs such as the Serial DAT.

appendRow(vals, nameOrIndex, sort=None)→ int:

Append a row to the end of the table, or after the specified row name/index. Returns the integer index of the new row.

vals - (Optional) If specified, will fill the row with the given values. It should be a list of items that can be expressed as strings. Each item will be copied to one cell.
nameOrIndex - (Optional) If specified will determine where the new row will be appended. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
sort - (Keyword, Optional) If specified will determine the column to keep sorted after the insertion. If it's a numeric value it represents the numeric index of the column. If it is a string it represents a column label.
n.appendRow()
n.appendRow( [1,2,3], 'January' )  #append with values (1,2,3) after the row labelled 'January'
n.appendRow( [1,2,3], 5 )  #append row with values (1,2,3) after the row 5.
n.appendRow( [1,2,3], sort='Month' )  #append row with values (1,2,3) keeping column 'Month' sorted.
appendRows(vals, nameOrIndex, sort=None)→ int:

Append rows to the end of the table, or after the specified row name/index. Returns the integer of the last row appended.

vals - (Optional) If specified, will fill the rows with the given values. It should be a list of lists of items that can be expressed as strings. Each item will be copied to one cell.
nameOrIndex - (Optional) If specified will determine where the new row will be appended. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
sort - (Keyword, Optional) If specified will determine the column to keep sorted after the insertion. If it's a numeric value it represents the numeric index of the column. If it is a string it represents a column label.
n.appendRows()
n.appendRows( [[1,2,3],[4,5,6,7]], 'January' )  #after the row labelled 'January append 2 rows: first one with values (1,2,3), then one with values (4,5,6,7)
n.appendRows( [[1,2,3]], 5 )  # after row 5 append one row with values (1,2,3).
n.appendRows( [1,2,3] )  # append 3 rows with values 1, 2, 3 respectively.
appendCol(vals, nameOrIndex, sort=None)→ int:

Append a column to the end of the table. See appendRow for similar usage.

appendCols(vals, nameOrIndex, sort=None)→ int:

Append columns to the end of the table. See appendRows for similar usage.

insertRow(vals, nameOrIndex, sort=None)→ int:

Insert a row to the beginning of the table or before the specified row name/index. See DAT.appendRow() for similar usage.

insertCol(vals, nameOrIndex, sort=None)→ int:

Insert a column to the beginning of the table or before the specified row name/index. See DAT.appendRow() for similar usage.

replaceRow(nameOrIndex, vals, entireRow=True)→ int:

Replaces the contents of an existing row.

nameOrIndex - Specifies the row that will be replaced. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
vals - (Optional) If specified, will overwrite the row with the given values. It should be a list of lists of items that can be expressed as strings. Each item will be copied to one cell.
entireRow - (Keyword, Optional) If True, overwrites every cell in the specified row. If False, will only overwrite as many cells in the row as there are items in vals.
n.replaceRow(0) # will empty all the cells in row 0 (ie. replaced with nothing)
n.replaceRow('January', ['January', 1,2,3])  # the row 'January' will be replaced with the list of 4 items.
n.replaceRow(2, [1,2,3], entireRow=False)  # at row 2 the 3 items will replace the first 3 items in the row.
replaceCol(nameOrIndex, vals, entireCol=True)→ int:

Replaces the contents of an existing column. See DAT.replaceRow for similar usage.

deleteRow(nameOrIndex)→ None:

Delete a single row at the specified row name or index.

nameOrIndex - May be a string for a row name, or numeric index for rowindex.
deleteRows(vals)→ None:

Deletes multiple rows at the row names or indices specified in vals.

vals - If specified, will delete each row given. It should be a list of items that can be expressed as strings. If no vals is provided deleteRows does nothing.
deleteCol(nameOrIndex)→ None:

Delete a single column at the specified column name or index.

nameOrIndex - May be a string for a column name, or numeric index for column index.
deleteCols(vals)→ None:

Deletes multiple columns at the column names or indices specified in vals.

vals - If specified, will delete each column given. It should be a list of items that can be expressed as strings. If no vals is provided deleteCols does nothing.
setSize(numrows, numcols)→ None:

Set the exact size of the table.

numrows - The number of rows the table should have.
numcols - The number of columns the table should have.
scroll(row, col)→ None:

Bring current DAT viewers to the specified row and column

row - Row to scroll to.
col - (Optional) Column to scroll to for tables.

### Accessing Table Content

[rowNameOrIndex, colNameOrIndex]→ td.Cell:

cells in a table may be accessed with the [] subscript operator.

The NameOrIndex may be an exact string name, or it may be a numeric index value. Pattern Matching is not supported.

rowNameOrIndex - If a string it specifies a row name, if it's numeric it specifies a row index.
colNameOrIndex - If a string it specifies a column name, if it's numeric it specifies a column index.
c = n[4, 'June']
c = n[3, 4]
cell(rowNameOrIndex, colNameOrIndex, caseSensitive=True, val=False)→ td.Cell | str | None:

Find a single cell in the table, or None if none are found.

rowNameOrIndex/colNameOrIndex - If a string it specifies a row/column name. If it's numeric it specifies a row/column index. Pattern Matching is supported for strings.
caseSensitive - (Optional) Specifies whether or not case sensitivity is used.
val - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of Cell Class items.
c = n.cell(5, 'June') #Return a cell under row 5, column 'June'.
c = n.cell('A*', 2) #Find a cell under any row beginning with an A, in column 2.
c = n.cell('A*', 2, val=True) #Return the str type of the found cell
cells(rowNameOrIndex, colNameOrIndex, caseSensitive=True, val=False)→ list:

Returns a (possibly empty) list of cells that match the given row/column names or indices. See DAT.cell method for similar usage.

findCell(pattern, rows=None, cols=None, valuePattern=True, rowPattern=True, colPattern=True, caseSensitive=False, val=False)→ Cell | str | None:

Returns a cell that matches the given pattern and row/column names or indices or None if no match is found.

pattern - The pattern to match a cell.
rows (Keyword, Optional) - If specified, looks for cell only in the specified rows. Must be specified as a list.
cols (Keyword, Optional) - If specified, looks for cell only in the specified columns. Must be specified as a list.
valuePattern, rowPattern, colPattern(Keyword, Optional) - If specified and set to False, disables pattern matching for a cell, rows or columns.
caseSensitive(Keyword, Optional) - Cell matching is case sensitive if set to true.
val - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of Cell Class items.

# given a table "table1"

# # id # fruit      # color #

# # 0  # Strawberry # Red #

# # 1  # Banana     # Yellow #

# # 2  # Cucumber   # Green #

# # 3  # Blueberry  # Blue #

# # 4  # Clementine # Orange #

# # 5  # *Fruit     # Green #

# t is the reference to a table DAT

t = op('/project1/table1')

# search for any cell with the value 'Red'

# will return type:Cell cell:(1, 2) owner:/project1/table1 value:Red

t.findCell('Red')

# search for any cell in the column 'fruit' with a value starting with 'blue'

# will return type:Cell cell:(4, 1) owner:/project1/table1 value:Blueberry

t.findCell('blue*',cols=['fruit'])

# search for any cell in the column 'fruit' with a value starting with 'blue'

# with case-sensitive search enabled

# will return None

t.findCell('blue*',cols=['fruit'], caseSensitive=True)

# will return type:Cell cell:(0, 1) owner:/project1/table1 value:fruit

# as the '*' in the search pattern will be used to pattern match, the

# first row of the second column is matched

t.findCell('*Fruit')

# will return type:Cell cell:(6, 1) owner:/project1/table1 value:*Fruit

# as pattern matching for the search pattern is disabled

# hence the '*' is not interpreted as a pattern but a string to look for

t.findCell('*Fruit', valuePattern=False)

# search for any cell with the pattern '*Fruit'

# will return the str of the found cell, say 'SweetFruit'

t.findCell('*Fruit', val=True)
findCells(pattern, rows=None, cols=None, valuePattern=True, rowPattern=True, colPattern=True, val=False)→ list:

Returns a (possibly empty) list of cells that match the given patterns and row/column names or indices.

pattern - The pattern to match cells.
rows (Keyword, Optional) - If specified, looks for cells only in the specified rows.
cols (Keyword, Optional) - If specified, looks for cells only in the specified columns.
valuePattern, rowPattern, colPattern(Keyword, Optional) - If specified, overrides pattern matching for cells, rows or columns.
caseSensitive(Keyword, Optional) - Cell matching is case sensitive if set to true.
val - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of Cell Class items.
row(*nameOrIndexes, caseSensitive=True, val=False)→ List[Cell]:

Returns a list of cells from the first row matching the name/index, or None if nothing is found.

nameOrIndexes - Include any number of these. If a string it specifies a row name, if it's numeric it specifies a row index. Pattern Matching is supported.
caseSensitive - (Optional) Specifies whether or not case sensitivity is used.
val - (Optional) If set to true, returns list of cell item strings instead of list of Cell Class items.
See DAT.col() for similar usage.

r = op('table1').row(3, caseSensitive=False)
r = op('table1').row('June')
r = op('table1').row('A*', 'B*') #returns first row beginning with A or B
r = op('table1').row('June', val=True) #returns list of all strings stored under the row 'June'
rows(*nameOrIndexes, caseSensitive=True, val=False)→ List[List[Cell]]:

Returns a (possibly empty) list of rows (each row being a list of cells). If no arguments are given it returns all rows in the table.

nameOrIndexes - (Optional) Include any number of these. If a string it specifies a row name, if it's numeric it specifies a row index. Pattern Matching is supported.
caseSensitive - (Optional) Specifies whether or not case sensitivity is used.
val - (Optional) If set to true, returns list of cell item strings instead of list of Cell Class items.
See DAT.rows() for similar usage.

for r in op('table1').rows():

# do something with row 'r'

for r in op('table1').rows(val=True):
    # do something with the strings values of the row 'r'
col(*nameOrIndexes, caseSensitive=True, val=False)→ list:

Returns a list of cells from the first col matching the name/index, or None if nothing is found.

nameOrIndexes - Include any number of these. If a string it specifies a column name, if it's numeric it specifies a column index. Pattern Matching is supported.
caseSensitive - (Optional) Specifies whether or not case sensitivity is used.
val - (Optional) If set to true, returns list of cell item strings instead of list of Cell Class items.
r = op('table1').col(3, caseSensitive=False)
r = op('table1').col('June')
r = op('table1').col('A*', 'B*') #returns first column beginning with A or B
r = op('table1').col('June', val=True) #returns list of all strings stored under the column 'June'
cols(*nameOrIndexes, caseSensitive=True, val=False)→ List[List[Cell]]:

Returns a (possibly empty) list of columns (each being a list themselves). If no arguments are given then all columns in the table are returned.

nameOrIndexes - (Optional) Include any number of these. If a string it specifies a column name, if it's numeric it specifies a column index. Pattern Matching is supported.
caseSensitive - (Optional) Specifies whether or not case sensitivity is used.
val - (Optional) If set to true, returns list of cell item strings instead of list of Cell Class items.
for c in op('table1').cols():

# do something with each column 'c'

for c in op('table1').cols(val=True):
    # do something with the string values in each column 'c'
