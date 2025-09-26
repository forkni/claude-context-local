# CHOP ltcoutCHOP

## Overview

The LTC Out CHOP outputs "linear timecode" which is a SMPTE timecode data encoded into an audio signal. See also Linear Timecode.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `playmode` | Play Mode | Menu | Specifies the method used to output LTC, there are 2 options. |
| `play` | Play | Toggle | Specifies whether the count should increment or hold steady. |
| `cue` | Cue | Toggle | While set to on, the output is held at the specified initial values below. |
| `cuepulse` | Cue Pulse | Pulse | When pulsed, the output is set to the initial values below. |
| `frame` | Frame | Int | The initial frame to count from. |
| `second` | Second | Int | The initial second to count from. |
| `minute` | Minute | Int | The initial minute to count from. |
| `hour` | Hour | Int | The initial hour to count from. |
| `framerate` | Frame Rate | Float | The number of complete frame messages per second the signal encodes. It is usually between 24 and 30. |
| `dropframe` | Drop Frame Numbering | Toggle | Drop frame numbering converts 30 fps time code to the 29.97 fps NTSC standard. Frame numbers 0 and 1 are skipped during the first second of every minute, except multiples of 10 minutes. |
| `highfpsbehaviour` | High FPS Behaviour | Menu | Specifies the method for counting frame numbers when the set frame rate is higher than the LTC frame rate. Menu enabled only when the set frame rate is a multiple of the LTC frame rate. This menu h... |
| `timecodeop` | Timecode Object/CHOP/DAT | Str | Set the LTC output value with a reference to a timecode. Should be a reference to either a CHOP with channels 'hour', 'second', 'minute', 'frame', a DAT with a timecode string in its first cell, or... |
| `audiorate` | Audio Rate | Float | This audio sampling rate of the output signal. |
| `user1` | User Data 1 | Int | Send this value in the bits reserved for User Data 1. |
| `user2` | User Data 2 | Int | Send this value in the bits reserved for User Data 2. |
| `user3` | User Data 3 | Int | Send this value in the bits reserved for User Data 3. |
| `user4` | User Data 4 | Int | Send this value in the bits reserved for User Data 4. |
| `user5` | User Data 5 | Int | Send this value in the bits reserved for User Data 5. |
| `user6` | User Data 6 | Int | Send this value in the bits reserved for User Data 6. |
| `user7` | User Data 7 | Int | Send this value in the bits reserved for User Data 7. |
| `user8` | User Data 8 | Int | Send this value in the bits reserved for User Data 8. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP ltcoutCHOP operator
ltcoutchop_op = op('ltcoutchop1')

# Get/set parameters
freq_value = ltcoutchop_op.par.active.eval()
ltcoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
ltcoutchop_op = op('ltcoutchop1')
output_op = op('output1')

ltcoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(ltcoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **27** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
