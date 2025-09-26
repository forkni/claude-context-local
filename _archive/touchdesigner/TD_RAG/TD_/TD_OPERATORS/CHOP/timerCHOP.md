# CHOP timerCHOP

## Overview

The Timer CHOP is an engine for running timed processes. It outputs channels such as timing fractions, counters, pulses and timer states, and it calls python functions (callbacks) when various timing events occur.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Menu | The Timer cooks: Never / Always / While Running (while in "running" state) / While Playing (while in "running" state and Play is on). |
| `timecontrol` | Time Control | Menu | Sequential (timeline-independent) or Locked to Timeline. In Locked to Timeline, non-deterministic features are disabled. External CHOP Channel lets you drive the master time (.masterSeconds etc) us... |
| `deferpars` | Defer Par Changes | Toggle | When On, parameter changes like Length, Cycles and others are ignored until the next Intitalize. When Off, paraameter changes affect the timer immediately (possibly giving jumps in state). |
| `initialize` | Initialize | Pulse | (pulse parameter) Initialize is the signal to get the timer ready: sets the counters to zero (delay, timer, cycle, segment), set the output channels in the proper state, done to be off, the onIniti... |
| `start` | Start | Pulse | (pulse) Start is the signal to commence the timers counting. It will count through the delay first, then the timer length. It does an Initialize if it is not already initialized, and then starts co... |
| `lengthtype` | Length Type | Menu | Describes how the length is defined. |
| `length` | Length | Float | (float) the time-length of the timer. Set the Units menu to Seconds, Frames or Samples. |
| `lengthunits` | Length Units | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `delay` | Delay | Float | (float) after Start, the delay before the timer begins counting. |
| `delayunits` | Delay Units | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `play` | Play | Toggle | (onoff) Pauses the timer. It is basically a 0 or 1 multiplier on the Speed. |
| `speed` | Speed | Float | (default 1) Slows down or speeds up the timer. |
| `cue` | Cue | Toggle | Freezes playing at the Cue Point. |
| `cuepulse` | Cue Pulse | Pulse | Jump instantly to the Cue Point. |
| `cuepoint` | Cue Point | Float | Time (Seconds, Frames or Fraction) which the cue point is frozen to. |
| `cueunits` | Cue Units | Menu | Choose between using Samples, Frames, Seconds, Fraction(0-1) as the units for this parameter. |
| `cycle` | Cycle | Toggle | (default Off) causes the timer to loop back to 0 when it reaches the end of the cycle. |
| `cyclelimit` | Cycle Limit | Toggle | When the Cycle parameter is On, this determines if it will cycle indefinitely or cycle some maximum number of cycles. |
| `maxcycles` | Maximum Cycles | Int | When Cycle is on and Cycle Limit is on, this sets the maximum number of cycles. |
| `cycleendalert` | Cycle End Alert | Float | The number of seconds, frames or samples before a cycle, segment or done state is reached that the onCycleEndAlert() callback is called. This allows you to prepare for the next cycle, segment or ti... |
| `notifyunits` | Notify Units | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `exitendcycle` | Exit Segment at End of Cycle | Pulse | When pulsed, it will exit the cycle (and segment) at the end of the currently-playing cycle. |
| `gotoendcycle` | Go to End of Cycle | Pulse | When pulsed, it will exit the cycle (and segment) immediately. |
| `gotodone` | Go to Done | Pulse | Will immediately go to the Done state. |
| `ondone` | On Done | Menu | Determines which action to take when the timer gets to the end, ie "is done" or finished. Note there is also a onDone callback that can be used for customizing behavior. |
| `callbacks` | Callbacks DAT | DAT | The path to the DAT containing callbacks for this Timer CHOP. |
| `segdat` | Segments DAT | DAT | A table DAT that contains one row per timer (segment). The column headings can be delay or begin, length, cycle, cyclelimit, maxcycles and cycleendalert, which override the equivalent parameters. (... |
| `segmethod` | Segment Method | Menu | If the Segment Method is Serial Timers, the timers will be played back-to-back. If the Segment Method is Parallel Timers, the timers can be played at the same time, and a set of channels will be ou... |
| `segunits` | Segment Units | Menu | For the columns delay, begin, length and cycleendalert, you specify whether its seconds, frames or samples with this menu. |
| `segsendtime` | Segments End Time | Menu | Describes how the end time is calculated. |
| `channelcolumns` | Columns to Custom Channels | Str | Optional extra columns (any name) in the segments DAT can be output as extra channels (the columns must contain numbers). Specify their names in the Columns to Channels parameter. The channel name ... |
| `interpolation` | Custom Channel Interpolation | Menu | By default, custom channels step to their new value at the begin of the segment. This menu lets you interpolate to the new value linearly, or any combination of ease-in and ease-out. |
| `infocolumns` | Columns to Info DAT | Str | Optional extra columns (any name) in the segments DAT can be output to the Info DAT (attach an Info DAT to the Timer CHOP) if you specify their names in this parameter. |
| `gotoprevseg` | Go to Previous Segment | Pulse | (pulse) Jump to Previous Segment. |
| `gotonextseg` | Go to Next Segment | Pulse | (pulse) Jump to Next Segment.      Lingo     Segment  each segment acts as one timer, with delay time, length, number of cycles to repeat and other conditions.     Begin  in Parallel Timers, the nu... |
| `subrange` | Sub Range | Toggle | Turn this parameter on to limit the timer output to a subrange of the full length. |
| `substart` | Sub Start | Float | The beginning point of the sub range. |
| `substartunits` | Sub Start Units | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `subend` | Sub End | Float | The end point of the sub range. |
| `subendunits` | Sub End Units | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `subendaction` | Sub End Action | Menu | Controls the behavior once the sub range end point is reached: Loop at End, or Pause at End. |
| `outfraction` | Timer Fraction | Toggle | Outputs channel timer_fraction for each segment. |
| `outtimercount` | Timer Count | Menu | Outputs the elapsed Seconds channel as timer_seconds, Frames outputs channel as timer_frames, or Samples outputs channel as timer_samples. Because this is elapsed time, timer_frames starts at 0, as... |
| `outtimeractive` | Timer Active | Toggle | Outputs channel timer_active which is on only while the timer fraction is counting (is non-zero). |
| `outtimerpulse` | Timer Pulse | Toggle | Outputs channel timer_pulse when the timer reaches its length. |
| `outdelayfraction` | Delay Fraction | Toggle | Outputs a 0-1 fraction in delay_fraction while the delay occurs. |
| `outdelaycount` | Delay Count | Menu | Outputs the delay count in seconds, frames or samples. |
| `outinit` | Initializing | Toggle | Outputs channel initializing = 1 while the timer is initalizing (i.e. while the callback onInitialize() returns non-zero). |
| `outready` | Ready | Toggle | Outputs channel ready which is 1 after an Initialize and before a Start. |
| `outreadypulse` | Ready Pulse | Toggle | Outputs a pulse when initialization has finished and the timer is ready to start. It pulses even when the timer starts rights away after an initialization. |
| `outrunning` | Running | Toggle | Outputs channel running which is 1 after a Start and before the Done. |
| `outdone` | Done | Toggle | Outputs channel done when done or complete. |
| `outdonepulse` | Done Pulse | Toggle | Outputs channel done when the all timers have reached their completion. |
| `outcycle` | Cycles | Toggle | Outputs channel cycles, which is the number of cycles completed (In a segment), starting with 0 during the entire first cycle. If you jump to Done, cycle is incremented as if it played normally to ... |
| `outcyclepulse` | Cycle Pulse | Toggle | Outputs a pulse at the end of every cycle, even on the first and only cycle. |
| `outcycleplusfraction` | Cycles + Fraction | Toggle | Outputs channel cycle_plus_fraction, starting with 0 for entire first cycle. |
| `outseg` | Segment | Toggle | Outputs channel segment, starting with 0 for first segment. |
| `outsegpulse` | Segment Pulse | Toggle | Outputs channel segment_pulse which is a pulse at the end of each segment. |
| `outsegplusfraction` | Segment + Fraction | Toggle | Outputs channel segment_plus_fraction, starting with 0 for first segment ending at #segments at end. |
| `outlength` | Length | Menu | Outputs channel length, starting with 0 for first segment ending at #segments at end. |
| `outcumulativecount` | Cumulative Timer Count | Menu | Outputs cumulative_seconds, cumulative_frames or cumulative_samples. It is a time count that adds up all the Timer Active times for all segments since Start: it is affected by "Speed", and counts u... |
| `outplayingcount` | Playing Timer Count | Menu | Outputs playing_seconds, playing_frames or playing_samples. It is a time count that adds up all the Timer Active times for all segments since Start: it is not affected by "Speed", and counts up onl... |
| `outrunningcount` | Running Time Count | Menu | Outputs the "wall-clock" time since Start occurred, no matter what are the delays, speeds, cycles or pre-mature clicking of Go To Segment End, etc. It stops counting when Done has been reached. run... |
| `outmastercount` | Master Time Count | Menu | Outputs master_seconds, master_frames or master_samples. It is a time count that adds up all the Timer Active times for all segments since Start: it is affected by "Speed", and counts up only while... |
| `extchop` | External CHOP | CHOP | The CHOP used to control the current point in the timer. |
| `extunits` | External Units | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `extchannel` | External Channel | StrMenu | The channel that will control the current point of the timer. |
| `exttcobj` | External Timecode Object | Str | Time is specified using a timecode. Should be a reference to either a CHOP with channels 'hour', 'second', 'minute', 'frame', a DAT with a timecode string in its first cell, or a Timecode Class obj... |
| `extstartoff` | External Start Offset | Float | Specifies the external time at which the timer should start. |
| `extinitoff` | External Initialize Offset | Float | Specifies the external time at which the timer should initialize. |
| `rate` | Sample Rate | Float | The sample rate that the CHOP outputs at, which is also used when the units of Length, Delay and Cycle End Alert time are set to Samples. The default sample rate is 60 samples per second. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP timerCHOP operator
timerchop_op = op('timerchop1')

# Get/set parameters
freq_value = timerchop_op.par.active.eval()
timerchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
timerchop_op = op('timerchop1')
output_op = op('output1')

timerchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(timerchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **77** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
