# COMP tableCOMP

## Overview

The Table Component creates a grid of user interface gadgets.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `attributes` | Cell Attributes DAT | DAT | A list of attribute DATs, one per cell. |
| `rowattributes` | Row Attributes DAT | DAT | A list of attribute DATs, one per row. |
| `colattributes` | Col Attributes DAT | DAT | A list of attribute DATs, one per column. |
| `tableattributes` | Table Attributes DAT | DAT | A single reference to an attribute DAT. |
| `values` | Values DAT | DAT | A list of values that contain the contents of each cell when the cell is a field type. |
| `tablerows` | Table Rows | Int | The number of rows in the table. |
| `tablecols` | Table Columns | Int | The number of columns in the table. |
| `tablealign` | Table Align | Menu | Specifies the order in which cells are arranged: |
| `fontsizeunit` | Font Size Unit | Menu | Lets you choose the unit of the specified font size. |
| `infoformat` | Info Format | Menu | Determines how the state information in a connected Info DAT is displayed. |
| `tableoffset` | Table Offset | Int | Offset the Table. This is not offsetting the Table COMP itself but the Table as it is drawn. So when selecting to Crop the Children, the Table will be potentially cut off at the borders of the Tabl... |
| `tablereset` | Table Reset | Pulse | Refreshes the Table COMP. This can be useful if certain definition DATs have changed. |
| `x` | X | Int | Specify the horizontal position in pixels relative to its parent. |
| `y` | Y | Int | Specify the vertical position in pixels relative to its parent. |
| `w` | Width | Int | Specify the panel's width in pixels. |
| `h` | Height | Int | Specify the Panel's height in pixels. |
| `fixedaspect` | Fixed Aspect | Menu | Allows easy creation of panels with a specific aspect set in the Aspect Ratio parameter below. Only requires setting the width or height of the panel and the other dimension is calculated based on ... |
| `aspect` | Aspect Ratio | Float | Specify the ratio when using Fixed Aspect parameter above, the ratio is width/height. |
| `layer` | Depth Layer | Float | Specifies the order the panel components are drawn in, similar to layers in Photoshop. Higher values will be drawn over any other panel with a lower value (that is at the same level of hierarchy). ... |
| `hmode` | Horizontal Mode | Menu | Select one of 3 modes to determine the horizontal width of the panel. |
| `leftanchor` | Left Anchor | Float | Position of the left anchor of the panel with respect to the parent. This value is normalized 0-1, 0 is the left edge of the parent and 1 is the right edge of the parent. |
| `leftoffset` | Left Offset | Float | An offset for the left anchor in pixels. |
| `rightanchor` | Right Anchor | Float | Position of the right anchor of the panel with respect to the parent. This value is normalized 0-1, 0 is the left edge of the parent and 1 is the right edge of the parent. |
| `rightoffset` | Right Offset | Float | An offset for the right anchor in pixels. |
| `horigin` | Horizontal Origin | Float | Sets the position of the panel's origin horizontally. The default origin (0,0) is the bottom-left corner of the panel. |
| `hfillweight` | Horizontal Fill Weight | Float | When multiple panels are using Horizontal Mode = Fill and being aligned by the parent either Left to Right or Right to Left, this fill weight parameter can be used to bias the fill width of the pan... |
| `vmode` | Vertical Mode | Menu | Select one of 3 modes to determine the vertical height of the panel. |
| `bottomanchor` | Bottom Anchor | Float | Position of the bottom anchor of the panel with respect to the parent. This value is normalized 0-1, 0 is the bottom edge of the parent and 1 is the top edge of the parent. |
| `bottomoffset` | Bottom Offset | Float | An offset for the bottom anchor in pixels. |
| `topanchor` | Top Anchor | Float | Position of the top anchor of the panel with respect to the parent. This value is normalized 0-1, 0 is the bottom edge of the parent and 1 is the top edge of the parent. |
| `topoffset` | Top Offset | Float | An offset for the top anchor in pixels. |
| `vorigin` | Vertical Origin | Float | Sets the position of the panel's origin vertically. The default origin (0,0) is the bottom-left corner of the panel. |
| `vfillweight` | Vertical Fill Weight | Float | When multiple panels are using Vertical Mode = Fill and being aligned by the parent either Top to Bottom or Bottom to Top, this fill weight parameter can be used to bias the fill height of the panels. |
| `alignallow` | Parent Alignment | Menu | When set to Ignore, the Panel will ignore any Align parameter settings from its parent. |
| `alignorder` | Align Order | Float | This parameter allows you to specify the align position when its parent's Align parameter is set to something other then None or Match Network Nodes. Lower numbers are first. |
| `postoffset` | Post Offset | XY | Adds an offset after all other postions and alignment options have been applied to the panel. |
| `sizefromwindow` | Size from Window | Toggle | When enabled the panel component's width and height are set by resizing its floating viewer window. |
| `display` | Display | Toggle | Specifies if the panel is displayed or hidden. Changing this parameter may incur some layout processing costs.  For simple cases, such as overlays it is more performant to adjust the opacity parame... |
| `enable` | Enable | Toggle | Allows you to prevent all interaction with this panel. |
| `helpdat` | Help DAT | DAT | Lets you specify the path to a Text DAT whose content will be displayed as a rollover pop-up help for the control panel. |
| `cursor` | Cursor | Menu | Changes the cursor displayed when cursor is over the panel. |
| `multitouch` | Multi-Touch | Menu | When enabled, this panel will process the first touch it gets in a similar manner to how it processes a mouse click, with updates to u, v, state etc.  The touch event must be initiated from the pan... |
| `constraincursor` | Constrain Cursor | Toggle | Constrains the cursor to this panel, keeping it inside once it enters. |
| `clickthrough` | Click Through | Toggle | When enabled all mouse clicks are ignored by this Panel Component. |
| `mousewheel` | Use Mouse Wheel | Toggle | Turn on to capture events when the mouse wheel is used over the panel. |
| `uvbuttons` | Mouse UV Buttons | Toggle | Allows you to specify which mouse buttons update the uv Panel Values. |
| `mouserel` | Relative UV | Toggle | When enabled the uv Panel Values will reflect relative mouse movement. |
| `resize` | Drag Edges to Resize | Toggle | Four checkboxes allow you to enable resizing a panel by grabbing the corresponding edge or corner: Resize Left, Right, Bottom, Top. |
| `resizew` | W Range | Float | Limits the left-right (width) resizing range. |
| `resizeh` | H Range | Float | Limits the bottom-top (height) resizing range. |
| `reposition` | Drag to Reposition | Menu | Enables repositioning of the panel or window by dragging with the mouse. |
| `repocomp` | Component | PanelCOMP | Enabled by choosing the Component option from the Reposition parameter. Specify the path to the panel component you would like to reposition by mouse. |
| `repositionx` | X Range | Float | Enabled by choosing the Component option from the Reposition parameter.  Sets the maximum range for  repositioning the panel component horizontally. |
| `repositiony` | Y Range | Float | Enabled by choosing the Component option from the Reposition parameter.  Sets the maximum range for repositioning the panel component vertically. |
| `anchordrag` | Anchor Drag | Menu | When Drag To Reposition parameter is set to Component, and the panel's Horizontal Mode and/or Vertical Mode is set to Anchors, this menu determines whether drag-to-reposition actions change Anchor ... |
| `scrolloverlay` | Scroll Overlay | Menu | Controls whether the panel is affected by scrollbar position. This allows the creation of panel overlays that aren't affected by the panel's scrollbars. |
| `bgcolor` | Background Color | RGB | RGB values for the background. (default: black (0,0,0)) |
| `bgalpha` | Background Alpha | Float | Set the alpha value for the background. |
| `top` | Background TOP | TOP | Allows you to specify a TOP as the background for the panel. |
| `topfill` | TOP Fill | Menu | This menu specifies the way the Background TOP will fill the panel's background. |
| `topsmoothness` | TOP Smoothness | Menu | This menu controls background TOP's viewer smoothness settings. In previous builds of TouchDesigner, this was always 'Mipmap Pixels', so old files will load with this setting whereas the default fo... |
| `bordera` | Border A | RGB | RGB values for border A color. |
| `borderaalpha` | Border A Alpha | Float | Alpha value for border A color. |
| `borderb` | Border B | RGB | RGBA values for border B color. |
| `borderbalpha` | Border B Alpha | Float | Alpha value for border B color. |
| `leftborder` | Left Border | Menu | What color the 2 left-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `leftborderi` | Left Border Inside | Menu | Same as above parameter but used for an inside border. |
| `rightborder` | Right Border | Menu | What color the 2 right-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `rightborderi` | Right Border Inside | Menu | Same as above parameter but used for an inside border. |
| `bottomborder` | Bottom Border | Menu | What color the 2 bottom-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `bottomborderi` | Bottom Border Inside | Menu | Same as above parameter but used for an inside border. |
| `topborder` | Top Border | Menu | What color the 2 top-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `topborderi` | Top Border Inside | Menu | Same as above parameter but used for an inside border. |
| `borderover` | Border Over Children | Toggle | Draws the panel's borders on top of all children panels. |
| `dodisablecolor` | Disable Color | Toggle | Enable the use of a unique disable color below when the panel's Enable = Off. |
| `disablecolor` | Disable Color | RGB | RGB values for the disable color. (default: black (0,0,0)) |
| `disablealpha` | Disable Alpha | Float | Set the alpha value for the disable color. |
| `multrgb` | Multiply RGB by Alpha | Toggle | Multiplies the RGB channels by the alpha channel. |
| `composite` | Composite | Menu | Selects how the panel is composited with its siblings panels. See the Composite TOP for a description of the various composite methods. |
| `opacity` | Opacity | Float | Allows you to control the transparency of the panel. |
| `align` | Align | Menu | This menu allows you to specify how the children inside the Panel Component will be laid out. The options Layout Grid Rows,  Layout Grid Columns and Match Network Nodes will scale the Panel Compone... |
| `spacing` | Spacing | Float | This is enabled by choosing any Align option other than None or Match Network Nodes. It defines the space between the children when they are being aligned. |
| `alignmax` | Max per Line | Int | This is enabled by choosing any Align option other than None, Layout Grid Horizontal, Layout Grid Vertical, or Match Network Nodes, and defines the maximum number of children placed in one row or c... |
| `margin` | Margin | Float | The four fields allow you to specify the space that surrounds the Panel Component. The margin is the space between the Panel Component's border and the outer edge.   The Margin is defined in absolu... |
| `justifymethod` | Justify Mathod | Menu | This menu specifies if the panel's children are being justified as a group or individually using the Jusitfy Horizontal / Vertical parameters below. |
| `justifyh` | Justify Horizontal | Menu | This menu specifies if the panel's children are being justified horizontally. |
| `justifyv` | Justify Vertical | Menu | This menu specifies if the panel's children are being justified vertically. |
| `fit` | Fit | Menu | This menu allows you to scale the panel's children. It overrides the Justify Horizontal and Justify Vertical parameters. |
| `scale` | Scale | XY | Allows you to uniformly scale the Panel's children. |
| `offset` | Offset | XY | Allows you to offset the Panel's children. This parameter is overwritten by the Align, Justify Horizontal, and Justify Vertical parameters above. |
| `crop` | Crop | Menu | This menu determines if any children panels which are positioned partially or completely outside the panel component's dimensions get cropped. |
| `phscrollbar` | Horizontal Scrollbar | Menu | Setting for horizontal scrollbar on this panel. |
| `pvscrollbar` | Vertical Scrollbar | Menu | Setting for vertical scrollbar on this panel. |
| `scrollbarthickness` | Thickness | Int | Set the thickness of the scrollbars in pixels. |
| `drag` | When Dragging This | Menu | Specify if this Panel Component can be dragged. |
| `dragscript` | Drag Script | DAT | Specify a script that will be executed when starting to drag a Panel Component. Please refer to the Drag Script section of the Drag and Drop page. |
| `dropdestscript` | Drop Destination Script | DAT | Specify a script that will be executed when the dragged Panel Component is dropped. A temporary network is created and the component (or the alternative operator specified in Dropped Component) is ... |
| `droptypescript` | Drop Types | DAT | If a drop destination script is specified, you can also add a DAT table with a list of return types that the drop destination script will provide. Return types can be one of the op types (COMP,TOP,... |
| `paneldragop` | Dropped Operator | OP | The Dropped Component parameter is the easiest way to specify an alternative operator to drop. Note that this alternative operator must exist, otherwise the component itself will be dropped. The al... |
| `drop` | On Dropping Into | Menu | Specify if this Panel Component accepts items that are dropped onto it. |
| `dropscript` | Drop Script | DAT | A component's Drop Script is run when you drop another component or an external file into that component. Please refer to the Drop Scripts - Text section of the Drag and Drop page.          Alterna... |
| `ext` | Extension | Sequence | Sequence of info for creating extensions on this component |
| `reinitextensions` | Re-Init Extensions | Pulse | Recompile all extension objects. Normally extension objects are compiled only when they are referenced and their definitions have changed. |
| `parentshortcut` | Parent Shortcut | COMP | Specifies a name you can use anywhere inside the component as the path to that component. See Parent Shortcut. |
| `opshortcut` | Global OP Shortcut | COMP | Specifies a name you can use anywhere at all as the path to that component. See Global OP Shortcut. |
| `iop` | Internal OP | Sequence | Sequence header for internal operators. |
| `nodeview` | Node View | Menu | Determines what is displayed in the node viewer, also known as the Node Viewer. Some options will not be available depending on the Component type (Object Component, Panel Component, Misc.) |
| `opviewer` | Operator Viewer | OP | Select which operator's node viewer to use when the Node View parameter above is set to Operator Viewer. |
| `keepmemory` | Keep in Memory | Toggle |  |
| `enablecloning` | Enable Cloning | Toggle | Control if the OP should be actively cloneing. Turning this off causes this node to stop cloning it's 'Clone Master'. |
| `enablecloningpulse` | Enable Cloning Pulse | Pulse | Instantaneously clone the contents. |
| `clone` | Clone Master | COMP | Path to a component used as the Master Clone. |
| `loadondemand` | Load on Demand | Toggle | Loads the component into memory only when required. Good to use for components that are not always used in the project. |
| `enableexternaltox` | Enable External .tox | Toggle | When on (default), the external .tox file will be loaded when the .toe starts and the contents of the COMP will match that of the external .tox. This can be turned off to avoid loading from the ref... |
| `enableexternaltoxpulse` | Enable External .tox Pulse | Pulse | This button will re-load from the external .tox file (if present). |
| `externaltox` | External .tox Path | File | Path to a .tox file on disk which will source the component's contents upon start of a .toe. This allows for components to contain networks that can be updated independently. If the .tox file can n... |
| `reloadcustom` | Reload Custom Parameters | Toggle | When this checkbox is enabled, the values of the component's Custom Parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on nod... |
| `reloadbuiltin` | Reload Built-In Parameters | Toggle | When this checkbox is enabled, the values of the component's built-in parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on n... |
| `savebackup` | Save Backup of External | Toggle | When this checkbox is enabled, a backup copy of the component specified by the External .tox parameter is saved in the .toe file.  This backup copy will be used if the External .tox can not be foun... |
| `subcompname` | Sub-Component to Load | Str | When loading from an External .tox file, this option allows you to reach into the .tox and pull out a COMP and make that the top-level COMP, ignoring everything else in the file (except for the con... |
| `relpath` | Relative File Path Behavior | Menu | Set whether the child file paths within this COMP are relative to the .toe itself or the .tox, or inherit from parent. |

## Usage Examples

### Basic Usage

```python
# Access the COMP tableCOMP operator
tablecomp_op = op('tablecomp1')

# Get/set parameters
freq_value = tablecomp_op.par.active.eval()
tablecomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tablecomp_op = op('tablecomp1')
output_op = op('output1')

tablecomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tablecomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **121** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
