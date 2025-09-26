# CHOP blacktraxCHOP

## Overview

The BlackTrax CHOP will provide motion tracking data from <http://blacktrax.cast-soft.com>.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the CHOP receives information sent to the network port. While Off, no updating occurs. |
| `port` | Port | Int | The port that will accept packets. |
| `protocol` | Protocol | Menu | The network protocol to use. Refer to the Network Protocols article for more information. |
| `netaddress` | Network Address | Str | When using Multicast, this is the address that will listen for packets. |
| `samplerate` | Sample Rate | Int | Sets the sample rate of this CHOP. |
| `outputformat` | Output Format | Menu | Specifies the format for the CHOP channels (ie. how many beacons to add). "From Mapping Table" adds one beacon to the CHOP for every row in the mapping table. "From Max Beacons" adds the number spe... |
| `maxbeacons` | Max Beacons | Int | Specifies how many beacons to add to the CHOP. Used with the "From Max Beacons" output format. |
| `centroid` | Centroid | Toggle | When enabled, adds beacon translation and rotation channels. |
| `velocity` | Velocity | Toggle | When enabled, adds beacon velocity channels. |
| `acceleration` | Acceleration | Toggle | When enabled, adds beacon acceleration channels. |
| `leds` | LEDs | Toggle | When enabled, adds position channels for each LED in the beacon. |
| `reset` | Reset Channels | Toggle | Clears any stored beacons and removes any stale data while On. |
| `resetpulse` | Reset Pulse | Pulse | Instantly clears any stored beacons and removes any stale data. |
| `mappingtable` | Mapping Table | DAT | A DAT table that maps beacon IDs to CHOP channels (beacon0, beacon1, etc.). The first row will map to beacon0, second row to beacon1, etc. Beacon ID is a unique non-negative integer and is specifie... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP blacktraxCHOP operator
blacktraxchop_op = op('blacktraxchop1')

# Get/set parameters
freq_value = blacktraxchop_op.par.active.eval()
blacktraxchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
blacktraxchop_op = op('blacktraxchop1')
output_op = op('output1')

blacktraxchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(blacktraxchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
