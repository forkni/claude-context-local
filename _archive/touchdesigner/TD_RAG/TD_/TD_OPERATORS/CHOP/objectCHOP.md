# CHOP objectCHOP

## Overview

The Object CHOP compares two objects and outputs channels containing their raw or relative positions and orientations.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `dat` | DAT Table | DAT | Uses a Table DAT to specify the target and reference objects to use. The first column will be the target objects while the second column will be the reference objects. No headers are used. |
| `target` | Target Object | Object | The object that is being compared to the position of the reference object. The Target Object can be expressed as a text string. This can be useful when the object name needs to be a variable - it a... |
| `reference` | Reference Object | Object | The object that acts as the origin of the comparison. The Reference Object can be expressed as a text string. |
| `swaptargetreference` | Swap Target/Reference | Toggle | Swap the objects defined above in the Target Object and Reference Object parameters. |
| `compute` | Compute | Menu | Specify the information to output from the objects as described in the parameters below. Except for 'measurements', these match the standard transform formats as described by the Transform CHOP. |
| `translate` | Position | Toggle | The displacement from the reference object to the target object. |
| `rotate` | Rotation | Toggle | The orientation difference from the reference object to the target object. |
| `scale` | Scale | Toggle | The scale difference from reference object to the target object. |
| `quat` | Quaternion | Toggle | The quaternion from reference object to the target object. |
| `bear` | Bearing | Toggle | The rotation necessary for the reference object to be facing the target object. |
| `singlebear` | Single Bearing Angle | Toggle | An angle representing where the target object is relative to the reference object. Zero degrees is directly in front, 90 degrees is beside and 180 degrees is behind. |
| `distance` | Distance | Toggle | The distance between the two objects. |
| `invsqr` | Inverse Square Distance | Toggle | The inverse squared distance between the two objects, useful for modeling electric forces, audio dropoff and gravity. |
| `xord` | Transform Order | Menu | The transform order to use for Rotation, Scale, Transform, Bearing, or Single Bearing Angle Compute modes. |
| `rord` | Rotate Order | Menu | The rotation order to use for Rotation, Scale, Transform, Bearing, or Single Bearing Angle Compute modes. |
| `includeorderchans` | Include Order Channels | Toggle | Turn on to include channels for Transform Order and Rotate Order. |
| `bearingref` | Bearing Reference | Menu | Bearing requires a direction to use as a reference base. |
| `bearing` | Bearing Vector | XYZ | An arbitrary base direction for the bearing calculation. |
| `tscopex` | Point Scope X | Str | When one of the optional point inputs is connected, this determines which channels represent X, Y and Z. |
| `tscopey` | Point Scope Y | Str | When one of the optional point inputs is connected, this determines which channels represent X, Y and Z. |
| `tscopez` | Point Scope Z | Str | When one of the optional point inputs is connected, this determines which channels represent X, Y and Z. |
| `appendattribs` | Append Attributes | Toggle | Adds a rotate attribute to any rotation channels the Object CHOP creates. |
| `smoothrotate` | Smooth Rotation | Toggle | When on outputs a smooth rotation curve without graphical jumps at 0, 90, etc. |
| `nameformat` | Channel Names | Menu | Sets how the created channels are named. |
| `outputrange` | Output Range | Menu | The start and end time of the desired interval of the object path. |
| `cookpast` | Cook Past Values (slow) | Toggle | If the project has skipped one or more frames, this will attempt to cook it's inputs at multiple previous frames to avoid discontinuities in it's calculations. |
| `start` | Start | Float | The start time of the desired interval of the object path. |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `end` | End | Float | The end time of the desired interval of the object path. |
| `endunit` | End Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `left` | Extend Left | Menu | The extend condition before the CHOP interval. They are: |
| `right` | Extend Right | Menu | Extend condition after the interval. Same options as Extend Left. |
| `defval` | Default Value | Float | The value used for the Default Value extend condition.      Note: When creating rotation channels, the Transform CHOP and Object CHOP will select values which minimize frame-to-frame discontinuity.... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP objectCHOP operator
objectchop_op = op('objectchop1')

# Get/set parameters
freq_value = objectchop_op.par.active.eval()
objectchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
objectchop_op = op('objectchop1')
output_op = op('output1')

objectchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(objectchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **39** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
