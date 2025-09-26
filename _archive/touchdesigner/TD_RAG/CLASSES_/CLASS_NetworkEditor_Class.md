---
title: "CLASS_NetworkEditor_Class"
category: CLASS
document_type: reference
difficulty: intermediate
# Enhanced metadata
user_personas: ["script_developer", "intermediate_user", "automation_specialist"]
completion_signals: ["can_access_class_properties", "understands_class_management", "can_implement_class_functionality"]

time_estimate: 10-15 minutes
operators:
- Container_COMP
- Panel_COMP
concepts:
- ui_management
- network_navigation
- pane_control
- operator_placement
- view_control
- interface_customization
- backdrop_display
- network_overview
- programmatic_ui_control
prerequisites:
- Python_fundamentals
- CLASS_UI_Class
- CLASS_Pane_Class
- operator_fundamentals
workflows:
- network_navigation
- operator_placement
- ui_customization
- view_management
- network_organization
- backdrop_control
- tool_development
- automated_workflows
keywords:
- network editor class
- ui control
- pane management
- operator placement
- backdrop display
- zoom control
- view navigation
- network editor interface
- operator linking
- parameter display
- home()
- placeOPs()
- fitWidth()
- fitHeight()
tags:
- python
- api_reference
- ui_interface
- pane_subclass
- network_navigation
- view_control
- operator_management
- automation
relationships:
  CLASS_Pane_Class: strong
  CLASS_UI_Class: strong
  MODULE_td_Module: medium
  PY_Python_Tips: medium
related_docs:
- CLASS_Pane_Class
- CLASS_UI_Class
- MODULE_td_Module
- PY_Python_Tips
hierarchy:
  secondary: ui_control
  tertiary: network_editor
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- network_navigation
- operator_placement
- ui_customization
- view_management
---

# NetworkEditor Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Container_COMP, Panel_COMP]
concepts: [ui_management, network_navigation, pane_control, operator_placement, view_control, interface_customization, backdrop_display, network_overview, programmatic_ui_control]
prerequisites: [Python_fundamentals, CLASS_UI_Class, CLASS_Pane_Class, operator_fundamentals]
workflows: [network_navigation, operator_placement, ui_customization, view_management, network_organization, backdrop_control, tool_development, automated_workflows]
related: [CLASS_Pane_Class, CLASS_UI_Class, MODULE_td_Module, PY_Python_Tips]
relationships: {
  "CLASS_Pane_Class": "strong",
  "CLASS_UI_Class": "strong",
  "MODULE_td_Module": "medium",
  "PY_Python_Tips": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "ui_control"
  tertiary: "network_editor"
keywords: [network editor class, ui control, pane management, operator placement, backdrop display, zoom control, view navigation, network editor interface, operator linking, parameter display, home(), placeOPs(), fitWidth(), fitHeight()]
tags: [python, api_reference, ui_interface, pane_subclass, network_navigation, view_control, operator_management, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: network_navigation, operator_placement, ui_customization

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Class Ui Class] → [Class Pane Class]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Pane Class] → [CLASS UI Class] → [MODULE td Module]

**Related Topics**: network navigation, operator placement, ui customization

## Summary

NetworkEditor class provides access to Network Editor object, which allows network navigation and operator placement. It can be accessed with the `networkeditor` object, found in the automatically imported [PY_td] module. Alternatively, one can use the regular python statement: `import`. Use of the `import` statement is limited to modules in the search path, where as the `mod` format allows complete statements in one line, which is more useful for entering expressions. Also note that [CLASS_DAT] modules cannot be organized into packages as regular file system based python modules can be.

## Relationship Justification

Inherits from Pane class and accessed through UI class. Connected to td module for operator referencing patterns and Python Tips for common UI automation examples. Essential for programmatic network management.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods Overview](#methods-overview)
  - [fitWidth()](#fitwidth)
  - [fitHeight()](#fitheight)
  - [home()](#home)
  - [homeSelected()](#homeselected)
  - [placeOPs()](#placeops)

## Introduction

The NetworkEditor class describes an instance of a Network Editor. They are subclasses of the [CLASS_Pane_Class](CLASS_Pane_Class.md), which can be accessed from the [CLASS_UI_Class](CLASS_UI_Class.md) object.

## Members

`showBackdropCHOPs` → `bool`:
Enable or disable CHOP viewers as backdrops.

`showBackdropGeometry` → `bool`:
Enable or disable SOP and Geometry object viewers as backdrops.

`showBackdropTOPs` → `bool`:
Enable or disable TOP viewers as backdrops.

`showColorPalette` → `bool`:
Enable or disable display of the operator color palette selector.

`showDataLinks` → `bool`:
Enable or disable disable of operator data links.

`showList` → `bool`:
Control display of operators as a list, or connected nodes.

`showNetworkOverview` → `bool`:
Enable or disable display of the network overview.

`showParameters` → `bool`:
Enable or disable display of the currently selected operator parameters.

`straightLinks` → `bool`:
Control display of operator links as straight or curved.

`x` → `float`:
Get or set the x coordinate of the network editor area, where 1 unit = 1 pixel when zoom = 1.

`y` → `float`:
Get or set the y coordinate of the network editor area, where 1 unit = 1 pixel when zoom = 1.

`zoom` → `float`:
Get or set the zoom factor of the network editor area, where a zoom factor of 1 draws each node at its unscaled resolution.

## Methods Overview

### fitWidth()

fitWidth(width)→ `None`:

Fit the network area to specified width, specified in node units. This affects the zoom factor.

- `width` - The width to fit to.

### fitHeight()

fitHeight(height)→ `None`:

Fit the network area to specified height, specified in node units. This affects the zoom factor.

- `height` - The height to fit to.

### home()

home(zoom=True, op=None)→ `None`:

Home all operators in the network.

- `zoom` - (Keyword, Optional) When true, the view will be scaled accordingly, otherwise the nodes will only be re-centered.
- `op` - (Keyword, Optional) If an operator is specified, the network will be homed around its location.

```python
p = ui.panes['pane1']
n = op('/project1')
p.home(op=n)
p = ui.panes[2]
p.home(zoom=True)
```

### homeSelected()

homeSelected(zoom=True)→ `None`:

Home all selected operators in the network.

- `zoom` - (Keyword, Optional) When true, the view will be scaled accordingly, otherwise the nodes will only be re-centered.

### placeOPs()

placeOPs(listOfOPs, inputIndex=None, outputIndex=None, delOP=None, undoName='Operators')→ `None`:

Use the mouse to place the specified operators in the pane.

- `listOfOps` - The list of operators to be placed.
- `inputIndex` - If specified, which input index to connect to.
- `outputIndex` - If specified, which output index to connect to.
- `delOP` - If specified, deletes that operator immediately after placing the listOfOPs.
- `undoName` - Describes the Undo operation.
