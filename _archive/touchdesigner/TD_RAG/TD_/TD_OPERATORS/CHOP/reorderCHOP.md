# CHOP reorderCHOP

## Overview

The Reorder CHOP re-orders the first input CHOP's channels by numeric or alphabetic patterns.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Method | Menu | There are three different reordering methods. You can enter a Numeric Pattern, a Character Pattern, or use an optional second input CHOP as an order reference. |
| `orderref` | Order Reference | Menu | Only enabled if a second input is present. Specifies the format of that input. |
| `numpattern` | Numeric Pattern | Str | This reorders the channels by channel number. Normally the index order is 0,1,2,3... etc.. The first channel is at index 0. Standard numeric patterns are allowed such as "0-6:1,2" or "!*:1,3". |
| `charpattern` | Character Pattern | StrMenu | This reorders the channels by channel name. Standard character patterns are allowed such as "ch[XYZ]" or "chan[1-15:2,5]" or "chan? ch*". See Scope and Channel Name Matching Options p. 102 in the s... |
| `seed` | Seed | Float | Only available if Channel Reorder Method is set to "Random", specify any number, integer or non-integer, which starts the random number generator. Each number gives completely different patterns, b... |
| `nvalue` | N Value | Int | Only available if Channel Reorder Method is set to "Merge N Groups" or "Every Nth Channel". |
| `rempos` | Remaining Position | Menu | Channels that do not match are called "remaining" and can also be ordered: they can be placed at the At Beginning or At Ending (in reference to the position of the matched channels). |
| `remorder` | Remaining Order | Menu | The channels that did not match can have the Same as Input order, or can be sorted AlphaNumerically. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP reorderCHOP operator
reorderchop_op = op('reorderchop1')

# Get/set parameters
freq_value = reorderchop_op.par.active.eval()
reorderchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
reorderchop_op = op('reorderchop1')
output_op = op('output1')

reorderchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(reorderchop_op)
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
