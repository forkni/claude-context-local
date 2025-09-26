# DAT evaluateDAT

## Overview

The Evaluate DAT changes the cells of the incoming DAT using string-editing and math expressions.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `dat` | Input Data DAT | DAT | An alternative DAT table to be used in place of an input table. |
| `datexpr` | Expressions DAT | DAT | An alternative DAT table to be used in place of a formula table. |
| `output` | Output | StrMenu | Determines what format will be used for output from the DAT. |
| `expr` | Expression | Str | Expression used to evaluate each cell if an Expression input or DAT is not supplied. |
| `outputsize` | Output Table Size | Menu | If the Output Table Size parameter is Strings, Expressions, or Commands, and there is a second input, you can choose the output table size to be either Input DAT or the Formula DAT.  If the Formula... |
| `dependency` | Monitor Data Dependencies | Toggle | If the Output parameter is set to Strings or Expressions, the DAT will monitor any nodes used by the data, as well as check for time dependencies, and cook accordingly. This toggle is on by default... |
| `backslash` | Convert Backslash Characters | Toggle | Will convert things like   to newlines,  to tabs etc. Note that  ,  will be converted to spaces if the input DAT is a table. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT evaluateDAT operator
evaluatedat_op = op('evaluatedat1')

# Get/set parameters
freq_value = evaluatedat_op.par.active.eval()
evaluatedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
evaluatedat_op = op('evaluatedat1')
output_op = op('output1')

evaluatedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(evaluatedat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
