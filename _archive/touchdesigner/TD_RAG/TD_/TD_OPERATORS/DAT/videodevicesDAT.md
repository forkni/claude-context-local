# DAT videodevicesDAT

## Overview

The Video Devices DAT provides information about all detected video devices.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `driver` | Driver | Menu | Menu of available drivers, table will only include devices belonging to selected driver. |
| `alldrivers` | All Drivers | Toggle | While on, the table will display devices from all available drivers. |
| `input` | Input Devices | Toggle | Toggle to include input devices. |
| `output` | Output Devices | Toggle | Toggle to include output devices. |
| `callbacks` | Callbacks DAT | DAT | Runs this script once for each change to the table (ie. device state change). |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT videodevicesDAT operator
videodevicesdat_op = op('videodevicesdat1')

# Get/set parameters
freq_value = videodevicesdat_op.par.active.eval()
videodevicesdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
videodevicesdat_op = op('videodevicesdat1')
output_op = op('output1')

videodevicesdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(videodevicesdat_op)
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
