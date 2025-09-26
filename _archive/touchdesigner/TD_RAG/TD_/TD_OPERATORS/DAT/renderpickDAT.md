# DAT renderpickDAT

## Overview

The Render Pick DAT lets you get information about the 3D surface at any pixel of any 3D render, allowing you to implement multi-touch on a 3D rendered scene.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `strategy` | Strategy | Menu | Decides when to update values based on pick interactions. |
| `clearprev` | Clear Previous Pick on New Pick | Toggle | This parameter is only enabled when the Strategy is set to Hold Last Picked. When this is on, starting a new pick on empty space will clear the values. When off, the last values will be held if the... |
| `responsetime` | Response Time | Menu | Determines when the values are updated. |
| `pickradius` | Pick Radius | Int | Controls the radius of the search area for the pick. If nothing is found at the pick's center it will keep searching for geometry in the search area defined by the Pick Radius. |
| `pickradstep` | Pick Radial Step | Int | Used to reduce the searching within the search area. The search area is sampled at locations that correspond to 'spokes' outwards from the center pick point. |
| `pickcirstep` | Pick Circular Step | Int | Used to reduce the searching within the search area. The search area is sampled at locations that correspond to 'rings' outwards from the center pick point. |
| `rendertop` | Render/RenderPass TOP | TOP | Specifies which scene to pick on, and which camera to pick from. By default the first camera listed in the Render TOP will be used for picking. Another camera can be specified with the 'Custom Pick... |
| `custompickcameras` | Custom Pick Camera(s) | Object | Picking can be done from the viewport of custom camera(s) by specifying one or more Camera COMP here. If this parameter is blank the cameras from the Render TOP are used. To pick from the viewpoint... |
| `allowmulticamera` | Allow Multi-Camera Rendering | Toggle | Multi-Camera Rendering is a faster way to render multiple passes at the same time, and is thus a speed improvement for doing many picks at the same time. This feature may not work correctly for som... |
| `usepickableflags` | Use Pickable Flags | Toggle | When turned on only geometry whose Pickable Flag is on can be selected by the Render Pick DAT. The Pickable Flag is found on all Object components. |
| `includenonpickable` | Include Non-Pickable Objects | Toggle | Includes the non-pickable objects in the picking algorithm such that non-pickable objects may occlude pickable objects.  For example, if there is only one pickable object in the scene with lots of ... |
| `mergeinputdat` | Merge Input DAT | Toggle | Appends input table to the Render Pick DATs columns. |
| `activatecallbacks` | Activate Callbacks | Toggle | Enables Callback DAT for each pick event. |
| `callbacks` | Callbacks DAT | DAT | Path to a DAT containing callbacks for pick event received. |
| `position` | Fetch Position | Menu | Returns the position of the point picked on the geometry. Columns tx, ty, tz. |
| `normal` | Fetch Normal | Menu | Returns the normals of the point picked on the geometry. Columns nx, ny, nz. |
| `referenceobj` | Reference Object | Object | Object used when fetching position or normals Relative to Object. |
| `color` | Fetch Point Color | Toggle | Returns the point color of the point picked on the geometry. Columns cr, cg, cb, ca. |
| `uv` | Fetch Texture UV | Toggle | Returns the texture coordinates of the point picked on the geometry. Columns mapu, mapv, mapw. |
| `depth` | Fetch Depth | Toggle | Returns the depth of the point picked on the geometry. This value a non-linear ratio of the point's position between the near and far planes of the Depth Buffer. Column is depth. |
| `instanceid` | Fetch Instance ID | Toggle | Returns the Instance ID of the object. This will always be 0 if instancing is off. Column is instance. |
| `customattrib1` | Custom Attrib 1 | Str | Specify which custom attributes to return from the object. |
| `customattrib1type` | Custom Attrib 1 Type | Menu | The type of attribute is selected from this menu. |
| `customattrib2` | Custom Attrib 2 | Str | Specify which custom attributes to return from the object. |
| `customattrib2type` | Custom Attrib 2 Type | Menu | The type of attribute is selected from this menu. |
| `customattrib3` | Custom Attrib 3 | Str | Specify which custom attributes to return from the object. |
| `customattrib3type` | Custom Attrib 3 Type | Menu | The type of attribute is selected from this menu. |
| `customattrib4` | Custom Attrib 4 | Str | Specify which custom attributes to return from the object. |
| `customattrib4type` | Custom Attrib 4 Type | Menu | The type of attribute is selected from this menu. |
| `language` | Language | Menu | Select how the DAT decides which script language to operate on. |
| `extension` | Edit/View Extension | Menu | Select the file extension this DAT should expose to external editors. |
| `customext` | Custom Extension | Str | Specifiy the custom extension. |
| `wordwrap` | Word Wrap | Menu | Enable Word Wrap for Node Display. |

## Usage Examples

### Basic Usage

```python
# Access the DAT renderpickDAT operator
renderpickdat_op = op('renderpickdat1')

# Get/set parameters
freq_value = renderpickdat_op.par.active.eval()
renderpickdat_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
renderpickdat_op = op('renderpickdat1')
output_op = op('output1')

renderpickdat_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(renderpickdat_op)
```

## Technical Details

### Operator Family

**DAT** - Data Operators - Process and manipulate table/text data

### Parameter Count

This operator has **33** documented parameters.

## Navigation

- [Back to DAT Index](../DAT/DAT_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
