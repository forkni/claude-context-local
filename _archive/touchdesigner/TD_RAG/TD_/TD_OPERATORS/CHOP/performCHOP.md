# CHOP performCHOP

## Overview

The Perform CHOP outputs many channels like frames-per-second, describing the current state of the TouchDesigner process.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `fps` | Frames per Second | Toggle | The number of frames rendered in the last second. |
| `msec` | Frame Time | Toggle | Amount of time each frame takes to cook in msec. |
| `cook` | Cook | Toggle | Is equal to 1 when a frame is cooked and equal to 0 when a frame is skipped.  It is often useful to view this channel in a Trail CHOP to see when frames are skipped (dropped). |
| `droppedframes` | Dropped Frames | Toggle | The number of frames dropped between the last frame and the current frame. |
| `mvreadahead` | Movie Read Ahead Misses | Toggle | How many times the movie read ahead failed to maintain the number of specified Read Ahead frames. |
| `gpumemused` | GPU Mem Used (MB) | Toggle | Amount of GPU memory used (in megabytes). |
| `totalgpumem` | Total GPU Mem (MB) | Toggle | Total amount of GPU memory available on the system (in megabytes). |
| `activeops` | Total Active OPs | Toggle | How many OPs are actively cooking. |
| `deactivatedops` | Total Deactivated OP Calls | Toggle | Number of calls to cook a component that has its Cooking Flag turned off. |
| `totalops` | Total OPs | Toggle | Total number of OPs in the .toe file. |
| `cpumemused` | CPU Mem Used (MB) | Toggle | Amount of CPU memory used (in megabytes). |
| `cookstate` | Cook State | Toggle | Monitors which frames actually cooked. Pass the Perform CHOP to a Trail CHOP to properly see the trail of frames that did and did not cook. (It appears as always 1 because the viewer is displaying ... |
| `cookrealtime` | Cook Realtime | Toggle | Monitors the state of the realtime flag, determining if TouchDesigner is running in realtime mode or not. |
| `cookrate` | Cookrate | Toggle | The global target cook rate (frames per second) of the project. This is the frames per second of the root component, root.time.rate, typically 60, though due to frames taking too long to cook, the ... |
| `timeslicestep` | Time Slice Step | Toggle | The number of frames that TouchDesigner stepped forward for the current cook. It's the length of the Time Slice in frames. It will be equal to 1 when the system is taking 1000/root.time.rate msec o... |
| `timeslicemsec` | Time Slice Milliseconds | Toggle | The length of the current Time Slice in milliseconds. |
| `performmode` | Perform Mode | Toggle | Monitors the state of Perform Mode. |
| `performfocus` | Perform Window Focus | Toggle | Monitors if the Perform Window currently has focus or not. |
| `gputemp` | GPU Temperature (Slow) | Toggle | Monitors the temperature of the system's GPUs. |
| `aclinestatus` | AC Line Status | Toggle | Indicates if the laptop's AC Charger is plugged in and active. 1 if AC line is detected, 0 otherwise. |
| `batterycharging` | Battery Charging | Toggle | Indicates if the battery is being charged. 1 if charging, 0 otherwise. |
| `batterylife` | Battery Life | Toggle | Indicated charge remaining in battery, 1 is battery full, 0 is battery empty. |
| `batterytime` | Battery Time | Toggle | Estimated time remaining in battery charge. Only works if AC Line is disconnected and battery is not being charged. |
| `activeexpressions` | Active Expressions | Toggle | The number of active python expressions found in the project. |
| `optimizedexpression` | Optimized Expressions | Toggle | The number of python expression that have been optimized, see Optimized Python Expressions. |
| `cachedexpressions` | Expressions Using Cache | Toggle | The number of python expression that have been cached, see Optimized Python Expressions. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP performCHOP operator
performchop_op = op('performchop1')

# Get/set parameters
freq_value = performchop_op.par.active.eval()
performchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
performchop_op = op('performchop1')
output_op = op('output1')

performchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(performchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **32** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
