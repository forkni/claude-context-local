# DAT folderDAT

## Overview

The Folder DAT lists the files and subfolders found in a file system folder and monitors any changes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When off, the DAT outputs a single-row table with only the headings, useful when dormant or when sending the DAT to a Replicator COMP. |
| `rootfolder` | Root Folder | Folder | The folder in the filesystem whose contents will be displayed in the DAT list. |
| `refresh` | Refresh | Toggle | When on, it monitors the specified folder(s) of the filesystem. |
| `refreshpulse` | Refresh Pulse | Pulse | The pulse button reads the folder contents once. |
| `async` | Asynchronous Update | Toggle | When on, the update happens asynchronously from the main thread so it doesn't make TouchDesigner drop frames or pause. As a result, the Folder DAT way not update its data within the next frame afte... |
| `nameformat` | Name Format | Menu | Select whether to include the filename extension or not. |
| `dateformat` | Date Format | Menu | The format used to display the item's dates in the table. |
| `type` | Type | Menu | The types of contents to display. |
| `folders` | Folders | Str | Use Pattern Matching to specify which folders are included.  Matches the folder path.  Delimiters used are spaces and commas.  To match spaces, enclose the entire search term in double quotes. |
| `names` | Names | Str | Use Pattern Matching to specify which names are included.  Delimiters used are spaces and commas.  To match spaces, enclose the entire search term in double quotes. |
| `allextensions` | All Extensions | Toggle | Includes all file extensions. |
| `imageextensions` | Image Extensions | Toggle | Includes image contents that are supported by TouchDesigner. See supported File Types. |
| `movieextensions` | Movie Extensions | Toggle | Includes movie contents that are supported by TouchDesigner. See supported File Types. |
| `audioextensions` | Audio Extensions | Toggle | Includes audio contents that are supported by TouchDesigner. See supported File Types. |
| `extensions` | Extensions | Str | Use Pattern Matching to specify which extensions are included. Extensions listed here should not include the period. E.g *txt, not*.txt. |
| `subfolders` | Include Subfolders | Toggle | Includes the subfolders from the root folder specified. |
| `mindepth` | Minumum Depth | Int | Set a minmum depth for the subfolders the Folder DAT should recursively search through. |
| `limitdepth` | Limit Depth | Toggle | Turns on the Maximum Depth parameter to limit searching through subfolders. Turning this toggle off will search through all subtrees. |
| `maxdepth` | Maximum Depth | Int | Set the maximum depth for the subfolders the Folder DAT should recursively search through. |
| `namecol` | Name | Toggle | The name of the folder or file. In the case of a file this includes the extension. ie. myfile.txt |
| `basenamecol` | Base Name | Toggle | The name of the folder or file. In the case of a file this form does not includes the extension. ie. myfile |
| `extensioncol` | Extension | Toggle | The file extension of the file, blank for folders. ie. txt |
| `typecol` | Type | Toggle | The type of file as reported by the operating system. |
| `sizecol` | Size | Toggle | The size of the file in Bytes. Folders do not report any size. |
| `depthcol` | Depth | Toggle | How many folders deep the item is found from the Root Folder. Items on the Root Folder level have a depth of 0. |
| `foldercol` | Folder | Toggle | The path of the folder, or in the case of a file, the path of the folder the file is found in. |
| `pathcol` | Path | Toggle | The full path to the folder or file. |
| `relpathcol` | Relative Path | Toggle | The relative path to the folder or file from the Root Folder. |
| `datecreatedcol` | Date Created | Toggle | The date of creation. |
| `datemodifiedcol` | Date Modified | Toggle | The date of most recent modification. |
| `dateaccessedcol` | Date Accessed | Toggle | The date of most recent access or opening. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT folderDAT operator
folderdat_op = op('folderdat1')

# Get/set parameters
freq_value = folderdat_op.par.active.eval()
folderdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
folderdat_op = op('folderdat1')
output_op = op('output1')

folderdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(folderdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **35** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
