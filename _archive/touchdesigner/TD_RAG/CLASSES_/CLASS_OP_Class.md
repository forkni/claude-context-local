---
title: "OP Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "intermediate_user", "automation_specialist", "visual_programmer"]
completion_signals: ["can_access_op_properties", "understands_operator_management", "can_implement_procedural_scripting", "manages_network_hierarchy"]

operators:
- Replicator_COMP
- Examine_DAT
- OP_Find_DAT
- Merge_CHOP
- nullCHOP
- tcpipDAT
concepts:
- operator_referencing
- parameter_management
- network_hierarchy
- operator_state
- data_persistence
- procedural_scripting
- error_handling
- cook_management
prerequisites:
- Python_fundamentals
- operator_basics
workflows:
- procedural_network_building
- scripted_automation
- component_scripting
- dynamic_parameter_control
- state_management
- error_handling
keywords:
- op
- node
- operator
- path
- name
- id
- flag
- bypass
- lock
- cook
- parameter
- storage
- fetch
- store
- parent
- children
- input
- output
- find
- ops
tags:
- python
- api
- base_class
- node
- scripting
- core
relationships:
  CLASS_Par_Class: strong
  CLASS_Page_Class: strong
  MODULE_td_Module: strong
related_docs:
- CLASS_Par_Class
- CLASS_Page_Class
- MODULE_td_Module
# Enhanced search optimization
search_optimization:
  primary_keywords: ["op", "operator", "node", "class"]
  semantic_clusters: ["api_programming", "object_management", "network_hierarchy"]
  user_intent_mapping:
    beginner: ["what is op class", "basic operator reference", "how to access nodes"]
    intermediate: ["operator methods", "parameter management", "network traversal"]
    advanced: ["procedural scripting", "dynamic operator control", "advanced node manipulation"]

hierarchy:
  secondary: fundamentals
  tertiary: operator
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- procedural_network_building
- scripted_automation
- component_scripting
- dynamic_parameter_control
---

# OP Class

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: procedural_network_building, scripted_automation, component_scripting

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Operator Basics]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Par Class] → [CLASS Page Class] → [MODULE td Module]

**Related Topics**: procedural network building, scripted automation, component scripting

<!-- TD-META
category: CLASS
document_type: reference
operators: [Replicator_COMP, Examine_DAT, OP_Find_DAT, Merge_CHOP, nullCHOP, tcpipDAT]
concepts: [operator_referencing, parameter_management, network_hierarchy, operator_state, data_persistence, procedural_scripting, error_handling, cook_management]
prerequisites: [Python_fundamentals, operator_basics]
workflows: [procedural_network_building, scripted_automation, component_scripting, dynamic_parameter_control, state_management, error_handling]
related: [CLASS_Par_Class, CLASS_Page_Class, MODULE_td_Module]
relationships: {
  "CLASS_Par_Class": "strong",
  "CLASS_Page_Class": "strong",
  "MODULE_td_Module": "strong"
}
hierarchy:
  "primary": "scripting"
  "secondary": "fundamentals"
  "tertiary": "operator"
keywords: [op, node, operator, path, name, id, flag, bypass, lock, cook, parameter, storage, fetch, store, parent, children, input, output, find, ops]
tags: [python, api, base_class, node, scripting, core]
TD-META -->

The OP class defines a reference to a single operator.

## Content

