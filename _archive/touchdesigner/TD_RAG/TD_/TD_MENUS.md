# TouchDesigner Menus Reference

## Overview

This document contains the complete TouchDesigner menu structure with commands and keyboard shortcuts. The menus are organized hierarchically as they appear in the TouchDesigner interface.

## Usage Notes

- **Commands**: Internal TouchDesigner commands that are executed when menu items are selected
- **Shortcuts**: Keyboard shortcuts associated with menu items
- **Hierarchy**: Indentation shows menu nesting levels

---

## New

**Command**: `run /ui/dialogs/mainmenu/menu/scripts/new` | **Shortcut**: **network → new**

## Create Project Folder

**Command**: `dialogs "New Project"` | **Shortcut**: **network → new → project**

## Open

**Command**: `run /ui/dialogs/mainmenu/menu/scripts/open` | **Shortcut**: **app → load**

## Open Recent

**Command**: `run /ui/dialogs/mainmenu/menu/scripts/openrecent`

## Save

**Command**: `run /ui/dialogs/mainmenu/menu/scripts/save` | **Shortcut**: **app → save**

## Save As

**Command**: toewrite -a | **Shortcut**: **app → saveas**

## Quit TouchDesigner

**Command**: quit | **Shortcut**: **app → quit**

## Undo

**Command**: undo -u | **Shortcut**: **app → undo**

## Redo

**Command**: undo -r | **Shortcut**: **app → redo**

## Preferences

**Command**: `dialogs preferences` | **Shortcut**: **network → edit → prefs**

## TouchDesigner Help

**Command**: help -d Main_Page

## About TouchDesigner

**Command**: `dialogs "Version"` | **Shortcut**: **network → show → version**

## Additional Menu Items

## Beat

**Command**: `dialogs beat`

## Console

**Command**: `dialogs console` | **Shortcut**: **network → console**

## Errors

**Command**: `dialogs errors`

## Explorer

**Command**: `dialogs explorer` | **Shortcut**: **network → explorer**

## Export Movie

**Command**: `dialogs "Export Movie"` | **Shortcut**: **network → export → movie**

## Finder

**Command**: `dialogs explorer` | **Shortcut**: **network → explorer**

## TouchDesigner Forums

**Command**: viewfile <https://forum.derivative.ca/>

## Import File

**Command**: `dialogs "Import File"` | **Shortcut**: **network → import → file**

## Key Manager

**Command**: `dialogs key` | **Shortcut**: **network → license → manager**

## Learn TouchDesigner

**Command**: help -d Learn_TouchDesigner

## MIDI Device Mapper

**Command**: `dialogs midi` | **Shortcut**: **network → midimapper**

## Offline Help

**Command**: `viewfile "$TFS/Samples/Learn/offlineHelp/https.docs.derivative.ca/Main_Page.htm"`

## Operator Help

**Command**: help -d Operator

## Operator Snippets

**Command**: `dialogs Snippets`

## Palette Browser

**Command**: `dialogs palette` | **Shortcut**: **network → palette → browse**

## Performance Monitor

**Command**: `dialogs performance` | **Shortcut**: **app → performance**

## Project Privacy... (Pro Only)

**Command**: `dialogs privacy`

## Python Examples

**Command**: `viewfile "$TFS/Samples/Learn/PythonExamples.toe"`

## Python Help

**Command**: help -d Introduction_to_Python

## Release Notes

**Command**: help -d Release_Notes

## Browse Samples

**Command**: `viewfile "$TFS/Samples"`

## Search/Replace

**Command**: `dialogs search` | **Shortcut**: **network → search**

## Auto Set DAT Language

**Command**: `run /ui/dialogs/mainmenu/menu/scripts/setdatlang` | **Shortcut**: **network → edit → setdatlang**

## Textport and DATs

**Command**: `dialogs textport` | **Shortcut**: **app → textport**

## Troubleshooting

**Command**: help -d Troubleshooting

## Variables/Macros

**Command**: controlpanel -f -o /ui/dialogs/dialog_legacy

## Window Placement

**Command**: `dialogs window` | **Shortcut**: **network → winplacement**

---

## Summary

This menu reference contains all available TouchDesigner menu items with their associated commands and keyboard shortcuts.

### Command Types

- **File operations**: New, Open, Save, Import, Export
- **Edit operations**: Cut, Copy, Paste, Delete, Duplicate
- **Navigation**: Window management and viewport controls
- **Playback**: Timeline and performance controls
- **System**: Preferences, Help, and utility functions

### Notes

- Menu structure may vary slightly between TouchDesigner versions
- Some menu items may be context-sensitive and only appear in certain situations
- Commands shown are the internal TouchDesigner script commands
- Shortcuts use TouchDesigner's internal naming convention

---

*Generated from TouchDesignerMenus.json*
