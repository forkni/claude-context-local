# TOP webrenderTOP

## Overview

The Web Render TOP takes a URL or DAT and renders a webpage via a separate browser process that uses Chromium Embedded Frameworks (CEF), and passes the result back through shared memory.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enables/disables the Web Render TOP. |
| `source` | Source | Menu | Source of the webpage, which can be an address via URL or File, or data from a DAT |
| `url` | URL or File | File | Uniform Resource Locator or the address of the web page |
| `dat` | DAT | DAT | Text to be loaded into a webpage |
| `reloadsrc` | Reload Source | DAT | Reload source DAT, URL or File. |
| `reload` | Reload Current Page | Pulse | Reloads the current page, the same as refreshing a web browser. |
| `resetcount` | Reset Update Count | Pulse | Reset the counter for the number of times the webpage has been updated (available via an Info CHOP). |
| `updatewhenloaded` | Only Update when Loaded | Toggle | Only shows the web page when it is full loaded. |
| `alwayscook` | Cook Always | DAT | Cook every frame if on.  If off, the Web Render TOP will cook for a 10 additional frames after the last update received to maintain continuity. |
| `transparent` | Transparent Background | Toggle | Loads the webpage with a transparent background.  This option will restart the browser process. |
| `audio` | Audio Options | Toggle | Let the browser process play audio if the web page contains audio.  This option will restart the browser process. |
| `mediastream` | Enable Media Stream | Toggle | Allows the web render instance to use the mic and the camera. |
| `maxrenderrate` | Maximum Render Frame Rate | Int | Sets the maximum frame rate the page will be rendered at.  Can be higher than 60 but does not guarantee a frame rate. |
| `numbuffers` | Number of Frame Buffers | Int | Sets the maximum number of cached images |
| `userdir` | User Cache Directory | Str | Persistent directory used by cef for storing user data. |
| `options` | Options | Str | Additional options that can be passed to the browser process.  This option will restart the browser process.  A list of options for the chromium browser can be found at here.  Note that these optio... |
| `autorestart` | Restart if Process Died | Toggle | Automatically restart the browser process if it died. |
| `autorestartpulse` | Restart | Pulse | Triggers the Restart immediately on button release (button-up). This can be accessed in python using the pulse() method. |
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
# Access the TOP webrenderTOP operator
webrendertop_op = op('webrendertop1')

# Get/set parameters
freq_value = webrendertop_op.par.active.eval()
webrendertop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
webrendertop_op = op('webrendertop1')
output_op = op('output1')

webrendertop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(webrendertop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
