# CHOP etherdreamCHOP

## Overview

EtherDream is a laser controller.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | If turned off, the EtherDream CHOP will stop sending data to the EtherDream and will immediately clear its point buffer. Consider it equivalent to powering off the EtherDream. |
| `netaddress` | Network Address | Str | Set this parameter to the network address that both the EtherDream and the user's computer are connected to. It should have the following format: xxx.xxx.xx.xxx    To determine the required network... |
| `port` | Network Port | Int | By default, the EtherDream uses TCP Port 7765. Firewall settings may need to be adjusted to allow for the EtherDream CHOP to properly communicate with the EtherDream. |
| `queuetime` | Queue Time | Float | Determines the queue size of the EtherDream point buffer and the corresponding time required to drain it. It is often useful to reduce this value when sending fewer points. |
| `queueunits` | Queue Units | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `xscale` | X Scale | Float | Allows the input x values to be scaled by the specified factor. |
| `yscale` | Y Scale | Float | Allows the input y values to be scaled by the specified factor. |
| `redscale` | Red Scale | Float | Allows the input r values to be scaled by the specified factor. |
| `greenscale` | Green Scale | Float | Allows the input g values to be scaled by the specified factor. |
| `bluescale` | Blue Scale | Float | Allows the input b values to be scaled by the specified factor. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP etherdreamCHOP operator
etherdreamchop_op = op('etherdreamchop1')

# Get/set parameters
freq_value = etherdreamchop_op.par.active.eval()
etherdreamchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
etherdreamchop_op = op('etherdreamchop1')
output_op = op('output1')

etherdreamchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(etherdreamchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
