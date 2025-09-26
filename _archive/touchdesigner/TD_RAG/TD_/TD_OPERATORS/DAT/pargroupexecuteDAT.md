# DAT pargroupexecuteDAT

## Overview

TouchDesigner DAT operator.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the DAT will respond to the Parameter that is referenced. |
| `op` | OPs | OP | Specify which operator(s) the triggering parameter belongs to. |
| `pars` | Parameters | Str | Specify which parameter(s) to monitor for triggering the script. |
| `callbackmode` | Callback Mode | Menu | This controls the format of the 'curr' and 'prev' arguments to the callbacks. |
| `valuechange` | Value Change | Toggle | The onValueChange() method executes when the parameter value specified changes value in any way. It is called once each frame. |
| `onpulse` | On Pulse | Toggle | The onPulse() method executes when a 'pulse' type parameter is pulsed by clicking on it or via the Par.pulse() method. |
| `expressionchange` | Expression Change | Toggle | The onExpressionChange() method executes whenever the specified parameter's expression changes. For example, changing the expression from me.time.frame to me.time.seconds will trigger the script. |
| `exportchange` | Export Change | Toggle | The onExportChange() method executes if the export path to the specified parameter changes. For example, if the parameter is being exported to from /chopname/chan1 and that is changed so /chopname2... |
| `enablechange` | Enable Change | Toggle | The onEnableChange() method executes if the specified parameter goes from being disabled to enabled. |
| `modechange` | Mode Change | Toggle | The onModeChange() method executes if the specified parameter's mode changes between the available constant, expression, export or bind mode. |
| `custom` | Custom | Toggle | Monitor Custom Parameters. |
| `builtin` | Built-In | Toggle | Monitor Built-In parameters. |
| `edit` | Edit.. | Pulse | Clicking this opens a text editor to edit text in the DAT. |
| `file` | File | File | The filesystem path and name of the file to load. Accepts .txt and .dat files. |
| `syncfile` | Sync to File | Toggle | When On, loads the file from disk into the DAT when the projects starts.  A filename must be specified.  Turning on the option will load the file from disk immediately.  If the file does not exist,... |
| `loadonstart` | Load on Start | Toggle | When On, reloads the file from disk into the DAT when the projects starts. |
| `loadonstartpulse` | Load File | Pulse | Instantly reloads the file. |
| `write` | Write on Toe Save | Toggle | When On, writes the contents of the DAT out to the file on disk when the project is saved. |
| `writepulse` | Write File | Pulse | Instantly write the file to disk. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT pargroupexecuteDAT operator
pargroupexecutedat_op = op('pargroupexecutedat1')

# Get/set parameters
freq_value = pargroupexecutedat_op.par.active.eval()
pargroupexecutedat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pargroupexecutedat_op = op('pargroupexecutedat1')
output_op = op('output1')

pargroupexecutedat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pargroupexecutedat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
