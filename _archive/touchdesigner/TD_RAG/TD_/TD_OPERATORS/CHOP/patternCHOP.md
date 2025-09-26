# CHOP patternCHOP

## Overview
The Pattern CHOP generates a sequence of samples in a channel.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `wavetype` | Type | Menu | The shape of one cycle of the pattern. |
| `length` | Length | Int | Set the number of samples for this CHOP. |
| `numcycles` | Number of Cycles | Float | Set the number of repeating cycles of the Type shapes over the Length, except for Random. |
| `steppercycle` | Step per Cycle | Float |  |
| `numsteps` | Number of Steps | Int |  |
| `bias` | Bias | Float | Makes Triangle type into a sawtooth wave, and sets the Square type variable-width. |
| `seed` | Seed | Float | The seed for the random Types. |
| `phase` | Phase | Float | Shifts the cycle. |
| `phasestep` | Phase Step per Channel | Float | Increases the phase for each channel. A Phase Step of .25 when there are 2 channels will shift the second channel to be 1/4 cycle later phase than the first phase, where if the 2 channels are used ... |
| `taper` | Taper | Float | Two parameters to multiply by a line from taper1 at the start to taper2 at the end. The default of (1 1) has no effect. |
| `taperdecay` | Taper Decay Rate | Float | An exponent that is applied to the result of the taper. |
| `amp` | Amplitude | Float | See also the Range. |
| `offset` | Offset | Float | See also the Range. |
| `fromrange` | From Range | Float | A value at each From Range will become its corresponding To Range value. |
| `torange` | To Range | Float | A value at each From Range will become its corresponding To Range value. |
| `integer` | Integer | Menu | A round-off menu to convert all numbers to integers. |
| `reverse` | Reverse | Toggle | Reverses the final order of the samples as in the Stretch CHOP. |
| `randomize` | Randomize | Pulse | When the Type parameter above is set to Random Non-Repeating Integers, this trigger will randomize all the values. |
| `channelname` | Channel Names | Str | You can creates many channels with simple patterns like chan[1-20], which generates 20 channels from chan1 to chan20, or t[xyz] which generates tx, ty and tz. See the section, Common CHOP Parameter... |
| `combine` | Combine Channels | Menu | If an input CHOP is attached, it adopts the length and sample rate of the input CHOP, and |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left right extend conditions (before/after range). |
| `right` | Extend Right | Menu | The right extend conditions (before/after range). |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |


## Usage Examples

### Basic Usage
```python
# Access the CHOP patternCHOP operator
patternchop_op = op('patternchop1')

# Get/set parameters
freq_value = patternchop_op.par.active.eval()
patternchop_op.par.active = 1
```

### In Networks
```python
# Connect operators
input_op = op('source1')
patternchop_op = op('patternchop1')
output_op = op('output1')

patternchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(patternchop_op)
```

## Technical Details

### Operator Family
**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count
This operator has **30** documented parameters.

## Navigation
- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
