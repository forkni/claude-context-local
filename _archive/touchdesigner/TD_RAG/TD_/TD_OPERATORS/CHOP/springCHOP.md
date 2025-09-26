# CHOP springCHOP

## Overview

The Spring CHOP creates vibrations influenced by the input channels, as if a mass was attached to a spring.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `springk` | Spring Constant | Float | The strength of the spring. Larger spring constants produce higher frequency oscillations. |
| `mass` | Mass | Float | The mass of the object on the end of the spring. Higher masses will produce lower frequency oscillations, have higher amplitudes, and be more resistant to damping. |
| `dampingk` | Damping Constant | Float | The amount of damping (resistance) applied to the spring action. Higher damping causes oscillations to die off more quickly. |
| `method` | Input Effect | Menu | Determines whether the input channel(s) represents a position or a force. |
| `condfromchan` | Intial Conditions from Channel | Toggle | If On, the initial position and velocity are calculated from the values at the beginning of the channel. |
| `initpos` | Initial Position | Float | The initial position of the mass attached to the spring. |
| `initspeed` | Initial Speed | Float | The initial velocity of the mass attached to the spring. |
| `reset` | Reset | Toggle | While On resets the spring effect of the CHOP. |
| `resetpulse` | Reset Pulse | Pulse | Instantly reset the spring effect. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP springCHOP operator
springchop_op = op('springchop1')

# Get/set parameters
freq_value = springchop_op.par.active.eval()
springchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
springchop_op = op('springchop1')
output_op = op('output1')

springchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(springchop_op)
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
