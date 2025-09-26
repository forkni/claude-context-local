# CHOP functionCHOP

## Overview

The Function CHOP provides more complicated math functions than found in the Math CHOP : trigonometic functions, logarithmic functions and exponential functions, and also audio decibels (dB)-power-amplitude conversions.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `func` | Function | Menu | Which math function to apply to the channels. All of the functions are unary functions except for the binary functions 'arctan (Input1/Input2)' and 'Input1 ^ Input2'. In the cases of power function... |
| `baseval` | Base Value | Float | The value of the base for 'Log base N' and 'Base ^ Input1'. parameter name /baseval |
| `expval` | Exponent Value | Float | The value of the exponent for 'Input1 ^ Exponent'. channel name /expval |
| `angunit` | Angle Units | Menu | For trigonometric functions, the angles can be measured in Degrees, Radians, or Cycles (0 to 1). |
| `match` | Match by | Menu | How to pair channels together from the two inputs for the binary functions, by name or by channel index. |
| `error` | Error Handling | Menu | How to correct samples with math errors: |
| `pinfval` | + Infinity Value | Float | Value to use when an infinity error occurs. Caused by sinh(), cosh() and tan(). |
| `ninfval` | - Infinity Value | Float | Value to use when a negative infinity error occurs. Caused by sinh() and tan(). |
| `domval` | Domain Error Value | Float | Value to use when a domain error occurs. Caused by asin(), acos(), log10(), logN(), ln() and sqrt(). |
| `divval` | Divide Error Value | Float | Value to use when a divide by zero error occurs. Caused by pow(x,y). |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP functionCHOP operator
functionchop_op = op('functionchop1')

# Get/set parameters
freq_value = functionchop_op.par.active.eval()
functionchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
functionchop_op = op('functionchop1')
output_op = op('output1')

functionchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(functionchop_op)
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
