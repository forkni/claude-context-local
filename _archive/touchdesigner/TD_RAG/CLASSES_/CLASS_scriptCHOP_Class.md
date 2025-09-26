---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Script_CHOP
- Expression_CHOP
- Pattern_CHOP
concepts:
- procedural_channel_generation
- chop_scripting
- python_callbacks
- custom_operator_creation
- numpy_integration
- parameter_management
- time_slice_processing
prerequisites:
- CLASS_CHOP_Class
- Python_fundamentals
- numpy_basics
workflows:
- custom_data_generation
- advanced_data_manipulation
- procedural_animation
- algorithm_implementation_in_chops
- real_time_data_processing
- audio_reactive_systems
keywords:
- script chop class
- scripting
- procedural generation
- CHOP data
- numpy
- custom parameters
- onCook
- onSetupParameters
- onPulse
- appendChan
- clear
- copy
- time slice
- channel manipulation
- copyNumpyArray
- destroyCustomPars
tags:
- python
- api_reference
- chop
- scripting
- procedural
- numpy
- real_time
- data_processing
- animation
- algorithms
relationships:
  CLASS_CHOP_Class: strong
  CLASS_Channel_Class: strong
  PY_Working_with_CHOPs_in_Python: strong
  CLASS_scriptTOP_Class: medium
  PY_Python_Tips: medium
related_docs:
- CLASS_CHOP_Class
- CLASS_Channel_Class
- CLASS_scriptTOP_Class
- PY_Working_with_CHOPs_in_Python
- PY_Python_Tips
hierarchy:
  secondary: chop_scripting
  tertiary: script_chop_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- custom_data_generation
- advanced_data_manipulation
- procedural_animation
- algorithm_implementation_in_chops
---

# scriptCHOP Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_CHOP, Expression_CHOP, Pattern_CHOP]
concepts: [procedural_channel_generation, chop_scripting, python_callbacks, custom_operator_creation, numpy_integration, parameter_management, time_slice_processing]
prerequisites: [CLASS_CHOP_Class, Python_fundamentals, numpy_basics]
workflows: [custom_data_generation, advanced_data_manipulation, procedural_animation, algorithm_implementation_in_chops, real_time_data_processing, audio_reactive_systems]
related: [CLASS_CHOP_Class, CLASS_Channel_Class, CLASS_scriptTOP_Class, PY_Working_with_CHOPs_in_Python, PY_Python_Tips]
relationships: {
  "CLASS_CHOP_Class": "strong",
  "CLASS_Channel_Class": "strong",
  "PY_Working_with_CHOPs_in_Python": "strong",
  "CLASS_scriptTOP_Class": "medium",
  "PY_Python_Tips": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "chop_scripting"
  tertiary: "script_chop_class"
keywords: [script chop class, scripting, procedural generation, CHOP data, numpy, custom parameters, onCook, onSetupParameters, onPulse, appendChan, clear, copy, time slice, channel manipulation, copyNumpyArray, destroyCustomPars]
tags: [python, api_reference, chop, scripting, procedural, numpy, real_time, data_processing, animation, algorithms]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: custom_data_generation, advanced_data_manipulation, procedural_animation

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Class Chop Class] → [Python Fundamentals] → [Numpy Basics]
**This document**: CLASS reference/guide
**Next steps**: [CLASS CHOP Class] → [CLASS Channel Class] → [CLASS scriptTOP Class]

**Related Topics**: custom data generation, advanced data manipulation, procedural animation

## Summary

Specialized CHOP class for procedural data generation using Python. Critical for custom algorithms, data processing, and procedural animation workflows.This class inherits from the CHOP class. It references a specific Script CHOP.

## Relationship Justification

IInherits from CHOP class and works directly with Channel class for data manipulation. Strongly connected to CHOP usage guide for practical examples. Paired with scriptTOP class as complementary procedural operators.

## Content

