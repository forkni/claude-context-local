# SOP armSOP

## Overview

The Arm SOP creates all the necessary geometry for an arm, and provides a smooth, untwisted skin that connects the arm to the body.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `capttype` | Capture Type | Menu | You can use either Ellipses or Capture Regions as deformation geometry. Ellipses are for use with the Skeleton SOP. Capture Regions are for use with the Capture SOP. |
| `axis` | Arm Axis | Menu | Position the model along the +X or -X axis. |
| `bonerad` | Radius | Float | Controls the scale of the circle radii. |
| `rotatehand` | Rotate Hand | Toggle | This parameter rotates the hand and the wrist joint to match the orientation of the hand-print object. In order to operate correctly, the end-affector (hand print) scale transformations must remain... |
| `autoelbow` | Auto Elbow Twist | Toggle | This parameter affects the default twist of the elbow joint to a more natural position. |
| `elbowtwist` | Elbow Twist | Float | Specifies the rotation angle of the elbow joint. |
| `flipelbow` | Flip Elbow | Toggle | This toggle positions the arm using an alternative elbow position solution. |
| `clavlength` | Clavicle | Float | Control bone lengths, as illustrated above. |
| `humlength` | Humerous | Float | Control bone lengths, as illustrated above. |
| `ulnalength` | Ulna | Float | Control bone lengths, as illustrated above. |
| `handlength` | Hand | Float | Control bone lengths, as illustrated above. |
| `shoulder` | Shoulder Joint | Float | Control the joint lengths, as illustrated above. |
| `elbow` | Elbow Joint | Float | Control the joint lengths, as illustrated above. |
| `wrist` | Wrist Joint | Float | Control the joint lengths, as illustrated above. |
| `shoulder1t` | Shoulder 1 | XYZ | The X, Z position of the first shoulder circle, as well as its overall scale. |
| `shoulder2t` | Shoulder 2 | XYZ | The X, Z position of the second shoulder circle, as well as its overall scale. |
| `shoulder3t` | Shoulder 3 | XYZ | The X, Z position of the third shoulder circle, as well as its overall scale. |
| `shoulder4t` | Shoulder 4 | XYZ | The X, Z position of the fourth shoulder circle, as well as its overall scale. |
| `shoulder5t` | Shoulder 5 | XYZ | The X, Z position of the fifth shoulder circle, as well as its overall scale. |
| `elbow1t` | Elbow 1 | XYZ | The X, Z position of the first elbow circle, as well as its overall scale. |
| `elbow2t` | Elbow 2 | XYZ | The X, Z position of the second elbow circle, as well as its overall scale. |
| `elbow3t` | Elbow 3 | XYZ | The X, Z position of the third elbow circle, as well as its overall scale. |
| `elbow4t` | Elbow 4 | XYZ | The X, Z position of the fourth elbow circle, as well as its overall scale. |
| `elbow5t` | Elbow 5 | XYZ | The X, Z position of the fifth elbow circle, as well as its overall scale. |
| `wrist1t` | Wrist 1 | XYZ | The X, Z position of the first wrist circle, as well as its overall scale. |
| `wrist2t` | Wrist 2 | XYZ | The X, Z position of the second wrist circle, as well as its overall scale. |
| `wrist3t` | Wrist 3 | XYZ | The X, Z position of the third wrist circle, as well as its overall scale. |
| `wrist4t` | Wrist 4 | XYZ | The X, Z position of the fourth wrist circle, as well as its overall scale. |
| `wrist5t` | Wrist 5 | XYZ | The X, Z position of the fifth wrist circle, as well as its overall scale. |
| `affector` | Affector Object | Object | Allows the end affector to be another object, or simply defined by a default box, which is controlled by the transformations below. |
| `t` | Translate | XYZ | End Affector Translation. For a full explanation of transforms, see the Transform SOP. |
| `r` | Rotate | XYZ | End Affector Rotation. For a full explanation of transforms, see the Transform SOP. |
| `s` | Scale | XYZ | End Affector Scale. For a full explanation of transforms, see the Transform SOP. |

## Usage Examples

### Basic Usage

```python
# Access the SOP armSOP operator
armsop_op = op('armsop1')

# Get/set parameters
freq_value = armsop_op.par.active.eval()
armsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
armsop_op = op('armsop1')
output_op = op('output1')

armsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(armsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **33** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
