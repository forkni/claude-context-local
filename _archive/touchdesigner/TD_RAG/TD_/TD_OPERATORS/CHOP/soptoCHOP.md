# CHOP soptoCHOP

## Overview

The SOP to CHOP uses a geometry object to choose a SOP from which the channels will be created.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sop` | SOP | SOP | Specifies which Object / SOP contains the geometry you want to fetch. |
| `group` | Group | StrMenu | Only points within the specified group are Fetched. If blank, all points are fetched. |
| `position` | Position | Toggle | When On will retrieve the position attributes (P) from the SOP and create channels tx, ty, tz. |
| `colorrgb` | Color RGB | Toggle | When On will retrieve the RGB color attributes (Cd0, Cd1, Cd2) from the SOP and create channels cr, cg, cb. |
| `coloralpha` | Color Alpha | Toggle | When On will retrieve the Alpha color attribute (Cd4) from the SOP and create channel alpha. |
| `normal` | Normal | Toggle | When On will retrieve the Normal attributes (N) from the SOP and create channels nx, ny, nz. |
| `textureuv` | Texture UV | Toggle | When On will retrieve the UV texture attributes (uv0, uv1) from the SOP and create channels u and v. |
| `texturew` | Texture W | Toggle | When On will retrieve the W texture attribute (uv2) from the SOP and create channel w. |
| `pointindex` | Point Index | Toggle | Turn On to output the point index of each point in the SOP in a channel called index. |
| `normpos` | Normal Position XYZ | Toggle | Turn On |
| `custom` | Custom | Toggle | Turn On to access any attributes in the SOP including Custom Attributes by using the two parameters below. |
| `attribscope` | Attribute Scope | Str | This selects the custom attributes of the SOP to acquire.      You can use any attribute. If you look at the SOP's info by middle-mouse clicking on the SOP and there are other attributes, you can s... |
| `renamescope` | Rename Scope | Str | This parameter matches each channel acquired in the Attribute Scope. There must be one name per attribute value. By default, it translates the P attribute (position of the point) to tx, ty and tz c... |
| `transobj` | Transform Object | Object | If a transform object is specified, the point values will be represented relative to that object's origin and rotation. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP soptoCHOP operator
soptochop_op = op('soptochop1')

# Get/set parameters
freq_value = soptochop_op.par.active.eval()
soptochop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
soptochop_op = op('soptochop1')
output_op = op('output1')

soptochop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(soptochop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **21** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