- [Introduction](#introduction)
- [scriptCHOP Specific](#scriptchop-specific)
  - [Members](#members)
  - [Methods](#methods)
  - [Callbacks](#callbacks)
- [CHOP Class](#chop-class)
  - [Members](#chop-members)
  - [Methods](#chop-methods)
- [OP Class](#op-class)
  - [Members](#op-members)
    - [General](#general)
    - [Common Flags](#common-flags)
    - [Appearance](#appearance)
    - [Connection](#connection)
    - [Cook Information](#cook-information)
    - [Type](#type)
  - [Methods](#op-methods)
    - [General](#op-general)
    - [Errors](#errors)
    - [Appearance](#op-appearance)
    - [Viewers](#viewers)
    - [Storage](#storage)
    - [Miscellaneous](#miscellaneous)

## Introduction

This class inherits from the [CLASS_CHOP] class. It references a specific [CLASS_ScriptCHOP].

## scriptCHOP Specific

### Members

#### timeSliceDefault

timeSliceDefault → bool (Read Only):

Get the default Time Slice for the [CLASS_ScriptCHOP]. Equal to the first input's isTimeSlice.

### Methods

These methods can be used by including them in the onCook callback of the [CLASS_ScriptCHOP]. Using them outside the callback may cause unexpected results.

#### copyNumpyArray()

copyNumpyArray(numpyArray, baseName='chan')→ None:

Copies the contents of the numpyArray into the CHOP.

- `numpyArray` - The NumPy Array to copy. Must be shape(numChannels, numSamples). The data type must be float32.
- `baseName` - (Keyword, Optional) The base of all created channel names beginning with a suffix of 1. Example 'chan' creates 'chan1', 'chan2', etc.

#### destroyCustomPars()

destroyCustomPars()→ int:

Remove all custom parameters from the [CLASS_ScriptCHOP]. Returns number of destroyed pars.

#### sortCustomPages()

sortCustomPages(*pages)→ None:

Reorder custom parameter pages.

- `pages` - any number of page names in their new order

```python
scriptOp.sortPages('Definition','Controls')
```

#### clear()

clear()→ None:

Remove all channels from the CHOP. The channel length, sample rate etc. remain unchanged.

#### appendCustomPage()

appendCustomPage(name)→ [CLASS_Page]:

Add a new page of custom parameters. See [CLASS_Page] for more details.

```python
page = scriptOp.appendCustomPage('Custom1')
page.appendFloat('X1')
```

#### copy()

copy(chop)→ None:

Match all of this CHOPs channel data to the given CHOP. This includes sample rate, length, channel names and channel data.

- `chop` - The CHOP to copy. This should be a [CLASS_CHOP] instance, not a path to the CHOP.

#### appendChan()

appendChan(name)→ [CLASS_Channel]:

Append a new channel to the CHOP. If no name is given the channel will be given a default but unique name.

- `name` - (Optional) The name to give the channel.

```python
c = n.appendChan()
c = n.appendChan('velocity')
```

### Callbacks

The following python callbacks are associated with this operator.

```python
# me - this DAT
# scriptOp - the OP which is cooking

# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def onSetupParameters(scriptOp):
    page = scriptOp.appendCustomPage('Custom')
    p = page.appendFloat('Valuea', label='Value A')
    p = page.appendFloat('Valueb', label='Value B')
    return

# called whenever custom pulse parameter is pushed
def onPulse(par):
    return

def onCook(scriptOp):
    scriptOp.clear()
    return
```

## CHOP Class

### Members

As these attributes are dependent on each other, set the rate and start (or startTime) attributes, before the len, end (or endTime) attributes.

#### numChans

numChans → int (Read Only):

The number of channels.

#### numSamples

numSamples → int:

Get or set the number of samples (or indices) per channel. You can change the number of samples by setting this value, only in a [CLASS_ScriptCHOP].

#### start

start → float:

Get or set the start index of the channels. This can be modified only when the CHOP is a [CLASS_ScriptCHOP].

#### end

end → float:

Get or set the end index of the channels. This can be modified only when the CHOP is a [CLASS_ScriptCHOP].

#### rate

rate → float:

Get or set the sample rate of the CHOP. This can be modified only when the CHOP is a [CLASS_ScriptCHOP].

#### isTimeSlice

isTimeSlice → bool:

Get or set the last cooked Time Slice value. True if the CHOP last cooked as a Time Slice. This can be modified only when the CHOP is a [CLASS_ScriptCHOP].

#### export

export → bool:

Get or set Export Flag.

#### exportChanges

exportChanges → int (Read Only):

Number of times the export mapping information has changed.

#### isCHOP

isCHOP → bool (Read Only):

True if the operator is a CHOP.

### Methods

#### [nameOrIndex]

[nameOrIndex]→ [CLASS_Channel]:

Channels may be easily accessed from a CHOP using the [] subscript operator.

- `nameOrIndex` - Must be an exact string name, or it may be a numeric channel index. Wildcards are not supported. Refer to the help on channels to see how to use the returned [CLASS_Channel] object.

```python
n = op('pattern1')
c = n[4]
c = n['chan2']
# and to get the third sample from the channel, assuming the channel has 3 or more samples:
n = op('pattern1')
c = n['chan2'][2]
```

#### chan()

chan(*nameOrIndex, caseSensitive=True)→ [CLASS_Channel] | None:

Returns the first [CLASS_Channel] that matches the given name or index or None if none are found.

Multiple patterns may be specified which are all added to the search.

- `nameOrIndex` - May be a string name, possibly using [REF_PatternMatching], or it may be a numeric channel index. You can provide multiple.
- `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.

```python
n = op('pattern1')
c = n.chan(4)
c = n.chan('chan*')
c = n.chan('chan3zall', caseSensitive=False)
```

#### chans()

chans(*nameOrIndex, caseSensitive=True)→ list:

Returns a (possibly empty) list of Channels that match that specified names or indices. Multiple names and indices may be provided.

- `nameOrIndex` - (Optional) One or more string names, possibly using [REF_PatternMatching], or numeric channel index. No arguments are passed, a list of all channels is returned.
- `caseSensitive` - (Optional) Specifies whether or not case sensitivity is used.

```python
n = op('pattern1')
newlist = n.chans() # get all channels in the CHOP
newlist = n.chans('a*', 3,4,5, 'd*')
```

#### numpyArray()

numpyArray()→ numpy.array:

Returns all of the channels in this CHOP a 2D NumPy array with a width equal to the channel length (the number of samples) and a height equal to the number of channels. See [REF_NumPy].

#### convertToKeyframes()

convertToKeyframes(tolerance=0.1)→ [CLASS_AnimationCOMP]:

Create an [CLASS_AnimationCOMP] that contains a keyframed approximation of the CHOP's channels.

The resultant [CLASS_AnimationCOMP] is returned.

- `tolerance` - (Keyword, Optional) If this is not given, the default value is 0.1. It may be overridden for higher accuracy match between the source channels and the resulting keyframed channels.

#### save()

save(filepath, createFolders=False)→ str:

Saves the channel to the file system. Supported file formats are .clip, .bclip, .chan, .bchan and .aiff.

Returns the file path used.

- `filepath` - (Optional) The path and filename to save to.
- `createFolders` - (Keyword, Optional) If True, it creates the not existent directories provided by the filepath.

```python
n = op('pattern1')
name = n.save()   #save in native format with default name
n.save('output.chan')  #ascii readable tab delimited format
n.save('output.aiff')  #supported audio format
```

## OP Class

### Members

#### General

**valid** → bool (Read Only): True if the referenced operator currently exists, False if it has been deleted.

**id** → int (Read Only): Unique id for the operator. This id can also be passed to the op() and ops() methods. Id's are not consistent when a file is re-opened, and will change if the OP is copied/pasted, changes OP types, deleted/undone. The id will not change if the OP is renamed though. Its data type is integer.

**name** → str: Get or set the operator name.

**path** → str (Read Only): Full path to the operator.

**digits** → int (Read Only): Returns the numeric value of the last consecutive group of digits in the name, or None if not found. The digits can be in the middle of the name if there are none at the end of the name.

**base** → str (Read Only): Returns the beginning portion of the name occurring before any digits.

**passive** → bool (Read Only): If true, operator will not cook before its access methods are called. To use a passive version of an operator n, use passive(n).

**curPar** → [CLASS_Par] (Read Only): The parameter currently being evaluated. Can be used in a parameter expression to reference itself. An easy way to see this is to put the expression curPar.name in any string parameter.

**curBlock** → (Read Only): The SequenceBlock of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

**curSeq** → [CLASS_Sequence] (Read Only): The Sequence of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

**time** → [CLASS_OP] (Read Only): Time Component that defines the operator's time reference.

**ext** → class (Read Only): The object to search for parent extensions. Example: `me.ext.MyClass`

**fileFolder** → str (Read Only): Returns the folder where this node is saved.

**filePath** → str (Read Only): Returns the file location of this node.

**mod** → mod (Read Only): Get a module on demand object that searches for DAT modules relative to this operator.

**pages** → list (Read Only): A list of all built-in pages.

**parGroup** → tuple (Read Only): An intermediate parameter collection object, from which a specific parameter group can be found. Example: `n.parGroup.t` or `n.parGroup['t']`

**par** → [CLASS_Par] (Read Only): An intermediate parameter collection object, from which a specific parameter can be found. Example: `n.par.tx` or `n.par['tx']`

**builtinPars** → list or par (Read Only): A list of all built-in parameters.

**customParGroups** → list of parGroups (Read Only): A list of all ParGroups, where a ParGroup is a set of parameters all drawn on the same line of a dialog, sharing the same label.

**customPars** → list of par (Read Only): A list of all custom parameters.

**customPages** → list (Read Only): A list of all custom pages.

**replicator** → [CLASS_OP] or None (Read Only): The replicatorCOMP that created this operator, if any.

**storage** → dict (Read Only): Storage is dictionary associated with this operator. Values stored in this dictionary are persistent, and saved with the operator. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with methods such as [CLASS_OP].fetch() or [CLASS_OP].store() described below, or examined with an Examine DAT.

**tags** → list: Get or set a set of user defined strings. Tags can be searched using [CLASS_OP].findChildren() and the OP Find DAT.

**children** → list (Read Only): A list of operators contained within this operator. Only component operators have children, otherwise an empty list is returned.

**numChildren** → int (Read Only): Returns the number of children contained within the operator. Only component operators have children.

**numChildrenRecursive** → int (Read Only): Returns the number of operators contained recursively within this operator. Only component operators have children.

**op** → [CLASS_OP] or None (Read Only): The operator finder object, for accessing operators through paths or shortcuts.

**opex** → [CLASS_OP] (Read Only): An operator finder object, for accessing operators through paths or shortcuts. Works like the op() shortcut method, except it will raise an exception if it fails to find the node instead of returning None as op() does.

**parent** → Shortcut (Read Only): The Parent Shortcut object, for accessing parent components through indices or shortcuts.

**iop** → [CLASS_OP] (Read Only): The Internal Operator Shortcut object, for accessing internal shortcuts. See also [REF_InternalOperators].

**ipar** → ParCollection (Read Only): The Internal Operator Parameter Shortcut object, for accessing internal shortcuts. See also [REF_InternalParameters].

**currentPage** → [CLASS_Page]: Get or set the currently displayed parameter page. It can be set by setting it to another page or a string label.

#### Common Flags

**activeViewer** → bool: Get or set Viewer Active Flag.

**allowCooking** → bool: Get or set Cooking Flag. Only COMPs can disable this flag.

**bypass** → bool: Get or set Bypass Flag.

**cloneImmune** → bool: Get or set Clone Immune Flag.

**current** → bool: Get or set Current Flag.

**display** → bool: Get or set Display Flag.

**expose** → bool: Get or set the Expose Flag which hides a node from view in a network.

**lock** → bool: Get or set Lock Flag.

**selected** → bool: Get or set Selected Flag. This controls if the node is part of the network selection. (yellow box around it).

**seq** → (Read Only): An intermediate sequence collection object, from which a specific sequence group can be found.

**python** → bool: Get or set parameter expression language as python.

**render** → bool: Get or set Render Flag.

**showCustomOnly** → bool: Get or set the Show Custom Only Flag which controls whether or not non custom parameters are display inparameter dialogs.

**showDocked** → bool: Get or set Show Docked Flag. This controls whether this node is visible or hidden when it is docked to another node.

**viewer** → bool: Get or set Viewer Flag.

#### Appearance

**color** → tuple(r, g, b): Get or set color value, expressed as a 3-tuple, representing its red, green, blue values. To convert between color spaces, use the built in colorsys module.

**comment** → str: Get or set comment string.

**nodeHeight** → int: Get or set node height, expressed in network editor units.

**nodeWidth** → int: Get or set node width, expressed in network editor units.

**nodeX** → int: Get or set node X value, expressed in network editor units, measured from its left edge.

**nodeY** → int: Get or set node Y value, expressed in network editor units, measured from its bottom edge.

**nodeCenterX** → int: Get or set node X value, expressed in network editor units, measured from its center.

**nodeCenterY** → int: Get or set node Y value, expressed in network editor units, measured from its center.

**dock** → [CLASS_OP]: Get or set the operator this operator is docked to. To clear docking, set this member to None.

**docked** → list (Read Only): The (possibly empty) list of operators docked to this node.

#### Connection

**inputs** → list (Read Only): List of input operators (via left side connectors) to this operator. To get the number of inputs, use len(OP.inputs).

**outputs** → list (Read Only): List of output operators (via right side connectors) from this operator.

**inputConnectors** → list (Read Only): List of input connectors (on the left side) associated with this operator.

**outputConnectors** → list (Read Only): List of output connectors (on the right side) associated with this operator.

#### Cook Information

**cookFrame** → float (Read Only): Last frame at which this operator cooked.

**cookTime** → float (Read Only): Deprecated Duration of the last measured cook (in milliseconds).

**cpuCookTime** → float (Read Only): Duration of the last measured cook in CPU time (in milliseconds).

**cookAbsFrame** → float (Read Only): Last absolute frame at which this operator cooked.

**cookStartTime** → float (Read Only): Last offset from frame start at which this operator cook began, expressed in milliseconds.

**cookEndTime** → float (Read Only): Last offset from frame start at which this operator cook ended, expressed in milliseconds. Other operators may have cooked between the start and end time. See the cookTime member for this operator's specific cook duration.

**cookedThisFrame** → bool (Read Only): True when this operator has cooked this frame.

**cookedPreviousFrame** → bool (Read Only): True when this operator has cooked the previous frame.

**childrenCookTime** → float (Read Only): Deprecated The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenCPUCookTime** → float (Read Only): The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenCookAbsFrame** → float (Read Only): Deprecated The absolute frame on which childrenCookTime is based.

**childrenCPUCookAbsFrame** → float (Read Only): The absolute frame on which childrenCPUCookTime is based.

**gpuCookTime** → float (Read Only): Duration of GPU operations during the last measured cook (in milliseconds).

**childrenGPUCookTime** → float (Read Only): The total accumulated GPU cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

**childrenGPUCookAbsFrame** → float (Read Only): The absolute frame on which childrenGPUCookTime is based.

**totalCooks** → int (Read Only): Number of times the operator has cooked.

**cpuMemory** → int (Read Only): The approximate amount of CPU memory this Operator is using, in bytes.

**gpuMemory** → int (Read Only): The amount of GPU memory this OP is using, in bytes.

#### Type

**type** → str (Read Only): Operator type as a string. Example: 'oscin'.

**subType** → str (Read Only): Operator subtype. Currently only implemented for components. May be one of: 'panel', 'object', or empty string in the case of base components.

**OPType** → str (Read Only): Python operator class type, as a string. Example: 'oscinCHOP'. Can be used with COMP.create() method.

**label** → str (Read Only): Operator type label. Example: 'OSC In'.

**icon** → str (Read Only): Get the letters used to create the operator's icon.

**family** → str (Read Only): Operator family. Example: CHOP. Use the global dictionary families for a list of each operator type.

**isFilter** → bool (Read Only): True if operator is a filter, false if it is a generator.

**minInputs** → int (Read Only): Minimum number of inputs to the operator.

**maxInputs** → int (Read Only): Maximum number of inputs to the operator.

**isMultiInputs** → bool (Read Only): True if inputs are ordered, false otherwise. Operators with an arbitrary number of inputs have unordered inputs, example Merge CHOP.

**visibleLevel** → int (Read Only): Visibility level of the operator. For example, expert operators have visibility level 1, regular operators have visibility level 0.

**isBase** → bool (Read Only): True if the operator is a Base (miscellaneous) component.

**isCHOP** → bool (Read Only): True if the operator is a CHOP.

**isCOMP** → bool (Read Only): True if the operator is a component.

**isDAT** → bool (Read Only): True if the operator is a DAT.

**isMAT** → bool (Read Only): True if the operator is a Material.

**isObject** → bool (Read Only): True if the operator is an object.

**isPanel** → bool (Read Only): True if the operator is a Panel.

**isSOP** → bool (Read Only): True if the operator is a SOP.

**isTOP** → bool (Read Only): True if the operators is a TOP.

**licenseType** → str (Read Only): Type of License required for the operator.

### Methods

#### General

**NOTE**: create(), copy() and copyOPs() is done by the parent operator (a component). For more information see [CLASS_COMP].create, [CLASS_COMP].copy and [CLASS_COMP].copyOPs methods.

**pars(pattern)→ list**: Returns a (possibly empty) list of parameter objects that match the pattern.

**cook(force=False, recurse=False, includeUtility=False)→ None**: Cook the contents of the operator if required.

**copyParameters(OP, custom=True, builtin=True)→ None**: Copy all of the parameters from the specified operator. Both operators should be the same type.

**changeType(OPtype)→ OP**: Change referenced operator to a new operator type. After this call, this OP object should no longer be referenced. Instead use the returned OP object.

**dependenciesTo(OP)→ list**: Returns a (possibly empty) list of operator dependency paths between this operator and the specified operator. Multiple paths may be found.

**evalExpression(str)→ value**: Evaluate the expression from the context of this OP. Can be used to evaluate arbitrary snippets of code from arbitrary locations.

**destroy()→ None**: Destroy the operator referenced by this OP. An exception will be raised if the OP's operator has already been destroyed.

**var(name, search=True)→ str**: Evaluate avariable. This will return the empty string, if not found. Most information obtained from variables (except for Root and Component variables) are accessible through other means in Python, usually in the global td module.

**openMenu(x=None, y=None)→ None**: Open a node menu for the operator at x, y. Opens at mouse if x & y are not specified.

**relativePath(OP)→ str**: Returns the relative path from this operator to the OP that is passed as the argument. See [CLASS_OP].shortcutPath for a version using expressions.

**setInputs(listOfOPs)→ None**: Set all the operator inputs to the specified list.

**shortcutPath(OP, toParName=None)→ str**: Returns an expression from this operator to the OP that is passed as the argument. See [CLASS_OP].relativePath for a version using relative path constants.

**ops(pattern1, pattern2.., includeUtility=False)→ list of OPs**: Returns a (possibly empty) list of OPs that match the patterns, relative to the inside of this OP.

**resetPars(parNames='*', parGroupNames='*', pageNames='*', includeBuiltin=True, includeCustom=True)→ bool**: Resets the specified parameters in the operator.

#### Errors

**addScriptError(msg)→ None**: Adds a script error to a node.

**addError(msg)→ None**: Adds an error to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

**addWarning(msg)→ None**: Adds a warning to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

**errors(recurse=False)→ str**: Get error messages associated with this OP.

**warnings(recurse=False)→ str**: Get warning messages associated with this OP.

**scriptErrors(recurse=False)→ str**: Get script error messages associated with this OP.

**clearScriptErrors(recurse=False, error='*')→ None**: Clear any errors generated during script execution. These may be generated during execution of DATs, Script Nodes, Replicator COMP callbacks, etc.

**childrenCPUMemory()→ int**: Returns the total CPU memory usage for all the children from this COMP.

**childrenGPUMemory()→ int**: Returns the total GPU memory usage for all the children from this COMP.

#### Appearance

**resetNodeSize()→ None**: Reset the node tile size to its default width and height.

#### Viewers

**closeViewer(topMost=False)→ None**: Close the floating content viewers of the OP.

**openViewer(unique=False, borders=True)→ None**: Open a floating content viewer for the OP.

**resetViewer(recurse=False)→ None**: Reset the OP content viewer to default view settings.

**openParameters()→ None**: Open a floating dialog containing the operator parameters.

#### Storage

Storage can be used to keep data within components. Storage is implemented as one python dictionary per node.

When an element of storage is changed by using n.store() as explained below, expressions and operators that depend on it will automatically re-cook. It is retrieved with the n.fetch() function.

Storage is saved in .toe and .tox files and restored on startup.

Storage can hold any python object type (not just strings as in Tscript variables). Storage elements can also have optional startup values, specified separately. Use these startup values for example, to avoid saving and loading some session specific object, and instead save or load a well defined object like None.

See the Examine DAT for procedurally viewing the contents of storage.

**fetch(key, default, search=True, storeDefault=False)→ value**: Return an object from the OP storage dictionary. If the item is not found, and a default it supplied, it will be returned instead.

**fetchOwner(key)→ OP**: Return the operator which contains the stored key, or None if not found.

**store(key, value)→ value**: Add the key/value pair to the OP's storage dictionary, or replace it if it already exists. If this value is not intended to be saved and loaded in the toe file, it can be be given an alternate value for saving and loading, by using the method storeStartupValue described below.

**unstore(keys1, keys2..)→ None**: For key, remove it from the OP's storage dictionary. Pattern Matching is supported as well.

**storeStartupValue(key, value)→ None**: Add the key/value pair to the OP's storage startup dictionary. The storage element will take on this value when the file starts up.

**unstoreStartupValue(keys1, keys2..)→ None**: For key, remove it from the OP's storage startup dictionary. Pattern Matching is supported as well. This does not affect the stored value, just its startup value.

#### Miscellaneous

****getstate**()→ dict**: Returns a dictionary with persistent data about the object suitable for pickling and deep copies.

****setstate**()→ dict**: Reads the dictionary to update persistent details about the object, suitable for unpickling and deep copies.
