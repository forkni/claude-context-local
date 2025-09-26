# CHOP realsenseCHOP

## Overview

DEPRECATED: The RealSense CHOP references a RealSense TOP camera and fetches tracking data from it.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When enabled, actively fetches skeleton tracking data from a RealSense TOP. |
| `top` | RealSense TOP | TOP | The RealSense TOP camera to fetch skeleton data from. |
| `skeletons` | Skeletons | Toggle | When enabled, displays the skeleton channels. |
| `maxplayers` | Max Players | Int | Specify the max number of players tracked. |
| `pos` | Image Position Pixels | Toggle | When enabled, will display positions of each landmark in image pixels as x/y channels. |
| `norm` | Image Positions Normalized | Toggle | When enabled, will display normalized position values of each landmark as u/v channels. |
| `confidence` | Confidence | Toggle | When enabled, will display the confidence value of each landmark. When the confidence channel value is 0 the landmark is untracked. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP realsenseCHOP operator
realsensechop_op = op('realsensechop1')

# Get/set parameters
freq_value = realsensechop_op.par.active.eval()
realsensechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
realsensechop_op = op('realsensechop1')
output_op = op('output1')

realsensechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(realsensechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
