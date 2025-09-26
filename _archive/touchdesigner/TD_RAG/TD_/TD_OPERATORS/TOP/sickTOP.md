# TOP sickTOP

## Overview

The SICK TOP can be used to retrieve point cloud data from a LIDAR sensor made by SICK.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Activate the connection to the sensor. Only one SICK node can be active in a project at time. If a second node is activated it will cause an error message. |
| `reinitialize` | Reinitialize | Pulse | Restart the connection with the sensor. This will shutdown the connection and reinitialize using the current parameters. You can also toggle the Active parameter off and on again to reinitialize th... |
| `launchfile` | Launch File | File | A path to the launch file to configure the sensor. A valid launch file is necessary to connect to the sensor. Sample launch files for each sensor can be downloaded from SICK's website. Advanced con... |
| `deviceaddress` | Device Address | Str | The IP address for the sensor. If this parameter is blank, the default address in the launch file will be used. |
| `port` | Port | Str | The port number for the sensor. If this parameter is blank, the default port number in the launch file will be used. |
| `customargs` | Custom Arguments | Str | Additional arguments that should be included when initializing the sensor. This can be used to customize parameters for individual sensors while still using the same launch file. Arguments should b... |
| `red` | Red | Menu | The name of the data field that will be assigned to the red component of the output image e.g. 'x'. The available fields will vary depending on the sensor and can be selected from the flyout menu t... |
| `green` | Green | Menu | The name of the data field that will be assigned to the green component of the output image e.g. 'g'. The available fields will vary depending on the sensor and can be selected from the flyout menu... |
| `blue` | Blue | Menu | The name of the data field that will be assigned to the blue component of the output image e.g. 'z'. The available fields will vary depending on the sensor and can be selected from the flyout menu ... |
| `alpha` | Alpha | Menu | The name of the data field that will be assigned to the alpha component of the output image e.g. 'one'. The available fields will vary depending on the sensor and can be selected from the flyout me... |
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
# Access the TOP sickTOP operator
sicktop_op = op('sicktop1')

# Get/set parameters
freq_value = sicktop_op.par.active.eval()
sicktop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sicktop_op = op('sicktop1')
output_op = op('output1')

sicktop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sicktop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
