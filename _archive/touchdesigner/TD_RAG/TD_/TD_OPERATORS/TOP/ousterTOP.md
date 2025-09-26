# TOP ousterTOP

## Overview

The Ouster TOP is used to send and receive data with an Ouster Imaging Lidar.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enables connections with the device. |
| `deviceaddress` | Device Address | Str | The IP address or the name of the Ouster device. The address is only required during configuraton. The device will request an address from the local DHCP server when it is connected to the network.... |
| `lidarport` | Lidar Port | Int | The UDP port number to receive lidar data. |
| `imuport` | IMU Port | Int | The UDP port number to receive data from the inertial measurement unit (IMU) on the device. The IMU data can be accessed by connecting the Ouster TOP to an Info CHOP. |
| `commandport` | Command Port | Int | The TCP/IP port number to use to send configuration commands to the device. |
| `targetaddress` | Target Address | StrMenu | The IP address where the sensor should send the lidar and IMU data to. If the parameter is blank, the address of the current machine will be used. This field should only be necessary if the sending... |
| `localaddress` | Local Address | StrMenu | An IP address for the current machine that should be used to connect to the device with. If the address is left blank, the default network address will be used. |
| `scanmode` | Scan Mode | Menu | Select a scanning mode to set the sensor's horizontal resolution and number of revolutions per second. The vertical resolution is determined by the hardware e.g. an OS1-64 sensor has vertical resol... |
| `configdevice` | Configure Device | Toggle | Enable this toggle to have the Ouster TOP set the configuration properties of the device. If the device has already been configured to the correct mode and network connections than this can be disa... |
| `layout` | Image Layout | Menu | Use this parameter to determine how data is arranged in the output image. The layout of data is generally not important when used as a point cloud. |
| `redchannel` | Red | Menu | Select what sensor data will be placed into the red channel of the output image. |
| `greenchannel` | Green | Menu | Select what sensor data will be placed into the green channel of the output image. |
| `bluechannel` | Blue | Menu | Select what sensor data will be placed into the blue channel of the output image. |
| `alphachannel` | Alpha | Menu | Select what sensor data will be placed into the alpha channel of the output image. |
| `timemode` | Time Sync Mode | Menu | Select how the sensor generates timestamp information. |
| `pulseinpolarity` | Sync Pulse In Polarity | Menu | The polarity of the SYNC_PULSE_IN signal to use. |
| `iomode` | Multipurpose IO Mode | Menu | Determines how the sensor uses the SYNC_PULSE_OUT signal. |
| `pulseoutpolarity` | Sync Pulse Out Polarity | Menu | Polarity of the output signal pulse. |
| `pulseoutfrequency` | Sync Pulse Out Frequency | Int | Frequency of the output pulse in Hz (must be greater than 0). |
| `pulseoutangle` | Sync Pulse Out Angle | Int | The encoder angle at which to output a signal pulse. Measured in degrees less than 360. |
| `pulseoutwidth` | Sync Pulse Out Width | Int | Width of the output signal pulse in mm. |
| `nmeainpolarity` | NMEA In Polarity | Menu | Sets the polarity of the NMEA URT input $GPRMC messages. Set to 'Active High' if UART is active high, idle low, and the start bit is after a falling edge. |
| `nmeaignorevalidchar` | NMEA Ignore Valid Char | Toggle | Turn off, if the NMEA UART input $GPRMC messages should be ignored if valid character is not set, and turn on if messages should be used for time syncing regardless of the valid character. |
| `nmeabaudrate` | NMEA Baud Rate | Menu | The baud rate for the incoming NMEA URT input $GPRMC messages. |
| `nmealeapseconds` | NMEA Leap Seconds | Int | An integer number of leap seconds that will be added to the UDP timestamp when calculating seconds since 00:00:00 Thursday, 1 Jan 1970. Set to 0 for Unix Epoch Time. |
| `autostart` | Auto Start | Toggle | Tell the sensor to automatically begin sending data when it turns on. The default is On. |
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
# Access the TOP ousterTOP operator
oustertop_op = op('oustertop1')

# Get/set parameters
freq_value = oustertop_op.par.active.eval()
oustertop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
oustertop_op = op('oustertop1')
output_op = op('output1')

oustertop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(oustertop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **39** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
