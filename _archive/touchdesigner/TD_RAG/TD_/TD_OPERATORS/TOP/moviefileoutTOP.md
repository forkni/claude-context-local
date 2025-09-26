# TOP moviefileoutTOP

## Overview

The Movie File Out TOP saves a TOP stream out to a QuickTime or MP4 (.mp4) movie in a variety of formats, plus the Animation, Cineform and Hap Q video codecs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | Output either a movie, image, image sequence, or stop-frame movie. |
| `videocodec` | Video Codec | Menu | Select the video compression codec used to encode the movie. |
| `videocodectype` | Video Codec Type | Menu | Some video codecs such as Apple ProRes, Hap and Hap Q have a various different types such as ProRes 442 HQ, ProRe 4444 HQ etc. |
| `imagefiletype` | Image File Type | Menu | Choose what file type to use when Type is set to Image. |
| `uniquesuff` | Unique Suffix | Toggle | When enabled, me.fileSuffix will be a unique suffix when used in the file parameter. |
| `n` | N | Int | N is the index used in me.fileSuffix. When unique suffix is enabled, N specifies the starting index to increment from when calculating a unique suffix/name. |
| `leadingzerosdigits` | Leading Zeros Digits | Int | Specify the minimum number of suffix digits that the filename will have. If the sequence number is less than this number, leading zeros will be appended to total the number of suffix digits to be t... |
| `file` | File | File | Sets the path and filename of the movie file that is saved out. The filename must include the file extension such as .mov/.mp4 etc. For movies, generally the .mov file extension will work with the ... |
| `moviepixelformat` | Movie Pixel Format | Menu | Options for the pixel format based on the Video Codec selected. Use this parameter to change the color quality of the output (how many bits are used, YUV sampling etc.), as well as selecting format... |
| `audiochop` | Audio CHOP | CHOP | Specify a CHOP to use as the audio track for the movie. Drag & Drop a CHOP here or manually enter the CHOP's path. The CHOP needs to be time-sliced. |
| `audiocodec` | Audio Codec | Menu | Select the audio compression codec used to encode the audio. |
| `audiobitrate` | Audio Bit Rate | Menu | The bitrate to write the audio out at.  Note: A particlular behavior on Windows OS AAC encoder; for 1 and 2 channelsthe selction of bit rate is for both channels ie. its 192kb/s for either of them,... |
| `quality` | Quality | Float | Select the quality of the movie compression. NOTE: Some codecs can not output lossless compression. |
| `fps` | Movie FPS | Float | The frame rate of the movie file created. |
| `limitlength` | Limit Length | Toggle | This can be used to automatically stop recording the file once it reaches a specified length. |
| `length` | Length | Float | The length to stop recording the file at. |
| `lengthunit` | Length Unit | Menu | The unit the length is specified in. |
| `record` | Record | Toggle | When this parameter is set to 1, the movie will be recording. |
| `pause` | Pause | Toggle | Pauses the recording. |
| `addframe` | Add Frame | Pulse | Adds a single frame to the output for each click of the button.  Pause must be On to enable the Add Frame parameter. |
| `maxthread` | Max Threads | Int | When outputting sequences of images, this controls the maximum number of threads can be used to output images (one thread per image). If this is set to 1 then the main thread will be used to write ... |
| `headerdat` | Header Source DAT | DAT | The path to a Table DAT that stores header metadata that should be written to the output image or movie file. Header data is written as key-value pairs with the first column storing the keys and th... |
| `pointcloud` | Save as Point Cloud | Toggle | When enabled, an additional header will be added to the file that indicates the contents are point data rather than images. This header is used to automatically load the file into a Point File In T... |
| `input` | Additional Input TOP | Sequence | Sequence of TOPs containing image data to add to the file |
| `stallforopen` | Stall for File Open | Toggle | When this is on playback will stall until the file is opened and ready to receive frames, to make sure the frame that was inputted when Record was turned on gets recorded. When this is off recordin... |
| `profile` | Profile | Menu | Select the H.264 profile to use. |
| `preset` | Preset | Menu | The H264 preset to use. |
| `bitratemode` | Bit Rate Mode | Menu | Select between Constant or Variable bit rate, and regular or high quality bit rate modes. |
| `avgbitrate` | Average Bitrate (Kb/s) | Float | Set the average bitrate target for the encoding. |
| `peakbitrate` | Peak Bitrate (Kb/s) | Float | Set the peak bitrate allowed for the encoding. |
| `keyframeinterval` | Keyframe Interval | Int | Set the number of frames between key-frames (I-frames) while encoding. |
| `maxbframes` | Max B-Frames | Int | Controls the maximum number of B-frames (bi-directional frames) that will be created between pairs of key-frames. |
| `motionpredict` | Motion Prediction | Menu | Controls the quality of the Motion Prediction used when encoding H264/H265. |
| `frameslicing` | Frame Slicing | Toggle | Controls if H264/H265 frames are sliced into multiple pieces, allowing them to be decoded using multiple CPUs more easily. |
| `numslices` | Num Slices | Int | The number of slices each frame is split into. |
| `entropymode` | Entropy Mode | Menu | Controls which entropy mode is used for H265 encoding. |
| `secondarycompression` | Secondary Compression | Toggle | Hap uses a secondary CPU compression stage usually. Encoding video without this compression will result in faster playback, but potentially larger file sizes (which would require faster drives to p... |
| `encodetestmode` | Encode Test Mode | Toggle | This mode disables file writting, and only does the encoding. This is useful to test the GPU/CPU performance of encoding while taking the SSD speed out of the equation. |
| `mipmaps` | Include Mip Maps | Toggle | When saving out .dds file, mipmaps can be included if this is enabled. This is primarily used for the PreFilter Map TOP, which will encode special information into the mipmap levels of the texture ... |
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
# Access the TOP moviefileoutTOP operator
moviefileouttop_op = op('moviefileouttop1')

# Get/set parameters
freq_value = moviefileouttop_op.par.active.eval()
moviefileouttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
moviefileouttop_op = op('moviefileouttop1')
output_op = op('output1')

moviefileouttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(moviefileouttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **52** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
