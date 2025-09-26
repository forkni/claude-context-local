# CHOP envelopeCHOP

## Overview

The Envelope CHOP outputs the maximum amplitude in the vicinity of each sample of the input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Type | Menu | The two methods of calculating the envelope: |
| `bounds` | Envelope Bounds | Menu |  |
| `width` | Envelope Width | Float | The width of the window to use in the envelope calculation. Adjust this width to capture as many features of the input as needed. It is expressed in Units. |
| `widthunit` | Envelope Width Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `interp` | Interpolate | Menu |  |
| `norm` | Normalize Power Envelope | Toggle | Keeps the total power in the signal constant when adjusting the Envelope Width. |
| `resample` | Resample Envelope | Toggle | When On, the envelope can be resampled to the Sample Rate specified in the parameter below. |
| `samplerate` | Sample Rate | Float | Set the sample rate to resample the envelope to when the Resample Envelope parameter above is On. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP envelopeCHOP operator
envelopechop_op = op('envelopechop1')

# Get/set parameters
freq_value = envelopechop_op.par.active.eval()
envelopechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
envelopechop_op = op('envelopechop1')
output_op = op('output1')

envelopechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(envelopechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
