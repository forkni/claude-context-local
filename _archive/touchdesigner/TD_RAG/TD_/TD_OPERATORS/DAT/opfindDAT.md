# DAT opfindDAT

## Overview

The OP Find DAT traverses the component hierarchy starting at one component and looking at all nodes within that component, and outputs a table with one row per node that matches criteria the user chooses.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `activecook` | Active Cook | Menu | Determines when to cook the DAT. |
| `cookpulse` | Cook Pulse | Pulse | Manually force the OP Find DAT to update. |
| `component` | Component | COMP | The path to the component where the search starts from. |
| `includecomponent` | Include Component | Toggle | Include the component the search starts from in the search itself. |
| `includewired` | Include Wire Hierarchy | Toggle | Any components wired to the starting component are included in the search. |
| `mindepth` | Minimum Depth | Int | Set a minmum depth for the sub-components the OP Find DAT should recursively search through. |
| `limitmaxdepth` | Limit Max Depth | Toggle | Turns on the Maximum Depth parameter to limit searching through sub-components. Turning this toggle off will search through all sub-networks. |
| `maxdepth` | Maximum Depth | Int | Set the maximum depth for the sub-components the OP Find DAT should recursively search through. |
| `limitmaxops` | Limit Max Operators | Toggle | Limit the total number of operators iterated in the search. |
| `maxops` | Maximum Operators | Int | Number of operators the search is limited to. |
| `objects` | Object COMPs | Toggle | Include Object COMPs, like Geo COMP, in the search. |
| `panels` | Panel COMPs | Toggle | Include Panel COMPs, like Container COMP, in the search. |
| `other` | Other COMPs | Toggle | Include other type COMPs, like Base COMP, in the search. |
| `tops` | TOPs | Toggle | Include DAT family operators in the search. |
| `chops` | CHOPs | Toggle | Include CHOP family operators in the search. |
| `sops` | SOPs | Toggle | Include SOP family operators in the search. |
| `mats` | MATs | Toggle | Include MAT family operators in the search. |
| `dats` | DATs | Toggle | Include DAT family operators in the search. |
| `casesensitive` | Case Sensitive | Toggle | Use case sensitivity in all pattern matching below. |
| `combinefilters` | Combine Filters | Menu | Combine 'All', 'Any' or 'Custom' of the filters below to get a match. 'Custom' allows for specifying a subselection of filters with 'or' and 'and' keywords. |
| `customcombine` | Custom Combine | Str | Specify which filters to combine in the search. |
| `namefilter` | Name | Str | Use the operator's names like 'wave1', 'wave2', etc. |
| `typefilter` | Type | Str | Use names like waveCHOP and panelexecuteDAT. Look at the column Type to see the syntax. |
| `parentshortcutfilter` | Parent Shortcut | Str | Only match operators that include the here specified Parent Shortcut. |
| `opshortcutfilter` | OP Shortcut | Str | Only match operators that include the here specified OP Shortcut. |
| `pathfilter` | Path | Str | Specify a path that the operator should be located in. |
| `parentfilter` | Parent Path (relative) | Str | Specify a relative parent path that operators should be located in. This is a filter option on the parentPath column of this DAT that can be enabled by toggling the Parent Path parameter on this DA... |
| `excludefilter` | Exclude Path (relative) | Str | Specify a relative path that should be excluded from the search. |
| `wirepathfilter` | Wire Path | Str |  |
| `commentfilter` | Comment | Str | Only match operators that include the here specified comment string. |
| `tagsfilter` | Tags | Str | Only match operators that match the here specified tags. Multiple tags can be searched for as a space seperated list. |
| `textfilter` | DAT Text | Str | Only include operators that - in the case of being from the DAT family - match specified string in their content. |
| `parnamefilter` | Par Name | Str | Only match operators with specified parameter name.  Parameters must match ALL of name, value and expression to be included. |
| `parvaluefilter` | Par Value | Str | Only include operators that match specified parameter value. Parameters must match ALL of name, value and expression to be included. |
| `parexpressionfilter` | Par Expression | Str | Only include operators that match specified parameter expression string. Parameters must match ALL of name, value and expression to be included. |
| `parnondefaultonly` | Par Non-Default Only | Toggle | Only match with parameters that are non-default values. |
| `legacycols` | Use Legacy Columns | Toggle | Use only when expecting column headers to be named with legacy titles. |
| `idcol` | ID | Toggle | An integer that uniquely defines the node in this process. It's the same number for the duration of the process, but may be different when you run the process again. |
| `namecol` | Name | Toggle | Inlcude the name of the operator in the result table. |
| `typecol` | Type | Toggle | Include the operator type in the result table. For example rampTOP. |
| `parentshortcutcol` | Parent Shortcut | Toggle | Include the operator's Parent Shortcut in the result table. |
| `opshortcutcol` | OP Shortcut | Toggle | Include the operator's OP Shortcut in the result table. |
| `pathcol` | Path | Toggle | Include the operator's path in the result table. |
| `relpathcol` | Relative Path | Toggle | Include the operator's, relative to the search root, path in the result table. |
| `parentpath` | Parent Path | Toggle | Include the parent path. |
| `wirepathcol` | Wire Path | Toggle | Include the operator's wire path in the result table. |
| `depthcol` | Depth | Toggle | Include a column showing the relative depth to the root path of the found operator. |
| `cooktimescol` | Cook Times | Toggle | Include cook-time of found operators. |
| `tagscol` | Tags | Toggle | Include the operator's tags. |
| `genprop` | General Properties | Toggle | Include the operator's name, id, isCOMP, node position, node size and dock id in the result table. |
| `cputime` | CPU Time | Toggle | Include the operator's CPU cooktime in the result table. |
| `gputime` | GPU Time | Toggle | Include the operator's GPU cooktime in the result table. |
| `cpumem` | CPU Memory | Toggle | Include the operator's CPU memory in the result table. |
| `gpumem` | GPU Memory | Toggle | Include the operator's GPU memory in the result table. |
| `children` | Children | Toggle | Include the children of the operator in the result table. |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callbacks for each event received. See opfindDAT_Class for usage. |
| `convertbool` | Convert Bool to Int | Toggle | For boolean logic values, the value will be '1' or '0'. When this parameter is Off, they will be 'True" or 'False'. |
| `convertnone` | Convert None to Empty | Toggle | For 'None' values, the value will be converted to Empty. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT opfindDAT operator
opfinddat_op = op('opfinddat1')

# Get/set parameters
freq_value = opfinddat_op.par.active.eval()
opfinddat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
opfinddat_op = op('opfinddat1')
output_op = op('output1')

opfinddat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(opfinddat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **62** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
