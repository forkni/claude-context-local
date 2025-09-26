# DAT ndiDAT

## Overview

The NDI DAT lists in a table and monitors all NDI sources and streams found on the network. Callbacks are provided to trigger actions when sources are added/removed/changed and when streams start/stop.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `callbacks` | Callbacks DAT | datref | Script callbacks for events relating to NDI sources and streams. |
| `extraips` | Extra Search IPs | string | By default NDI searches using mDNS, which is usually limited to locate networks. To find sources available on machines not reachable by mDNS, this parameter can be filled with a space-separated lis... |
| `persistence` | Persistence (ms) | float | Persistence affects how long an entry in the DAT stays present even after the source has disappeared. This allows for a source to disappear for a bit and then reappear without being removed from th... |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT ndiDAT operator
ndidat_op = op('ndidat1')

# Get/set parameters
freq_value = ndidat_op.par.active.eval()
ndidat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
ndidat_op = op('ndidat1')
output_op = op('output1')

ndidat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(ndidat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **7** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
