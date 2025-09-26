# CHOP leapmotionCHOP

## Overview

The Leap Motion CHOP reads hand, finger, tool and gesture data from the Leap Motion controller.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When 'On' data is captured from the Leap Motion sensor. |
| `api` | API | Menu | Select between Leap Motion V2 or V4/V5 SDKs for tracking. V5 offers the fastest and most stable tracking, V2 offers some legacy features like gestures. |
| `libfolder` | Library Folder | Folder | This parameter is used on Windows only to point to the location of the library file (.dll) that corresponds to the selected API version. The dll file can be found in the driver kit downloaded from ... |
| `hmd` | HMD Mode | Menu | Switches the device to Head Mounted Display mode. |
| `debugchannels` | Debug Channels | Toggle | If set, the following channels will be included:  ### Arguments: *connected - 1 if the Leap Motion sensor is connected, 0 otherwise.    *  sequence_id - Unique id corresponding to the current frame. |
| `statuschannels` | Status Channels | Toggle | If set, the following channels will be included:  ### Arguments: *hands - Number of hands detected by the sensor.    *  fingers - Number of fingers detected by the sensor.    *  tools - Number of... |
| `namedhands` | Named Hands | Toggle | This names the hand channels as either right (r) or left (l) hands. |
| `hands` | Hands | Int | Number of hands. The following channels will be included for each detected hand:  ### Arguments: *hand*:t[xyz] - Coordinates of the hand relative to the sensor.    *hand*:r[xyz] - Rotation of t... |
| `lefthands` | Left Hands | Int | When using 'Named Hands', specify how many left hands will be tracked. |
| `righthands` | Right Hands | Int | When using 'Named Hands', specify how many right hands will be tracked. |
| `handvelocity` | Hand Velocity | Toggle | If set, the following channels will be included for each hand, in addition to any others:  ### Arguments: *hand*:v[xyz] - Velocity of the detected hand. |
| `handsphere` | Hand Sphere | Toggle | This is only available when using API = Version 2 Tracking. It adds the following channels to tracking hands:  ### Arguments: *hand*/sphere:t[xyz] - Position of the detected hand sphere.    *  ha... |
| `pinchstrength` | Pinch Strength | Toggle | Pinch is defined as the distance between the thumb and first finger. ### Arguments: *hand*:pinch - How much pinch is detected between the thumb and first finger. |
| `grabstrength` | Grab Strength | Toggle | Grab is defined as how close a hand is to being a fist.  ### Arguments: *hand*:grab - How much grab is detected, strength is 0 for a flat hand and 1 for a fist. |
| `namedfingers` | Named Fingers | Toggle | Instead of simply using a finger index number for each finger tracked, when On this names the finger channels as thumb, index, middle, ring, and pinky. |
| `fingersperhand` | Fingers per Hand | Int | When not using 'Named Fingers', specify how many fingers to track per hand. |
| `fingerrotation` | Finger Rotation | Toggle | Track the rotation for all fingers.  ### Arguments: *hand*/finger*:r[xyz] - The rotation of the finger. |
| `fingersize` | Finger Size | Toggle | If set, the following channels will be included for each finger, in addition to any others:  ### Arguments: *hand*/finger*:length - Length of the detected finger.    *  hand*/finger*:width - Widt... |
| `fingerextended` | Finger Extended | Toggle | Track how straight the fingers are, a finger is considered extended when it is straight as if pointing. ### Arguments: *hand*/finger*:extended - How straight the finger is. |
| `fingerjoints` | Finger Joints | Toggle | Tracks the position of every joint of every finger. ### Arguments: *hand*/finger*/joint_mcp:t[xyz] - The mcp joint position of the finger.*  hand*/finger*/joint_pip:t[xyz] - The pip joint positi... |
| `tools` | Tools | Int | Number of tools. The following channels will be included for each detected tool:  ### Arguments: *tool*:t[xyz] - Coordinates of the tool relative to the sensor.    *tool*:length - Length of the... |
| `circlegestures` | Circle Gestures | Int | Number of circle gestures. The following channels will be included for each detected Circle Gesture:  ### Arguments: *circle*:handindex - Index of the hand associated with the gesture. See Notes.... |
| `swipegestures` | Swipe Gestures | Int | Number of swipe gestures. The following channels will be included for each detected Swipe Gesture:  ### Arguments: *swipe*:handindex - Index of the hand associated with the gesture. See Notes.   ... |
| `keytapgestures` | Key Tap Gestures | Int | Number of key tap gestures. The following channels will be included for each detected Key Tap Gesture:  ### Arguments: *keytap*:handindex - Index of the hand associated with the gesture. See Note... |
| `screentapgestures` | Screen Tap Gestures | Int | Number of screen tap gestures, which is recognized as a quick forward tapping movement by a tool or finger. The following channels will be included for each detected screen tap gesture: ### Argumen... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP leapmotionCHOP operator
leapmotionchop_op = op('leapmotionchop1')

# Get/set parameters
freq_value = leapmotionchop_op.par.active.eval()
leapmotionchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
leapmotionchop_op = op('leapmotionchop1')
output_op = op('output1')

leapmotionchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(leapmotionchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
