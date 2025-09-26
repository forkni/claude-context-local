# CHOP oakselectCHOP

## Overview

Access a stream of the OAK Device CHOP

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Toggle whether the OAK Select CHOP cooks. |
| `chop` | OAK Device CHOP | CHOP | An OAK Device CHOP running a depthai pipeline. |
| `stream` | Stream | StrMenu | The name of the stream to be received. |
| `queuesize` | Queue Size | Int | For memory efficiency, this parameter controls the number of messages TouchDesigner reuses when receiving messages from OAK. See "Queue Size" below. |
| `maxitems` | Max Items | Int | This parameter helps the OAK Select CHOP output a consistent number of channels. When running an image detection pipeline, the number of detected items will vary from frame to frame, but we want To... |
| `outputformat` | Output Format | Menu | The default option "Items As Separate Channels" enables time-slicing while "Items as Separate Samples" does not. If the stream is one which automatically fills in the CHOP, then "Items as Separate ... |
| `firstsample` | Use First Sample Only | Toggle | Only use the most recently received message with the OAK Select CHOP. For example, for an IMU stream which is sending very high-frame rate data, toggling this parameter will only show the latest sa... |
| `rate` | Sample Rate | Float | The sample rate of the CHOP. The default sample rate is me.time.rate. |
| `callbacks` | Callbacks DAT | DAT | Specifies the DAT which holds the callbacks. |
| `setuppars` | Setup Parameters | Pulse | Clicking the button runs the setupParameters() callback function. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP oakselectCHOP operator
oakselectchop_op = op('oakselectchop1')

# Get/set parameters
freq_value = oakselectchop_op.par.active.eval()
oakselectchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oakselectchop_op = op('oakselectchop1')
output_op = op('output1')

oakselectchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oakselectchop_op)
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
