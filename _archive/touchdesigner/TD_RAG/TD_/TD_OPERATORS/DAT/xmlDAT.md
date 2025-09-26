# DAT xmlDAT

## Overview

The XML DAT can be used to parse arbitrary XML and SGML/HTML formatted data.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sgml` | Parse SGML/HTML | Toggle | If enabled, the input should be in SGML/HTML format. This includes form data. If disabled, XML format is assumed. |
| `merge` | Merge | Menu | Merge and label can be used to combine two inputs of data. The second input must be XML formatted, and not SGML/HTML. These two parameters control where and how the second input is merged. |
| `mlabel` | Label | Str | Specify the element at which the merge occurs. |
| `label` | Label | Str | Element labels must match this parameter. |
| `type` | Type | Str | Element types must match this parameter. |
| `text` | Text | Str | Element text must match this parameter. |
| `name` | Name | Str | If an element contains attributes, at least one must have a name matching this parameter. |
| `value` | Value | Str | If an element contains attributes, at least one must have a value matching this parameter. |
| `plabel` | Parent Label | Str | Elements must have a parent whose label matches this parameter. |
| `ptype` | Parent Type | Str | Elements must have a parent whose type matches this parameter. |
| `ptext` | Parent Text | Str | Elements must have a parent whose text matches this parameter. |
| `pname` | Parent Name | Str | Elements must have a parent with an attribute whose name matches this parameter. |
| `pvalue` | Parent Value | Str | Elements must have a parent with an attribute whose value matches this parameter. |
| `oaname` | Name Attributes | Str | Only output attributes whos name match this parameter. |
| `oavalue` | Value Attributes | Str | Only output attributes whose value match this parameter. |
| `oclabel` | Children Labels | Str | Only output children whose label match this parameter. |
| `show` | Show | Menu | This controls how the selected elements are presented. |
| `lprefix` | Label Prefix | Toggle | This determines whether or not the element label is prefixed when outputting tables or attributes or children. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT xmlDAT operator
xmldat_op = op('xmldat1')

# Get/set parameters
freq_value = xmldat_op.par.active.eval()
xmldat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
xmldat_op = op('xmldat1')
output_op = op('output1')

xmldat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(xmldat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
