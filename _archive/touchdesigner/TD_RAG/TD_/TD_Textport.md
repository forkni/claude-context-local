---
title: "Textport"
category: "TD_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "15 minutes"
user_personas: ["developer", "python_programmer", "tscript_user", "debugger"]
completion_signals: ["can_open_and_use_the_textport", "knows_how_to_run_python_commands"]
operators: ["OPViewerTOP"]
concepts: ["textport", "console", "python", "tscript", "scripting", "debugging", "dat"]
prerequisites: []
workflows: ["scripting", "debugging", "live_coding"]
keywords: ["textport", "console", "script", "python", "tscript", "print", "debug"]
tags: ["core", "ui", "guide", "scripting", "debugging"]
related_docs:
- "TD_ConsoleDialog"
- "MODULE_TdModule"
- "MODULE_TduModule"
- "REF_Tscript"
---

# Textport

## Content
- [Introduction](#introduction)
- [Textport Dialog](#textport-dialog)
- [Tips for Working in the Textport](#tips-for-working-in-the-textport)
- [Python in the Textport](#python-in-the-textport)
- [TScript in the Textport](#tscript-in-the-textport)
- [textport Command (Tscript only)](#textport-command-tscript-only)

## Introduction

The Textport is the dialog box in which commands and scripts can be typed in manually. Output to the textport includes script errors and messages from `print()` and `debug()` calls in python code. You can also edit [DATs] in the textport.

`Dialogs -> Textport` brings up the main textport, but you can also press `F4` to open the Textport as a floating window. `F4` will also work in Perform Mode.

You can type python expressions and get them evaluated, as simple as `2+3`, which prints `5` on the next line.

> **Tip:** If you mis-type a line and press Enter, to edit it you can press the up-arrow to get the last lines you typed, and you can edit them with arrow/backspace/delete characters, then press Enter to re-execute it.

If you are writing an expression like `op('/project1/geo1').par.tx`, you can more easily type `op('`, then drag the node to the textport (which adds its path to the string), and then type `').par.tx` and Enter: It will do the same thing.

> **Tip:** You can edit several [DATs] in the textport at once. Right-click on a [DAT] and select `Edit Contents in Textport...`. It will open a new tab in the textport where you can edit or view code.

Note that some startup and system errors are output to `Dialogs -> Console`.

You can put textports in panes by setting the `Pane Type` menu to `Textport and DATs`.

There are two scripting languages in TouchDesigner: Python and the obsolete Tscript. For Tscript, all commands are described in Tscript Commands and Tscript Expressions, and its scripting syntax is found in Tscript. `textport` is a Tscript command that can be used to manipulate the contents of the dialog.

You can redirect Python `stdout` and `stderr` to any [DAT]. Then you can use the `OP Viewer TOP` or `COMP` to convert that [DAT] into a texture and integrate it into your UI.

## Textport Dialog

The textport can be opened from the `Dialogs` menu or by using the `Alt+Shift+T` keyboard shortcut. Textport can also be opened as a Pane.

The simplest method to input Python scripts is through the textport. The textport, like all scripting in TouchDesigner, allows scripts to be specified in either Python or Tscript.

After opening the textport, make sure it is set to Python language. This is controlled by the small toggle button in the upper left side of the textport.

When it is set to `Py`, all input is interpreted as Python. When set to `T` it is interpreted as tscript.

In addition the textport prompt and text color have different values for each language, making it easier to identify which state the textport is in.

Dragging a `Text DAT` onto the Textport will give you the following options:

- **Run DAT** - paste the command to execute the DAT as a script into the Textport. This option is only available in the main Textport tab.
- **Open DAT** - open the contents of the DAT in a new tab in the Textport. You can switch between tabs by clicking on the tab header near the top of the dialog box.
- **Paste Text** - pastes in the DAT's path name just like other OPs.

Additionally, any selected text can be dragged onto the Textport from anywhere on the interface.

### Shortcut: Textport History

A history of recent commands can be brought up by right-clicking anywhere in the textport. Pressing the "up" arrow key will step back through the command history. Pressing the down arrow key will step forward through command history.

### Textport Search

The search field at the top of the textport can be used to find strings in the scrollable text of the textport.

### Textport History

When working with DATs in the textport, a history of viewed DATs will be available on the right side of the Textport header.

## Tips for Working in the Textport

Holding shift and clicking on textport text will select the text between the cursor and the mouse position instead of just moving the cursor.

## Python in the Textport

In the textport, you can enter `help` for a list of available commands or `help(object)` for any python object, like `help(op('/project1').par.x)`.

Script errors and messages from `print()` commands are also output to this dialog box.

The main textport also receives the error messages and `print()` commands from all scripts that are run in DATs.

However startup and system errors are output to `Dialogs -> Console`.

You can save typing OP path names by simply dragging any OP onto the Textport. Just drag the OP onto the Textport using the left mouse button.

As a simple test type the following into the textport:

```python
help(op)
```

This will output all help related to the `op()` method found in the [MODULE_TdModule].

The `td Module` is the main module containing all TouchDesigner related classes and objects. It is imported by default when the application begins.
Another useful module is the [MODULE_TduModule]. This module contains some specific TouchDesigner utility functions useful during scripting.

## TScript in the Textport

In the textport, you can enter `help` for a list of available commands or `exhelp` for a list of available expression functions. You can also access Tscript commands and expressions from the Help menu by selecting `Commands and Expressions`.

Script errors and messages from `echo` commands are also output to this dialog box.

The main textport also receives the error messages and `echo` commands from all scripts that are run in DATs.

However startup and system errors are output to `Dialogs -> Console`.

You can save typing OP path names by simply dragging any OP onto the Textport. Just drag the OP onto the Textport using the left mouse button.

## textport Command (Tscript only)

The `textport` command is used to manipulate the Textport dialog. One of the advantages of using `textport` is the ability to load DATs without having to navigate to them through the Network pane. For example, to load a DAT in a floating Textport, the following code can be used:

```tscript
textport -l /datpath/datname
```

This can be particularly useful while debugging scripts or monitoring network performance.
