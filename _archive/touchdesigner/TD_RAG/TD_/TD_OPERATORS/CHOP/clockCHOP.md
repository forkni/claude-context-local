# CHOP clockCHOP

## Overview

The Clock CHOP generates channels that reflect the time of year, month, week, day, hour, minute, second and millisecond.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `output` | Output | Menu | Fractions or Units affects the channel data that is output from the Clock CHOP. Fraction gives convenient 0-1 ramps and Units give integers, like 0-23 for the hours of a day. For example, use Fract... |
| `hourformat` | Hour Format | Menu | 12 hour or 24 hour - Causes the hour channel to cycle through 12 or 24 hours. Also affects the AM/PM channel. |
| `houradjust` | Hour Adjust | Float | After the Clock CHOP reads the current time, it adds Hour Adjust to pretend the current time is different than the actual current time. |
| `startref` | Start Reference | Menu | The date/time that corresponds to year 0, day 1, hour 0, minute 0. It can be relative to Jan 1, 2000 or to the time that the TouchDesigner process started. |
| `msec` | Millisecond | Str | If Output is Units, it is the current millisecond, starting at 0 at the start of a second, going up to 999 at the end of a second. If Output is Fraction, it is the current fraction of a millisecond. |
| `sec` | Second | Str | If Output is Units, it is the current second, starting at 0 for on-the-hour, going up to 59. If Output is Fraction, it is the current fraction of a second (45 seconds past the minute gives .75). |
| `min` | Minute | Str | If Output is Units, it is the current minute, starting at 0 for on-the-hour, going up to 59. If Output is Fraction, it is the current fraction of a minute (45 seconds past the minute gives .75). |
| `hour` | Hour | Str | If Output is Units, it is the current hour, starting at 0 for midnight and affected by AM/PM. If Output is Fraction, it is the current fraction of an hour (15 minutes past the hour gives .25), taki... |
| `ampm` | AM/PM | Str | 0 if before noon, 1 if after noon. |
| `wday` | Day of Week | Str | If Output is Units, it is the actual day of the week, starting with 0 for Monday and 6 for Sunday. |
| `day` | Day of Month | Str | If Output is Units, it is the actual day of the month, so on March 20, it is 20. If Output is Fraction, it is fraction of a day of the current moment, so at 6:30 PM, it is .77, taking into account ... |
| `yday` | Day of Year | Str | If Output is Units, it is the Day of year, starting with 0 for January 1. If it is Fraction, it is the same as Day of Month. |
| `week` | Week | Str | Week of the year, starting with 0 for the first week and 51 for the last week of the year. |
| `month` | Month | Str | Month of the year, starting with 1 for January and 12 for December. |
| `year` | Year | Str | If Output is Units, it is the integer year number relative to the Start Reference, starting at 0, so year 2009 is 9 by default. If Output is Fraction, it is the current fraction of a year, taking i... |
| `latitude` | Latitude | Float | Enter a latitude (hours/min north/south) of your location. (defaults to Toronto, Canada). Fractional hours are permitted. For example:  43.6532 hours and 0 minutes, is identical to 43 hours and 39 ... |
| `northsouth` | NS | Menu | Set if the Latitude value above is in the north or south hemisphere. |
| `longitude` | Longitude | Float | Enter a longitude (hours/min east/west) of your location. Fractional hours are permitted. The parameter longitude1 is hours, longitude2 is minutes. |
| `eastwest` | EW | Menu | Set if the Longitude value above is in the east or west hemisphere. |
| `moonphase` | Moon Phase | Str | Outputs the moon phase (0 to 1. .5 is a full moon, 0 and 1 are at the time of the new moon). |
| `sunphase` | Sun Phase | Str | (0 to 1, where sunrise=0, sunset = 1, and it reverses down to 0 in time for the sunrise. |
| `sunrise` | Sunrise | Str | Outputs the sunrise time (0 to 1, midnight=0, twenty-four hours later = 1). |
| `sunset` | Sunset | Str | Outputs the sunset time (0 to 1, midnight=0, twent.y-four hours later = 1). |
| `declination` | Declination | Str | (-180 to 180, degrees north/south that the sun is off the equator). |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP clockCHOP operator
clockchop_op = op('clockchop1')

# Get/set parameters
freq_value = clockchop_op.par.active.eval()
clockchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
clockchop_op = op('clockchop1')
output_op = op('output1')

clockchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(clockchop_op)
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
