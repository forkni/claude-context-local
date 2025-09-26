# CHOP analyzeCHOP

## Overview

The Analyze CHOP looks at the values of all the values of a channel, and for all functions except "Duplicates", outputs a single-number result into the output. When Duplicates is selected, 2 extra channels per input channel are created indicating the number of duplicates and their first sample index.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `function` | Function | Menu | This menu determines the function applied to the channel. |
| `allowstart` | Allow Start Peaks | Toggle | If the values of the first 2 samples are v0 and v1, if v0 > v1, count it as a peak. The default is to never count the first sample as a peak. |
| `allowend` | Allow End Peaks | Toggle | If the values of the last 2 samples are vn and vm, if vm > vn, count it as a peak. The default is to never count the last sample as a peak. |
| `nopeakvalue` | No Peak Value | Float | When no peaks are found, make this number (default is -1) the result that is output. When the Function is set to Peak Index or Peak Value, it is a way to detect that no peaks were found. |
| `valleys` | Analyze Valleys vs Peaks | Toggle | Analyze instead for the First Valley, Highest Valley, and Lowest Valley, when the corresponding Function menu options are chosen. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP analyzeCHOP operator
analyzechop_op = op('analyzechop1')

# Get/set parameters
freq_value = analyzechop_op.par.active.eval()
analyzechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
analyzechop_op = op('analyzechop1')
output_op = op('output1')

analyzechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(analyzechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
