---
title: "Undo Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
user_personas: ["script_developer", "advanced_user"]
operators: []
concepts: ["undo", "redo", "scripting_callbacks", "state_management"]
prerequisites: ["Python_fundamentals", "CLASS_UI"]
workflows: ["advanced_scripting", "custom_component_development"]
keywords: ["undo", "redo", "callback", "block", "stack", "ui"]
tags: ["python", "api", "core", "ui", "undo"]
related_docs:
- CLASS_UI
- MODULE_td
---

# Undo Class

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods](#methods)
- [Undo Block Examples](#undo-block-examples)
- [Undo Callbacks](#undo-callbacks)

## Introduction

A class to enable and disable undo functionality. Undo blocks can be created in scripts. At the end of callbacks, any dangling undo blocks will be terminated. See examples at bottom of page.

This class is available as a member of the global [CLASS_UI], via `ui.undo`.

## Members

### globalState

`globalState` → `bool`:

> Is global undo enabled or not.

### redoStack

`redoStack` → `list` (Read Only):

> A list of names for redo operations available.

### state

`state` → `bool` (Read Only):

> Is undo enabled or not.

### undoStack

`undoStack` → `list` (Read Only):

> A list of names for undo operations available.

## Methods

### startBlock()

`startBlock(name, enable=True)`→ `None`:

> Start a named undo block. While the block is active, any script changes to TouchDesigner objects that are undoable in the editor will be added to the undo stack.
>
> - `name` - The name of the block, which should briefly describe the change that would be undone.
> - `enable` - In the rare case you want to insert a block that doesn't store undo info within a block that does, you can create a block with enable off.
>
> ```python
> # undoing this will remove the noiseTOP and noiseSOP only.
>
> ui.undo.startBlock("constant1 r = 0")
> a = op('constant1').par.colorr = 0
> ui.undo.startBlock("constant2 g = 0", enable=False)
> a = op('constant2').par.colorg = 0
> ui.undo.endBlock()
> a = op('constant3').par.colorb = 0
> ui.undo.endBlock()
> ```

### clear()

`clear()`→ `None`:

> Clear undo and redo stack. This will terminate any current undo blocks.

### addCallback()

`addCallback(callback, info=None)`→ `None`:

> Add a Python callback into the current undo block.
>
> The callback should be defined as `def yourCallbackName(isUndo, info)`. The `isUndo` argument tells if the call is an undo or a redo (the same callback is used for both) and the `info` argument is the same Python object passed to `addCallback`, and should contain any information needed to perform the undo/redo.
>
> - `callback` - user defined callback function. Should be defined as `callback(isUndo, info)`
> - `info` - this argument will be passed back to user in the callback

### redo()

`redo()`→ `None`:

> Redo the next operation. This will terminate any current undo blocks.

### undo()

`undo()`→ `None`:

> Undo the last operation. This will terminate any current undo blocks.

### endBlock()

`endBlock()`→ `None`:

> Terminate an undo block.

## Undo Block Examples

Setting up an undo block is as simple as starting it and then doing any changes that the editor can normally undo:

```python
ui.undo.startBlock("Change Title Text")
op('title').par.text = 'Making Your Own Undo System'
op('title').par.fontsize = 30
ui.undo.endBlock()
```

After running this script, performing an undo action will change the referenced text and fontsize parameters to go back to whatever their previous values were. Redo functionality is similarly automatic.

## Undo Callbacks

You can also perform Python actions as part of an undo stack. This is necessary when you are changing something that the TouchDesigner editor does not know how to undo, such as changing extension values. The undo callback takes an `info` argument, which should be used to provide both undo and redo information to the callback.

```python
# an undo callback must be defined before it is referenced by ui.undo.addCallback
# this callback will be called when TouchDesigner is trying to undo a block in which it was added
def undoMasterChange(isUndo, info):
    # isUndo tells whether this call is an undo or a redo
    # info is any Python object, provided by the user
    if isUndo: # True means undo
        ext.MasterExt.data = info['prev'] # change data back to what we stored as "prev"
    else: # False means redo
        ext.MasterExt.data = info['new'] # change data back to what we stored as "new"

newData = 'new stuff'

# start the block
ui.undo.startBlock("Update Master Data")

# store undo/redo info
info = {'prev': ext.MasterExt.data, 'new': newData} 

# next, perform the change
ext.MasterExt.data = newData

# TouchDesigner doesn't know how to undo the above, so add the callback
ui.undo.addCallback(undoMasterChange, info)

# you can mix callbacks with normal undoable items, so the next line will be added to the block
op('master').par.Version += 1 

# end the block
ui.undo.endBlock()
```

Note: The order that things are added to the undo block can matter. When undoing, changes will be undone and callbacks will be run in the reverse order that they were received in the undo block. When redoing, changes will be made in the same order they were originally received in the undo block.
