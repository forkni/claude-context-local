---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Window_COMP
- Container_COMP
- Panel_COMP
concepts:
- window_management
- perform_mode
- display_output
- ui_layout
- application_windowing
- multi_monitor_support
- dpi_scaling
prerequisites:
- CLASS_COMP_Class
- Python_fundamentals
- perform_mode_basics
workflows:
- live_performance_output
- kiosk_applications
- multi_screen_setup
- user_interface_design
- automated_window_control
- display_calibration
keywords:
- window comp class
- perform mode window
- output window
- display output
- application window
- fullscreen
- borderless
- window size
- window position
- DPI scaling
- foreground
- setForeground()
- scalingMonitorIndex
- isBorders
- isFill
- isOpen
tags:
- python
- api_reference
- perform_mode
- display
- fullscreen
- ui
- window_management
- multi_monitor
- automation
relationships:
  CLASS_COMP_Class: strong
  REF_Perform_Mode: strong
  CLASS_UI_Class: medium
  HARDWARE_Multiple_Monitors: medium
related_docs:
- CLASS_COMP_Class
- REF_Perform_Mode
- CLASS_UI_Class
- HARDWARE_Multiple_Monitors
hierarchy:
  secondary: ui_components
  tertiary: window_comp_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- live_performance_output
- kiosk_applications
- multi_screen_setup
- user_interface_design
---

