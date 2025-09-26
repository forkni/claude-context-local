# DAT monitorsDAT

## Overview

The Monitors DAT is a table of data about all currently detected monitors with information on the resolution, screen positioning, monitor name and description, GPU, and a flag indicating whether it is a primary monitor or not.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `callbacks` | Callbacks DAT | DAT | Runs this script once for each change to the table (ie. monitor state change). See monitorsDAT_Class for usage. |
| `bounds` | Bounds | Toggle | While on, an additional "bounds" row will be added to the table. The dimensions correspond to a bounding box around all the detected monitors. In this row, "primary" refers to the index in the tabl... |
| `monitors` | Monitors | Menu | Specify which monitors to report information about. |
| `units` | Units | Menu | Specify if the numbers are reported in Native Pixel units or DPI Scaled units. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT monitorsDAT operator
monitorsdat_op = op('monitorsdat1')

# Get/set parameters
freq_value = monitorsdat_op.par.active.eval()
monitorsdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
monitorsdat_op = op('monitorsdat1')
output_op = op('output1')

monitorsdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(monitorsdat_op)
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
