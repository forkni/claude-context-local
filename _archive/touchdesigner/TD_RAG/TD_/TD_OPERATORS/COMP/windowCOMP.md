# COMP windowCOMP

## Overview

The Window Component allows you to create and maintain a separate floating window displaying the contents of any Panel or any other Node Viewer.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `winop` | Window Operator | OP | Specifies the operator the window will display. |
| `title` | Title | Str | Specify the window's title. |
| `justifyoffsetto` | Justisy and Offset to... | Menu | All the positioning parameters below are done relative to the location you specify here. Your window can span more than the specified 'area', it's just used as the reference for positioning. Note f... |
| `ignoretaskbar` | Ignore Taskbar | Toggle | The Windows taskBar is ignored when this option is 'On'. When off the taskbar is accounted for so position and sizing will not cover it up. |
| `monitor` | Monitor | Int | Specify the monitor index when Area is set to Single Monitor. |
| `justifyh` | Justify Horizontal | Menu | Aligns the window horizontally with the monitor or bounds of all monitors. |
| `justifyv` | Justify Vertical | Menu | Aligns the window vertically with the monitor or bounds of all monitors. |
| `winoffset` | Offset | Int | Horizontal offset applied to window after justifying. |
| `single` | Shift to Single Monitor | Menu | This menu has options for shifting the opening window. You can either shift to a single monitor or shift to the monitor the cursor is over when the window opens. |
| `dpiscaling` | DPI Scaling | Menu | Options for managing DPI scaling on high DPI monitors. To inspect a monitor's DPI scaling setting, you can use the Monitors DAT and refer to the dpi_scale column. |
| `size` | Opening Size | Menu | Determines how the size of the window is determined. |
| `winw` | Width | Int | The width of the window when Opening Size parameter is set to Custom. |
| `winh` | Height | Int | The height of the window when Opening Size parameter is set to Custom. |
| `update` | Update Settings from Window | Pulse | When the window is open you can reposition and resize it. Clicking this button will then read its current windows settings and apply them to the parameters above. |
| `borders` | Borders | Toggle | Controls whether or not the window contains borders and a title bar. |
| `bordersinsize` | Include Borders in Size | Toggle | When 'On' the borders are included in the size of the window. |
| `alwaysontop` | Always on Top | Toggle | Controls whether or not the window always sits atop other floating windows. |
| `cursorvisible` | Cursor Visible | Menu | Controls whether or not the cursor remains visible when over this window. |
| `closeescape` | Close on Escape Key | Toggle | When 'On' pressing the escape key over this window will close it. TIP: Shift-Escape will always close it, whether this parameter is on or off. |
| `interact` | Allow Viewer Interaction | Toggle | Enables interactions with the operator specified in the Window Operator parameter. |
| `allowminimize` | Allow Minimize | Toggle | Enables the window to be minimized in the taskbar (dock in macOS). |
| `vsyncmode` | V-Sync Mode | Menu | Controls how the window is updated with regards to V-Sync. Enabled means it will update in sync with the monitors refresh which avoids tearing and lost frames. Disabled means it can update at any p... |
| `drawwindow` | Draw Window | Toggle | When disabled the window will not update it's contents at all. Useful for processes that arn't doing rendering such as Audio or networking processes, or for when using VR devices. |
| `hwframelock` | Hardware Frame-Lock | Toggle | Provides multi-GPU frame-lock sync using Nvidia Quadro Sync and AMD S400 sync cards. For more information, see Syncing Multiple Computers and Hardware Frame Lock. |
| `openglstereo` | OpenGL Stereo | Toggle | No longer supported. Turn 'On' when using openGL stereoscopic output. |
| `winrightop` | Right Eye Operator | OP | No longer supported. This parameter is enabled when the OpenGL Stereo parameter above is turned on. Specify the Camera COMP used for the right eye here. |
| `performance` | Open as Perform Window | Pulse | Opens this Window COMP in Perform Mode. Any Window COMP can be set as default Perform Window (opens using F1 shortcut) using the Window Placement Dialog. This button allows you to open this Window ... |
| `winopen` | Open as Separate Window | Pulse | Opens this Window COMP as its own floating window, not as the Perform Window. Useful for things such as dialog boxes, popups, or testing, but should not be used for putting final rendered content t... |
| `winclose` | Close | Pulse | Closes the window, if it's open. |
| `setperform` | Set as Perform Window | Pulse | Permanently changes the Perform Window setting in the Window Placement dialog to this window. |
| `opendialog` | Window Placement Dialog | Pulse | A shortcut to open the Window Placement dialog. |
| `includedialog` | Include in Placement Dialog | Toggle | When 'On' this Window COMP will be displayed in the Window Placement Dialog. |
| `ext` | Extension | Sequence | Sequence of info for creating extensions on this component |
| `reinitextensions` | Re-Init Extensions | Pulse | Recompile all extension objects. Normally extension objects are compiled only when they are referenced and their definitions have changed. |
| `parentshortcut` | Parent Shortcut | COMP | Specifies a name you can use anywhere inside the component as the path to that component. See Parent Shortcut. |
| `opshortcut` | Global OP Shortcut | COMP | Specifies a name you can use anywhere at all as the path to that component. See Global OP Shortcut. |
| `iop` | Internal OP | Sequence | Sequence header for internal operators. |
| `opviewer` | Operator Viewer | OP | Select which operator's node viewer to use when the Node View parameter above is set to Operator Viewer. |
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
# Access the COMP windowCOMP operator
windowcomp_op = op('windowcomp1')

# Get/set parameters
freq_value = windowcomp_op.par.active.eval()
windowcomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
windowcomp_op = op('windowcomp1')
output_op = op('output1')

windowcomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(windowcomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **50** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
