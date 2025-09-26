# CHOP blobtrackCHOP

## Overview

The Blob Track CHOP allows tracking blobs in 2D point data

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the CHOP receives information from the input. While off, no processing occurs. Existing blobs will remain. |
| `searchmode` | Search Mode | Int | Controls how searching for blobs is done across all the points. |
| `maxblobs` | Max Blobs | Int | The maximum number of blobs that can be tracked. |
| `maxpointdistance` | Max Point Distance in Blob | Float | Two measured points from the input are considered to be part of the same blob if they are this distance or closer to each other. |
| `maxblobmovement` | Max Blob Movement | Float | This controls the maximum distance a blob can move between successive frames and still be considered the same 'blob'. |
| `areaofinterest` | Area of Interest | Menu | Limits the area in which blobs are tracked. Points outside the area of interest are ignored. |
| `center` | Center | XY | The center of the area of interest. |
| `size` | Size | WH | The size of the area of interest. |
| `rotate` | Rotate | Float | Rotate the area of interest. |
| `allowmovementoutside` | Allow Movement Outside Area | Toggle | When this is on, blobs detected within the Area of Interest can move outside of that area and still be tracked. When this is off blobs that move outside the area of interest will stop being tracked. |
| `outputcentroid` | Output Centroid | Toggle | Include the centroid of detected blobs as part of the output channels. |
| `outputvelocity` | Output Velocity | Toggle | Include the velocity of detected blobs as part of the output channels. |
| `minblobpoints` | Min Points per Blob | Int | Minimum number of points that must be near each other to form a blob. Use to help filter out false positives. |
| `blobinittime` | Blob Init Time (s) | Float | Amount of time a blob must be detected to be considered trustworthy. Use to help filter out false positives. A blob will only be output if it's been detected for at least time amount of time. |
| `lostblobtimeout` | Lost Blob Timeout (s) | Float | The amount of time before a blob that has been lost is removed from the output. |
| `predicttype` | Blob Movement Prediction Type | Menu | With prediction enabled, blobs from the last frame have their new position predicted before being matched to the current frame. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP blobtrackCHOP operator
blobtrackchop_op = op('blobtrackchop1')

# Get/set parameters
freq_value = blobtrackchop_op.par.active.eval()
blobtrackchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
blobtrackchop_op = op('blobtrackchop1')
output_op = op('output1')

blobtrackchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(blobtrackchop_op)
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
