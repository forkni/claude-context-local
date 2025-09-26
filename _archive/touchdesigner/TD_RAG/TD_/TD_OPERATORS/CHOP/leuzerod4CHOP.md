# CHOP leuzerod4CHOP

## Overview

The Leuze ROD4 CHOP connects to the Leuze ROD4 laser scanner via TCP/IP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the CHOP receives information from the scanner. While off, the network connection is disconnected and no updating occurs. |
| `netaddress` | Network Address | Str | The IP address of the ROD4 scanner. |
| `port` | Network Port | Int | The network port of the scanner. |
| `rod4porotocol` | ROD4 Protocol | Menu | Selects which protocol to use. This must match the protocol the scanner was set to use in the RODplussoft setup utility for the device. You may still get some sort of data if the wrong protocol is ... |
| `inputcoordinate` | Input Coordinate | Menu | Available when using ROD4plus ASCII-Remote protocol, specifies whether to use Polar or Cartesian input coordinates. This must match the coordinate the scanner was set to use in the RODplussoft setu... |
| `outputmode` | Output Mode | Menu | Select Raw Data or Blob Tracking mode for output channels. The parameters below are only available in Blob Tracking mode. |
| `maxblobs` | Max Blobs | Int | The maximum number of blobs that can be tracked. |
| `maxpointdistance` | Max Point Distance in Blob | Float | Two measured points from the scanner are considered to be part of the same blob if they are this distance or closer to each other. Distance is specified in meters. |
| `maxblobmovement` | Max Blob Movement | Float | Specified in meters. This controls the maximum distance a blob can move between successive frames and still be considered the same 'blob'. |
| `areaofinterest` | Area of Interest | Menu | Limits the area in which blobs are tracked. |
| `maxdistance` | Max Distance | Float | Maximum distance in which blobs are tracked when Area of Interest parameter is set to Distance Based. |
| `lowerleft` | Lower Left Corner | Float | Specifies the lower left corner of the bounding box used when Area of Interest parameter is set to Bounding Box. |
| `upperright` | Upper Right Corner | Float | Specifies the upper right corner of the bounding box used when Area of Interest parameter is set to Bounding Box. |
| `allowmovementoutside` | Allow Movement Outside Area | Toggle | When this is on, blobs detected within the Area of Interest can move outside of that area and still be tracked. When this is off blobs that move outside the area of interest will stop being tracked. |
| `boundingboxmask` | Bounding Box Mask TOP | TOP | Specify a TOP to use as a mask for the bounding box when Area of Interest parameter is set to Bounding Box. Any pixel with a non-zero value will be treated as part of the area of interest, any pixe... |
| `rotate` | Rotate Incoming Coordinates | Float | Rotates all incoming coordinates where the tx and ty values are rotated around a perpendicular z-axis. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP leuzerod4CHOP operator
leuzerod4chop_op = op('leuzerod4chop1')

# Get/set parameters
freq_value = leuzerod4chop_op.par.active.eval()
leuzerod4chop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
leuzerod4chop_op = op('leuzerod4chop1')
output_op = op('output1')

leuzerod4chop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(leuzerod4chop_op)
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