# windowCOMP Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Window_COMP, Container_COMP, Panel_COMP]
concepts: [window_management, perform_mode, display_output, ui_layout, application_windowing, multi_monitor_support, dpi_scaling]
prerequisites: [CLASS_COMP_Class, Python_fundamentals, perform_mode_basics]
workflows: [live_performance_output, kiosk_applications, multi_screen_setup, user_interface_design, automated_window_control, display_calibration]
related: [CLASS_COMP_Class, REF_Perform_Mode, CLASS_UI_Class, HARDWARE_Multiple_Monitors]
relationships: {
  "CLASS_COMP_Class": "strong",
  "REF_Perform_Mode": "strong",
  "CLASS_UI_Class": "medium",
  "HARDWARE_Multiple_Monitors": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "ui_components"
  tertiary: "window_comp_class"
keywords: [window comp class, perform mode window, output window, display output, application window, fullscreen, borderless, window size, window position, DPI scaling, foreground, setForeground(), scalingMonitorIndex, isBorders, isFill, isOpen]
tags: [python, api_reference, perform_mode, display, fullscreen, ui, window_management, multi_monitor, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: live_performance_output, kiosk_applications, multi_screen_setup

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Class Comp Class] → [Python Fundamentals] → [Perform Mode Basics]
**This document**: CLASS reference/guide
**Next steps**: [CLASS COMP Class] → [REF Perform Mode] → [CLASS UI Class]

**Related Topics**: live performance output, kiosk applications, multi screen setup

## Summary

Python class interface for Window COMP operations. Essential for perform mode applications, multi-display setups, and programmatic window management.

## Relationship Justification

Inherits from COMP class and is essential for Perform Mode functionality. Connected to UI class for window management operations and Multiple Monitors guide for multi-display configuration. Critical for deployment and live performance applications.

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [scalingMonitorIndex](#scalingmonitorindex)
  - [isBorders](#isborders)
  - [isFill](#isfill)
  - [isOpen](#isopen)
  - [width](#width)
  - [height](#height)
  - [x](#x)
  - [y](#y)
  - [contentX](#contentx)
  - [contentY](#contenty)
  - [contentWidth](#contentwidth)
  - [contentHeight](#contentheight)
- [Methods](#methods)
  - [setForeground()](#setforeground)
- [COMP Class](#comp-class)
  - [Members](#comp-members)
    - [General](#comp-general)
    - [Privacy](#comp-privacy)
    - [Connection](#comp-connection)
  - [Methods](#comp-methods)
    - [Component Management](#component-management)
    - [Custom Parameters](#custom-parameters)
    - [Privacy Methods](#privacy-methods)
    - [Component Variables](#component-variables)
- [OP Class](#op-class)
  - [Members](#op-members)
    - [General](#op-general)
    - [Common Flags](#common-flags)
    - [Appearance](#op-appearance)
    - [Connection](#op-connection)
    - [Cook Information](#cook-information)
    - [Type](#type)
  - [Methods](#op-methods)
    - [General Methods](#general-methods)
    - [Errors](#errors)
    - [Appearance Methods](#appearance-methods)
    - [Viewers](#viewers)
    - [Storage](#storage)
    - [Miscellaneous](#miscellaneous)

## Introduction

This class inherits from the [CLASS_COMP] class. It references a specific Window COMP.

## Members

### scalingMonitorIndex

scalingMonitorIndex → int (Read Only):

The index of the monitor whose DPI scale is being used to for the Window. This is the usually the monitor the window is covering the most.

### isBorders

isBorders → bool (Read Only):

True if the window is bordered.

### isFill

isFill → bool (Read Only):

True if the window will stretch its contents to fill its specified area.

### isOpen

isOpen → bool (Read Only):

True when window is open.

### width

width → int (Read Only):

Window width. Expressed in points or pixels, depending on the DPI Scaling parameter of the Window COMP.

### height

height → int (Read Only):

Window height. Expressed in points or pixels, depending on the DPI Scaling parameter of the Window COMP.

### x

x → int (Read Only):

Window X coordinate relative to the bottom left of the main monitor. Expressed in points or pixels, depending on the DPI Scaling parameter of the Window COMP.

### y

y → int (Read Only):

Window Y coordinate relative to the bottom left of the main monitor. Expressed in points or pixels, depending on the DPI Scaling parameter of the Window COMP.

### contentX

contentX → int (Read Only):

X position of left edge of the windows contents. Ignores borders if they are present. Expressed in points or pixels, depending on the 'DPI Scaling' parameter setting.

### contentY

contentY → int (Read Only):

Y position of bottom edge of the windows contents. Ignores borders if they are present. Expressed in points or pixels, depending on the 'DPI Scaling' parameter setting.

### contentWidth

contentWidth → int (Read Only):

Width of windows contents. Ignores borders if they are present. Expressed in points or pixels, depending on the 'DPI Scaling' parameter setting.

### contentHeight

contentHeight → int (Read Only):

Height of windows contents. Ignores borders if they are present. Expressed in points or pixels, depending on the 'DPI Scaling' parameter setting.

## Methods

### setForeground()

setForeground()→ bool:

Activates the window, sets it to the foregound and other visual cues. Sets focus and increases process priority.

Can only be called by a foreground process, or a child of a foreground process.

Returns true if successful.

## COMP Class

### COMP Members

#### COMP General

**extensions** → List (Read Only):
A list of extensions attached to this component.

**extensionsReady** → Bool (Read Only):
True unless the extensions are currently compiling. Can be used to avoid accessing promoted members prematurely during an extension initialization function.

**internalOPs** → Dict (Read Only):
A dictionary of internal operator shortcuts found in this component. See also [CLASS_OP].iop

**internalPars** → Dict (Read Only):
A dictionary of internal parameters shortcuts found in this component. See also [CLASS_OP].ipar

**clones** → List (Read Only):
A list of all components cloned to this component.

**componentCloneImmune** → Bool:
Get or set component clone Immune flag. This works together with the cloneImmune member of the [CLASS_OP]. When componentCloneImmune is True, everything inside the clone is immune. When componentCloneImmune is False, it uses the [CLASS_OP] cloneImmune member to determine if just the component is immune (its parameters etc, but not the component's network inside).

**vfs** → VFS (Read Only):
An intermediate VFS object from which embedded VFSFile objects can be accessed. For more information see [REF_VirtualFileSystem].

**dirty** → Bool (Read Only):
True if the contents of the component need to be saved.

**currentChild** → OP (Read Only):
The child operator that is currently selected. To make an operator current, use its own [CLASS_OP].current method.

**selectedChildren** → List (Read Only):
The list of currently selected children. To change an individual operator's selection state, use its own [CLASS_OP].selected method.

**cpuCookTime** → float (Read Only):
Duration of the last measured cook in CPU time (in milliseconds).

**childrenCPUCookTime** → float (Read Only):
The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenCPUCookAbsFrame** → int (Read Only):
The absolute frame on which childrenCookTime is based.

**gpuMemory** → int (Read Only):
The amount of GPU memory this OP is using, in bytes.

**pickable** → Bool:
Get or set pickable flag.

**utility** → Bool:
Get or set utility flag.

**isCOMP** → Bool (Read Only):
True if the operator is a component.

#### COMP Privacy

**isPrivate** → Bool (Read Only):
True if the the component contents cannot be directly viewed.

**isPrivacyActive** → Bool (Read Only):
True if the component is private, and privacy is active. When inactive the contents can be temporarily viewed.

**isPrivacyLicensed** → Bool (Read Only):
True if the component is private and if the required CodeMeter license is present to run it.

**privacyFirmCode** → int (Read Only):
The CodeMeter firm code needed to use this private component. 0 if this component is not private using a CodeMeter dongle.

**privacyProductCode** → int (Read Only):
The CodeMeter product code needed to use this private component. 0 if this component is not private using a CodeMeter dongle.

**privacyDeveloperName** → string (Read Only):
The name of the developer of this private component.

**privacyDeveloperEmail** → string (Read Only):
The email of the developer of this private component.

#### COMP Connection

**inputCOMPs** → List (Read Only):
List of input components to this component through its top connector.

**inputCOMPConnectors** → List (Read Only):
List of input connectors (on the top) associated with this component.

**outputCOMPs** → List (Read Only):
List of output components from this component through its bottom connector.

**outputCOMPConnectors** → List (Read Only):
List of output connectors (on the bottom) associated with this component.

### COMP Methods

#### Component Management

**create(opType, name, initialize=True)** → OP:
Create a new node of the given type, inside this component. If name is supplied the new node will use that name, or the next numbered name if its already in use. opType can be a specific type object, example waveCHOP, or it can be a string 'waveCHOP'. If given an actual instance of a node n, these can be accessed via type(n) and n.OPType respectively.

An initialization script associated with the operator is run, unless initialize=False. The new node is returned.

- `opType` - The python OP type for the type of operator you want to create.
- `name` - (Optional) The name for the new operator. If there already is an operator with that name, the next numbered name will be used.
- `initialize` - (Keyword, Optional) If set to false, then the initialization script for that node won't be run.

```python
n.create(waveCHOP)
w = n.create(boxSOP, 'box12')
```

**collapseSelected()** → None:
Move all selected operators into a new Base COMP. Equivalent to right-click on the network background and choosing Collapse Selected.

**copy(OP, name=None, includeDocked=True)** → OP:
Copy the operator into this component. If name is supplied, the new node will use that name. The new node is returned.

- `OP` - The operator to copy. This is not a string, it must be an OP.
- `name` - (Keyword, Optional) If provided, the new node will have this name.
- `includeDocked` - (Keyword, Optional) When true a copy will include any externally docked operators to the source component.

```python
w = n.copy( op('wave1') )
```

**copyOPs(listOfOPs)** → List:
Copy a list of operators into this component. This is preferred over multiple single copies, as connections between the operators are preserved. A new list with the created operators is returned.

- `listOfOPs` - A list containing one or more OPs to be copied.

```python
alist = [op('wave1'), op('wave2')]
n.copyOPs(alist)
```

**findChildren(type=None, name=None, path=None, depth=None, maxDepth=None, text=None, comment=None, tags=[], allTags=False, parValue=None, parExpr=None, parName=None, onlyNonDefaults=False, includeUtility=False, key=None)** → List of OPs:
Return a list of operators matching the specified criteria.

- `type` - (Keyword, Optional) Specify the type of OP.
- `name` - (Keyword, Optional) Specify the name of the OP. Pattern Matching supported.
- `path` - (Keyword, Optional) Specify the path of the OP. Pattern Matching supported.
- `depth` - (Keyword, Optional) Specify the relative depth of the OP to the calling OP.
- `maxDepth` - (Keyword, Optional) Specify the maximum relative depth of the OP from the calling OP.
- `text` - (Keyword, Optional) Specify the DAT contents of the OP. Pattern Matching supported.
- `comment` - (Keyword, Optional) Specify the OP comment. Pattern Matching supported.
- `tags` - (Keyword, Optional) Specify a list of tags to search. Pattern Matching supported.
- `allTags` - (Keyword, Optional) When True, only include OPs where all specified tags are matched.
- `parValue` - (Keyword, Optional) Specify the value of any parameters in the OP. Pattern Matching supported.
- `parExpr` - (Keyword, Optional) Specify the expression of any parameters in the OP. Pattern Matching supported.
- `parName` - (Keyword, Optional) Specify the name of any parameters in the OP. Pattern Matching supported.
- `onlyNonDefaults` - (Keyword, Optional) When True, only non default parameters are included.
- `includeUtility` - (Keyword, Optional) If specified, controls whether or not Utility nodes are included.
- `key` - (Keyword, Optional) Specify a custom search function.

**initializeExtensions(index=None)** → Extension:
Initialize the components extensions. To initialize an individual extension, specify its index. Returns the compiled extension.

- `index` - (Optional) Index to initialize. 0 = first extension, etc.

**loadTox(filepath, unwired=False, pattern=None, password=None)** → OP:
Load the component from the given file path into this component.

- `filepath` - The path and filename of the .tox to load.
- `unwired` - (Keyword, Optional) If True, the component inputs will remain unwired.
- `pattern` - (Keyword, Optional) Can be specified to only load operators within the component that match the pattern.
- `password` - (Keyword, Optional) If specified, decrypts the tox with the password.

**loadByteArray(byteArray, unwired=False, pattern=None, password=None)** → OP:
Load the component from the given bytearray into this COMP. See `.saveByteArray()` as a way to generate this byteArray.

- `bytearray` - A bytearray containing the component, from a call to saveByteArray().
- `unwired` - (Keyword, Optional) If True, the component inputs will remain unwired.
- `pattern` - (Keyword, Optional) Can be specified to only load operators within the component that match the pattern.
- `password` - (Keyword, Optional) If specified, decrypts the component with the password.

**reload(filepath, password=None)** → None:
Reloads the component from the given file path. This will replace its children as well as top level parameters and update flags, node width/height, storage, comments and inputs (but keep original node x,y).

- `filepath` - The path and filename of the .tox to load.
- `password` - (Keyword, Optional) If specified, decrypts the component with the password.

**resetNetworkView(recurse)** → None:
Reset the network view such that the network editor will be re-homed upon entering this component.

- `recurse` - (Optional) When True, resets network view of all children components as well. Default False.

**save(filepath, createFolders=False, password=None)** → Path:
Saves the component to disk. If no path is provided, a default filename is used and the .tox is saved to project.folder. Returns the filename used.

- `filepath` - (Optional) The path and filename to save the .tox to.
- `createFolders` - (Keyword, Optional) If True, it creates the not existent directories provided by the filepath.
- `password` - (Keyword, Optional) If specified, encrypts the tox with the password.

**saveByteArray(password=None)** → bytearray:
Save the component into a bytearray. The bytearray is the same data that is held in a .tox file. loadByteArray() can be used to load the component.

- `password` - (Keyword, Optional) If specified, encrypts the tox with the password.

**saveExternalTox(recurse=False, password=None)** → int:
Save out the contents of any COMP referencing an external .tox. Returns the number of components saved.

- `recurse` - (Keyword, Optional) If set to True, child components are included in the operation.
- `password` - (Keyword, Optional) If specified, encrypts the tox with the password.

#### Custom Parameters

**appendCustomPage(name)** → Page:
Add a new page of custom parameters. See [CLASS_Page] for more details. See [REF_CustomParameters] for the procedure.

```python
n = op('base1')
page = n.appendCustomPage('Custom1')
page.appendFloat('X1')
```

**destroyCustomPars()** → Total:
Remove all custom parameters from COMP.

**sortCustomPages(page1, page2, page3...)** → None:
Reorder custom parameter pages by listing their page names.

```python
n = op('base1')
n.sortCustomPages('Definition','Controls')
```

#### Privacy Methods

**accessPrivateContents(key)** → Bool:
Gain access to a private component. The component will still be private the next time it is saved or re-opened. Returns true when the key is correct, and access is granted. If dongle privacy is being used, no arguments are required.

- `key` - (Optional) The existing key phrase. This should resolve to a non-blank string. Not required for dongle privacy.

**addPrivacy(key, developerName=None)** → None:
Add privacy to a component with the given key. Privacy can only be added to components that currently have no privacy. Adding Privacy requires a Pro license.

- `key` - The new key phrase. This should resolve to a non-blank string.

**addPrivacy(firmCode, productCode, developerName=None, developerEmail=None)** → None:
Add privacy to a component with the given CodeMeter firm code and product code. Privacy can only be added to components that currently have no privacy. Adding Privacy requires a Pro license.

- `firmCode` - The CodeMeter firm code to use.
- `productCode` - The CodeMeter product code to use.

**blockPrivateContents(key)** → None:
Block access to a private component that was temporarily accessible.

**removePrivacy(key)** → Bool:
Completely remove privacy from a component. Returns true when the key is correct.

- `key` - The existing key phrase. This should resolve to a non-blank string.

#### Component Variables

**setVar(name, value)** → None:
Set a component variable to the specified value.

- `name` - The variable name to use.
- `value` - The value for this variable.

**unsetVar(name)** → None:
Unset the specified component variable. This removes the entry from the 'local/set_variables' table, if found.

- `name` - The name of the variable to unset.

**vars(pattern1, pattern2...)** → List:
Return a list of all component variables in this COMP. Optional name patterns may be specified.

- `pattern` - (Optional) The name(s) of variables whose values should be returned. Pattern Matching can be used.

```python
a = n.vars()
a = n.vars('A*', 'B*')
```

## OP Class

### OP Members

#### OP General

**valid** → bool (Read Only):
True if the referenced operator currently exists, False if it has been deleted.

**id** → int (Read Only):
Unique id for the operator. This id can also be passed to the op() and ops() methods.

**name** → str:
Get or set the operator name.

**path** → str (Read Only):
Full path to the operator.

**digits** → int (Read Only):
Returns the numeric value of the last consecutive group of digits in the name, or None if not found.

**base** → str (Read Only):
Returns the beginning portion of the name occurring before any digits.

**passive** → bool (Read Only):
If true, operator will not cook before its access methods are called.

**curPar** → td.Par (Read Only):
The parameter currently being evaluated.

**curBlock** → (Read Only):
The SequenceBlock of the parameter currently being evaluated.

**curSeq** → Sequence (Read Only):
The Sequence of the parameter currently being evaluated.

**time** → OP (Read Only):
Time Component that defines the operator's time reference.

**ext** → class (Read Only):
The object to search for parent extensions.

**fileFolder** → str (Read Only):
Returns the folder where this node is saved.

**filePath** → str (Read Only):
Returns the file location of this node.

**mod** → mod (Read Only):
Get a module on demand object that searches for DAT modules relative to this operator.

**pages** → list (Read Only):
A list of all built-in pages.

**parGroup** → tuple (Read Only):
An intermediate parameter collection object, from which a specific parameter group can be found.

**par** → td.Par (Read Only):
An intermediate parameter collection object, from which a specific parameter can be found.

**builtinPars** → list or par (Read Only):
A list of all built-in parameters.

**customParGroups** → list of parGroups (Read Only):
A list of all ParGroups, where a ParGroup is a set of parameters all drawn on the same line of a dialog.

**customPars** → list of par (Read Only):
A list of all custom parameters.

**customPages** → list (Read Only):
A list of all custom pages.

**replicator** → OP or None (Read Only):
The replicatorCOMP that created this operator, if any.

**storage** → dict (Read Only):
Storage is dictionary associated with this operator. Values stored in this dictionary are persistent, and saved with the operator.

**tags** → list:
Get or set a set of user defined strings. Tags can be searched using [CLASS_OP].findChildren() and the OP Find DAT.

**children** → list (Read Only):
A list of operators contained within this operator. Only component operators have children.

**numChildren** → int (Read Only):
Returns the number of children contained within the operator.

**numChildrenRecursive** → int (Read Only):
Returns the number of operators contained recursively within this operator.

**op** → OP or None (Read Only):
The operator finder object, for accessing operators through paths or shortcuts.

**opex** → OP (Read Only):
An operator finder object, for accessing operators through paths or shortcuts. Works like the op() shortcut method, except it will raise an exception if it fails to find the node.

**parent** → Shortcut (Read Only):
The Parent Shortcut object, for accessing parent components through indices or shortcuts.

**iop** → OP (Read Only):
The Internal Operator Shortcut object, for accessing internal shortcuts.

**ipar** → ParCollection (Read Only):
The Internal Operator Parameter Shortcut object, for accessing internal shortcuts.

**currentPage** → Page:
Get or set the currently displayed parameter page.

#### Common Flags

**activeViewer** → bool:
Get or set Viewer Active Flag.

**allowCooking** → bool:
Get or set Cooking Flag. Only COMPs can disable this flag.

**bypass** → bool:
Get or set Bypass Flag.

**cloneImmune** → bool:
Get or set Clone Immune Flag.

**current** → bool:
Get or set Current Flag.

**display** → bool:
Get or set Display Flag.

**expose** → bool:
Get or set the Expose Flag which hides a node from view in a network.

**lock** → bool:
Get or set Lock Flag.

**selected** → bool:
Get or set Selected Flag. This controls if the node is part of the network selection.

**seq** → (Read Only):
An intermediate sequence collection object, from which a specific sequence group can be found.

**python** → bool:
Get or set parameter expression language as python.

**render** → bool:
Get or set Render Flag.

**showCustomOnly** → bool:
Get or set the Show Custom Only Flag which controls whether or not non custom parameters are display in parameter dialogs.

**showDocked** → bool:
Get or set Show Docked Flag. This controls whether this node is visible or hidden when it is docked to another node.

**viewer** → bool:
Get or set Viewer Flag.

#### OP Appearance

**color** → tuple(r, g, b):
Get or set color value, expressed as a 3-tuple, representing its red, green, blue values.

**comment** → str:
Get or set comment string.

**nodeHeight** → int:
Get or set node height, expressed in network editor units.

**nodeWidth** → int:
Get or set node width, expressed in network editor units.

**nodeX** → int:
Get or set node X value, expressed in network editor units, measured from its left edge.

**nodeY** → int:
Get or set node Y value, expressed in network editor units, measured from its bottom edge.

**nodeCenterX** → int:
Get or set node X value, expressed in network editor units, measured from its center.

**nodeCenterY** → int:
Get or set node Y value, expressed in network editor units, measured from its center.

**dock** → OP:
Get or set the operator this operator is docked to. To clear docking, set this member to None.

**docked** → list (Read Only):
The (possibly empty) list of operators docked to this node.

#### OP Connection

**inputs** → list (Read Only):
List of input operators (via left side connectors) to this operator.

**outputs** → list (Read Only):
List of output operators (via right side connectors) from this operator.

**inputConnectors** → list (Read Only):
List of input connectors (on the left side) associated with this operator.

**outputConnectors** → list (Read Only):
List of output connectors (on the right side) associated with this operator.

#### Cook Information

**cookFrame** → float (Read Only):
Last frame at which this operator cooked.

**cookTime** → float (Read Only):
**Deprecated** Duration of the last measured cook (in milliseconds).

**cpuCookTime** → float (Read Only):
Duration of the last measured cook in CPU time (in milliseconds).

**cookAbsFrame** → float (Read Only):
Last absolute frame at which this operator cooked.

**cookStartTime** → float (Read Only):
Last offset from frame start at which this operator cook began, expressed in milliseconds.

**cookEndTime** → float (Read Only):
Last offset from frame start at which this operator cook ended, expressed in milliseconds.

**cookedThisFrame** → bool (Read Only):
True when this operator has cooked this frame.

**cookedPreviousFrame** → bool (Read Only):
True when this operator has cooked the previous frame.

**childrenCookTime** → float (Read Only):
**Deprecated** The total accumulated cook time of all children of this operator during the last frame.

**childrenCPUCookTime** → float (Read Only):
The total accumulated cook time of all children of this operator during the last frame.

**childrenCookAbsFrame** → float (Read Only):
**Deprecated** The absolute frame on which childrenCookTime is based.

**childrenCPUCookAbsFrame** → float (Read Only):
The absolute frame on which childrenCPUCookTime is based.

**gpuCookTime** → float (Read Only):
Duration of GPU operations during the last measured cook (in milliseconds).

**childrenGPUCookTime** → float (Read Only):
The total accumulated GPU cook time of all children of this operator during the last frame.

**childrenGPUCookAbsFrame** → float (Read Only):
The absolute frame on which childrenGPUCookTime is based.

**totalCooks** → int (Read Only):
Number of times the operator has cooked.

**cpuMemory** → int (Read Only):
The approximate amount of CPU memory this Operator is using, in bytes.

**gpuMemory** → int (Read Only):
The amount of GPU memory this OP is using, in bytes.

#### Type

**type** → str (Read Only):
Operator type as a string. Example: 'oscin'.

**subType** → str (Read Only):
Operator subtype. Currently only implemented for components.

**OPType** → str (Read Only):
Python operator class type, as a string. Example: 'oscinCHOP'.

**label** → str (Read Only):
Operator type label. Example: 'OSC In'.

**icon** → str (Read Only):
Get the letters used to create the operator's icon.

**family** → str (Read Only):
Operator family. Example: CHOP.

**isFilter** → bool (Read Only):
True if operator is a filter, false if it is a generator.

**minInputs** → int (Read Only):
Minimum number of inputs to the operator.

**maxInputs** → int (Read Only):
Maximum number of inputs to the operator.

**isMultiInputs** → bool (Read Only):
True if inputs are ordered, false otherwise.

**visibleLevel** → int (Read Only):
Visibility level of the operator.

**isBase** → bool (Read Only):
True if the operator is a Base (miscellaneous) component.

**isCHOP** → bool (Read Only):
True if the operator is a CHOP.

**isCOMP** → bool (Read Only):
True if the operator is a component.

**isDAT** → bool (Read Only):
True if the operator is a DAT.

**isMAT** → bool (Read Only):
True if the operator is a Material.

**isObject** → bool (Read Only):
True if the operator is an object.

**isPanel** → bool (Read Only):
True if the operator is a Panel.

**isSOP** → bool (Read Only):
True if the operator is a SOP.

**isTOP** → bool (Read Only):
True if the operators is a TOP.

**licenseType** → str (Read Only):
Type of License required for the operator.

### OP Methods

#### General Methods

**pars(pattern)** → list:
Returns a (possibly empty) list of parameter objects that match the pattern.

- `pattern` - Is a string following the Pattern Matching rules, specifying which parameters to return.

**cook(force=False, recurse=False, includeUtility=False)** → None:
Cook the contents of the operator if required.

- `force` - (Keyword, Optional) If True, the operator will always cook.
- `recurse` - (Keyword, Optional) If True, all children and sub-children of the operator will be cooked.
- `includeUtility` - (Keyword, Optional) If specified, controls whether or not utility components are included.

**copyParameters(OP, custom=True, builtin=True)** → None:
Copy all of the parameters from the specified operator. Both operators should be the same type.

- `OP` - The operator to copy.
- `custom` - (Keyword, Optional) When True, custom parameters will be copied.
- `builtin` - (Keyword, Optional) When True, built in parameters will be copied.

**changeType(OPtype)** → OP:
Change referenced operator to a new operator type. After this call, this OP object should no longer be referenced.

- `OPtype` - The python class name of the operator type you want to change this operator to.

**dependenciesTo(OP)** → list:
Returns a (possibly empty) list of operator dependency paths between this operator and the specified operator.

**evalExpression(str)** → value:
Evaluate the expression from the context of this OP.

- `str` - The expression to evaluate.

**destroy()** → None:
Destroy the operator referenced by this OP.

**var(name, search=True)** → str:
Evaluate a variable. This will return the empty string, if not found.

- `name` - The variable name to search for.
- `search` - (Keyword, Optional) If set to True the operator hierarchy is searched until a variable matching that name is found.

**openMenu(x=None, y=None)** → None:
Open a node menu for the operator at x, y. Opens at mouse if x & y are not specified.

- `x` - (Keyword, Optional) The X coordinate of the menu, measured in screen pixels.
- `y` - (Keyword, Optional) The Y coordinate of the menu, measured in screen pixels.

**relativePath(OP)** → str:
Returns the relative path from this operator to the OP that is passed as the argument.

**setInputs(listOfOPs)** → None:
Set all the operator inputs to the specified list.

- `listOfOPs` - A list containing one or more OPs. Entries in the list can be None to disconnect specific inputs.

**shortcutPath(OP, toParName=None)** → str:
Returns an expression from this operator to the OP that is passed as the argument.

- `toParName` - (Keyword, Optional) Return an expression to this parameter instead of its operator.

**ops(pattern1, pattern2.., includeUtility=False)** → list of OPs:
Returns a (possibly empty) list of OPs that match the patterns, relative to the inside of this OP.

- `pattern` - Can be string following the Pattern Matching rules, or an integer OP Id.
- `includeUtility` - (Keyword, Optional) If specified, controls whether or not utility components are included.

**resetPars(parNames='*', parGroupNames='*', pageNames='*', includeBuiltin=True, includeCustom=True)** → bool:
Resets the specified parameters in the operator. Returns true if anything was changed.

- `parNames` - (Keyword, Optional) Specify parameters by Par name.
- `parGroupNames` - (Keyword, Optional) Specify parameters by ParGroup name.
- `pageNames` - (Keyword, Optional) Specify parameters by page name.
- `includeBuiltin` - (Keyword, Optional) Include builtin parameters.
- `includeCustom` - (Keyword, Optional) Include custom parameters.

#### Errors

**addScriptError(msg)** → None:
Adds a script error to a node.

- `msg` - The error to add.

**addError(msg)** → None:
Adds an error to an operator. Only valid if added while the operator is cooking.

- `msg` - The error to add.

**addWarning(msg)** → None:
Adds a warning to an operator. Only valid if added while the operator is cooking.

- `msg` - The error to add.

**errors(recurse=False)** → str:
Get error messages associated with this OP.

- `recurse` - Get errors in any children or subchildren as well.

**warnings(recurse=False)** → str:
Get warning messages associated with this OP.

- `recurse` - Get warnings in any children or subchildren as well.

**scriptErrors(recurse=False)** → str:
Get script error messages associated with this OP.

- `recurse` - Get errors in any children or subchildren as well.

**clearScriptErrors(recurse=False, error='*')** → None:
Clear any errors generated during script execution.

- `recurse` - Clear script errors in any children or subchildren as well.
- `error` - Pattern to match when clearing errors.

**childrenCPUMemory()** → int:
Returns the total CPU memory usage for all the children from this COMP.

**childrenGPUMemory()** → int:
Returns the total GPU memory usage for all the children from this COMP.

#### Appearance Methods

**resetNodeSize()** → None:
Reset the node tile size to its default width and height.

#### Viewers

**closeViewer(topMost=False)** → None:
Close the floating content viewers of the OP.

- `topMost` - (Keyword, Optional) If True, any viewer window containing any parent of this OP is closed instead.

**openViewer(unique=False, borders=True)** → None:
Open a floating content viewer for the OP.

- `unique` - (Keyword, Optional) If False, any existing viewer for this OP will be re-used.
- `borders` - (Keyword, Optional) If true, the floating window containing the viewer will have borders.

**resetViewer(recurse=False)** → None:
Reset the OP content viewer to default view settings.

- `recurse` - (Keyword, Optional) If True, this is done for all children and sub-children as well.

**openParameters()** → None:
Open a floating dialog containing the operator parameters.

#### Storage

Storage can be used to keep data within components. Storage is implemented as one python dictionary per node. When an element of storage is changed by using `n.store()`, expressions and operators that depend on it will automatically re-cook. Storage is saved in .toe and .tox files and restored on startup.

**fetch(key, default, search=True, storeDefault=False)** → value:
Return an object from the OP storage dictionary. If the item is not found, and a default it supplied, it will be returned instead.

- `key` - The name of the entry to retrieve.
- `default` - (Optional) If provided and no item is found then the passed value/object is returned instead.
- `storeDefault` - (Keyword, Optional) If True, and the key is not found, the default is stored as well.
- `search` - (Keyword, Optional) If True, the parent of each OP is searched recursively until a match is found.

**fetchOwner(key)** → OP:
Return the operator which contains the stored key, or None if not found.

- `key` - The key to the stored entry you are looking for.

**store(key, value)** → value:
Add the key/value pair to the OP's storage dictionary, or replace it if it already exists.

- `key` - A string name for the storage entry.
- `value` - The value/object to store.

**unstore(keys1, keys2..)** → None:
For key, remove it from the OP's storage dictionary. Pattern Matching is supported as well.

- `keys` - The name or pattern defining which key/value pairs to remove from the storage dictionary.

**storeStartupValue(key, value)** → None:
Add the key/value pair to the OP's storage startup dictionary. The storage element will take on this value when the file starts up.

- `key` - A string name for the storage startup entry.
- `value` - The startup value/object to store.

**unstoreStartupValue(keys1, keys2..)** → None:
For key, remove it from the OP's storage startup dictionary. Pattern Matching is supported as well.

- `keys` - The name or pattern defining which key/value pairs to remove from the storage startup dictionary.

#### Miscellaneous

****getstate**()** → dict:
Returns a dictionary with persistent data about the object suitable for pickling and deep copies.

****setstate**()** → dict:
Reads the dictionary to update persistent details about the object, suitable for unpickling and deep copies.
