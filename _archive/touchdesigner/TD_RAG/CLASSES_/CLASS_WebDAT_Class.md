---
title: "webDAT Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 25-30 minutes
user_personas: ["script_developer", "web_developer", "data_specialist"]
operators: ["webDAT"]
concepts: ["web_scraping", "http_requests", "data_fetching"]
prerequisites: ["Python_fundamentals", "CLASS_DAT", "CLASS_OP_Class"]
workflows: ["fetching_web_data", "building_dashboards", "api_integration"]
keywords: ["web", "dat", "http", "download", "query", "content"]
tags: ["python", "api", "core", "dat", "web"]
related_docs:
- CLASS_DAT
- CLASS_OP_Class
- MODULE_td
---

# webDAT Class

## Content

- [Introduction](#introduction)
- [webDAT Class Members](#webdat-class-members)
- [webDAT Class Methods](#webdat-class-methods)
- [DAT Class](#dat-class)
  - [Members](#members)
  - [Methods](#methods)
    - [Modifying Content](#modifying-content)
    - [Modifying Text Content](#modifying-text-content)
    - [Modifying a Single Cell of a Table](#modifying-a-single-cell-of-a-table)
    - [Modifying Table Content](#modifying-table-content)
    - [Accessing Table Content](#accessing-table-content)
- [OP Class](#op-class)
  - [Members](#members-1)
    - [General](#general)
    - [Common Flags](#common-flags)
    - [Appearance](#appearance)
    - [Connection](#connection)
    - [Cook Information](#cook-information)
    - [Type](#type)
  - [Methods](#methods-1)
    - [General](#general-1)
    - [Errors](#errors)
    - [Appearance](#appearance-1)
    - [Viewers](#viewers)
    - [Storage](#storage)
    - [Miscellaneous](#miscellaneous)

## Introduction

This class inherits from the [CLASS_DAT]. It references a specific Web DAT.

## webDAT Class Members

### downloadCurrent

`downloadCurrent` → `int` (Read Only):

> Total bytes downloaded so far.

### downloadFraction

`downloadFraction` → `float` (Read Only):

> Fraction of downloaded size to total size.

### downloadTotal

`downloadTotal` → `int` (Read Only):

> Total size for download, expressed in bytes.

### queryContentEncoding

`queryContentEncoding` → `str` (Read Only):

> Query Content Encoding, as returned from HTML query.

### queryContentLength

`queryContentLength` → `int` (Read Only):

> Query Content Length, as returned from HTML query.

### queryContentType

`queryContentType` → `str` (Read Only):

> Query Content Type, as returned from HTML query.

### queryContentTypeCharset

`queryContentTypeCharset` → `str` (Read Only):

> Query Content Type character set, as returned from HTML query.

## webDAT Class Methods

No operator specific methods.

---

# DAT Class

## Members

`export` → `bool` :

> Get or set Export Flag

`module` → `'module'` (Read Only):

> Retrieve the contents of the DAT as a module. This allows for functions in the module to be called directly. E.g `n.module.function(arg1, arg2)`

`numRows` → `int` (Read Only):

> Number of rows in the DAT table.

`numCols` → `int` (Read Only):

> Number of columns in the DAT table.

`text` → `str` :

> Get or set contents. Tables are treated as tab delimited columns, newline delimited rows.

`editingFile` → `str` (Read Only):

> The path to the current file used by external editors.

`isTable` → `bool` (Read Only):

> True if the DAT contains table formatted data.

`isText` → `bool` (Read Only):

> True if the DAT contains text formatted data. (ie, not table formatted).

`isEditable` → `bool` (Read Only):

> True if the DAT contents can be edited (Text DATs, Table DATs, locked DATs etc).

`isDAT` → `bool` (Read Only):

> True if the operator is a DAT.

`locals` → `dict` (Read Only):

> Local dictionary used during python execution of scripts in this DAT. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with scripts, or with an Examine DAT.

`jsonObject` → `dict` (Read Only):

> Parses the DAT as json and returns a python object.

`flush()`→ `None`:

> Dummy function required to redirect stdout to DATs.

`isatty()`→ `False`:

> Required to redirect stdout to DATs.

## Methods

`run(arg1, arg2..., endFrame=False, fromOP=None, asParameter=False, group=None, delayFrames=0, delayMilliSeconds=0, delayRef=me)`→ `td.Run`:

> Run the contents of the DAT as a script, returning a Run object which can be used to optionally modify its execution.
>
> - `arg` - (Optional) Arguments that will be made available to the script in a local tuple named `args`.
> - `endFrame` - (Keyword, Optional) If set to True, the execution will be delayed until the end of the current frame.
> - `fromOP` - (Keyword, Optional) Specifies an optional operator from which the execution will be run relative to.
> - `asParameter` - (Keyword, Optional) When fromOP used, run relative to a parameter of fromOP.
> - `group` - (Keyword, Optional) Can be used to specify a group label string. This label can then be used with the `td.runs` object to modify its execution.
> - `delayFrames` - (Keyword, Optional) Can be used to delay the execution a specific amount of frames.
> - `delayMilliSeconds` - (Keyword, Optional) Can be used to delay the execution a specific amount of milliseconds. This value is rounded to the nearest frame.
> - `delayRef` - (Keyword, Optional) Specifies an optional operator which is controlled by a different Time Component. If your own local timeline is paused, you can point to another timeline to ensure this script will still execute for example.
>
> ```python
> # grab DAT
> n = op('text1')
> # run the DAT
> n.run()
> # run the data with some arguments
> r.run('firstArgIsString', secondArgIsVariable)
> ```

`save(filepath, append=False, createFolders=False)`→ `str`:

> Saves the content of the DAT to the file system. Returns the file path that it was saved to.
>
> - `filepath` - (Optional) The path and filename to save the file to. If this is not given then a default named file will be saved to `project.folder`
> - `append` - (Keyword, Optional) If set to True and the format is txt, then the contents are appended to the existing file.
> - `createFolders` - (Keyword, Optional) If True, it creates the not existent directories provided by the filepath.
>
> ```python
> name = n.save() #save in native format with default name
> n.save('output.txt') #human readable format without channel names
> n.save('C:/Desktop/myFolder/output.txt', createFolders=True)  # supply file path and createFolder flag
> ```

`write(args)`→ `str`:

> Append content to this DAT. Can also be used to implement DAT printing functions.
>
> ```python
> # grab DAT
> n = op('text1')
> # append message directly to DAT
> n.write('Hello World')
> # use print method
> print('Hello World', file=n)
> ```

`detectLanguage(setLanguage=False)`→ `str`:

> Returns the result of attempting to auto-detect the programming language in the DAT based on the contained text.
>
> - `setLanguage` - (Keyword, Optional) If True sets the language parameters on the DAT appropriately

### Modifying Content

The following methods can be used to modify the contents of a DAT. This can be done when the DAT is a Text DAT, or Script DAT for example, or a DAT that is Locked.

`clear(keepSize=False, keepFirstRow=False, keepFirstCol=False)`→ `None`:

> Remove all rows and columns from the table.
>
> - `keepSize` - (Keyword, Optional) If set to True, size is unchanged, but entries will be set to blank, dependent on other options below.
> - `keepFirstRow` - (Keyword, Optional) If set to True, the first row of cells are retained.
> - `keepFirstCol` - (Keyword, Optional) If set to True, the first column of cells are retained.
>
> ```python
> n.clear() #remove all rows and columns
> n.clear(keepSize=True) #set all table cells to blank
> n.clear(keepFirstRow=True) #remove all rows, but keep the first
> n.clear(keepFirstRow=True, keepFirstCol=True) #keep the first row, first column, and set remaining cells to blank
> ```

`copy(DAT)`→ `None`:

> Copy the text or table from the specified DAT operator.
>
> - `OP` - The DAT operator whose contents should be copied into the DAT.

### Modifying Text Content

When the DAT is not a table, but a block of text, its contents can be simply accessed through its `text` member.

```python
t = op('merge1').text
op('text2').text = 'merge1 contains:' + t

op('text3').text = "Hello there!"
```

### Modifying a Single Cell of a Table

Using `DAT[row, column]` where `row, column` specifies which cell to modify. The row and column may be integer numbers starting at 0, or strings which are the column names or row names (in row 0 or column 0 respectively):

```python
op('table1')['Monday',1] = 'day1'

tab = op('table1')
tab[0,0] = 'corner'
tab[1,'select'] = 'yes'
tab['Monday',1] = 'day1'
```

### Modifying Table Content

The following methods can be used to modify the contents of a table type DAT containing rows and columns. This can be done when the DAT is a basic Table DAT, or Script DAT. It can also be used to append rows to FIFO-style DATs such as the Serial DAT.

`appendRow(vals, nameOrIndex, sort=None)`→ `int`:

> Append a row to the end of the table, or after the specified row name/index. Returns the integer index of the new row.
>
> - `vals` - (Optional) If specified, will fill the row with the given values. It should be a list of items that can be expressed as strings. Each item will be copied to one cell.
> - `nameOrIndex` - (Optional) If specified will determine where the new row will be appended. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
> - `sort` - (Keyword, Optional) If specified will determine the column to keep sorted after the insertion. If it's a numeric value it represents the numeric index of the column. If it is a string it represents a column label.
>
> ```python
> n.appendRow()
> n.appendRow( [1,2,3], 'January' )  #append with values (1,2,3) after the row labelled 'January'
> n.appendRow( [1,2,3], 5 )  #append row with values (1,2,3) after the row 5.
> n.appendRow( [1,2,3], sort='Month' )  #append row with values (1,2,3) keeping column 'Month' sorted.
> ```

`appendRows(vals, nameOrIndex, sort=None)`→ `int`:

> Append rows to the end of the table, or after the specified row name/index. Returns the integer of the last row appended.
>
> - `vals` - (Optional) If specified, will fill the rows with the given values. It should be a list of lists of items that can be expressed as strings. Each item will be copied to one cell.
> - `nameOrIndex` - (Optional) If specified will determine where the new row will be appended. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
> - `sort` - (Keyword, Optional) If specified will determine the column to keep sorted after the insertion. If it's a numeric value it represents the numeric index of the column. If it is a string it represents a column label.
>
> ```python
> n.appendRows()
> n.appendRows( [[1,2,3],[4,5,6,7]], 'January' )  #after the row labelled 'January append 2 rows: first one with values (1,2,3), then one with values (4,5,6,7)
> n.appendRows( [[1,2,3]], 5 )  # after row 5 append one row with values (1,2,3).
> n.appendRows( [1,2,3] )  # append 3 rows with values 1, 2, 3 respectively.
> ```

`appendCol(vals, nameOrIndex, sort=None)`→ `int`:

> Append a column to the end of the table. See `appendRow` for similar usage.

`appendCols(vals, nameOrIndex, sort=None)`→ `int`:

> Append columns to the end of the table. See `appendRows` for similar usage.

`insertRow(vals, nameOrIndex, sort=None)`→ `int`:

> Insert a row to the beginning of the table or before the specified row name/index. See `DAT.appendRow()` for similar usage.

`insertCol(vals, nameOrIndex, sort=None)`→ `int`:

> Insert a column to the beginning of the table or before the specified row name/index. See `DAT.appendRow()` for similar usage.

`replaceRow(nameOrIndex, vals, entireRow=True)`→ `int`:

> Replaces the contents of an existing row.
>
> - `nameOrIndex` - Specifies the row that will be replaced. If it's a numeric value it represents the numeric index of the row. If it is a string it represents a row label.
> - `vals` - (Optional) If specified, will overwrite the row with the given values. It should be a list of lists of items that can be expressed as strings. Each item will be copied to one cell.
> - `entireRow` - (Keyword, Optional) If True, overwrites every cell in the specified row. If False, will only overwrite as many cells in the row as there are items in `vals`.
>
> ```python
> n.replaceRow(0) # will empty all the cells in row 0 (ie. replaced with nothing)
> n.replaceRow('January', ['January', 1,2,3])  # the row 'January' will be replaced with the list of 4 items.
> n.replaceRow(2, [1,2,3], entireRow=False)  # at row 2 the 3 items will replace the first 3 items in the row.
> ```

`replaceCol(nameOrIndex, vals, entireCol=True)`→ `int`:

> Replaces the contents of an existing column. See `DAT.replaceRow` for similar usage.

`deleteRow(nameOrIndex)`→ `None`:

> Delete a single row at the specified row name or index.
>
> - `nameOrIndex` - May be a string for a row name, or numeric index for rowindex.

`deleteRows(vals)`→ `None`:

> Deletes multiple rows at the row names or indices specified in `vals`.
>
> - `vals` - If specified, will delete each row given. It should be a list of items that can be expressed as strings. If no `vals` is provided `deleteRows` does nothing.

`deleteCol(nameOrIndex)`→ `None`:

> Delete a single column at the specified column name or index.
>
> - `nameOrIndex` - May be a string for a column name, or numeric index for column index.

`deleteCols(vals)`→ `None`:

> Deletes multiple columns at the column names or indices specified in `vals`.
>
> - `vals` - If specified, will delete each column given. It should be a list of items that can be expressed as strings. If no `vals` is provided `deleteCols` does nothing.

`setSize(numrows, numcols)`→ `None`:

> Set the exact size of the table.
>
> - `numrows` - The number of rows the table should have.
> - `numcols` - The number of columns the table should have.

`scroll(row, col)`→ `None`:

> Bring current DAT viewers to the specified row and column
>
> - `row` - Row to scroll to.
> - `col` - (Optional) Column to scroll to for tables.

### Accessing Table Content

`[rowNameOrIndex, colNameOrIndex]`→ `td.Cell`:

> cells in a table may be accessed with the `[]` subscript operator.
>
> The `NameOrIndex` may be an exact string name, or it may be a numeric index value. Pattern Matching is not supported.
>
> - `rowNameOrIndex` - If a string it specifies a row name, if it's numeric it specifies a row index.
> - `colNameOrIndex` - If a string it specifies a column name, if it's numeric it specifies a column index.
>
> ```python
> c = n[4, 'June']
> c = n[3, 4]
> ```

`cell(rowNameOrIndex, colNameOrIndex, caseSensitive=True, val=False)`→ `td.Cell` | `str` | `None`:

> Find a single cell in the table, or `None` if none are found.
>
> - `rowNameOrIndex/colNameOrIndex` - If a string it specifies a row/column name. If it's numeric it specifies a row/column index. Pattern Matching is supported for strings.
> - `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
> - `val` - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of `Cell Class` items.
>
> ```python
> c = n.cell(5, 'June') #Return a cell under row 5, column 'June'.
> c = n.cell('A*', 2) #Find a cell under any row beginning with an A, in column 2.
> c = n.cell('A*', 2, val=True) #Return the str type of the found cell
> ```

`cells(rowNameOrIndex, colNameOrIndex, caseSensitive=True, val=False)`→ `list`:

> Returns a (possibly empty) list of cells that match the given row/column names or indices. See `DAT.cell` method for similar usage.

`findCell(pattern, rows=None, cols=None, valuePattern=True, rowPattern=True, colPattern=True, caseSensitive=False, val=False)`→ `Cell` | `str` | `None`:

> Returns a cell that matches the given pattern and row/column names or indices or `None` if no match is found.
>
> - `pattern` - The pattern to match a cell.
> - `rows` (Keyword, Optional) - If specified, looks for cell only in the specified rows. Must be specified as a list.
> - `cols` (Keyword, Optional) - If specified, looks for cell only in the specified columns. Must be specified as a list.
> - `valuePattern`, `rowPattern`, `colPattern`(Keyword, Optional) - If specified and set to False, disables pattern matching for a cell, rows or columns.
> - `caseSensitive`(Keyword, Optional) - Cell matching is case sensitive if set to true.
> - `val` - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of `Cell Class` items.
>
> ```python
> # given a table "table1":
> # # id # fruit      # color  #
> # # 0  # Strawberry # Red    #
> # # 1  # Banana     # Yellow #
> # # 2  # Cucumber   # Green  #
> # # 3  # Blueberry  # Blue   #
> # # 4  # Clementine # Orange #
> # # 5  # *Fruit     # Green  #
>
> # t is the reference to a table DAT
> t = op('/project1/table1')
>
> # search for any cell with the value 'Red'
> # will return type:Cell cell:(1, 2) owner:/project1/table1 value:Red
> t.findCell('Red')
>
> # search for any cell in the column 'fruit' with a value starting with 'blue'
> # will return type:Cell cell:(4, 1) owner:/project1/table1 value:Blueberry
> t.findCell('blue*',cols=['fruit'])
>
> # search for any cell in the column 'fruit' with a value starting with 'blue'
> # with case-sensitive search enabled
> # will return None
> t.findCell('blue*',cols=['fruit'], caseSensitive=True)
>
> # will return type:Cell cell:(0, 1) owner:/project1/table1 value:fruit
> # as the '*' in the search pattern will be used to pattern match, the 
> # first row of the second column is matched
> t.findCell('*Fruit')
>
> # will return type:Cell cell:(6, 1) owner:/project1/table1 value:*Fruit
> # as pattern matching for the search pattern is disabled
> # hence the '*' is not interpreted as a pattern but a string to look for
> t.findCell('*Fruit', valuePattern=False)
>
> # search for any cell with the pattern '*Fruit'
> # will return the str of the found cell, say 'SweetFruit'
> t.findCell('*Fruit', val=True)
> ```

`findCells(pattern, rows=None, cols=None, valuePattern=True, rowPattern=True, colPattern=True, val=False)`→ `list`:

> Returns a (possibly empty) list of cells that match the given patterns and row/column names or indices.
>
> - `pattern` - The pattern to match cells.
> - `rows` (Keyword, Optional) - If specified, looks for cells only in the specified rows.
> - `cols` (Keyword, Optional) - If specified, looks for cells only in the specified columns.
> - `valuePattern`, `rowPattern`, `colPattern`(Keyword, Optional) - If specified, overrides pattern matching for cells, rows or columns.
> - `caseSensitive`(Keyword, Optional) - Cell matching is case sensitive if set to true.
> - `val` - (Keyword, Optional) If set to true, returns list of cell item strings instead of list of `Cell Class` items.

`row(*nameOrIndexes, caseSensitive=True, val=False)`→ `List[Cell]`:

> Returns a list of cells from the first row matching the name/index, or `None` if nothing is found.
>
> - `nameOrIndexes` - Include any number of these. If a string it specifies a row name, if it's numeric it specifies a row index. Pattern Matching is supported.
> - `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
> - `val` - (Optional) If set to true, returns list of cell item strings instead of list of `Cell Class` items.
>
> See `DAT.col()` for similar usage.
>
> ```python
> r = op('table1').row(3, caseSensitive=False)
> r = op('table1').row('June')
> r = op('table1').row('A*', 'B*') #returns first row beginning with A or B
> r = op('table1').row('June', val=True) #returns list of all strings stored under the row 'June'
> ```

`rows(*nameOrIndexes, caseSensitive=True, val=False)`→ `List[List[Cell]]`:

> Returns a (possibly empty) list of rows (each row being a list of cells). If no arguments are given it returns all rows in the table.
>
> - `nameOrIndexes` - (Optional) Include any number of these. If a string it specifies a row name, if it's numeric it specifies a row index. Pattern Matching is supported.
> - `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
> - `val` - (Optional) If set to true, returns list of cell item strings instead of list of `Cell Class` items.
>
> See `DAT.rows()` for similar usage.
>
> ```python
> for r in op('table1').rows():
> # do something with row 'r'
>
> for r in op('table1').rows(val=True):
>     # do something with the strings values of the row 'r'
> ```

`col(*nameOrIndexes, caseSensitive=True, val=False)`→ `list`:

> Returns a list of cells from the first col matching the name/index, or `None` if nothing is found.
>
> - `nameOrIndexes` - Include any number of these. If a string it specifies a column name, if it's numeric it specifies a column index. Pattern Matching is supported.
> - `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
> - `val` - (Optional) If set to true, returns list of cell item strings instead of list of `Cell Class` items.
>
> ```python
> r = op('table1').col(3, caseSensitive=False)
> r = op('table1').col('June')
> r = op('table1').col('A*', 'B*') #returns first column beginning with A or B
> r = op('table1').col('June', val=True) #returns list of all strings stored under the column 'June'
> ```

`cols(*nameOrIndexes, caseSensitive=True, val=False)`→ `List[List[Cell]]`:

> Returns a (possibly empty) list of columns (each being a list themselves). If no arguments are given then all columns in the table are returned.
>
> - `nameOrIndexes` - (Optional) Include any number of these. If a string it specifies a column name, if it's numeric it specifies a column index. Pattern Matching is supported.
> - `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.
> - `val` - (Optional) If set to true, returns list of cell item strings instead of list of `Cell Class` items.
>
> ```python
> for c in op('table1').cols():
> # do something with each column 'c'
>
> for c in op('table1').cols(val=True):
>     # do something with the string values in each column 'c'
> ```

---

# OP Class

## Members

### General

`valid` → `bool` (Read Only):

> True if the referenced operator currently exists, False if it has been deleted.

`id` → `int` (Read Only):

> Unique id for the operator. This id can also be passed to the `op()` and `ops()` methods. Id's are not consistent when a file is re-opened, and will change if the OP is copied/pasted, changes OP types, deleted/undone. The id will not change if the OP is renamed though. Its data type is integer.

`name` → `str` :

> Get or set the operator name.

`path` → `str` (Read Only):

> Full path to the operator.

`digits` → `int` (Read Only):

> Returns the numeric value of the last consecutive group of digits in the name, or None if not found. The digits can be in the middle of the name if there are none at the end of the name.

`base` → `str` (Read Only):

> Returns the beginning portion of the name occurring before any digits.

`passive` → `bool` (Read Only):

> If true, operator will not cook before its access methods are called. To use a passive version of an operator n, use `passive(n)`.

`curPar` → `td.Par` (Read Only):

> The parameter currently being evaluated. Can be used in a parameter expression to reference itself. An easy way to see this is to put the expression `curPar.name` in any string parameter.

`curBlock` → (Read Only):

> The `SequenceBlock` of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

`curSeq` → `Sequence` (Read Only):

> The `Sequence` of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

`time` → `OP` (Read Only):

> Time Component that defines the operator's time reference.

`ext` → `class` (Read Only):

> The object to search for parent extensions.
>
> `me.ext.MyClass`

`fileFolder` → `str` (Read Only):

> Returns the folder where this node is saved.

`filePath` → `str` (Read Only):

> Returns the file location of this node.

`mod` → `mod` (Read Only):

> Get a module on demand object that searches for DAT modules relative to this operator.

`pages` → `list` (Read Only):

> A list of all built-in pages.

`parGroup` → `tuple` (Read Only):

> An intermediate parameter collection object, from which a specific parameter group can be found.
>
> `n.parGroup.t`
>
> # or
>
> `n.parGroup['t']`

`par` → `td.Par` (Read Only):

> An intermediate parameter collection object, from which a specific parameter can be found.
>
> `n.par.tx`
>
> # or
>
> `n.par['tx']`

`builtinPars` → `list` or `par` (Read Only):

> A list of all built-in parameters.

`customParGroups` → `list` of `parGroups` (Read Only):

> A list of all `ParGroups`, where a `ParGroup` is a set of parameters all drawn on the same line of a dialog, sharing the same label.

`customPars` → `list` of `par` (Read Only):

> A list of all custom parameters.

`customPages` → `list` (Read Only):

> A list of all custom pages.

`replicator` → `OP` or `None` (Read Only):

> The `replicatorCOMP` that created this operator, if any.

`storage` → `dict` (Read Only):

> Storage is dictionary associated with this operator. Values stored in this dictionary are persistent, and saved with the operator. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with methods such as `OP.fetch()` or `OP.store()` described below, or examined with an `Examine DAT`.

`tags` → `list` :

> Get or set a set of user defined strings. Tags can be searched using `OP.findChildren()` and the `OP Find DAT`.
>
> The set is a regular python set, and can be accessed accordingly:
>
> `n.tags = ['effect', 'image filter']`
> `n.tags.add('darken')`

`children` → `list` (Read Only):

> A list of operators contained within this operator. Only component operators have children, otherwise an empty list is returned.

`numChildren` → `int` (Read Only):

> Returns the number of children contained within the operator. Only component operators have children.

`numChildrenRecursive` → `int` (Read Only):

> Returns the number of operators contained recursively within this operator. Only component operators have children.

`op` → `OP` or `None` (Read Only):

> The operator finder object, for accessing operators through paths or shortcuts. Note: a version of this method that searches relative to '/' is also in the global `td` module.
>
> `op(pattern1, pattern2..., includeUtility=False)` → `OP` or `None`
>
> Returns the first OP whose path matches the given pattern, relative to the inside of this operator. Will return `None` if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.
>
> - `pattern` - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
> - `includeUtility` (Optional) - if True, allow Utility nodes to be returned. If False, Utility nodes will be ignored.
>
> `b = op('project1')`
> `b = op('foot*', 'hand*')` #comma separated
> `b = op('foot* hand*')`  #space separated
> `b = op(154)`

`op.shortcut` → `OP`

> An operator specified with by a Global OP Shortcut. If no operator exists an exception is raised. These shortcuts are global, and must be unique. That is, cutting and pasting an operator with a Global OP Shortcut specified will lead to a name conflict. One shortcut must be renamed in that case. Furthermore, only components can be given Global OP Shortcuts.
>
> - `shortcut` - Corresponds to the Global OP Shortcut parameter specified in the target operator.
>
> `b = op.Videoplayer`
>
> To list all Global OP Shortcuts:
>
> `for x in op:`
> `print(x)`

`opex` → `OP` (Read Only):

> An operator finder object, for accessing operators through paths or shortcuts. Works like the `op()` shortcut method, except it will raise an exception if it fails to find the node instead of returning `None` as `op()` does. This is now the recommended way to get nodes in parameter expressions, as the error will be more useful than, for example, `NoneType` has no attribute "par", that is often seen when using `op()`. Note: a version of this method that searches relative to '/' is also in the global `td` module.
>
> `op(pattern1, pattern2..., includeUtility=False)` → `OP`
>
> Returns the first OP whose path matches the given pattern, relative to the inside of this operator. Will return `None` if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.
>
> - `pattern` - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
> - `includeUtility` (Optional) - if True, allow Utility nodes to be returned. If False, Utility operators will be ignored.

`parent` → `Shortcut` (Read Only):

> The Parent Shortcut object, for accessing parent components through indices or shortcuts.
>
> Note: a version of this method that searches relative to the current operator is also in the global `td` module.
>
> `parent(n)` → `OP` or `None`
>
> The nth parent of this operator. If n not specified, returns the parent. If n = 2, returns the parent of the parent, etc. If no parent exists at that level, `None` is returned.
>
> - `n` - (Optional) n is the number of levels up to climb. When n = 1 it will return the operator's parent.
>
> `p = parent(2)` #grandfather

`parent.shortcut` → `OP`

> A parent component specified with a shortcut. If no parent exists an exception is raised.
>
> - `shortcut` - Corresponds to the Parent Shortcut parameter specified in the target parent.
>
> `n = parent.Videoplayer`
>
> See also `Parent Shortcut` for more examples.

`iop` → `OP` (Read Only):

> The Internal Operator Shortcut object, for accessing internal shortcuts. See also `Internal Operators`. Note: a version of this method that searches relative to the current operator is also in the global `td` Module.

`ipar` → `ParCollection` (Read Only):

> The Internal Operator Parameter Shortcut object, for accessing internal shortcuts. See also `Internal Parameters`. Note: a version of this method that searches relative to the current operator is also in the global `td` Module.

`currentPage` → `Page` :

> Get or set the currently displayed parameter page. It can be set by setting it to another page or a string label.
>
> `n.currentPage = 'Common'`

### Common Flags

The following methods get or set specific operator Flags. Note specific operators may contain other flags not in this section.

`activeViewer` → `bool` :

> Get or set Viewer Active Flag.

`allowCooking` → `bool` :

> Get or set Cooking Flag. Only COMPs can disable this flag.

`bypass` → `bool` :

> Get or set Bypass Flag.

`cloneImmune` → `bool` :

> Get or set Clone Immune Flag.

`current` → `bool` :

> Get or set Current Flag.

`display` → `bool` :

> Get or set Display Flag.

`expose` → `bool` :

> Get or set the Expose Flag which hides a node from view in a network.

`lock` → `bool` :

> Get or set Lock Flag.

`selected` → `bool` :

> Get or set Selected Flag. This controls if the node is part of the network selection. (yellow box around it).

`seq` → (Read Only):

> An intermediate sequence collection object, from which a specific sequence group can be found.
>
> `n.seq.Color` #raises Exception if not found.
>
> # or
>
> `n.seq['Color']` #returns None if not found.

`python` → `bool` :

> Get or set parameter expression language as python.

`render` → `bool` :

> Get or set Render Flag.

`showCustomOnly` → `bool` :

> Get or set the Show Custom Only Flag which controls whether or not non custom parameters are display inparameter dialogs.

`showDocked` → `bool` :

> Get or set Show Docked Flag. This controls whether this node is visible or hidden when it is docked to another node.

`viewer` → `bool` :

> Get or set Viewer Flag.

### Appearance

`color` → `tuple(r, g, b)` :

> Get or set color value, expressed as a 3-tuple, representing its red, green, blue values. To convert between color spaces, use the built in `colorsys` module.

`comment` → `str` :

> Get or set comment string.

`nodeHeight` → `int` :

> Get or set node height, expressed in network editor units.

`nodeWidth` → `int` :

> Get or set node width, expressed in network editor units.

`nodeX` → `int` :

> Get or set node X value, expressed in network editor units, measured from its left edge.

`nodeY` → `int` :

> Get or set node Y value, expressed in network editor units, measured from its bottom edge.

`nodeCenterX` → `int` :

> Get or set node X value, expressed in network editor units, measured from its center.

`nodeCenterY` → `int` :

> Get or set node Y value, expressed in network editor units, measured from its center.

`dock` → `OP` :

> Get or set the operator this operator is docked to. To clear docking, set this member to `None`.

`docked` → `list` (Read Only):

> The (possibly empty) list of operators docked to this node.

### Connection

See also the `OP.parent` methods. To connect components together see `COMP_Class#Connection` section.

`inputs` → `list` (Read Only):

> List of input operators (via left side connectors) to this operator. To get the number of inputs, use `len(OP.inputs)`.

`outputs` → `list` (Read Only):

> List of output operators (via right side connectors) from this operator.

`inputConnectors` → `list` (Read Only):

> List of input connectors (on the left side) associated with this operator.

`outputConnectors` → `list` (Read Only):

> List of output connectors (on the right side) associated with this operator.

### Cook Information

`cookFrame` → `float` (Read Only):

> Last frame at which this operator cooked.

`cookTime` → `float` (Read Only):

> Deprecated Duration of the last measured cook (in milliseconds).

`cpuCookTime` → `float` (Read Only):

> Duration of the last measured cook in CPU time (in milliseconds).

`cookAbsFrame` → `float` (Read Only):

> Last absolute frame at which this operator cooked.

`cookStartTime` → `float` (Read Only):

> Last offset from frame start at which this operator cook began, expressed in milliseconds.

`cookEndTime` → `float` (Read Only):

> Last offset from frame start at which this operator cook ended, expressed in milliseconds. Other operators may have cooked between the start and end time. See the `cookTime` member for this operator's specific cook duration.

`cookedThisFrame` → `bool` (Read Only):

> True when this operator has cooked this frame.

`cookedPreviousFrame` → `bool` (Read Only):

> True when this operator has cooked the previous frame.

`childrenCookTime` → `float` (Read Only):

> Deprecated The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

`childrenCPUCookTime` → `float` (Read Only):

> The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

`childrenCookAbsFrame` → `float` (Read Only):

> Deprecated The absolute frame on which `childrenCookTime` is based.

`childrenCPUCookAbsFrame` → `float` (Read Only):

> The absolute frame on which `childrenCPUCookTime` is based.

`gpuCookTime` → `float` (Read Only):

> Duration of GPU operations during the last measured cook (in milliseconds).

`childrenGPUCookTime` → `float` (Read Only):

> The total accumulated GPU cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

`childrenGPUCookAbsFrame` → `float` (Read Only):

> The absolute frame on which `childrenGPUCookTime` is based.

`totalCooks` → `int` (Read Only):

> Number of times the operator has cooked.

`cpuMemory` → `int` (Read Only):

> The approximate amount of CPU memory this Operator is using, in bytes.

`gpuMemory` → `int` (Read Only):

> The amount of GPU memory this OP is using, in bytes.

### Type

`type` → `str` (Read Only):

> Operator type as a string. Example: 'oscin'.

`subType` → `str` (Read Only):

> Operator subtype. Currently only implemented for components. May be one of: 'panel', 'object', or empty string in the case of base components.

`OPType` → `str` (Read Only):

> Python operator class type, as a string. Example: 'oscinCHOP'. Can be used with `COMP.create()` method.

`label` → `str` (Read Only):

> Operator type label. Example: 'OSC In'.

`icon` → `str` (Read Only):

> Get the letters used to create the operator's icon.

`family` → `str` (Read Only):

> Operator family. Example: CHOP. Use the global dictionary `families` for a list of each operator type.

`isFilter` → `bool` (Read Only):

> True if operator is a filter, false if it is a generator.

`minInputs` → `int` (Read Only):

> Minimum number of inputs to the operator.

`maxInputs` → `int` (Read Only):

> Maximum number of inputs to the operator.

`isMultiInputs` → `bool` (Read Only):

> True if inputs are ordered, false otherwise. Operators with an arbitrary number of inputs have unordered inputs, example `Merge CHOP`.

`visibleLevel` → `int` (Read Only):

> Visibility level of the operator. For example, expert operators have visibility level 1, regular operators have visibility level 0.

`isBase` → `bool` (Read Only):

> True if the operator is a Base (miscellaneous) component.

`isCHOP` → `bool` (Read Only):

> True if the operator is a CHOP.

`isCOMP` → `bool` (Read Only):

> True if the operator is a component.

`isDAT` → `bool` (Read Only):

> True if the operator is a DAT.

`isMAT` → `bool` (Read Only):

> True if the operator is a Material.

`isObject` → `bool` (Read Only):

> True if the operator is an object.

`isPanel` → `bool` (Read Only):

> True if the operator is a Panel.

`isSOP` → `bool` (Read Only):

> True if the operator is a SOP.

`isTOP` → `bool` (Read Only):

> True if the operators is a TOP.

`licenseType` → `str` (Read Only):

> Type of License required for the operator.

## Methods

### General

NOTE: `create()`, `copy()` and `copyOPs()` is done by the parent operator (a component). For more information see `COMP.create`, `COMP.copy` and `COMP.copyOPs` methods.

`pars(pattern)`→ `list`:

> Returns a (possibly empty) list of parameter objects that match the pattern.
>
> - `pattern` - Is a string following the Pattern Matching rules, specifying which parameters to return.
>
> `newlist = op('geo1').pars('t?', 'r?', 's?')` #translate/rotate/scale parameters
>
> Note: If searching for a single parameter given a name, it's much more efficient to use the subscript operator. For example:
>
> `name = 'MyName1'`
> `op('geo1').par[name]`

`cook(force=False, recurse=False, includeUtility=False)`→ `None`:

> Cook the contents of the operator if required.
>
> - `force` - (Keyword, Optional) If True, the operator will always cook, even if it wouldn't under normal circumstances.
> - `recurse` - (Keyword, Optional) If True, all children and sub-children of the operator will be cooked.
> - `includeUtility` - (Keyword, Optional) If specified, controls whether or not utility components (eg Comments) are included in the results.

`copyParameters(OP, custom=True, builtin=True)`→ `None`:

> Copy all of the parameters from the specified operator. Both operators should be the same type.
>
> - `OP` - The operator to copy.
> - `custom` - (Keyword, Optional) When True, custom parameters will be copied.
> - `builtin` - (Keyword, Optional) When True, built in parameters will be copied.
>
> `op('geo1').copyParameters( op('geo2') )`

`changeType(OPtype)`→ `OP`:

> Change referenced operator to a new operator type. After this call, this OP object should no longer be referenced. Instead use the returned OP object.
>
> - `OPtype` - The python class name of the operator type you want to change this operator to. This is not a string, but instead is a class defined in the global `td` module.
>
> `n = op('wave1').changeType(nullCHOP)` #changes 'wave1' into a Null CHOP
> `n = op('text1').changeType(tcpipDAT)` #changes 'text1' operator into a TCPIP DAT

`dependenciesTo(OP)`→ `list`:

> Returns a (possibly empty) list of operator dependency paths between this operator and the specified operator. Multiple paths may be found.

`evalExpression(str)`→ `value`:

> Evaluate the expression from the context of this OP. Can be used to evaluate arbitrary snippets of code from arbitrary locations.
>
> - `str` - The expression to evaluate.
>
> `op('wave1').evalExpression('me.digits')`  #returns 1
>
> If the expression already resides in a parameter, use that parameters `evalExpression()` method instead.

`destroy()`→ `None`:

> Destroy the operator referenced by this OP. An exception will be raised if the OP's operator has already been destroyed.

`var(name, search=True)`→ `str`:

> Evaluate avariable. This will return the empty string, if not found. Most information obtained from variables (except for Root and Component variables) are accessible through other means in Python, usually in the global `td` module.
>
> - `name` - The variable name to search for.
> - `search` - (Keyword, Optional) If set to True (which is default) the operator hierarchy is searched until a variable matching that name is found. If false, the search is constrained to the operator.

`openMenu(x=None, y=None)`→ `None`:

> Open a node menu for the operator at x, y. Opens at mouse if x & y are not specified.
>
> - `x` - (Keyword, Optional) The X coordinate of the menu, measured in screen pixels.
> - `y` - (Keyword, Optional) The Y coordinate of the menu, measured in screen pixels.

`relativePath(OP)`→ `str`:

> Returns the relative path from this operator to the OP that is passed as the argument. See `OP.shortcutPath` for a version using expressions.

`setInputs(listOfOPs)`→ `None`:

> Set all the operator inputs to the specified list.
>
> - `listOfOPs` - A list containing one or more OPs. Entries in the list can be `None` to disconnect specific inputs. An empty list disconnects all inputs.

`shortcutPath(OP, toParName=None)`→ `str`:

> Returns an expression from this operator to the OP that is passed as the argument. See `OP.relativePath` for a version using relative path constants.
>
> - `toParName` - (Keyword, Optional) Return an expression to this parameter instead of its operator.

`ops(pattern1, pattern2.., includeUtility=False)`→ `list` of `OPs`:

> Returns a (possibly empty) list of OPs that match the patterns, relative to the inside of this OP.
>
> Multiple patterns may be provided. Numeric OP ids may also be used.
>
> - `pattern` - Can be string following the Pattern Matching rules, specifying which OPs to return, or an integer, which must be an OP Id. Multiple patterns can be given and all matched OPs will be returned.
> - `includeUtility` - (Keyword, Optional) If specified, controls whether or not utility components (eg Comments) are included in the results.
>
> Note: a version of this method that searches relative to '/' is also in the global `td` module.
>
> `newlist = n.ops('arm*', 'leg*', 'leg5/foot*')`

`resetPars(parNames='*', parGroupNames='*', pageNames='*', includeBuiltin=True, includeCustom=True)`→ `bool`:

> Resets the specified parameters in the operator.
>
> Returns true if anything was changed.
>
> - `parNames` (Keyword, Optional) - Specify parameters by Par name.
> - `parGroupNames` (Keyword, Optional) - Specify parameters by ParGroup name.
> - `pageNames` (Keyword, Optional) - Specify parameters by page name.
> - `includeBuiltin` (Keyword, Optional) - Include builtin parameters.
> - `includeCustom` (Keyword, Optional) - Include custom parameters.
>
> `op('player').resetPars(includeBuiltin=False)` # only reset custom

### Errors

`addScriptError(msg)`→ `None`:

> Adds a script error to a node.
>
> - `msg` - The error to add.

`addError(msg)`→ `None`:

> Adds an error to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).
>
> - `msg` - The error to add.

`addWarning(msg)`→ `None`:

> Adds a warning to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).
>
> - `msg` - The error to add.

`errors(recurse=False)`→ `str`:

> Get error messages associated with this OP.
>
> - `recurse` - Get errors in any children or subchildren as well.

`warnings(recurse=False)`→ `str`:

> Get warning messages associated with this OP.
>
> - `recurse` - Get warnings in any children or subchildren as well.

`scriptErrors(recurse=False)`→ `str`:

> Get script error messages associated with this OP.
>
> - `recurse` - Get errors in any children or subchildren as well.

`clearScriptErrors(recurse=False, error='*')`→ `None`:

> Clear any errors generated during script execution. These may be generated during execution of DATs, Script Nodes, Replicator COMP callbacks, etc.
>
> - `recurse` - Clear script errors in any children or subchildren as well.
> - `error` - Pattern to match when clearing errors
>
> `op('/project1').clearScriptErrors(recurse=True)`

`childrenCPUMemory()`→ `int`:

> Returns the total CPU memory usage for all the children from this COMP.

`childrenGPUMemory()`→ `int`:

> Returns the total GPU memory usage for all the children from this COMP.

### Appearance

`resetNodeSize()`→ `None`:

> Reset the node tile size to its default width and height.

### Viewers

`closeViewer(topMost=False)`→ `None`:

> Close the floating content viewers of the OP.
>
> - `topMost` - (Keyword, Optional) If True, any viewer window containing any parent of this OP is closed instead.
>
> `op('wave1').closeViewer()`
> `op('wave1').closeViewer(topMost=True)` # any viewer that contains 'wave1' will be closed.

`openViewer(unique=False, borders=True)`→ `None`:

> Open a floating content viewer for the OP.
>
> - `unique` - (Keyword, Optional) If False, any existing viewer for this OP will be re-used and popped to the foreground. If unique is True, a new window is created each time instead.
> - `borders` - (Keyword, Optional) If true, the floating window containing the viewer will have borders.
>
> `op('geo1').openViewer(unique=True, borders=False)` # opens a new borderless viewer window for 'geo1'

`resetViewer(recurse=False)`→ `None`:

> Reset the OP content viewer to default view settings.
>
> - `recurse` - (Keyword, Optional) If True, this is done for all children and sub-children as well.
>
> `op('/').resetViewer(recurse=True)` # reset the viewer for all operators in the entire file.

`openParameters()`→ `None`:

> Open a floating dialog containing the operator parameters.

### Storage

Storage can be used to keep data within components. Storage is implemented as one python dictionary per node.

When an element of storage is changed by using `n.store()` as explained below, expressions and operators that depend on it will automatically re-cook. It is retrieved with the `n.fetch()` function.

Storage is saved in `.toe` and `.tox` files and restored on startup.

Storage can hold any python object type (not just strings as in Tscript variables). Storage elements can also have optional startup values, specified separately. Use these startup values for example, to avoid saving and loading some session specific object, and instead save or load a well defined object like `None`.

See the `Examine DAT` for procedurally viewing the contents of storage.

`fetch(key, default, search=True, storeDefault=False)`→ `value`:

> Return an object from the OP storage dictionary. If the item is not found, and a default it supplied, it will be returned instead.
>
> - `key` - The name of the entry to retrieve.
> - `default` - (Optional) If provided and no item is found then the passed value/object is returned instead.
> - `storeDefault` - (Keyword, Optional) If True, and the key is not found, the default is stored as well.
> - `search` - (Keyword, Optional) If True, the parent of each OP is searched recursively until a match is found
>
> `v = n.fetch('sales5', 0.0)`

`fetchOwner(key)`→ `OP`:

> Return the operator which contains the stored key, or `None` if not found.
>
> - `key` - The key to the stored entry you are looking for.
>
> `who = n.fetchOwner('sales5')` #find the OP that has a storage entry called 'sales5'

`store(key, value)`→ `value`:

> Add the key/value pair to the OP's storage dictionary, or replace it if it already exists. If this value is not intended to be saved and loaded in the toe file, it can be be given an alternate value for saving and loading, by using the method `storeStartupValue` described below.
>
> - `key` - A string name for the storage entry. Use this name to retrieve the value using `fetch()`.
> - `value` - The value/object to store.
>
> `n.store('sales5', 34.5)` # stores a floating point value 34.5.
> `n.store('moviebank', op('/project1/movies'))` # stores an OP for easy access later on.

`unstore(keys1, keys2..)`→ `None`:

> For key, remove it from the OP's storage dictionary. Pattern Matching is supported as well.
>
> - `keys` - The name or pattern defining which key/value pairs to remove from the storage dictionary.
>
> `n.unstore('sales*')` # removes all entries from this OPs storage that start with 'sales'

`storeStartupValue(key, value)`→ `None`:

> Add the key/value pair to the OP's storage startup dictionary. The storage element will take on this value when the file starts up.
>
> - `key` - A string name for the storage startup entry.
> - `value` - The startup value/object to store.
>
> `n.storeStartupValue('sales5', 1)` # 'sales5' will have a value of 1 when the file starts up.

`unstoreStartupValue(keys1, keys2..)`→ `None`:

> For key, remove it from the OP's storage startup dictionary. Pattern Matching is supported as well. This does not affect the stored value, just its startup value.
>
> - `keys` - The name or pattern defining which key/value pairs to remove from the storage startup dictionary.
>
> `n.unstoreStartupValue('sales*')` # removes all entries from this OPs storage startup that start with 'sales'

### Miscellaneous

`__getstate__()`→ `dict`:

> Returns a dictionary with persistent data about the object suitable for pickling and deep copies.

`__setstate__()`→ `dict`:

> Reads the dictionary to update persistent details about the object, suitable for unpickling and deep copies.