- [1. Members](#members)
  - [1.1 General](#general)
  - [1.2 Common Flags](#common-flags)
  - [1.3 Appearance](#appearance)
  - [1.4 Connection](#connection)
  - [1.5 Cook Information](#cook-information)
  - [1.6 Type](#type)
- [2. Methods](#methods)
  - [2.1 General](#general-1)
  - [2.2 Errors](#errors)
  - [2.3 Appearance](#appearance-1)
  - [2.4 Viewers](#viewers)
  - [2.5 Storage](#storage)
  - [2.6 Miscellaneous](#miscellaneous)

## Members

### General

valid → bool (Read Only):

True if the referenced operator currently exists, False if it has been deleted.

id → int (Read Only):

Unique id for the operator. This id can also be passed to the op() and ops() methods. Id's are not consistent when a file is re-opened, and will change if the OP is copied/pasted, changes OP types, deleted/undone. The id will not change if the OP is renamed though. Its data type is integer.

name → str :

Get or set the operator name.

path → str (Read Only):

Full path to the operator.

digits → int (Read Only):

Returns the numeric value of the last consecutive group of digits in the name, or None if not found. The digits can be in the middle of the name if there are none at the end of the name.

base → str (Read Only):

Returns the beginning portion of the name occurring before any digits.

passive → bool (Read Only):

If true, operator will not cook before its access methods are called. To use a passive version of an operator n, use passive(n).

curPar → td.Par (Read Only):

The parameter currently being evaluated. Can be used in a parameter expression to reference itself. An easy way to see this is to put the expression curPar.name in any string parameter.

curBlock → (Read Only):

The SequenceBlock of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

curSeq → Sequence (Read Only):

The Sequence of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

time → OP (Read Only):

Time Component that defines the operator's time reference.

ext → class (Read Only):

The object to search for parent extensions.

me.ext.MyClass
fileFolder → str (Read Only):

Returns the folder where this node is saved.

filePath → str (Read Only):

Returns the file location of this node.

mod → mod (Read Only):

Get a module on demand object that searches for DAT modules relative to this operator.

pages → list (Read Only):

A list of all built-in pages.

parGroup → tuple (Read Only):

An intermediate parameter collection object, from which a specific parameter group can be found.

n.parGroup.t

# or

n.parGroup['t']
par → td.Par (Read Only):

An intermediate parameter collection object, from which a specific parameter can be found.

n.par.tx

# or

n.par['tx']
builtinPars → list or par (Read Only):

A list of all built-in parameters.

customParGroups → list of parGroups (Read Only):

A list of all ParGroups, where a ParGroup is a set of parameters all drawn on the same line of a dialog, sharing the same label.

customPars → list of par (Read Only):

A list of all custom parameters.

customPages → list (Read Only):

A list of all custom pages.

replicator → OP or None (Read Only):

The replicatorCOMP that created this operator, if any.

storage → dict (Read Only):

Storage is dictionary associated with this operator. Values stored in this dictionary are persistent, and saved with the operator. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with methods such as OP.fetch() or OP.store() described below, or examined with an Examine DAT.

tags → list :

Get or set a set of user defined strings. Tags can be searched using OP.findChildren() and the OP Find DAT.

The set is a regular python set, and can be accessed accordingly:

n.tags = ['effect', 'image filter']
n.tags.add('darken')
children → list (Read Only):

A list of operators contained within this operator. Only component operators have children, otherwise an empty list is returned.

numChildren → int (Read Only):

Returns the number of children contained within the operator. Only component operators have children.

numChildrenRecursive → int (Read Only):

Returns the number of operators contained recursively within this operator. Only component operators have children.

op → OP or None (Read Only):

The operator finder object, for accessing operators through paths or shortcuts. Note: a version of this method that searches relative to '/' is also in the global td module.

op(pattern1, pattern2..., includeUtility=False) → OP or None

Returns the first OP whose path matches the given pattern, relative to the inside of this operator. Will return None if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.

pattern - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
includeUtility (Optional) - if True, allow Utility nodes to be returned. If False, Utility nodes will be ignored.
b = op('project1')
b = op('foot*', 'hand*') #comma separated
b = op('foot*hand*')  #space separated
b = op(154)
op.shortcut → OP

An operator specified with by a Global OP Shortcut. If no operator exists an exception is raised. These shortcuts are global, and must be unique. That is, cutting and pasting an operator with a Global OP Shortcut specified will lead to a name conflict. One shortcut must be renamed in that case. Furthermore, only components can be given Global OP Shortcuts.
shortcut - Corresponds to the Global OP Shortcut parameter specified in the target operator.
b = op.Videoplayer
To list all Global OP Shortcuts:

for x in op:
 print(x)
opex → OP (Read Only):

An operator finder object, for accessing operators through paths or shortcuts. Works like the op() shortcut method, except it will raise an exception if it fails to find the node instead of returning None as op() does. This is now the recommended way to get nodes in parameter expressions, as the error will be more useful than, for example, NoneType has no attribute "par", that is often seen when using op(). Note: a version of this method that searches relative to '/' is also in the global td module.

op(pattern1, pattern2..., includeUtility=False) → OP

Returns the first OP whose path matches the given pattern, relative to the inside of this operator. Will return None if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.

pattern - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
includeUtility (Optional) - if True, allow Utility nodes to be returned. If False, Utility operators will be ignored.
parent → Shortcut (Read Only):

The Parent Shortcut object, for accessing parent components through indices or shortcuts.

Note: a version of this method that searches relative to the current operator is also in the global td module.

parent(n) → OP or None

The nth parent of this operator. If n not specified, returns the parent. If n = 2, returns the parent of the parent, etc. If no parent exists at that level, None is returned.

n - (Optional) n is the number of levels up to climb. When n = 1 it will return the operator's parent.
p = parent(2) #grandfather
parent.shortcut → OP

A parent component specified with a shortcut. If no parent exists an exception is raised.

shortcut - Corresponds to the Parent Shortcut parameter specified in the target parent.
n = parent.Videoplayer
See also Parent Shortcut for more examples.

iop → OP (Read Only):

The Internal Operator Shortcut object, for accessing internal shortcuts. See also Internal Operators. Note: a version of this method that searches relative to the current operator is also in the global td Module.

ipar → ParCollection (Read Only):

The Internal Operator Parameter Shortcut object, for accessing internal shortcuts. See also Internal Parameters. Note: a version of this method that searches relative to the current operator is also in the global td Module.

currentPage → Page :

Get or set the currently displayed parameter page. It can be set by setting it to another page or a string label.

n.currentPage = 'Common'

### Common Flags

The following methods get or set specific operator Flags. Note specific operators may contain other flags not in this section.

activeViewer → bool :

Get or set Viewer Active Flag.

allowCooking → bool :

Get or set Cooking Flag. Only COMPs can disable this flag.

bypass → bool :

Get or set Bypass Flag.

cloneImmune → bool :

Get or set Clone Immune Flag.

current → bool :

Get or set Current Flag.

display → bool :

Get or set Display Flag.

expose → bool :

Get or set the Expose Flag which hides a node from view in a network.

lock → bool :

Get or set Lock Flag.

selected → bool :

Get or set Selected Flag. This controls if the node is part of the network selection. (yellow box around it).

seq → (Read Only):

An intermediate sequence collection object, from which a specific sequence group can be found.

n.seq.Color #raises Exception if not found.

# or

n.seq['Color'] #returns None if not found.
python → bool :

Get or set parameter expression language as python.

render → bool :

Get or set Render Flag.

showCustomOnly → bool :

Get or set the Show Custom Only Flag which controls whether or not non custom parameters are display in parameter dialogs.

showDocked → bool :

Get or set Show Docked Flag. This controls whether this node is visible or hidden when it is docked to another node.

viewer → bool :

Get or set Viewer Flag.

### Appearance

color → tuple(r, g, b) :

Get or set color value, expressed as a 3-tuple, representing its red, green, blue values. To convert between color spaces, use the built in colorsys module.

comment → str :

Get or set comment string.

nodeHeight → int :

Get or set node height, expressed in network editor units.

nodeWidth → int :

Get or set node width, expressed in network editor units.

nodeX → int :

Get or set node X value, expressed in network editor units, measured from its left edge.

nodeY → int :

Get or set node Y value, expressed in network editor units, measured from its bottom edge.

nodeCenterX → int :

Get or set node X value, expressed in network editor units, measured from its center.

nodeCenterY → int :

Get or set node Y value, expressed in network editor units, measured from its center.

dock → OP :

Get or set the operator this operator is docked to. To clear docking, set this member to None.

docked → list (Read Only):

The (possibly empty) list of operators docked to this node.

### Connection

# See also

the OP.parent methods.
To connect components together see COMP_Class#Connection section.-->

inputs → list (Read Only):

List of input operators (via left side connectors) to this operator. To get the number of inputs, use len(OP.inputs).

outputs → list (Read Only):

List of output operators (via right side connectors) from this operator.

inputConnectors → list (Read Only):

List of input connectors (on the left side) associated with this operator.

outputConnectors → list (Read Only):

List of output connectors (on the right side) associated with this operator.

### Cook Information

cookFrame → float (Read Only):

Last frame at which this operator cooked.

cookTime → float (Read Only):

Deprecated Duration of the last measured cook (in milliseconds).

cpuCookTime → float (Read Only):

Duration of the last measured cook in CPU time (in milliseconds).

cookAbsFrame → float (Read Only):

Last absolute frame at which this operator cooked.

cookStartTime → float (Read Only):

Last offset from frame start at which this operator cook began, expressed in milliseconds.

cookEndTime → float (Read Only):

Last offset from frame start at which this operator cook ended, expressed in milliseconds. Other operators may have cooked between the start and end time. See the cookTime member for this operator's specific cook duration.

cookedThisFrame → bool (Read Only):

True when this operator has cooked this frame.

cookedPreviousFrame → bool (Read Only):

True when this operator has cooked the previous frame.

childrenCookTime → float (Read Only):

Deprecated The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

childrenCPUCookTime → float (Read Only):

The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

childrenCookAbsFrame → float (Read Only):

Deprecated The absolute frame on which childrenCookTime is based.

childrenCPUCookAbsFrame → float (Read Only):

The absolute frame on which childrenCPUCookTime is based.

gpuCookTime → float (Read Only):

Duration of GPU operations during the last measured cook (in milliseconds).

childrenGPUCookTime → float (Read Only):

The total accumulated GPU cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

childrenGPUCookAbsFrame → float (Read Only):

The absolute frame on which childrenGPUCookTime is based.

totalCooks → int (Read Only):

Number of times the operator has cooked.

cpuMemory → int (Read Only):

The approximate amount of CPU memory this Operator is using, in bytes.

gpuMemory → int (Read Only):

The amount of GPU memory this OP is using, in bytes.

### Type

type → str (Read Only):

Operator type as a string. Example: 'oscin'.

subType → str (Read Only):

Operator subtype. Currently only implemented for components. May be one of: 'panel', 'object', or empty string in the case of base components.

OPType → str (Read Only):

Python operator class type, as a string. Example: 'oscinCHOP'. Can be used with COMP.create() method.

label → str (Read Only):

Operator type label. Example: 'OSC In'.

icon → str (Read Only):

Get the letters used to create the operator's icon.

family → str (Read Only):

Operator family. Example: CHOP. Use the global dictionary families for a list of each operator type.

isFilter → bool (Read Only):

True if operator is a filter, false if it is a generator.

minInputs → int (Read Only):

Minimum number of inputs to the operator.

maxInputs → int (Read Only):

Maximum number of inputs to the operator.

isMultiInputs → bool (Read Only):

True if inputs are ordered, false otherwise. Operators with an arbitrary number of inputs have unordered inputs, example Merge CHOP.

visibleLevel → int (Read Only):

Visibility level of the operator. For example, expert operators have visibility level 1, regular operators have visibility level 0.

isBase → bool (Read Only):

True if the operator is a Base (miscellaneous) component.

isCHOP → bool (Read Only):

True if the operator is a CHOP.

isCOMP → bool (Read Only):

True if the operator is a component.

isDAT → bool (Read Only):

True if the operator is a DAT.

isMAT → bool (Read Only):

True if the operator is a Material.

isObject → bool (Read Only):

True if the operator is an object.

isPanel → bool (Read Only):

True if the operator is a Panel.

isSOP → bool (Read Only):

True if the operator is a SOP.

isTOP → bool (Read Only):

True if the operators is a TOP.

licenseType → str (Read Only):

Type of License required for the operator.

#### Methods

##### General

NOTE: create(), copy() and copyOPs() is done by the parent operator (a component). For more information see COMP.create, COMP.copy and COMP.copyOPs methods.

pars(pattern)→ list:

Returns a (possibly empty) list of parameter objects that match the pattern.

pattern - Is a string following the Pattern Matching rules, specifying which parameters to return.
newlist = op('geo1').pars('t?', 'r?', 's?') #translate/rotate/scale parameters
Note: If searching for a single parameter given a name, it's much more efficient to use the subscript operator. For example:

name = 'MyName1'
op('geo1').par[name]
cook(force=False, recurse=False, includeUtility=False)→ None:

Cook the contents of the operator if required.

force - (Keyword, Optional) If True, the operator will always cook, even if it wouldn't under normal circumstances.
recurse - (Keyword, Optional) If True, all children and sub-children of the operator will be cooked.
includeUtility - (Keyword, Optional) If specified, controls whether or not utility components (eg Comments) are included in the results.
copyParameters(OP, custom=True, builtin=True)→ None:

Copy all of the parameters from the specified operator. Both operators should be the same type.

OP - The operator to copy.
custom - (Keyword, Optional) When True, custom parameters will be copied.
builtin - (Keyword, Optional) When True, built in parameters will be copied.
op('geo1').copyParameters( op('geo2') )
changeType(OPtype)→ OP:

Change referenced operator to a new operator type. After this call, this OP object should no longer be referenced. Instead use the returned OP object.

OPtype - The python class name of the operator type you want to change this operator to. This is not a string, but instead is a class defined in the global td module.
n = op('wave1').changeType(nullCHOP) #changes 'wave1' into a Null CHOP
n = op('text1').changeType(tcpipDAT) #changes 'text1' operator into a TCPIP DAT
dependenciesTo(OP)→ list:

Returns a (possibly empty) list of operator dependency paths between this operator and the specified operator. Multiple paths may be found.

evalExpression(str)→ value:

Evaluate the expression from the context of this OP. Can be used to evaluate arbitrary snippets of code from arbitrary locations.

str - The expression to evaluate.
op('wave1').evalExpression('me.digits')  #returns 1
If the expression already resides in a parameter, use that parameters evalExpression() method instead.

destroy()→ None:

Destroy the operator referenced by this OP. An exception will be raised if the OP's operator has already been destroyed.

var(name, search=True)→ str:

Evaluate a variable. This will return the empty string, if not found. Most information obtained from variables (except for Root and Component variables) are accessible through other means in Python, usually in the global td module.

name - The variable name to search for.
search - (Keyword, Optional) If set to True (which is default) the operator hierarchy is searched until a variable matching that name is found. If false, the search is constrained to the operator.
openMenu(x=None, y=None)→ None:

Open a node menu for the operator at x, y. Opens at mouse if x & y are not specified.

x - (Keyword, Optional) The X coordinate of the menu, measured in screen pixels.
y - (Keyword, Optional) The Y coordinate of the menu, measured in screen pixels.
relativePath(OP)→ str:

Returns the relative path from this operator to the OP that is passed as the argument. See OP.shortcutPath for a version using expressions.

setInputs(listOfOPs)→ None:

Set all the operator inputs to the specified list.

listOfOPs - A list containing one or more OPs. Entries in the list can be None to disconnect specific inputs. An empty list disconnects all inputs.
shortcutPath(OP, toParName=None)→ str:

Returns an expression from this operator to the OP that is passed as the argument. See OP.relativePath for a version using relative path constants.

toParName - (Keyword, Optional) Return an expression to this parameter instead of its operator.
ops(pattern1, pattern2.., includeUtility=False)→ list of OPs:

Returns a (possibly empty) list of OPs that match the patterns, relative to the inside of this OP.

Multiple patterns may be provided. Numeric OP ids may also be used.

pattern - Can be string following the Pattern Matching rules, specifying which OPs to return, or an integer, which must be an OP Id. Multiple patterns can be given and all matched OPs will be returned.
includeUtility - (Keyword, Optional) If specified, controls whether or not utility components (eg Comments) are included in the results.
Note: a version of this method that searches relative to '/' is also in the global td module.

newlist = n.ops('arm*', 'leg*', 'leg5/foot*')
resetPars(parNames='*', parGroupNames='*', pageNames='*', includeBuiltin=True, includeCustom=True)→ bool:

Resets the specified parameters in the operator.

Returns true if anything was changed.

parNames (Keyword, Optional) - Specify parameters by Par name.
parGroupNames (Keyword, Optional) - Specify parameters by ParGroup name.
pageNames (Keyword, Optional) - Specify parameters by page name.
includeBuiltin (Keyword, Optional) - Include builtin parameters.
includeCustom (Keyword, Optional) - Include custom parameters.
op('player').resetPars(includeBuiltin=False) # only reset custom

#### Errors

addScriptError(msg)→ None:

Adds a script error to a node.

msg - The error to add.
addError(msg)→ None:

Adds an error to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

msg - The error to add.
addWarning(msg)→ None:

Adds a warning to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).

msg - The error to add.
errors(recurse=False)→ str:

Get error messages associated with this OP.

recurse - Get errors in any children or subchildren as well.
warnings(recurse=False)→ str:

Get warning messages associated with this OP.

recurse - Get warnings in any children or subchildren as well.
scriptErrors(recurse=False)→ str:

Get script error messages associated with this OP.

recurse - Get errors in any children or subchildren as well.
clearScriptErrors(recurse=False, error='*')→ None:

Clear any errors generated during script execution. These may be generated during execution of DATs, Script Nodes, Replicator COMP callbacks, etc.

recurse - Clear script errors in any children or subchildren as well.
error - Pattern to match when clearing errors
op('/project1').clearScriptErrors(recurse=True)
childrenCPUMemory()→ int:

Returns the total CPU memory usage for all the children from this COMP.

childrenGPUMemory()→ int:

Returns the total GPU memory usage for all the children from this COMP.

#### Appearance

resetNodeSize()→ None:

Reset the node tile size to its default width and height.

#### Viewers

closeViewer(topMost=False)→ None:

Close the floating content viewers of the OP.

topMost - (Keyword, Optional) If True, any viewer window containing any parent of this OP is closed instead.
op('wave1').closeViewer()
op('wave1').closeViewer(topMost=True) # any viewer that contains 'wave1' will be closed.
openViewer(unique=False, borders=True)→ None:

Open a floating content viewer for the OP.

unique - (Keyword, Optional) If False, any existing viewer for this OP will be re-used and popped to the foreground. If unique is True, a new window is created each time instead.
borders - (Keyword, Optional) If true, the floating window containing the viewer will have borders.
op('geo1').openViewer(unique=True, borders=False) # opens a new borderless viewer window for 'geo1'
resetViewer(recurse=False)→ None:

Reset the OP content viewer to default view settings.

recurse - (Keyword, Optional) If True, this is done for all children and sub-children as well.
op('/').resetViewer(recurse=True) # reset the viewer for all operators in the entire file.
openParameters()→ None:

Open a floating dialog containing the operator parameters.

#### Storage

Storage can be used to keep data within components. Storage is implemented as one python dictionary per node.

When an element of storage is changed by using n.store() as explained below, expressions and operators that depend on it will automatically re-cook. It is retrieved with the n.fetch() function.

Storage is saved in .toe and .tox files and restored on startup.

Storage can hold any python object type (not just strings as in Tscript variables). Storage elements can also have optional startup values, specified separately. Use these startup values for example, to avoid saving and loading some session specific object, and instead save or load a well defined object like None.

See the Examine DAT for procedurally viewing the contents of storage.

fetch(key, default, search=True, storeDefault=False)→ value:

Return an object from the OP storage dictionary. If the item is not found, and a default it supplied, it will be returned instead.

key - The name of the entry to retrieve.
default - (Optional) If provided and no item is found then the passed value/object is returned instead.
storeDefault - (Keyword, Optional) If True, and the key is not found, the default is stored as well.
search - (Keyword, Optional) If True, the parent of each OP is searched recursively until a match is found
v = n.fetch('sales5', 0.0)
fetchOwner(key)→ OP:

Return the operator which contains the stored key, or None if not found.

key - The key to the stored entry you are looking for.
who = n.fetchOwner('sales5') #find the OP that has a storage entry called 'sales5'
store(key, value)→ value:

Add the key/value pair to the OP's storage dictionary, or replace it if it already exists. If this value is not intended to be saved and loaded in the toe file, it can be be given an alternate value for saving and loading, by using the method storeStartupValue described below.

key - A string name for the storage entry. Use this name to retrieve the value using fetch().
value - The value/object to store.
n.store('sales5', 34.5) # stores a floating point value 34.5.
n.store('moviebank', op('/project1/movies')) # stores an OP for easy access later on.
unstore(keys1, keys2..)→ None:

For key, remove it from the OP's storage dictionary. Pattern Matching is supported as well.

keys - The name or pattern defining which key/value pairs to remove from the storage dictionary.
n.unstore('sales*') # removes all entries from this OPs storage that start with 'sales'
storeStartupValue(key, value)→ None:

Add the key/value pair to the OP's storage startup dictionary. The storage element will take on this value when the file starts up.

key - A string name for the storage startup entry.
value - The startup value/object to store.
n.storeStartupValue('sales5', 1) # 'sales5' will have a value of 1 when the file starts up.
unstoreStartupValue(keys1, keys2..)→ None:

For key, remove it from the OP's storage startup dictionary. Pattern Matching is supported as well. This does not affect the stored value, just its startup value.

keys - The name or pattern defining which key/value pairs to remove from the storage startup dictionary.
n.unstoreStartupValue('sales*') # removes all entries from this OPs storage startup that start with 'sales'

#### Miscellaneous

**getstate**()→ dict:

Returns a dictionary with persistent data about the object suitable for pickling and deep copies.

**setstate**()→ dict:

Reads the dictionary to update persistent details about the object, suitable for unpickling and deep copies.
