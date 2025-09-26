# DAT soptoDAT

## Overview

The SOP to DAT allows you to extract point, vertex and primitive (e.g. polygon) data and attributes from a SOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sop` | SOP | SOP | Specify the SOP to pull data from. |
| `extract` | Extract | Menu | Specify whether to pull point data or primitive data. |
| `group` | Group | StrMenu | Point or primitive group to extract. If none specify all data will be extracted. |
| `attrib` | Attributes | StrMenu | Attributes to extract.        Point specific attributes can include P and Pw for position and weight.          Primitive specific attributes include vertices and close. Vertices list the point numb... |
| `uvforpts` | Copy Vertex UV to Points | Toggle | Copies the vertex UVs to point UVs. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT soptoDAT operator
soptodat_op = op('soptodat1')

# Get/set parameters
freq_value = soptodat_op.par.active.eval()
soptodat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
soptodat_op = op('soptodat1')
output_op = op('output1')

soptodat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(soptodat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
