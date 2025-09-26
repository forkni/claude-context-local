# DAT parameterDAT

## Overview

The Parameter DAT outputs a table of parameter names and values of an operator, including custom parameters, from any OP type. It outputs pre-evaluated expressions, and the parameter mode.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `ops` | Operators | noderef | The operators determine where to obtain the channels. Specify or more operator names or paths. Examples: wave1, slider*, constant[1-9] constant[10-19:2], ../base1. Or select the operators using the... |
| `parameters` | Parameters | string | The list of parameters names (which can include wildcards) you want to get from the OP(s). One or more parameter, or * for all parameters. You can also specify a "NOT" selection with an ^. Or selec... |
| `includeopname` | Include Op Name | toggle | Adds the OP name to the beginning of each parameter name in the table |
| `renamefrom` | Rename from | string | See Pattern Matching. |
| `renameto` | Rename to | string | See Pattern Expansion. |
| `custom` | Custom | toggle | Output the operators' custom parameters. |
| `builtin` | Built-In | toggle | Output the operators' built-in parameters. |
| `header` | Header | toggle | Outputs the column headers. |
| `name` | Name | toggle | Outputs the parameter name. |
| `value` | Value | toggle | Outputs the evaluated parameter value. |
| `eval` | Eval | toggle | Outputs the evaluated parameter value as a python object. |
| `constant` | Constant | toggle | Outputs the current constant value of the parameter. |
| `expression` | Expression | toggle | Outputs the current python expression of the parameter. |
| `export` | Export | toggle | Outputs the export path of the parameter. |
| `mode` | Mode | toggle | Outputs the current mode of the parameter (constant, expression, or export). |
| `style` | Style | toggle | Outputs what format the parameter is (eg. Float for float parameters, Menu for menu parameters etc.). |
| `tupletname` | Tuplet Name | toggle | Outputs the name of the tuplet the parameter is in. For example, tx on the Geometry COMP is a part of the 't' tuplet. |
| `size` | Size | toggle | Outputs the size of the tuplet. For example, tx on the Geometry COMP would have a tuplet size of 3 since it's a part of the 't' tuplet with 3 parameters. |
| `path` | Path | toggle | Outputs the path to the node. |
| `menuindex` | Menu Index | toggle | If the parameter is a menu, then output the selected index of the menu. |
| `minmax` | Min/Max | toggle | Outputs the minimum and maximum values of the parameter. These values will clamp the value parameter to be within the range. If clampmin is 0 then the minimum will not clamp and the row/column entr... |
| `clampminmax` | Clamp Min/Max | toggle | Outputs whether or not the parameter has a clamped min or clamped max. If true, then the values are defined by min/max columns. |
| `normminmax` | Norm Min/Max | toggle | Outputs the minimum and maximum values of the parameter in the interface (ie. the minimum and maximum values of a slider). |
| `default` | Default | toggle | Outputs the default value of the parameter |
| `enabled` | Enabled | toggle | Outputs whether the parameter is currently enabled |
| `readonly` | Read Only | toggle | Outputs whether the parameter is currently read-only |
| `section` | Section | toggle | Outputs whether the parameter has a section divider/separator (ie. line) above it. |
| `menunames` | Menu Names | toggle | Outputs a list of the menu names for any menu parameters. |
| `menulabels` | Menu Labels | toggle | Outputs a list of the menu labels for any menu parameters. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT parameterDAT operator
parameterdat_op = op('parameterdat1')

# Get/set parameters
freq_value = parameterdat_op.par.active.eval()
parameterdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
parameterdat_op = op('parameterdat1')
output_op = op('output1')

parameterdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(parameterdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **33** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
