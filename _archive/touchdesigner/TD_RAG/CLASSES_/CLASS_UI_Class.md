---
title: "UI Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "technical_artist", "automation_specialist", "advanced_user"]
completion_signals: ["can_access_ui_properties", "understands_application_control", "can_implement_ui_scripting", "manages_user_interaction"]

operators:
- Panel_COMP
- Container_COMP
- Window_COMP
concepts:
- ui_scripting
- application_control
- window_management
- user_interaction
- dialogs
- file_io
- clipboard_management
- undo_stack
- perform_mode_control
prerequisites:
- Python_fundamentals
- MODULE_td_Module
workflows:
- custom_ui_development
- tool_building
- scripted_file_operations
- user_feedback_systems
- application_automation
- dialog_creation
keywords:
- user interface
- ui control
- perform mode
- panes
- preferences
- clipboard
- message box
- file dialog
- folder dialog
- open dialog
- status bar
- undo
- rollover
- mouse state
- window size
- ui automation
tags:
- python
- global
- ui
- dialog
- file
- window
- perform_mode
- scripting
- api
- interface_control
relationships:
  MODULE_td_Module: strong
  CLASS_Project_Class: medium
  REF_Multiple_Monitors: medium
related_docs:
- MODULE_td_Module
- CLASS_Project_Class
- REF_Multiple_Monitors
# Enhanced search optimization
search_optimization:
  primary_keywords: ["ui", "interface", "dialog", "window"]
  semantic_clusters: ["ui_control", "application_management", "user_interaction"]
  user_intent_mapping:
    beginner: ["what is ui class", "basic interface control", "how to show dialogs"]
    intermediate: ["ui automation", "file dialogs", "window management"]
    advanced: ["custom tool development", "advanced ui scripting", "application control"]

hierarchy:
  secondary: global_objects
  tertiary: ui_control
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- custom_ui_development
- tool_building
- scripted_file_operations
- user_feedback_systems
---

