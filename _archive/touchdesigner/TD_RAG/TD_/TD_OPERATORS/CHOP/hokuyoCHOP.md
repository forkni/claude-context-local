# CHOP hokuyoCHOP

## Overview

The Hokuyo CHOP is used for communication with Hokuyo laser scanners (serial or ethernet interface): Hokuyo Products

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | This enables the connection to the Hokuyo sensor. |
| `interface` | Interface | Menu | Select the device interface. |
| `port` | Serial Port | StrMenu | Selects the COM port that the serial connection will use.  Default port names 1 through 8 are available in the popup menu, though any name can be manually entered in this field. |
| `netaddress` | Network Address | Str | The network address of the laser scanner to connect to. The default address of a UST-10LX device is 192.168.0.10. |
| `highsensitivity` | High Sensitivity | Toggle | This check box enables the high sensitivity mode on the sensor. High Sensitivity mode increases the detection ability of the laser scanner, but with a higher chance of measurement error. Only avail... |
| `motorspeed` | Motor Speed | Int | Modifies the motor speed of the laser scanner. This should be used when running multiple laser scanners in the same environment. Different motor speeds across multiple laser scanners will avoid lig... |
| `startstep` | Start Step | Int | Specifies the first data point of the laser scan. Start step must be a number between first and last measurement point, and must be less than or equal to the end step parameter. Refer to the above ... |
| `endstep` | End Step | Int | Specifies the last data point of the laser scan. End step must be a number between first and last measurement point, and must be greater than or equal to the start step parameter. Refer to the abov... |
| `output` | Output | Menu | Outputs the scan data in either Polar or Cartesian coordinates. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP hokuyoCHOP operator
hokuyochop_op = op('hokuyochop1')

# Get/set parameters
freq_value = hokuyochop_op.par.active.eval()
hokuyochop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
hokuyochop_op = op('hokuyochop1')
output_op = op('output1')

hokuyochop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(hokuyochop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
