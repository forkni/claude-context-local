---
title: "COMP Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 25-30 minutes
user_personas: ["script_developer", "component_builder", "system_architect"]
operators: ["baseCOMP", "containerCOMP", "geoCOMP"]
concepts: ["component", "hierarchy", "encapsulation", "cloning", "privacy"]
prerequisites: ["Python_fundamentals", "operator_basics", "CLASS_OP_Class"]
workflows: ["building_reusable_components", "system_architecture", "ui_design"]
keywords: ["comp", "component", "operator", "scripting", "privacy", "clone"]
tags: ["python", "api", "core", "comp"]
related_docs:
- CLASS_OP_Class
- CLASS_Page
- MODULE_td
---

# COMP Class

## Content

- [Introduction](#introduction)
- [COMP Class Members](#comp-class-members)
  - [Privacy](#privacy)
  - [Connection](#connection)
- [COMP Class Methods](#comp-class-methods)
  - [Custom Parameters](#custom-parameters)
  - [Privacy](#privacy-1)
  - [Component Variables](#component-variables)
- [OP Class](#op-class)
  - [Members](#members)
    - [General](#general)
    - [Common Flags](#common-flags)
    - [Appearance](#appearance)
    - [Connection](#connection-1)
    - [Cook Information](#cook-information)
    - [Type](#type)
  - [Methods](#methods)
    - [General](#general-1)
    - [Errors](#errors)
    - [Appearance](#appearance-1)
    - [Viewers](#viewers)
    - [Storage](#storage)
    - [Miscellaneous](#miscellaneous)

## Introduction

A COMP describes a reference to a Component operator.

## COMP Class Members

### extensions

`extensions` → `List` (Read Only):

> A list of extensions attached to this component.

### extensionsReady

`extensionsReady` → `Bool` (Read Only):

> True unless the extensions are currently compiling. Can be used to avoid accessing promoted members prematurely during an extension initialization function.

### internalOPs

`internalOPs` → `Dict` (Read Only):

> A dictionary of internal operator shortcuts found in this component. See also `OP.iop`

### internalPars

`internalPars` → `Dict` (Read Only):

> A dictionary of internal parameters shortcuts found in this component. See also `OP.ipar`

### clones

`clones` → `List` (Read Only):

> A list of all components cloned to this component.

### componentCloneImmune

`componentCloneImmune` → `Bool`:

> Get or set component clone Immune flag. This works together with the `cloneImmune` member of the `OP_Class`. When `componentCloneImmune` is True, everything inside the clone is immune. When `componentCloneImmune` is False, it uses the `OP_Class` `cloneImmune` member to determine if just the component is immune (its parameters etc, but not the component's network inside).

### vfs

`vfs` → `VFS` (Read Only):

> An intermediate VFS object from which embedded `VFSFile` objects can be accessed. For more information see `Virtual File System`.

### dirty

`dirty` → `Bool` (Read Only):

> True if the contents of the component need to be saved.

### currentChild

`currentChild` → `OP` (Read Only):

> The child operator that is currently selected. To make an operator current, use its own `OP.current` method.

### selectedChildren

`selectedChildren` → `List` (Read Only):

> The list of currently selected children. To change an individual operator's selection state, use its own `OP.selected` method.

### cpuCookTime

`cpuCookTime` → `float` (Read Only):

> Duration of the last measured cook in CPU time (in milliseconds).

### childrenCPUCookTime

`childrenCPUCookTime` → `float` (Read Only):

> The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

### childrenCPUCookAbsFrame

`childrenCPUCookAbsFrame` → `int` (Read Only):

> The absolute frame on which `childrenCookTime` is based.

### gpuMemory

`gpuMemory` → `int` (Read Only):

> The amount of GPU memory this OP is using, in bytes.

### pickable

`pickable` → `Bool`:

> Get or set pickable flag.

### utility

`utility` → `Bool`:

> Get or set utility flag.

### isCOMP

`isCOMP` → `Bool` (Read Only):

> True if the operator is a component.

### Privacy

#### isPrivate

`isPrivate` → `Bool` (Read Only):

> True if the the component contents cannot be directly viewed.

#### isPrivacyActive

`isPrivacyActive` → `Bool` (Read Only):

> True if the component is private, and privacy is active. When inactive the contents can be temporarily viewed.

#### isPrivacyLicensed

`isPrivacyLicensed` → `Bool` (Read Only):

> True if the component is private and if the required CodeMeter license is present to run it.

#### privacyFirmCode

`privacyFirmCode` → `int` (Read Only):

> The CodeMeter firm code needed to use this private component. 0 if this component is not private using a CodeMeter dongle.

#### privacyProductCode

`privacyProductCode` → `int` (Read Only):

> The CodeMeter product code needed to use this private component. 0 if this component is not private using a CodeMeter dongle.

#### privacyDeveloperName

`privacyDeveloperName` → `string` (Read Only):

> The name of the developer of this private component.

#### privacyDeveloperEmail

`privacyDeveloperEmail` → `string` (Read Only):

> The email of the developer of this private component.

### Connection

#### inputCOMPs

`inputCOMPs` → `List` (Read Only):

> List of input components to this component through its top connector.

#### inputCOMPConnectors

`inputCOMPConnectors` → `List` (Read Only):

> List of input connectors (on the top) associated with this component.

#### outputCOMPs

`outputCOMPs` → `List` (Read Only):

> List of output components from this component through its bottom connector.

#### outputCOMPConnectors

`outputCOMPConnectors` → `List` (Read Only):

> List of output connectors (on the bottom) associated with this component.

## COMP Class Methods

### create()

`create(opType, name, initialize=True)`→ `OP`:

> Create a new node of the given type, inside this component. If name is supplied the new node will use that name, or the next numbered name if its already in use. `opType` can be a specific type object, example `waveCHOP`, or it can be a string 'waveCHOP'. If given an actual instance of a node n, these can be accessed via `type(n)` and `n.OPType` respectively.
>
> An initialization script associated with the operator is run, unless `initialize=False`. The new node is returned.
>
> - `opType` - The python OP type for the type of operator you want to create.
> - `name` - (Optional) The name for the new operator. If there already is an operator with that name, the next numbered name will be used.
> - `initialize` - (Keyword, Optional) If set to false, then the initialization script for that node won't be run. Most nodes don't do anything to initialize, but some do. For example the Light COMP initializes a network inside itself of SOPs.
>
> ```python
> n.create(waveCHOP)
> w = n.create(boxSOP, 'box12')
> ```

### collapseSelected()

`collapseSelected()`→ `None`:

> Move all selected operators into a new Base COMP. Equivalent to right-click on the network background and choosing Collapse Selected.

### copy()

`copy(OP, name=None, includeDocked=True)`→ `OP`:

> Copy the operator into this component. If name is supplied, the new node will use that name. The new node is returned.
>
> - `OP` - The operator to copy. This is not a string, it must be an OP.
> - `name` - (Keyword, Optional) If provided, the new node will have this name. If there already is an operator with that name, the next numbered name will be used.
> - `includeDocked` - (Keyword, Optional) When true a copy will include any externally docked operators to the source component.
>
> ```python
> w = n.copy( op('wave1') )
> ```

### copyOPs()

`copyOPs(listOfOPs)`→ `List`:

> Copy a list of operators into this component.
>
> This is preferred over multiple single copies, as connections between the operators are preserved. A new list with the created operators is returned.
>
> - `listOfOPs` - A list containing one or more OPs to be copied.
>
> ```python
> alist = [op('wave1'), op('wave2')]
> n.copyOPs(alist)
> ```

### findChildren()

`findChildren(type=None, name=None, path=None, depth=None, maxDepth=None, text=None, comment=None, tags=[], allTags=False, parValue=None, parExpr=None, parName=None, onlyNonDefaults=False, includeUtility=False, key=None)`→ `List of OPs`:

> Return a list of operators matching the specified criteria.
>
> - `type` - (Keyword, Optional) Specify the type of OP. Example `type=boxSOP`
> - `name` - (Keyword, Optional) Specify the name of the OP. Pattern Matching supported. Example: `name='project*'`
> - `path` - (Keyword, Optional) Specify the path of the OP. Pattern Matching supported. Example: `path='*/pics/*'`
> - `depth` - (Keyword, Optional) Specify the relative depth of the OP to the calling OP. Children have depth 1, their children have depth 2, etc.
> - `maxDepth` - (Keyword, Optional) Specify the maximum relative depth of the OP from the calling OP.
> - `text` - (Keyword, Optional) Specify the DAT contents of the OP. Pattern Matching supported. Example: `text='*import*'`
> - `comment` - (Keyword, Optional) Specify the OP comment. Pattern Matching supported. Example: `comment='*todo*'`
> - `tags` - (Keyword, Optional) Specify a list of tags to search. Pattern Matching supported. Example: `tags=['*sequencer*', '*interface*']`
> - `allTags` - (Keyword, Optional) When True, only include OPs where all specified tags are matched.
> - `parValue` - (Keyword, Optional) Specify the value of any parameters in the OP. Pattern Matching supported. Example: `parValue='500'`
> - `parExpr` - (Keyword, Optional) Specify the expression of any parameters in the OP. Pattern Matching supported. Example: `parExpr='*sin*'`
> - `parName` - (Keyword, Optional) Specify the name of any parameters in the OP. Pattern Matching supported. Example: `parName='clone'`
> - `onlyNonDefaults` - (Keyword, Optional) When True, only non default parameters are included.
> - `includeUtility` - (Keyword, Optional) If specified, controls whether or not Utility nodes (e.g. Comments) are included in the results.
> - `key` - (Keyword, Optional) Specify a custom search function.
>
> ```python
> #find all OPs whose name begins with circle
> n.findChildren(name='circle*')
>
> #find all wide CHOPs
> n.findChildren(type=CHOP, key = lambda x: x.nodeWidth > 200)
>
> #find all COMPs specifying clones
> n.findChildren(type=COMP, parName='clone', onlyNonDefaults=True)
> ```

### initializeExtensions()

`initializeExtensions(index=None)`→ `Extension`:

> Initialize the components extensions. To initialize an individual extension, specify its index.
>
> Returns the compiled extension.
>
> - `index` - (Optional) Index to initialize. 0 = first extension, etc.
>
> ```python
> n.initializeExtensions(0) # initialize first extension.
> ```

### loadTox()

`loadTox(filepath, unwired=False, pattern=None, password=None)`→ `OP`:

> Load the component from the given file path into this component.
>
> - `filepath` - The path and filename of the .tox to load.
> - `unwired` - (Keyword, Optional) If True, the component inputs will remain unwired.
> - `pattern` - (Keyword, Optional) Can be specified to only load operators within the component that match the pattern. Wildcards are not supported.
> - `password` - (Keyword, Optional) If specified, decrypts the tox with the password.

### loadByteArray()

`loadByteArray(byteArray, unwired=False, pattern=None, password=None)`→ `OP`:

> Load the component from the given bytearray into this COMP. See `.saveByteArray()` as a way to generate this byteArray.
>
> - `bytearray` - A bytearray containing the component, from a call to `saveByteArray()`.
> - `unwired` - (Keyword, Optional) If True, the component inputs will remain unwired.
> - `pattern` - (Keyword, Optional) Can be specified to only load operators within the component that match the pattern. Wildcards are not supported.
> - `password` - (Keyword, Optional) If specified, decrypts the component with the password."

### reload()

`reload(filepath, password=None)`→ `None`:

> Reloads the component from the given file path. This will replace its children as well as top level parameters and update flags, node width/height, storage, comments and inputs (but keep original node x,y).
>
> - `filepath` - The path and filename of the .tox to load.
> - `password` - (Keyword, Optional) If specified, decrypts the component with the password."

### resetNetworkView()

`resetNetworkView(recurse)`→ `None`:

> Reset the network view such that the network editor will be re-homed upon entering this component.
>
> - `recurse` - (Optional) When True, resets network view of all children components as well. Default False.
>
> ```python
> n.resetNetworkView(True) # reset network view of n and all its children.
> ```

### save()

`save(filepath, createFolders=False, password=None)`→ `Path`:

> Saves the component to disk. If no path is provided, a default filename is used and the .tox is saved to `project.folder`.
>
> Returns the filename used.
>
> - `filepath` - (Optional) The path and filename to save the .tox to.
> - `createFolders` - (Keyword, Optional) If True, it creates the not existent directories provided by the filepath.
> - `password` - (Keyword, Optional) If specified, encrypts the tox with the password.
>
> ```python
> name = n.save() # save in native tox format with default name
> n.save('output.tox')  # supply name
> n.save('C:/Desktop/myFolder/output.tox', createFolders=True)  # supply name and createFolder flag
> ```

### saveByteArray()

`saveByteArray(password=None)`→ `bytearray`:

> Save the component into a bytearray. The bytearray is the same data that is held in a .tox file. `loadByteArray()` can be used to load the component.
>
> - `password` - (Keyword, Optional) If specified, encrypts the tox with the password.

### saveExternalTox()

`saveExternalTox(recurse=False, password=None)`→ `int`:

> Save out the contents of any COMP referencing an external .tox
>
> Returns the number of components saved.
>
> - `recurse` - (Keyword, Optional) If set to True, child components are included in the operation.
> - `password` - (Keyword, Optional) If specified, encrypts the tox with the password.
>
> ```python
> root.saveExternalTox(recurse=True)
> op('geo1').saveExternalTox(recurse=False)
> ```

### Custom Parameters

#### appendCustomPage()

`appendCustomPage(name)`→ `Page`:

> Add a new page of custom parameters. See `Page Class` for more details. See `Custom Parameters` for the procedure.
>
> ```python
> n = op('base1')
> page = n.appendCustomPage('Custom1')
> page.appendFloat('X1')
> ```

#### destroyCustomPars()

`destroyCustomPars()`→ `Total`:

> Remove all custom parameters from COMP.

#### sortCustomPages()

`sortCustomPages(page1, page2, page3...)`→ `None`:

> Reorder custom parameter pages by listing their page names.
>
> ```python
> n = op('base1')
> n.sortCustomPages('Definition','Controls')
> ```

### Privacy

#### accessPrivateContents()

`accessPrivateContents(key)`→ `Bool`:

> Gain access to a private component. The component will still be private the next time it is saved or re-opened.
>
> Returns true when the key is correct, and access is granted. If dongle privacy is being used, no arguments are required.
>
> - `key` - (Optional) The existing key phrase. This should resolve to a non-blank string. Not required for dongle privacy.
>
> ```python
> n.accessPrivateContents('secret')
> ```

#### addPrivacy()

`addPrivacy(key, developerName=None)`→ `None`:

> Add privacy to a component with the given key.
>
> Privacy can only be added to components that currently have no privacy. Adding Privacy requires a Pro license.
>
> - `key` - The new key phrase. This should resolve to a non-blank string.
>
> ```python
> n.addPrivacy('secret')
> ```

`addPrivacy(firmCode, productCode, developerName=None, developerEmail=None)`→ `None`:

> Add privacy to a component with the given CodeMeter firm code and product code.
>
> Privacy can only be added to components that currently have no privacy. Adding Privacy requires a Pro license.
>
> The first bit of the CodeMeter Dongle's Feature Map must be set to enable privacy and add prodcut code as well as to access the private component in edit mode later.
>
> The private component can be used with any Dongle matching the firm code and product code without the first Feature Map bit set. In this case the component will run in private mode keeping the contents of the component hidden.
>
> - `firmCode` - The CodeMeter firm code to use.
> - `productCode` - The CodeMeter product code to use.
>
> ```python
> n.addPrivacy(10, 4)
> ```

#### blockPrivateContents()

`blockPrivateContents(key)`→ `None`:

> Block access to a private component that was temporarily accessible.
>
> ```python
> n.blockPrivateContents()
> ```

#### removePrivacy()

`removePrivacy(key)`→ `Bool`:

> Completely remove privacy from a component.
>
> Returns true when the key is correct.
>
> - `key` - The existing key phrase. This should resolve to a non-blank string.
>
> ```python
> n.removePrivacy('secret')
> ```

### Component Variables

#### setVar()

`setVar(name, value)`→ `None`:

> Set a component variable to the specified value.
>
> - `name` - The variable name to use.
> - `value` - The value for this variable.

#### unsetVar()

`unsetVar(name)`→ `None`:

> Unset the specified component variable. This removes the entry from the 'local/set_variables' table, if found.
>
> - `name` - The name of the variable to unset.

#### vars()

`vars(pattern1, pattern2...)`→ `List`:

> Return a list of all component variables in this COMP. Optional name patterns may be specified.
>
> - `pattern` - (Optional) The name(s) of variables whose values should be returned. Pattern Matching can be used.
>
> ```python
> a = n.vars()
> a = n.vars('A*', 'B*')
> ```

---

# OP Class

## Members

### General

`valid` → `bool` (Read Only):

> True if the referenced operator currently exists, False if it has been deleted.

`id` → `int` (Read Only):

> Unique id for the operator. This id can also be passed to the `op()` and `ops()` methods. Id's are not consistent when a file is re-opened, and will change if the OP is copied/pasted, changes OP types, deleted/undone. The id will not change if the OP is renamed though. Its data type is integer.

`name` → `str` :

> Get or set the operator name.

`path` → `str` (Read Only):

> Full path to the operator.

`digits` → `int` (Read Only):

> Returns the numeric value of the last consecutive group of digits in the name, or None if not found. The digits can be in the middle of the name if there are none at the end of the name.

`base` → `str` (Read Only):

> Returns the beginning portion of the name occurring before any digits.

`passive` → `bool` (Read Only):

> If true, operator will not cook before its access methods are called. To use a passive version of an operator n, use `passive(n)`.

`curPar` → `td.Par` (Read Only):

> The parameter currently being evaluated. Can be used in a parameter expression to reference itself. An easy way to see this is to put the expression `curPar.name` in any string parameter.

`curBlock` → (Read Only):

> The `SequenceBlock` of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

`curSeq` → `Sequence` (Read Only):

> The `Sequence` of the parameter currently being evaluated. Can be used in a parameter expression to reference itself.

`time` → `OP` (Read Only):

> Time Component that defines the operator's time reference.

`ext` → `class` (Read Only):

> The object to search for parent extensions.
>
> `me.ext.MyClass`

`fileFolder` → `str` (Read Only):

> Returns the folder where this node is saved.

`filePath` → `str` (Read Only):

> Returns the file location of this node.

`mod` → `mod` (Read Only):

> Get a module on demand object that searches for DAT modules relative to this operator.

`pages` → `list` (Read Only):

> A list of all built-in pages.

`parGroup` → `tuple` (Read Only):

> An intermediate parameter collection object, from which a specific parameter group can be found.
>
> `n.parGroup.t`
>
> # or
>
> `n.parGroup['t']`

`par` → `td.Par` (Read Only):

> An intermediate parameter collection object, from which a specific parameter can be found.
>
> `n.par.tx`
>
> # or
>
> `n.par['tx']`

`builtinPars` → `list` or `par` (Read Only):

> A list of all built-in parameters.

`customParGroups` → `list` of `parGroups` (Read Only):

> A list of all `ParGroups`, where a `ParGroup` is a set of parameters all drawn on the same line of a dialog, sharing the same label.

`customPars` → `list` of `par` (Read Only):

> A list of all custom parameters.

`customPages` → `list` (Read Only):

> A list of all custom pages.

`replicator` → `OP` or `None` (Read Only):

> The `replicatorCOMP` that created this operator, if any.

`storage` → `dict` (Read Only):

> Storage is dictionary associated with this operator. Values stored in this dictionary are persistent, and saved with the operator. The dictionary attribute is read only, but not its contents. Its contents may be manipulated directly with methods such as `OP.fetch()` or `OP.store()` described below, or examined with an `Examine DAT`.

`tags` → `list` :

> Get or set a set of user defined strings. Tags can be searched using `OP.findChildren()` and the `OP Find DAT`.
>
> The set is a regular python set, and can be accessed accordingly:
>
> `n.tags = ['effect', 'image filter']`
> `n.tags.add('darken')`

`children` → `list` (Read Only):

> A list of operators contained within this operator. Only component operators have children, otherwise an empty list is returned.

`numChildren` → `int` (Read Only):

> Returns the number of children contained within the operator. Only component operators have children.

`numChildrenRecursive` → `int` (Read Only):

> Returns the number of operators contained recursively within this operator. Only component operators have children.

`op` → `OP` or `None` (Read Only):

> The operator finder object, for accessing operators through paths or shortcuts. Note: a version of this method that searches relative to '/' is also in the global `td` module.
>
> `op(pattern1, pattern2..., includeUtility=False)` → `OP` or `None`
>
> Returns the first OP whose path matches the given pattern, relative to the inside of this operator. Will return `None` if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.
>
> - `pattern` - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
> - `includeUtility` (Optional) - if True, allow Utility nodes to be returned. If False, Utility nodes will be ignored.
>
> `b = op('project1')`
> `b = op('foot*', 'hand*')` #comma separated
> `b = op('foot* hand*')`  #space separated
> `b = op(154)`

`op.shortcut` → `OP`

> An operator specified with by a Global OP Shortcut. If no operator exists an exception is raised. These shortcuts are global, and must be unique. That is, cutting and pasting an operator with a Global OP Shortcut specified will lead to a name conflict. One shortcut must be renamed in that case. Furthermore, only components can be given Global OP Shortcuts.
>
> - `shortcut` - Corresponds to the Global OP Shortcut parameter specified in the target operator.
>
> `b = op.Videoplayer`
>
> To list all Global OP Shortcuts:
>
> `for x in op:`
> `print(x)`

`opex` → `OP` (Read Only):

> An operator finder object, for accessing operators through paths or shortcuts. Works like the `op()` shortcut method, except it will raise an exception if it fails to find the node instead of returning `None` as `op()` does. This is now the recommended way to get nodes in parameter expressions, as the error will be more useful than, for example, `NoneType` has no attribute "par", that is often seen when using `op()`. Note: a version of this method that searches relative to '/' is also in the global `td` module.
>
> `op(pattern1, pattern2..., includeUtility=False)` → `OP`
>
> Returns the first OP whose path matches the given pattern, relative to the inside of this operator. Will return `None` if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.
>
> - `pattern` - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
> - `includeUtility` (Optional) - if True, allow Utility nodes to be returned. If False, Utility operators will be ignored.

`parent` → `Shortcut` (Read Only):

> The Parent Shortcut object, for accessing parent components through indices or shortcuts.
>
> Note: a version of this method that searches relative to the current operator is also in the global `td` module.
>
> `parent(n)` → `OP` or `None`
>
> The nth parent of this operator. If n not specified, returns the parent. If n = 2, returns the parent of the parent, etc. If no parent exists at that level, `None` is returned.
>
> - `n` - (Optional) n is the number of levels up to climb. When n = 1 it will return the operator's parent.
>
> `p = parent(2)` #grandfather

`parent.shortcut` → `OP`

> A parent component specified with a shortcut. If no parent exists an exception is raised.
>
> - `shortcut` - Corresponds to the Parent Shortcut parameter specified in the target parent.
>
> `n = parent.Videoplayer`
>
> See also `Parent Shortcut` for more examples.

`iop` → `OP` (Read Only):

> The Internal Operator Shortcut object, for accessing internal shortcuts. See also `Internal Operators`. Note: a version of this method that searches relative to the current operator is also in the global `td` Module.

`ipar` → `ParCollection` (Read Only):

> The Internal Operator Parameter Shortcut object, for accessing internal shortcuts. See also `Internal Parameters`. Note: a version of this method that searches relative to the current operator is also in the global `td` Module.

`currentPage` → `Page` :

> Get or set the currently displayed parameter page. It can be set by setting it to another page or a string label.
>
> `n.currentPage = 'Common'`

### Common Flags

The following methods get or set specific operator Flags. Note specific operators may contain other flags not in this section.

`activeViewer` → `bool` :

> Get or set Viewer Active Flag.

`allowCooking` → `bool` :

> Get or set Cooking Flag. Only COMPs can disable this flag.

`bypass` → `bool` :

> Get or set Bypass Flag.

`cloneImmune` → `bool` :

> Get or set Clone Immune Flag.

`current` → `bool` :

> Get or set Current Flag.

`display` → `bool` :

> Get or set Display Flag.

`expose` → `bool` :

> Get or set the Expose Flag which hides a node from view in a network.

`lock` → `bool` :

> Get or set Lock Flag.

`selected` → `bool` :

> Get or set Selected Flag. This controls if the node is part of the network selection. (yellow box around it).

`seq` → (Read Only):

> An intermediate sequence collection object, from which a specific sequence group can be found.
>
> `n.seq.Color` #raises Exception if not found.
>
> # or
>
> `n.seq['Color']` #returns None if not found.

`python` → `bool` :

> Get or set parameter expression language as python.

`render` → `bool` :

> Get or set Render Flag.

`showCustomOnly` → `bool` :

> Get or set the Show Custom Only Flag which controls whether or not non custom parameters are display inparameter dialogs.

`showDocked` → `bool` :

> Get or set Show Docked Flag. This controls whether this node is visible or hidden when it is docked to another node.

`viewer` → `bool` :

> Get or set Viewer Flag.

### Appearance

`color` → `tuple(r, g, b)` :

> Get or set color value, expressed as a 3-tuple, representing its red, green, blue values. To convert between color spaces, use the built in `colorsys` module.

`comment` → `str` :

> Get or set comment string.

`nodeHeight` → `int` :

> Get or set node height, expressed in network editor units.

`nodeWidth` → `int` :

> Get or set node width, expressed in network editor units.

`nodeX` → `int` :

> Get or set node X value, expressed in network editor units, measured from its left edge.

`nodeY` → `int` :

> Get or set node Y value, expressed in network editor units, measured from its bottom edge.

`nodeCenterX` → `int` :

> Get or set node X value, expressed in network editor units, measured from its center.

`nodeCenterY` → `int` :

> Get or set node Y value, expressed in network editor units, measured from its center.

`dock` → `OP` :

> Get or set the operator this operator is docked to. To clear docking, set this member to `None`.

`docked` → `list` (Read Only):

> The (possibly empty) list of operators docked to this node.

### Connection

See also the `OP.parent` methods. To connect components together see `COMP_Class#Connection` section.

`inputs` → `list` (Read Only):

> List of input operators (via left side connectors) to this operator. To get the number of inputs, use `len(OP.inputs)`.

`outputs` → `list` (Read Only):

> List of output operators (via right side connectors) from this operator.

`inputConnectors` → `list` (Read Only):

> List of input connectors (on the left side) associated with this operator.

`outputConnectors` → `list` (Read Only):

> List of output connectors (on the right side) associated with this operator.

### Cook Information

`cookFrame` → `float` (Read Only):

> Last frame at which this operator cooked.

`cookTime` → `float` (Read Only):

> Deprecated Duration of the last measured cook (in milliseconds).

`cpuCookTime` → `float` (Read Only):

> Duration of the last measured cook in CPU time (in milliseconds).

`cookAbsFrame` → `float` (Read Only):

> Last absolute frame at which this operator cooked.

`cookStartTime` → `float` (Read Only):

> Last offset from frame start at which this operator cook began, expressed in milliseconds.

`cookEndTime` → `float` (Read Only):

> Last offset from frame start at which this operator cook ended, expressed in milliseconds. Other operators may have cooked between the start and end time. See the `cookTime` member for this operator's specific cook duration.

`cookedThisFrame` → `bool` (Read Only):

> True when this operator has cooked this frame.

`cookedPreviousFrame` → `bool` (Read Only):

> True when this operator has cooked the previous frame.

`childrenCookTime` → `float` (Read Only):

> Deprecated The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

`childrenCPUCookTime` → `float` (Read Only):

> The total accumulated cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

`childrenCookAbsFrame` → `float` (Read Only):

> Deprecated The absolute frame on which `childrenCookTime` is based.

`childrenCPUCookAbsFrame` → `float` (Read Only):

> The absolute frame on which `childrenCPUCookTime` is based.

`gpuCookTime` → `float` (Read Only):

> Duration of GPU operations during the last measured cook (in milliseconds).

`childrenGPUCookTime` → `float` (Read Only):

> The total accumulated GPU cook time of all children of this operator during the last frame. Zero if the operator is not a COMP and/or has no children.

`childrenGPUCookAbsFrame` → `float` (Read Only):

> The absolute frame on which `childrenGPUCookTime` is based.

`totalCooks` → `int` (Read Only):

> Number of times the operator has cooked.

`cpuMemory` → `int` (Read Only):

> The approximate amount of CPU memory this Operator is using, in bytes.

`gpuMemory` → `int` (Read Only):

> The amount of GPU memory this OP is using, in bytes.

### Type

`type` → `str` (Read Only):

> Operator type as a string. Example: 'oscin'.

`subType` → `str` (Read Only):

> Operator subtype. Currently only implemented for components. May be one of: 'panel', 'object', or empty string in the case of base components.

`OPType` → `str` (Read Only):

> Python operator class type, as a string. Example: 'oscinCHOP'. Can be used with `COMP.create()` method.

`label` → `str` (Read Only):

> Operator type label. Example: 'OSC In'.

`icon` → `str` (Read Only):

> Get the letters used to create the operator's icon.

`family` → `str` (Read Only):

> Operator family. Example: CHOP. Use the global dictionary `families` for a list of each operator type.

`isFilter` → `bool` (Read Only):

> True if operator is a filter, false if it is a generator.

`minInputs` → `int` (Read Only):

> Minimum number of inputs to the operator.

`maxInputs` → `int` (Read Only):

> Maximum number of inputs to the operator.

`isMultiInputs` → `bool` (Read Only):

> True if inputs are ordered, false otherwise. Operators with an arbitrary number of inputs have unordered inputs, example `Merge CHOP`.

`visibleLevel` → `int` (Read Only):

> Visibility level of the operator. For example, expert operators have visibility level 1, regular operators have visibility level 0.

`isBase` → `bool` (Read Only):

> True if the operator is a Base (miscellaneous) component.

`isCHOP` → `bool` (Read Only):

> True if the operator is a CHOP.

`isCOMP` → `bool` (Read Only):

> True if the operator is a component.

`isDAT` → `bool` (Read Only):

> True if the operator is a DAT.

`isMAT` → `bool` (Read Only):

> True if the operator is a Material.

`isObject` → `bool` (Read Only):

> True if the operator is an object.

`isPanel` → `bool` (Read Only):

> True if the operator is a Panel.

`isSOP` → `bool` (Read Only):

> True if the operator is a SOP.

`isTOP` → `bool` (Read Only):

> True if the operators is a TOP.

`licenseType` → `str` (Read Only):

> Type of License required for the operator.

## Methods

### General

NOTE: `create()`, `copy()` and `copyOPs()` is done by the parent operator (a component). For more information see `COMP.create`, `COMP.copy` and `COMP.copyOPs` methods.

`pars(pattern)`→ `list`:

> Returns a (possibly empty) list of parameter objects that match the pattern.
>
> - `pattern` - Is a string following the Pattern Matching rules, specifying which parameters to return.
>
> `newlist = op('geo1').pars('t?', 'r?', 's?')` #translate/rotate/scale parameters
>
> Note: If searching for a single parameter given a name, it's much more efficient to use the subscript operator. For example:
>
> `name = 'MyName1'`
> `op('geo1').par[name]`

`cook(force=False, recurse=False, includeUtility=False)`→ `None`:

> Cook the contents of the operator if required.
>
> - `force` - (Keyword, Optional) If True, the operator will always cook, even if it wouldn't under normal circumstances.
> - `recurse` - (Keyword, Optional) If True, all children and sub-children of the operator will be cooked.
> - `includeUtility` - (Keyword, Optional) If specified, controls whether or not utility components (eg Comments) are included in the results.

`copyParameters(OP, custom=True, builtin=True)`→ `None`:

> Copy all of the parameters from the specified operator. Both operators should be the same type.
>
> - `OP` - The operator to copy.
> - `custom` - (Keyword, Optional) When True, custom parameters will be copied.
> - `builtin` - (Keyword, Optional) When True, built in parameters will be copied.
>
> `op('geo1').copyParameters( op('geo2') )`

`changeType(OPtype)`→ `OP`:

> Change referenced operator to a new operator type. After this call, this OP object should no longer be referenced. Instead use the returned OP object.
>
> - `OPtype` - The python class name of the operator type you want to change this operator to. This is not a string, but instead is a class defined in the global `td` module.
>
> `n = op('wave1').changeType(nullCHOP)` #changes 'wave1' into a Null CHOP
> `n = op('text1').changeType(tcpipDAT)` #changes 'text1' operator into a TCPIP DAT

`dependenciesTo(OP)`→ `list`:

> Returns a (possibly empty) list of operator dependency paths between this operator and the specified operator. Multiple paths may be found.

`evalExpression(str)`→ `value`:

> Evaluate the expression from the context of this OP. Can be used to evaluate arbitrary snippets of code from arbitrary locations.
>
> - `str` - The expression to evaluate.
>
> `op('wave1').evalExpression('me.digits')`  #returns 1
>
> If the expression already resides in a parameter, use that parameters `evalExpression()` method instead.

`destroy()`→ `None`:

> Destroy the operator referenced by this OP. An exception will be raised if the OP's operator has already been destroyed.

`var(name, search=True)`→ `str`:

> Evaluate avariable. This will return the empty string, if not found. Most information obtained from variables (except for Root and Component variables) are accessible through other means in Python, usually in the global `td` module.
>
> - `name` - The variable name to search for.
> - `search` - (Keyword, Optional) If set to True (which is default) the operator hierarchy is searched until a variable matching that name is found. If false, the search is constrained to the operator.

`openMenu(x=None, y=None)`→ `None`:

> Open a node menu for the operator at x, y. Opens at mouse if x & y are not specified.
>
> - `x` - (Keyword, Optional) The X coordinate of the menu, measured in screen pixels.
> - `y` - (Keyword, Optional) The Y coordinate of the menu, measured in screen pixels.

`relativePath(OP)`→ `str`:

> Returns the relative path from this operator to the OP that is passed as the argument. See `OP.shortcutPath` for a version using expressions.

`setInputs(listOfOPs)`→ `None`:

> Set all the operator inputs to the specified list.
>
> - `listOfOPs` - A list containing one or more OPs. Entries in the list can be `None` to disconnect specific inputs. An empty list disconnects all inputs.

`shortcutPath(OP, toParName=None)`→ `str`:

> Returns an expression from this operator to the OP that is passed as the argument. See `OP.relativePath` for a version using relative path constants.
>
> - `toParName` - (Keyword, Optional) Return an expression to this parameter instead of its operator.

`ops(pattern1, pattern2.., includeUtility=False)`→ `list` of `OPs`:

> Returns a (possibly empty) list of OPs that match the patterns, relative to the inside of this OP.
>
> Multiple patterns may be provided. Numeric OP ids may also be used.
>
> - `pattern` - Can be string following the Pattern Matching rules, specifying which OPs to return, or an integer, which must be an OP Id. Multiple patterns can be given and all matched OPs will be returned.
> - `includeUtility` - (Keyword, Optional) If specified, controls whether or not utility components (eg Comments) are included in the results.
>
> Note: a version of this method that searches relative to '/' is also in the global `td` module.
>
> `newlist = n.ops('arm*', 'leg*', 'leg5/foot*')`

`resetPars(parNames='*', parGroupNames='*', pageNames='*', includeBuiltin=True, includeCustom=True)`→ `bool`:

> Resets the specified parameters in the operator.
>
> Returns true if anything was changed.
>
> - `parNames` (Keyword, Optional) - Specify parameters by Par name.
> - `parGroupNames` (Keyword, Optional) - Specify parameters by ParGroup name.
> - `pageNames` (Keyword, Optional) - Specify parameters by page name.
> - `includeBuiltin` (Keyword, Optional) - Include builtin parameters.
> - `includeCustom` (Keyword, Optional) - Include custom parameters.
>
> `op('player').resetPars(includeBuiltin=False)` # only reset custom

### Errors

`addScriptError(msg)`→ `None`:

> Adds a script error to a node.
>
> - `msg` - The error to add.

`addError(msg)`→ `None`:

> Adds an error to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).
>
> - `msg` - The error to add.

`addWarning(msg)`→ `None`:

> Adds a warning to an operator. Only valid if added while the operator is cooking. (Example Script SOP, CHOP, DAT).
>
> - `msg` - The error to add.

`errors(recurse=False)`→ `str`:

> Get error messages associated with this OP.
>
> - `recurse` - Get errors in any children or subchildren as well.

`warnings(recurse=False)`→ `str`:

> Get warning messages associated with this OP.
>
> - `recurse` - Get warnings in any children or subchildren as well.

`scriptErrors(recurse=False)`→ `str`:

> Get script error messages associated with this OP.
>
> - `recurse` - Get errors in any children or subchildren as well.

`clearScriptErrors(recurse=False, error='*')`→ `None`:

> Clear any errors generated during script execution. These may be generated during execution of DATs, Script Nodes, Replicator COMP callbacks, etc.
>
> - `recurse` - Clear script errors in any children or subchildren as well.
> - `error` - Pattern to match when clearing errors
>
> `op('/project1').clearScriptErrors(recurse=True)`

`childrenCPUMemory()`→ `int`:

> Returns the total CPU memory usage for all the children from this COMP.

`childrenGPUMemory()`→ `int`:

> Returns the total GPU memory usage for all the children from this COMP.

### Appearance

`resetNodeSize()`→ `None`:

> Reset the node tile size to its default width and height.

### Viewers

`closeViewer(topMost=False)`→ `None`:

> Close the floating content viewers of the OP.
>
> - `topMost` - (Keyword, Optional) If True, any viewer window containing any parent of this OP is closed instead.
>
> `op('wave1').closeViewer()`
> `op('wave1').closeViewer(topMost=True)` # any viewer that contains 'wave1' will be closed.

`openViewer(unique=False, borders=True)`→ `None`:

> Open a floating content viewer for the OP.
>
> - `unique` - (Keyword, Optional) If False, any existing viewer for this OP will be re-used and popped to the foreground. If unique is True, a new window is created each time instead.
> - `borders` - (Keyword, Optional) If true, the floating window containing the viewer will have borders.
>
> `op('geo1').openViewer(unique=True, borders=False)` # opens a new borderless viewer window for 'geo1'

`resetViewer(recurse=False)`→ `None`:

> Reset the OP content viewer to default view settings.
>
> - `recurse` - (Keyword, Optional) If True, this is done for all children and sub-children as well.
>
> `op('/').resetViewer(recurse=True)` # reset the viewer for all operators in the entire file.

`openParameters()`→ `None`:

> Open a floating dialog containing the operator parameters.

### Storage

Storage can be used to keep data within components. Storage is implemented as one python dictionary per node.

When an element of storage is changed by using `n.store()` as explained below, expressions and operators that depend on it will automatically re-cook. It is retrieved with the `n.fetch()` function.

Storage is saved in `.toe` and `.tox` files and restored on startup.

Storage can hold any python object type (not just strings as in Tscript variables). Storage elements can also have optional startup values, specified separately. Use these startup values for example, to avoid saving and loading some session specific object, and instead save or load a well defined object like `None`.

See the `Examine DAT` for procedurally viewing the contents of storage.

`fetch(key, default, search=True, storeDefault=False)`→ `value`:

> Return an object from the OP storage dictionary. If the item is not found, and a default it supplied, it will be returned instead.
>
> - `key` - The name of the entry to retrieve.
> - `default` - (Optional) If provided and no item is found then the passed value/object is returned instead.
> - `storeDefault` - (Keyword, Optional) If True, and the key is not found, the default is stored as well.
> - `search` - (Keyword, Optional) If True, the parent of each OP is searched recursively until a match is found
>
> `v = n.fetch('sales5', 0.0)`

`fetchOwner(key)`→ `OP`:

> Return the operator which contains the stored key, or `None` if not found.
>
> - `key` - The key to the stored entry you are looking for.
>
> `who = n.fetchOwner('sales5')` #find the OP that has a storage entry called 'sales5'

`store(key, value)`→ `value`:

> Add the key/value pair to the OP's storage dictionary, or replace it if it already exists. If this value is not intended to be saved and loaded in the toe file, it can be be given an alternate value for saving and loading, by using the method `storeStartupValue` described below.
>
> - `key` - A string name for the storage entry. Use this name to retrieve the value using `fetch()`.
> - `value` - The value/object to store.
>
> `n.store('sales5', 34.5)` # stores a floating point value 34.5.
> `n.store('moviebank', op('/project1/movies'))` # stores an OP for easy access later on.

`unstore(keys1, keys2..)`→ `None`:

> For key, remove it from the OP's storage dictionary. Pattern Matching is supported as well.
>
> - `keys` - The name or pattern defining which key/value pairs to remove from the storage dictionary.
>
> `n.unstore('sales*')` # removes all entries from this OPs storage that start with 'sales'

`storeStartupValue(key, value)`→ `None`:

> Add the key/value pair to the OP's storage startup dictionary. The storage element will take on this value when the file starts up.
>
> - `key` - A string name for the storage startup entry.
> - `value` - The startup value/object to store.
>
> `n.storeStartupValue('sales5', 1)` # 'sales5' will have a value of 1 when the file starts up.

`unstoreStartupValue(keys1, keys2..)`→ `None`:

> For key, remove it from the OP's storage startup dictionary. Pattern Matching is supported as well. This does not affect the stored value, just its startup value.
>
> - `keys` - The name or pattern defining which key/value pairs to remove from the storage startup dictionary.
>
> `n.unstoreStartupValue('sales*')` # removes all entries from this OPs storage startup that start with 'sales'

### Miscellaneous

`__getstate__()`→ `dict`:

> Returns a dictionary with persistent data about the object suitable for pickling and deep copies.

`__setstate__()`→ `dict`:

> Reads the dictionary to update persistent details about the object, suitable for unpickling and deep copies.
