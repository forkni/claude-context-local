---
category: REF
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators:
- Script_TOP
- Script_CHOP
- Script_SOP
- Script_DAT
- Parameter_CHOP
- Parameter_Execute_DAT
concepts:
- parameter_modes
- parameter_evaluation
- parameter_types
- python_expressions
- chop_exports
- parameter_binding
- operator_control
- parameter_attributes
prerequisites:
- operator_basics
- python_fundamentals
workflows:
- operator_customization
- procedural_control
- data_binding
- expression_creation
- parameter_automation
keywords:
- parameter
- mode
- constant
- expression
- export
- bind
- evaluated
- custom parameter
- par.eval()
- parameter attributes
- parameter types
- menu
- toggle
- string
- python object
tags:
- parameters
- scripting
- ui
- expressions
- binding
- export
- core
- fundamental
relationships:
  CLASS_Par_Class: strong
  PY_Custom_Parameters: strong
  CLASS_Page_Class: strong
  UI_ComponentEditorDialog: medium
  CLASS_ParGroup_Class: medium
related_docs:
- PY_Custom_Parameters
- CLASS_Par_Class
- CLASS_Page_Class
- UI_ComponentEditorDialog
- CLASS_ParGroup_Class
hierarchy:
  secondary: operator_control
  tertiary: parameter_basics
question_patterns: []
common_use_cases:
- operator_customization
- procedural_control
- data_binding
- expression_creation
---


# Parameter

<!-- TD-META
category: REF
document_type: guide
operators: [Script_TOP, Script_CHOP, Script_SOP, Script_DAT, Parameter_CHOP, Parameter_Execute_DAT]
concepts: [parameter_modes, parameter_evaluation, parameter_types, python_expressions, chop_exports, parameter_binding, operator_control, parameter_attributes]
prerequisites: [operator_basics, python_fundamentals]
workflows: [operator_customization, procedural_control, data_binding, expression_creation, parameter_automation]
related: [PY_Custom_Parameters, CLASS_Par_Class, CLASS_Page_Class, UI_ComponentEditorDialog, CLASS_ParGroup_Class]
relationships: {
  "CLASS_Par_Class": "strong",
  "PY_Custom_Parameters": "strong",
  "CLASS_Page_Class": "strong",
  "UI_ComponentEditorDialog": "medium",
  "CLASS_ParGroup_Class": "medium"
}
hierarchy:
  primary: "fundamentals"
  secondary: "operator_control"
  tertiary: "parameter_basics"
keywords: [parameter, mode, constant, expression, export, bind, evaluated, custom parameter, par.eval(), parameter attributes, parameter types, menu, toggle, string, python object]
tags: [parameters, scripting, ui, expressions, binding, export, core, fundamental]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical guide for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: operator_customization, procedural_control, data_binding

## 🔗 Learning Path

**Prerequisites**: [Operator Basics] → [Python Fundamentals]
**This document**: REF reference/guide
**Next steps**: [PY Custom Parameters] → [CLASS Par Class] → [CLASS Page Class]

**Related Topics**: operator customization, procedural control, data binding

## 🎯 Quick Reference

**Purpose**: Technical guide for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: operator_customization, procedural_control, data_binding

## 🔗 Learning Path

**Prerequisites**: [Operator Basics] → [Python Fundamentals]
**This document**: REF reference/guide
**Next steps**: [PY Custom Parameters] → [CLASS Par Class] → [CLASS Page Class]

**Related Topics**: operator customization, procedural control, data binding

## Summary

Fundamental guide to TouchDesigner parameters covering parameter types, modes, evaluation, and custom parameter basics. Core reference for understanding operator control.

## Relationship Justification

Core parameter concepts that connect strongly to Par class and Custom Parameters. Essential foundation for all parameter-related workflows in TouchDesigner.

## Content

- [Introduction](#introduction)
- [Parameter Types](#parameter-types)
- [Parameter Modes and Evaluation](#parameter-modes-and-evaluation)
- [Parameter Attributes](#parameter-attributes)
- [Custom Parameters](#custom-parameters)
- [Internal Parameters](#internal-parameters)
- [Sequential Parameters](#sequential-parameters)
- [See Also](#see-also)

## Introduction

Every operator in TouchDesigner has a set of control Parameters that can be integer or floating point numbers, menus, binary toggles, text strings or operator paths, which determine the output of the operator.

The parameter dialog is normally at the top-right of the network editor. Pressing 'p' turns off and on the parameter dialog. The parameter dialog for any operator can be opened by right-clicking on the operator and selecting "Parameters...".

Parameters in TouchDesigner only exist in Operators (OPs or "nodes").

## Parameter Types

Parameter types include:

- numbers, both integer and floating point
- number pairs, triples or quadruples (e.g. width and height, XYZ position, RGBA color)
- on-off flags (toggles)
- menus
- text strings
- paths to other nodes in TouchDesigner networks
- "pulse" buttons that initiate actions like running scripts
- python objects - any python object that you can make using numbers, True/False values, strings, lists and dictionaries. The python object has to be self-contained - it cannot refer to other operators or parameters, for example.

See the [REF_ComponentEditor] to create custom parameters and see the range of parameter types that are available.

## Parameter Modes and Evaluation

Every Parameter can be in one of four modes: Constant Mode, Expression Mode, Export Mode or Bind (Binding) Mode. An "**evaluated parameter**" is resulting value of the parameter based on its mode, expressions, exports or binds.

Parameters can be driven by Python expressions when the Parameter Mode is in Expression Mode.

**TIP**: Pressing ctrl-e/Cmd+e with the cursor in a parameter brings up the current parameter's expression in your text editor, making it easier to see and edit long expressions.

Parameters can be driven by [CLASS_CHOP]s by Exporting CHOP channels to a parameter, putting the parameter in Export Mode. In the example Parameter Dialog below, the Y-Translate parameter is being controlled via a CHOP channel export. This is indicated by the green color of the parameter in the dialog (think green for CHOPs!).

Parameters can be bi-directionally synced to other parameters and CHOP channels using Binding. The parameter will go into Bind Mode.

**IMPORTANT**: `op('pattern1').par.phase` is the python parameter object which usually gets converted to an evaluated value for you, like when you use it in a parameter expression. More safely, especially when using a parameter in scripts, use `op('pattern1').par.phase.eval()`, which always gives you the final evaluated value.

## Parameter Attributes

Parameters have numerous other attributes, some are parameter type-dependent.

- name (internal python name you see when you roll over the parameter)
- label
- default value
- minimum, maximum, clamp low, clamp high, clamp low value, clamp high value (for integers and floats)
- menu entries
- enable flag and enable expression (determines if you can access the parameter - usually means it it not relevant in the current state of other parameters)
- read-only - the parameter is active and evaluating but you can't hand-edit it until you turn off read-only
- section divider - in UI a line appears after the prior parameters

## Custom Parameters

Custom Parameters are user created parameters which can be added to Components, Custom Operators, and Script Operators ([CLASS_ScriptTOP](CLASS_Script_TOP.md) / [CLASS_ScriptCHOP](CLASS_Script_CHOP.md) / [CLASS_ScriptSOP](CLASS_Script_SOP.md) / [CLASS_ScriptDAT](CLASS_Script_DAT.md)). In the case of Components and Script Operators, you can create/edit/delete them in the [REF_ComponentEditor].

For more information see [REF_CustomParameters].

## Internal Parameters

See [PY_Internal_Parameters](PY_Internal_Parameters.md).

## Sequential Parameters

See [PY_Sequential_Parameters](PY_Sequential_Parameters.md).

## See Also
