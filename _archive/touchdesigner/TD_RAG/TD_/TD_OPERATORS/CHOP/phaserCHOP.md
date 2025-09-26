# CHOP phaserCHOP

## Overview

The Phaser CHOP does staggered (time-offset) animation interpolation. Phaser outputs one channel with multi-samples. Each sample animates from 0 to 1 over a cycle, but each sample value rises from 0 and arrives at 1 at different times.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `edge` | Edge | Float | The separation edge of the phasing between two states. A smaller edge corresponds to sharper separation according to differences in phase. Edge Parameter will not be used if there is an Edge Input. |
| `nsamples` | Num Samples | Int | Specify the size of the output. This parameter will not be used if there is a phase input. |
| `outputformat` | Output Format | Menu | Specifies the format of the output. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP phaserCHOP operator
phaserchop_op = op('phaserchop1')

# Get/set parameters
freq_value = phaserchop_op.par.active.eval()
phaserchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
phaserchop_op = op('phaserchop1')
output_op = op('output1')

phaserchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(phaserchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
