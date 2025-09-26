# CHOP joinCHOP

## Overview

The Join CHOP takes all its inputs and appends one CHOP after another.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `blendmethod` | Method | Menu | The blend method to produce a seamless sequence: |
| `blendfunc` | Shape | Menu | The blend interpolation shape to use. See Shape in the Cycle CHOP. |
| `blendbyinput` | First Input Specifies Blend Regions | Toggle | When this is checked on, the first input can be a multi-channel input which specifies blend regions for the remaining inputs into the Join CHOP. Channel 1 of input0 is used to blend between input1 ... |
| `blendregion` | Region | Float | The size of the blend region. |
| `blendregionunit` | Blend Region Unit | Menu |  |
| `blendbias` | Bias | Float | Which segment to favour when blending: the previous (-1), the next (+1) or neither (0). |
| `match` | Match by | Menu | Match channels between inputs by index or by name. |
| `step` | Step | Float | If set to 1, the next segment will be shifted up or down so that it begins where the last segment ended. |
| `stepscope` | Step Scope | Str | The names of channels that use Step. |
| `blendscope` | Blend Scope | Str | The names of the channels that should be blended. Other channels will not be blended. |
| `transscopex` | Translate X Blend | Str | The names of channels that will be translation-blended. Each string field contains a list of its component channels, such as *tx,*ty and *tz. |
| `transscopey` | Translate Y Blend | Str | The names of channels that will be translation-blended. Each string field contains a list of its component channels, such as *tx,*ty and *tz. |
| `transscopez` | Translate Z Blend | Str | The names of channels that will be translation-blended. Each string field contains a list of its component channels, such as *tx,*ty and *tz. |
| `quatrot` | Quaternion Blend | Toggle | Use quaternion blending on rotation channels. |
| `shortrot` | Shortest Path Rotation Blending | Toggle | If enabled, compensates. |
| `rotscope` | Rotation Scope | Str | Enabled when Shortest Path Rotation Blending is turned on. |
| `cyclelen` | Cycle Length | Float | Enabled when Shortest Path Rotation Blending is turned on. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP joinCHOP operator
joinchop_op = op('joinchop1')

# Get/set parameters
freq_value = joinchop_op.par.active.eval()
joinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
joinchop_op = op('joinchop1')
output_op = op('output1')

joinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(joinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
