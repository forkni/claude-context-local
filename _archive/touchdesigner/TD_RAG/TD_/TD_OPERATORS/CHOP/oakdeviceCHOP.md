# CHOP oakdeviceCHOP

## Overview

The OAK Device CHOP serves as the main interface to an OAK camera.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle |  |
| `sensor` | Sensor | StrMenu | Select the available OAK Device from the dropdown. |
| `refreshpulse` | Refresh Sensor List | Pulse | Refresh the list of available Sensors. |
| `initialize` | Initialize | Pulse | Initialize is the signal to get the OAK Device into a ready state: The onInitialize() callback is run and on succesfully concluding will run the createPipeline() callback. It indicates that its rea... |
| `start` | Start | Pulse |  |
| `play` | Play | Toggle | The built-in Play parameter can toggle whether or not TouchDesigner processes the new messages it receives from the camera. For example, suppose multiple OAK Select CHOPs or TOPs are connected to t... |
| `gotodone` | Go to Done | Pulse |  |
| `callbacks` | Callbacks DAT | DAT | The path to the DAT containing callbacks for this OAK Device CHOP. |
| `stream` | Stream | Sequence | Sequence of stream info parameters |
| `outinit` | Initializing | Toggle | Outputs channel initializing = 1 while the OAK Device is initalizing (i.e. while the callback onInitialize() returns non-zero). |
| `outinitfail` | Initialize Fail | Toggle | Outputs channel initialize_fail = 1 if the OAK Device ran into an error while initializing or creating the pipeline. |
| `outready` | Ready | Toggle | Outputs channel ready which is 1 after an Initialize and before a Start. |
| `outrunning` | Running | Toggle | Outputs channel running which is 1 after a Start and before the Done. |
| `outdone` | Done | Toggle | Outputs channel done = 1 when done or complete. |
| `outtimercount` | Timer Count | Menu |  |
| `outrunningcount` | Running Time Count | Menu | Outputs the "wall-clock" time since Start occurred, no matter if the device's Play parameter was turned off or not. Will stop counting when the Done state has been reached. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP oakdeviceCHOP operator
oakdevicechop_op = op('oakdevicechop1')

# Get/set parameters
freq_value = oakdevicechop_op.par.active.eval()
oakdevicechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oakdevicechop_op = op('oakdevicechop1')
output_op = op('output1')

oakdevicechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oakdevicechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
