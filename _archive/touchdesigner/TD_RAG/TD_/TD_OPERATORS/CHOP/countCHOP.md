# CHOP countCHOP

## Overview

The Count CHOP counts the number of times a channel crosses a trigger or release threshold.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `threshold` | Release = Trigger Threshold | Toggle | If on, the trigger threshold is also used as the release threshold. |
| `threshup` | Trigger Threshold | Float | The channel level that must be exceeded in order to trigger a count. |
| `threshdown` | Release Threshold | Float | A release count is triggered when the channel level drops below this threshold. |
| `retrigger` | Re-Trigger Delay | Float | The amount of time after a trigger point that a new trigger may occur. |
| `retriggerunit` | Re-Trigger Delay Unit | Menu |  |
| `triggeron` | Trigger On | Menu | Determines whether a trigger occurs on an increasing slope or decreasing slope when passing the trigger threshold. A release will occur on the opposite slope. |
| `output` | Limit | Menu | Select limit options such as loop and/or clamp from the menu. The value will remain in the range from Min to Max. |
| `limitmin` | Limit Minimum | Float | The minimum allowed count number. |
| `limitmax` | Limit Maximum | Float | The maximum allowed count number. |
| `offtoon` | Off to On | Menu | The operation to perform when a trigger event (off to on) occurs. |
| `on` | While On | Menu | The operation to perform while the input remains triggered (on). |
| `ontooff` | On to Off | Menu | The operation to perform when a release event (on to off) occurs. |
| `off` | While Off | Menu | The operation to perform while the input is not triggered (off).      Note: The scripts are run relative to the parent node of this CHOP, as if the script is in the node above this CHOP. |
| `resetcondition` | Reset Condition | Menu | This menu determines how the Reset input triggers a reset of the channel(s). |
| `resetvalue` | Reset Value | Float | The channel(s) is set to this value when reset. |
| `reset` | Reset | Toggle | When On resets the channel(s) to the Reset Value. The Count CHOP will only begin counting again when Reset is Off. |
| `resetpulse` | Reset Pulse | Pulse | Instantly resets the channel(s) to the Reset Value. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP countCHOP operator
countchop_op = op('countchop1')

# Get/set parameters
freq_value = countchop_op.par.active.eval()
countchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
countchop_op = op('countchop1')
output_op = op('output1')

countchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(countchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
