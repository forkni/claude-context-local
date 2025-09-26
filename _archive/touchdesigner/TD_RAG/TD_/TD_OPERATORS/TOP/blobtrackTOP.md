# TOP blobtrackTOP

## Overview

The Blob Track TOP is implemented using OpenCV.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `reset` | Reset | Toggle | Resets all tracking data and learned background data while this parameter is On. |
| `resetpulse` | Reset Pulse | Pulse | Instantly resets all tracking data and learned background data. |
| `monosource` | Mono Source | Menu | Blob tracking is done using a single channel. This menu controls what single channel is used to detect blobs. |
| `drawblobs` | Draw Blob Bounds | Toggle | Draws rectangles on the TOP image that shows where the tracked blobs are. |
| `blobcolor` | Blob Bound Color | RGB | Determines the color of the rectangles that are drawn to show the blobs. |
| `threshold` | Threshold | Float | Threshold used to create the binary texture when using background subtraction. It is the threshold of the difference between the background texture and the input texture. |
| `minblobsize` | Minimum Blob Size | Float | Blobs must be at least this big to be tracked. |
| `maxblobsize` | Maximum Blob Size | Float | Blobs larger than this will not be tracked. |
| `maxmovedistance` | Maximum Move Distance | Float | The maximum distance a blob can move in one frame and still be considered to the same blob (maintain the same ID). |
| `deletenearby` | Delete Nearby Blobs | Toggle | Sometimes (depending on the tracking method) duplicate blobs may be created. This feature allows you to delete blobs that are too close to each other. |
| `deletedist` | Minimum Distance | Float | When deleting nearby blobs, blobs will be deleted if they are within this number of pixels of each other. The smaller blob will be deleted. |
| `deletenearbytol` | Delete Area Tolerance | Float | Along with the distance, the area of the two blobs can be compared. If this parameter is 1, than the area is ignored. As this parameter gets smaller only blobs that have a significant size differen... |
| `deleteoverlap` | Delete Overlapping Blobs | Toggle | Deletes blobs that are overlapping. |
| `deleteoverlaptol` | Delete Overlap Tolerance | Float | If this parameter is 1 then only blobs that are completely overlapped will be deleted. As this value gets smaller less and less overlap is needed for a blob to get deleted. |
| `reviveblobs` | Revive Blobs | Toggle | When enabled, will revive lost blobs (ie. same ID) if they satisfy all the below parameters |
| `revivetime` | Revive Time | Float | The time (in seconds) threshold for reviving a lost blob. If a blob has been lost for longer than revive time, it will not be revived and is considered expired. |
| `revivearea` | Revive Area Difference | Float | The area difference threshold for the new blob and the lost blob. |
| `revivedistance` | Revive Distance | Float | The distance threshold between the new blob and the lost blob. |
| `includelost` | Include Lost Blobs in Table | Toggle | When enabled, lost blobs will be included in the Blob Track TOP's Info DAT table. |
| `includeexpired` | Include Expired Blobs in Table | Toggle | When enabled, expired blobs (ie. blobs that have no chance of revival) will be included in the Blob Track TOP's Info DAT table. |
| `expiredtime` | Expired Time | Float | Time in seconds for blobs to remain in the Info DAT table after expiring. |
| `outputresolution` | Output Resolution | Menu | quickly change the resolution of the TOP's data. |
| `resolution` | Resolution | Int | Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size. The drop down menu ... |
| `resmenu` | Resolution Menu | Pulse | A drop-down menu with some commonly used resolutions. |
| `resmult` | Use Global Res Multiplier | Toggle | Uses the Global Resolution Multiplier found in Edit>Preferences>TOPs. This multiplies all the TOPs resolutions by the set amount. This is handy when working on computers with different hardware spe... |
| `outputaspect` | Output Aspect | Menu | Sets the image aspect ratio allowing any textures to be viewed in any size. Watch for unexpected results when compositing TOPs with different aspect ratios. (You can define images with non-square p... |
| `aspect` | Aspect | Float | Use when Output Aspect parameter is set to Custom Aspect. |
| `armenu` | Aspect Menu | Pulse | A drop-down menu with some commonly used aspect ratios. |
| `inputfiltertype` | Input Smoothness | Menu | This controls pixel filtering on the input image of the TOP. |
| `fillmode` | Fill Viewer | Menu | Determine how the TOP image is displayed in the viewer. NOTE:To get an understanding of how TOPs work with images, you will want to set this to Native Resolution as you lay down TOPs when starting ... |
| `filtertype` | Viewer Smoothness | Menu | This controls pixel filtering in the viewers. |
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. Making this larger than 1 is essentially the same as taking the output from each pass, and passing it into the first input of the ... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP blobtrackTOP operator
blobtracktop_op = op('blobtracktop1')

# Get/set parameters
freq_value = blobtracktop_op.par.active.eval()
blobtracktop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
blobtracktop_op = op('blobtracktop1')
output_op = op('output1')

blobtracktop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(blobtracktop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **34** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
