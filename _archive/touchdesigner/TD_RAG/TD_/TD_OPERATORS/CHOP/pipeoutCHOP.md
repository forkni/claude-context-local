# CHOP pipeoutCHOP

## Overview

The Pipe Out CHOP can be used to transmit data out of TouchDesigner to other processes running on a remote machine using a network connection.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `mode` | Connection Mode | Menu | Set operation as server or client. |
| `address` | Server Address | Str | The computer name or IP address of the server computer. This address is a standard WWW address, such as 'foo' or 'foo.bar.com'. You can use an IP address (e.g. 100.123.45.78) or the computer's netw... |
| `port` | Server Port | Int | The network port to use. |
| `active` | Active | Toggle | When Off, data is not sent. |
| `sendinput` | Send Input | Toggle | On/off toggle for sending the data connected to the Pipe Out CHOP's input. |
| `sendsingle` | Send Current Sample Only | Toggle | This parameter is only enabled if the Pipe Out CHOP is not time sliced (See Common Page of parameters). If On, it only sends the current frame's sample. If Off, it sends all data between this frame... |
| `sample` | Single Sample | Menu | In single sample mode, this parameter determines which sample to send; the sample at frame 1 or the current sample. |
| `upload` | Send All Data | Pulse | When the button is pressed, sends all the channel names and their data once in one burst. |
| `script` | Script | Str | Use these parameters to send a one-time textport command through the pipe. |
| `sendscript` | Send Script | Pulse | Use these parameters to send a one-time textport command through the pipe. |
| `cookalways` | Cook Every Frame | Toggle | Turn this on to make sure this CHOP gets processed every frame. Usually CHOPs do not get processed every frame unless they are directly involved with some aspect of the geometry being displayed. |
| `pulse` | Send Monitor Pulses | Toggle | Sends pulses (a single null character) once a frame, to monitor the connection. This keeps the connection active, and keeps the Pipe In CHOP aware of the connection status so it can properly report... |
| `echo` | Echo Messages to Console | Toggle | Print all outgoing data to the Console which can be opened from the Dialogs menu. See this option in the Pipe In CHOP for more details. |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callback methods for each event sent. See pipeoutCHOP_Class for usage. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP pipeoutCHOP operator
pipeoutchop_op = op('pipeoutchop1')

# Get/set parameters
freq_value = pipeoutchop_op.par.active.eval()
pipeoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pipeoutchop_op = op('pipeoutchop1')
output_op = op('output1')

pipeoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pipeoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
