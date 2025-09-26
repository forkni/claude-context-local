# DAT cplusplusDAT

## Overview

The CPlusPlus DAT allows you to make custom DAT operators by writing your own plugin using C++.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `plugin` | Plugin Path | filepath dll load | The path to the plugin you want to load. |
| `reinit` | Re-Init Class | joinpair toggle | When this parameter is On 1, it will delete the instance of the class created by the plugin, and create a new one. |
| `reinitpulse` | Re-Init Class | nolabel button | Instantly reinitialize the class. |
| `unloadplugin` | Unload Plugin | toggle | When this parameter goes above 1, it will delete the instance of the class created by the plugin and unload the plugin. If multiple DATs have loaded the same plugin they will all need to unload it ... |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT cplusplusDAT operator
cplusplusdat_op = op('cplusplusdat1')

# Get/set parameters
freq_value = cplusplusdat_op.par.active.eval()
cplusplusdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
cplusplusdat_op = op('cplusplusdat1')
output_op = op('output1')

cplusplusdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(cplusplusdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **8** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
