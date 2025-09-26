# CHOP renderpickCHOP

## Overview

The Render Pick CHOP samples a rendering (from a Render TOP or a Render Pass TOP) and returns 3D information from the geometry at that particular pick location.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `strategy` | Strategy | Menu | Decides when to update values based on pick interactions. |
| `clearprev` | Clear Previous Pick on New Pick | Toggle | This parameter is only enabled when the Strategy is set to Hold Last Picked. When this is on, starting a new pick on empty space will clear the values. When off, the last values will be held if the... |
| `responsetime` | Response Time | Menu | Determines when the values are updated. |
| `pickradius` | Pick Radius | Int | Controls the radius of the search area for the pick. If nothing is found at the pick's center it will keep searching for geometry in the search area defined by the Pick Radius. |
| `pickradstep` | Pick Radial Step | Int | Used to reduce the searching within the search area. The search area is sampled at locations that correspond to 'spokes' outwards from the center pick point. |
| `pickcirstep` | Pick Circular Step | Int | Used to reduce the searching within the search area. The search area is sampled at locations that correspond to 'rings' outwards from the center pick point. |
| `rendertop` | Render/RenderPass TOP | TOP | Specifies which render to sample. |
| `usepickableflags` | Use Pickable Flags | Toggle | When turned on only geometry whose Pickable Flag is on can be selected by the Render Pick CHOP. The Pickable Flag is found on all Object components. |
| `includenonpickable` | Include Non-Pickable Objects | Toggle | Includes the non-pickable objects in the picking algorithm such that non-pickable objects may occlude pickable objects.  For example, if there is only one pickable object in the scene with lots of ... |
| `pickingby` | Picking by | Menu | Determines how the pick location is set. |
| `panel` | Panel | PanelCOMP | Specifies which panel component to use when picking by panel. |
| `panelvalue` | Panel Value | StrMenu | Specifies with panel value to use to trigger the pick when picking by panel. |
| `picku` | U | Float | Sets the u coordinate when picking by parameters. |
| `pickv` | V | Float | Sets the v coordinate when picking by parameters. |
| `select` | Select | Toggle | When picking by parameters, picking is active when this parameter = 1. |
| `activatecallbacks` | Activate Callbacks | Toggle | Enables Callback DAT for each pick event. |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callbacks for pick event received. |
| `position` | Fetch Position | Menu | Returns the position of the point picked on the geometry. Channels tx, ty, tz. |
| `normal` | Fetch Normal | Menu | Returns the normals of the point picked on the geometry. Channels nx, ny, nz. |
| `referenceobj` | Reference Object | Object | Object used when fetching position or normals Relative to Object. |
| `color` | Fetch Point Color | Toggle | Returns the point color of the point picked on the geometry. Channels cr, cg, cb, ca. |
| `uv` | Fetch Texture UV | Toggle | Returns the texture coordinates of the point picked on the geometry. Channels mapu, mapv, mapw. |
| `path` | Fetch Object Path | Toggle | Return the path to the object that is picked. This result requires and Info DAT with its Node Path parameter referecning the Render Pick CHOP. |
| `depth` | Fetch Depth | Toggle | Returns the depth of the point picked on the geometry. This value a non-linear ratio of the point's position between the near and far planes of the Depth Buffer. Channel is depth. |
| `instanceid` | Fetch Instance ID | Toggle | Returns the Instance ID of the object. This will always be 0 if instancing is off. Channel is instance. |
| `customattrib1` | Custom Attrib 1 | Str | Specify which custom attributes to return from the object. |
| `customattrib1type` | Custom Attrib 1 Type | Menu | The type of attribute is selected from this menu. |
| `customattrib2` | Custom Attrib 2 | Str | Specify which custom attributes to return from the object. |
| `customattrib2type` | Custom Attrib 2 Type | Menu | The type of attribute is selected from this menu. |
| `customattrib3` | Custom Attrib 3 | Str | Specify which custom attributes to return from the object. |
| `customattrib3type` | Custom Attrib 3 Type | Menu | The type of attribute is selected from this menu. |
| `customattrib4` | Custom Attrib 4 | Str | Specify which custom attributes to return from the object. |
| `customattrib4type` | Custom Attrib 4 Type | Menu | The type of attribute is selected from this menu. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP renderpickCHOP operator
renderpickchop_op = op('renderpickchop1')

# Get/set parameters
freq_value = renderpickchop_op.par.active.eval()
renderpickchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
renderpickchop_op = op('renderpickchop1')
output_op = op('output1')

renderpickchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(renderpickchop_op)
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
