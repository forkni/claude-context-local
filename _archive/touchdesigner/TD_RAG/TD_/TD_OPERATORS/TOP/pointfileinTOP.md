# TOP pointfileinTOP

## Overview

The Point File In TOP loads 3D point data into TOPs from either a single file or a sequence of files.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | File | File | The path and name of the point file to load. Point file formats are those found in File Types.  You can specify files on the internet using http:// ...       To treat a folder of files as an animat... |
| `reload` | Reload | Toggle | Change from 0 to 1 to force the file to reload. Useful when the file changes or did not exist at first. |
| `reloadpulse` | Reload Pulse | Pulse | Immediately reload the point data file. |
| `red` | Red | Menu | Select one of the available point data channels to place it into the red channel of the output image. Selecting One or Zero will place the constance value into the output channel. |
| `green` | Green | Menu | Select one of the available point data channels to place it into the green channel of the output image. Selecting One or Zero will place the constance value into the output channel. |
| `blue` | Blue | Menu | Select one of the available point data channels to place it into the blue channel of the output image. Selecting One or Zero will place the constance value into the output channel. |
| `alpha` | Alpha | Menu | Select one of the available point data channels to place it into the alpha channel of the output image. Selecting One or Zero will place the constance value into the output channel. |
| `playmode` | Play Mode | Menu | Specifies the method used to play the animation, there are 3 options. |
| `play` | Play | Toggle | Animation plays when 1, stops when 0. |
| `speed` | Speed | Float | This is a speed multiplier which only works when Play Mode is Sequential. A value of 1 is the default playback speed. A value of 2 is double speed, 0.5 is half speed and so on. Negative values will... |
| `cue` | Cue | Toggle | Jumps to Cue Point when set to 1. Only available when Play Mode is Sequential. |
| `cuepulse` | Cue Pulse | Pulse | Instantly jumps to the Cue Point position in the movie. |
| `cuepoint` | Cue Point | Float | Set any index in the animation as a point to jump to. |
| `cuepointunit` | Cue Point Unit | Menu | Select the units for this parameter from Index, Frames, Seconds, and Fraction (percentage). |
| `cuebehavior` | Cue Behavior | Menu | Customize the Cue parameter's behavior. |
| `index` | Index | Float | This parameter explicitly sets the file sequence position when Play Mode is set to Specify Index. The units menu on the right lets you specify the index in the following units: Index, Frames, Secon... |
| `indexunit` | Index Unit | Menu | Select the units for this parameter from Index, Frames, Seconds, and Fraction (percentage). |
| `loopcrossfade` | Loop Crossfade | Float | Crossfades the beginning and end of the animation together to create a smooth transition when looping. If the movie uses Trim options, it will crossfade Trim Start with Trim End positions. |
| `loopcrossfadeunit` | Loop Crossfade Unit | Menu | Select the units for this parameter from Index, Frames, Seconds, and Fraction (percentage). |
| `stepsize` | Step Size | Int | Sets how many frames to skip before displaying next frame. For example, a StepSize of 30 will display every 30th frame. The timing of the animation playback does not change, so with a Step Size of ... |
| `audioloop` | Audio Loop | Menu | This menu helps you determine how to treat the audio as the end of an animation approaches. This is needed because in some cases of playing an animation, like when driving with an index, the TOP wi... |
| `imageindexing` | Image Sequence Indexing | Menu | Determines how a file sequence is ordered. |
| `interp` | Interpolate Frames | Toggle | Interpolates between frames based based on exact time. For example, if the index (in frames) is 1.5, then frames 1 and 2 will be blended 50-50. If the index is 1.7 then 30% of frame 1 is blended wi... |
| `loadingerrorimage` | Loading/Error Image | Menu | When the file can not be loaded for some reason, select what to display instead. |
| `trim` | Trim | Toggle | Enables the parameters below to set trim in and out points. |
| `tstart` | Trim Start | Float | Trim the starting point of the movie. |
| `tstartunit` | Trim Start Unit | Menu | Select the units for this parameter from Index, Frames, Seconds, and Fraction (percentage). |
| `tend` | Trim End | Float | Trim the ending point of the movie. |
| `tendunit` | Trim End Unit | Menu | Select the units for this parameter from Index, Frames, Seconds, and Fraction (percentage). |
| `textendleft` | Extend Left | Menu | Determines how the Point File In TOP handles animation positions that lie before the Trim Start position. For example, if Trim Start is set to 1, and the animation's current index is -10, the Exten... |
| `textendright` | Extend Right | Menu | Determines how the Point File In TOP handles animation positions that lie after the Trim End position. For example, if Trim End is set to 20, and the animation's current index is 25, the Extend Rig... |
| `overridesample` | Override Sample Rate | Toggle | Turn On to change the sample rate of the movie. When loading an image sequence, use these parameters to set the playback speed for the sequence. |
| `samplerate` | Sample Rate | Float | Set the sample rate for playback when 'Override Sample Rate' above is On. |
| `prereadframes` | Pre-Read Frames | Int | Sets how many animation frames TouchDesigner reads ahead and stores in memory. The Point File In TOP will read and decode frames of the animation into CPU memory before they are used, this can elim... |
| `frametimeout` | Frame Read Timeout | Int | The time (in milliseconds) TouchDesigner will wait for a frame from the hard drive before giving up. If the Disk Read Timeout time is reached, that frame is simply skipped. This also works for netw... |
| `frametimeoutstrat` | Frame Timeout Strategy | Menu | When on, if the Disk Read Timeout is reached TouchDesigner will use the latest available frame in place of the skipped frame. |
| `alwaysloadinitial` | Always Load Initial Frame | Toggle | If this parameter is turned on, then for the first loaded frame the Frame Read Timeout will be ignored, and it will always wait for the first frame to ensure the node always starts up with a valid ... |
| `opentimeout` | File Open Timeout | Int | The time (in milliseconds) TouchDesigner will wait for a file to open. If the Disk Open Timout is reached, the Point File In TOP will stop waiting and make its image all black, with a grey square i... |
| `asyncupload` | Async Upload to GPU | Toggle | When enabled, this will use OpenGL features to upload movie images to the GPU asynchronously. This will reduce the cook time of the Movie File In TOP considerably (in the performance monitor the li... |
| `updateimage` | Update Image | Toggle | Image will not update when set to 0. Animation index will continue to move forward but the output image will not update. |
| `maxdecodecpus` | Max Decode CPUs | Int | Limit the maximum number of CPUs that will be used to decode certain file codecs that are capable of multi-CPU decoding. |
| `highperfread` | High Performance Read | Toggle | This option should be used when playing back files that require very high SSD read speeds. It greatly improves read performance in those cases. It should not be used for low resolution or low data ... |
| `highperfreadfactor` | High Performance Read Factor | Float | When doing high performance reads, this parameter controls the size of the read operations that are done on disk. Whatever the largest operation the codec asks to be done, this is multiplied by the... |
| `hwdecode` | Hardware Decode | Toggle | Controls if this node should use hardware decoding via the Nvidia hardware decoder chip. You can check if hardware decoding is being used using the Info CHOP, 'hardware_decode' channel. This parame... |
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
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. For every pass after the first it takes the result of the previous pass and replaces the node's first input with the result of the... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP pointfileinTOP operator
pointfileintop_op = op('pointfileintop1')

# Get/set parameters
freq_value = pointfileintop_op.par.active.eval()
pointfileintop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pointfileintop_op = op('pointfileintop1')
output_op = op('output1')

pointfileintop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pointfileintop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **57** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
