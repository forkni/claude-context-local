# CHOP mouseoutCHOP

## Overview

The Mouse Out CHOP forces the mouse position and button status to be driven from TouchDesigner using the incoming CHOP channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `posu` | Position U | Str | Channel name to look for that will drive the mouse U position. |
| `posv` | Position V | Str | Channel name to look for that will drive the mouse V position. |
| `lbuttonname` | Left Button | Str | Channel name to look for that will drive the mouse's left button state. |
| `rbuttonname` | Right Button | Str | Channel name to look for that will drive the mouse's right button state. |
| `mbuttonname` | Middle Button | Str | Channel name to look for that will drive the mouse's middle button state. |
| `cookalways` | Cook Every Frame | Toggle | Forces CHOP to cook every frame. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP mouseoutCHOP operator
mouseoutchop_op = op('mouseoutchop1')

# Get/set parameters
freq_value = mouseoutchop_op.par.active.eval()
mouseoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mouseoutchop_op = op('mouseoutchop1')
output_op = op('output1')

mouseoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mouseoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
