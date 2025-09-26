# COMP engineCOMP

## Overview

The Engine COMP will run a .tox file (component) in a separate process. It uses TouchEngine to manage these processes and pass data between the loaded component and the main project.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | Tox File | File | Specify the .tox file to load with TouchEngine. |
| `unload` | Unload | Pulse | Unload the currently loaded component. |
| `reload` | Reload | Pulse | Reload the currently loaded component. |
| `reloadoncrash` | Reload on Crash | Toggle | If the TouchEngine instance quits for any reason, restart it. |
| `assetpaths` | Asset Paths | Menu | Specify how relative paths inside the component are resolved. |
| `callbacks` | Callbacks DAT | DAT | The Callbacks DAT will execute for events related to the TouchEngine instance. |
| `clock` | Clock | Menu | Specify the temporal connection to the TouchEngine instance. |
| `matchrate` | Match Local Component Rate | Toggle | When on, the component will be cooked in TouchEngine at the same rate as the Engine COMP. |
| `fps` | Frames per Second | Float | The framerate for cooking the component in TouchEngine. |
| `wait` | Wait for Render | Toggle | When enabled, if a frame takes a long time to cook in TouchEngine the Engine COMP will wait during cooking rather than dropping the late frame.  This behaviour is affected by the size of the output... |
| `timeout` | Render Timeout | Int | When waiting for a frame, TouchEngine will give up waiting after this many milliseconds. |
| `inauto` | In Buffer Auto | Toggle | Automatically manage the number of input frames queued. |
| `inframes` | In Buffer Frames | Int | The number of input frames to queue before passing them to the TouchEngine instance.  To accommodate potential fluctuations in time-slice in the TouchEngine instance, CHOP inputs must send a number... |
| `outauto` | Out Buffer Auto | Toggle | Automatically manage the number of output frames queued. |
| `outframes` | Out Buffer Frames | Int | The number of output frames to queue after receiving them from the TouchEngine instance.  To accommodate potential fluctuations in time-slice in the Engine COMP, CHOP outputs must send a number of ... |
| `preroll` | Pre-Roll | Float | At initialization, run for this long before entering the ready state. |
| `prerollunits` | Pre-Roll Units | Menu | The units in which the Pre-Roll is measured. |
| `readywhen` | Ready when | Menu | Specify when the Engine COMP will go into the ready state. |
| `startoninit` | Start when Initialized | Toggle | When enabled, playback will start as soon as the component has initialized and is in the ready state. |
| `initialize` | Initialize | Pulse | Reload the .tox file, restarting the TouchEngine instance. |
| `start` | Start | Pulse | Starts playback of the component in the TouchEngine instance. |
| `play` | Play | Toggle | Turn cooking in the TouchEngine instance on or off. |
| `gotodone` | Go to Done | Pulse | Puts the Engine COMP in the done state. |
| `ondone` | On Done | Menu | Determines the actions taken, if any, when the Engine COMP enters the done state. |
| `oncompcreate` | On Engine COMP Create | Menu | Specify what happens when the Engine COMP is created, for example when the project is loaded. |
| `launch` | Launch Engine Process | Pulse | Starts the TouchEngine process if it is not running. |
| `quit` | Quit Engine Process | Pulse | Stops the TouchEngine process if it is running. |
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
# Access the COMP engineCOMP operator
enginecomp_op = op('enginecomp1')

# Get/set parameters
freq_value = enginecomp_op.par.active.eval()
enginecomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
enginecomp_op = op('enginecomp1')
output_op = op('output1')

enginecomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(enginecomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **45** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
