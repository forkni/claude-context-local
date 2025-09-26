# CHOP heliosdacCHOP

## Overview

Helios DAC is a laser controller.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | If turned off, the Helios DAC CHOP will stop sending data to the Helios DAC and will immediately clear its point buffer. Consider it equivalent to powering off the Helios DAC. |
| `device` | Device | StrMenu | Select the Helios DAC you want to control from this menu. |
| `queuetime` | Queue Time (Seconds) | Float | Determines the queue size of the Helios DAC CHOP point buffer and the corresponding time required to drain it. It is often useful to reduce this value when sending fewer points. |
| `xscale` | X Scale | Float | Allows the input x values to be scaled by the specified factor. |
| `yscale` | Y Scale | Float | Allows the input y values to be scaled by the specified factor. |
| `redscale` | Red Scale | Float | Allows the input r values to be scaled by the specified factor. |
| `greenscale` | Green Scale | Float | Allows the input g values to be scaled by the specified factor. |
| `bluescale` | Blue Scale | Float | Allows the input b values to be scaled by the specified factor. |
| `intensityscale` | Intensity Scale | Float | Allows the input intensity values (i) to be scaled by the specified factor. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP heliosdacCHOP operator
heliosdacchop_op = op('heliosdacchop1')

# Get/set parameters
freq_value = heliosdacchop_op.par.active.eval()
heliosdacchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
heliosdacchop_op = op('heliosdacchop1')
output_op = op('output1')

heliosdacchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(heliosdacchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