# UI Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Panel_COMP, Container_COMP, Window_COMP]
concepts: [ui_scripting, application_control, window_management, user_interaction, dialogs, file_io, clipboard_management, undo_stack, perform_mode_control]
prerequisites: [Python_fundamentals, MODULE_td_Module]
workflows: [custom_ui_development, tool_building, scripted_file_operations, user_feedback_systems, application_automation, dialog_creation]
related: [MODULE_td_Module, CLASS_Project_Class, REF_Multiple_Monitors]
relationships: {
  "MODULE_td_Module": "strong",
  "CLASS_Project_Class": "medium",
  "REF_Multiple_Monitors": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "global_objects"
  tertiary: "ui_control"
keywords: [user interface, ui control, perform mode, panes, preferences, clipboard, message box, file dialog, folder dialog, open dialog, status bar, undo, rollover, mouse state, window size, ui automation]
tags: [python, global, ui, dialog, file, window, perform_mode, scripting, api, interface_control]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: custom_ui_development, tool_building, scripted_file_operations

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [MODULE td Module] → [CLASS Project Class] → [REF Multiple Monitors]

**Related Topics**: custom ui development, tool building, scripted file operations

## Summary

Core class providing access to TouchDesigner's user interface elements and application-level UI controls. Essential for building custom tools, dialogs, and automated workflows that interact with the interface.

## Relationship Justification

Connected to td module as global object. Links to Project class for application-level control and Multiple Monitors for window management functionality.

## Content

- [Introduction](#introduction)
- [Usage](#usage)
- [Members Overview](#members-overview)
  - [clipboard](#clipboard)
  - [colors](#colors)
  - [dpiBiCubicFilter](#dpibicubicfilter)
  - [masterVolume](#mastervolume)
  - [options](#options)
  - [panes](#panes)
  - [performMode](#performmode)
  - [preferences](#preferences)
  - [redrawMainWindow](#redrawmainwindow)
  - [rolloverOp](#rolloverop)
  - [rolloverPar](#rolloverpar)
  - [rolloverPanel](#rolloverpanel)
  - [lastChopChannelSelected](#lastchopchannelselected)
  - [showPaletteBrowser](#showpalettebrowser)
  - [status](#status)
  - [undo](#undo)
  - [windowWidth](#windowwidth)
  - [windowHeight](#windowheight)
  - [windowX](#windowx)
  - [windowY](#windowy)
- [Methods Overview](#methods-overview)
  - [copyOPs()](#copyops)
  - [pasteOPs()](#pasteops)
  - [messageBox()](#messagebox)
  - [refresh()](#refresh)
  - [chooseFile()](#choosefile)
  - [chooseFolder()](#choosefolder)
  - [viewFile()](#viewfile)
  - [openBeat()](#openbeat)
  - [openBookmarks()](#openbookmarks)
  - [openCOMPEditor()](#opencompeditor)
  - [openConsole()](#openconsole)
  - [openDialogHelp()](#opendialoghelp)
  - [openErrors()](#openerrors)
  - [openExplorer()](#openexplorer)
  - [openExportMovie()](#openexportmovie)
  - [openImportFile()](#openimportfile)
  - [openKeyManager()](#openkeymanager)
  - [openMIDIDeviceMapper()](#openmididevicemapper)
  - [openNewProject()](#opennewproject)
  - [openOperatorSnippets()](#openoperatorsnippets)
  - [openPaletteBrowser()](#openpalettebrowser)
  - [openPerformanceMonitor()](#openperformancemonitor)
  - [openPreferences()](#openpreferences)
  - [openSearch()](#opensearch)
  - [openTextport()](#opentextport)
  - [openVersion()](#openversion)
  - [openWindowPlacement()](#openwindowplacement)
  - [findEditDAT()](#findeditdat)

## Introduction

The UI class describes access to the UI elements of the application, found in the automatically imported [PY_td] module.

## Usage

To access members and methods of this class use the default instance `ui`.

```python
# open the Midi Device Mapper Dialog
ui.openMIDIDeviceMapper()
```

## Members Overview

### clipboard

clipboard → str:

Get or set the operating system clipboard text contents.

### colors

colors → [CLASS_Colors] (Read Only):

Access to the application colors.

### dpiBiCubicFilter

dpiBiCubicFilter → bool:

Get or set the global DPI scale filtering mode of TouchDesigner windows. True means bi-cubic, False means linear.

### masterVolume

masterVolume → float:

Get or set the master audio output volume. A value of 0 is no output, while a value of 1 is full output.

### options

options → [CLASS_Options] (Read Only):

Access to the application options.

### panes

panes → [CLASS_Panes] (Read Only):

Access to the set of all panes.

### performMode

performMode → bool:

Get or set [REF_PerformMode]. Set to True to go into Perform Mode, False to go into Designer Mode.

### preferences

preferences → [CLASS_Preferences] (Read Only):

Access to the application preferences, which can also be access through the [REF_PreferencesDialog].

### redrawMainWindow

redrawMainWindow → bool:

Get or set whether the main window should redraw. The main window is either the main network editor, or the perform window.

### rolloverOp

rolloverOp → [CLASS_OP] (Read Only):

Operator currently under the mouse in a network editor.

### rolloverPar

rolloverPar → [CLASS_Par] (Read Only):

Parameter currently under the mouse in a parameter dialog.

### rolloverPanel

rolloverPanel → [CLASS_PanelCOMP] (Read Only):

Returns the latest panel to get a rollover event. Takes into account click through, depth order, and other panel settings.

### lastChopChannelSelected

lastChopChannelSelected → [CLASS_Channel] (Read Only):

Last CHOP channel selected via mouse.

### showPaletteBrowser

showPaletteBrowser → bool:

Get or set display of the palette browser.

### status

status → str:

Get or set the status message.

```python
ui.status = 'Operation Complete'
```

### undo

undo → [CLASS_Undo] (Read Only):

The Undo object, which provides access to application undo functions.

### windowWidth

windowWidth → int (Read Only):

Get the app window width.

### windowHeight

windowHeight → int (Read Only):

Get the app window height.

### windowX

windowX → int (Read Only):

Get the app window X position.

### windowY

windowY → int (Read Only):

Get the app window Y position.

## Methods Overview

### copyOPs()

copyOPs(listOfOPs)→ None:

Copy a list of operators to the operator clipboard. All operators must be children of the same component.

- `listOfOPs` - A list containing one or more OPs to be copied.

```python
ui.copyOPs( op('geo1').selected )
```

### pasteOPs()

pasteOPs(COMP, x=None, y=None)→ None:

Copy the contents of the operator clipboard into the specified component.

- `COMP` - The destination to receive the operators.
- `x` - (Optional) Network coordinates at which to paste the operators.
- `y` - (Optional) See x.

```python
l = ui.pasteOPs( op('geo2') )
```

### messageBox()

messageBox(title, message, buttons=['Ok'])→ int:

This method will open a message dialog box with the specified message. Returns the index of the button clicked.

- `title` - Specifies the window title.
- `message` - Specifies the content of the dialog.
- `buttons` - (Keyword, Optional) Specifies a list button labels to show in the dialog.

```python
# basic usage
ui.messageBox('Warning', 'Have a nice day.')

# specify options and report result
a = ui.messageBox('Please select:', 'Buttons:', buttons=['a', 'b', 'c'])
ui.messageBox('Results', 'You selected item: ' + str(a))

# pick a node from their paths
ui.messageBox('Please select:', 'Nodes:', buttons=parent().children)

# pick a node from their first names (list comprehension)
ui.messageBox('Please select:', 'Nodes:', buttons=[x.name for x in parent().children])

# pick a cell
ui.messageBox('Please select:', 'Cells:', buttons=op('table1').cells('*','*'))
```

### refresh()

refresh()→ None:

Update and redraw all viewports, nodes, UI elements etc immediately. This update is otherwise done once per frame at the end of all script executions. For example, if the current frame is manually changed during a script, a call to refresh will cause all dependent data to update immediately.

```python
for i in range(100):
    ui.status = str(i)
    ui.refresh()
```

### chooseFile()

chooseFile(load=True, start=None, fileTypes=None, title=None, asExpression=False)→ str | None:

Open a dialog box for loading or saving a file. Returns the filename selected or None if the dialog is cancelled.

- `load` - (Keyword, Optional) If set to True, the dialog will be a Load dialog, otherwise it's a Save dialog.
- `start` - (Keyword, Optional) If provided, specifies an initial folder location and/or filename selection.
- `fileTypes` - (Keyword, Optional) If provided, specifies a list of file extensions that can be used as filters. Otherwise '*.*' is the only filter.
- `asExpression` - (Keyword, Optional) If set to true, the results are provided as an expression, suitable for a Parameter expression or as input to an eval() call. App Class member constants such as samplesFolder may be included in the result.
- `title` - (Keyword, Optional) If provided, will override the default window title.

```python
a = ui.chooseFile(start='python_examples.toe', fileTypes=['toe'], title='Select a toe') # specify extension
a = ui.chooseFile(fileTypes=tdu.fileTypes['image'], title='Select an image') # any support image extension
path = ui.chooseFile(load=False,fileTypes=['txt'],title='Save table as:')
if (path):
    op('table1').save(path)
```

### chooseFolder()

chooseFolder(title='Select Folder', start=None, asExpression=False)→ str | None:

Open a dialog box for selecting a folder. Returns the folder selected or None if the dialog is cancelled.

- `title` - (Keyword, Optional) If provided, specifies the window title.
- `start` - (Keyword, Optional) If provided, specifies an initial folder location and/or filename selection.
- `asExpression` - (Keyword, Optional) If set to true, the results are provided as an expression, suitable for a Parameter expression or as input to an eval() call. App Class member constants such as samplesFolder may be included in the result.

```python
a = ui.chooseFolder()
a = ui.chooseFolder(title='Select a folder location.')
```

### viewFile()

viewFile(URL_or_path, showInFolder=False)→ None:

View a URL or file in the default external application. You can use `ui.viewFile()` to open a folder/directory in Windows Explorer or macOS Finder.

- `URL_or_path` - URL or path to launch.
- `showInFolder` - (Optional) Show file as selected in Explorer or macOS Finder instead of launching an external application.

```python
a = ui.viewFile('output.txt')
a = ui.viewFile('output.txt', showInFolder=True)
```

### openBeat()

openBeat()→ None:

Open the Beat Dialog.

### openBookmarks()

openBookmarks()→ None:

Open the Bookmarks Dialog.

### openCOMPEditor()

openCOMPEditor(path)→ None:

Open component editor for the specific operator.

- `path` - Specifies the path to the operator. An OP can be passed in as well.

### openConsole()

openConsole()→ None:

Open the Console Window.

### openDialogHelp()

openDialogHelp(title)→ None:

Open help page for the specific dialog.

- `title` - Specifies the help page to open.

```python
ui.openDialogHelp('Window Placement Dialog')
```

### openErrors()

openErrors()→ None:

Open the Errors Dialog.

### openExplorer()

openExplorer()→ None:

Open an Explorer window.

### openExportMovie()

openExportMovie(path)→ None:

Open the Export Movie Dialog.

- `path` - (Optional) Specifies the operator content to export.

```python
ui.openExportMovie('/project1/out1')
```

### openImportFile()

openImportFile()→ None:

Open the Import File Dialog.

### openKeyManager()

openKeyManager()→ None:

Open the Key Manager Dialog.

### openMIDIDeviceMapper()

openMIDIDeviceMapper()→ None:

Open the MIDI Device Mapper Dialog.

### openNewProject()

openNewProject()→ None:

Open the New Project Dialog.

### openOperatorSnippets()

openOperatorSnippets(family=None, type=None, example=None)→ None:

Open the Operator Snippets window.

### openPaletteBrowser()

openPaletteBrowser()→ None:

Open the Palette.

### openPerformanceMonitor()

openPerformanceMonitor()→ None:

Open the Performance Monitor Dialog.

### openPreferences()

openPreferences()→ None:

Open the Preferences Dialog.

### openSearch()

openSearch()→ None:

Open the Search Replace Dialog.

### openTextport()

openTextport()→ None:

Open the Textport.

### openVersion()

openVersion()→ None:

Open a dialog displaying current version information. See also: [CLASS_App].version

### openWindowPlacement()

openWindowPlacement()→ None:

Open the Window Placement Dialog.

### findEditDAT()

findEditDAT(filename)→ [CLASS_DAT] | None:

Given an external filename, finds the corresponding DAT thats update from this filename if any.

- `filename` - The external filename to search for.
