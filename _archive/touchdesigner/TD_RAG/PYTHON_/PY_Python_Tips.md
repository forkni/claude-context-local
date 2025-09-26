---
category: PY
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators:
- Execute_DAT
- Geometry_COMP
- Base_COMP
- Pattern_CHOP
- Table_DAT
- Evaluate_DAT
- Script_DAT
- Script_CHOP
concepts:
- python_scripting
- operator_referencing
- parameter_manipulation
- data_access
- operator_creation
- state_management
- time_based_animation
- storage
- quick_reference
prerequisites:
- Python_fundamentals
- MODULE_td_Module
- operator_basics
workflows:
- scripted_automation
- procedural_network_building
- dynamic_parameter_control
- quick_scripting_reference
- learning_python_in_touchdesigner
keywords:
- cheat sheet
- code snippets
- python examples
- how to
- common tasks
- scripting examples
- op manipulation
- parameter expression
- storage
- variables
- CHOP scripting
- DAT scripting
- list comprehension
- quick reference
tags:
- python
- scripting
- expressions
- automation
- cheatsheet
- examples
- quick_reference
- learning
relationships:
  MODULE_td_Module: strong
  PY_Working_with_CHOPs_in_Python: strong
  PY_Working_with_DATs_in_Python: strong
  PY_Working_with_OPs_in_Python: strong
  PY_Python_Reference: medium
related_docs:
- MODULE_td_Module
- PY_Working_with_CHOPs_in_Python
- PY_Working_with_DATs_in_Python
- PY_Working_with_OPs_in_Python
- PY_Python_Reference
hierarchy:
  secondary: quick_reference
  tertiary: code_examples
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- scripted_automation
- procedural_network_building
- dynamic_parameter_control
- quick_scripting_reference
---

# Python Tips

<!-- TD-META
category: PY
document_type: guide
operators: [Execute_DAT, Geometry_COMP, Base_COMP, Pattern_CHOP, Table_DAT, Evaluate_DAT, Script_DAT, Script_CHOP]
concepts: [python_scripting, operator_referencing, parameter_manipulation, data_access, operator_creation, state_management, time_based_animation, storage, quick_reference]
prerequisites: [Python_fundamentals, MODULE_td_Module, operator_basics]
workflows: [scripted_automation, procedural_network_building, dynamic_parameter_control, quick_scripting_reference, learning_python_in_touchdesigner]
related: [MODULE_td_Module, PY_Working_with_CHOPs_in_Python, PY_Working_with_DATs_in_Python, PY_Working_with_OPs_in_Python, PY_Python_Reference]
relationships: {
  "MODULE_td_Module": "strong",
  "PY_Working_with_CHOPs_in_Python": "strong", 
  "PY_Working_with_DATs_in_Python": "strong", 
  "PY_Working_with_OPs_in_Python": "strong",
  "PY_Python_Reference": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "quick_reference"
  tertiary: "code_examples"
keywords: [cheat sheet, code snippets, python examples, how to, common tasks, scripting examples, op manipulation, parameter expression, storage, variables, CHOP scripting, DAT scripting, list comprehension, quick reference]
tags: [python, scripting, expressions, automation, cheatsheet, examples, quick_reference, learning]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: scripted_automation, procedural_network_building, dynamic_parameter_control

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Module Td Module] → [Operator Basics]
**This document**: PY reference/guide
**Next steps**: [MODULE td Module] → [PY Working with CHOPs in Python] → [PY Working with DATs in Python]

**Related Topics**: scripted automation, procedural network building, dynamic parameter control

## Summary

Essential cheat sheet and reference guide containing practical Python code snippets for common TouchDesigner tasks. Serves as a quick reference for experienced users and learning material for beginners.

## Relationship Justification

Strong connection to core td module and practical guides. Added connection to optimized expressions since it provides expression examples. Essential reference for all Python scripting workflows.

## Introduction

How to do some common actions in Python. Also see Help -> Python Examples in the TouchDesigner UI.

## Contents

- [General to all OPs](#general-to-all-ops)
- [Expressions](#expressions)
- [Time](#time)
- [Storage in Python](#storage-in-python)
- [Commands](#commands)
- [Variables](#variables)
- [CHOPs](#chops)
- [Expressions](#expressions)
- [DATs](#dats)
- [Expressions](#expressions)

## General to all OPs

# Expressions

# Python

Getting an OP's path op('sphere1').path
Getting an OP's name op('sphere1').name
Getting an OP's digits op('sphere1').digits
Querying the value of an OP's parameter op('sphere1').par.tx.eval()
or when it's constant op('sphere1').par.tx

Querying a parameter in the same OP me.par.tx
Getting Info CHOP channels from an OP
without cooking it passive(op('moviein1')).width
Getting an OP's parent parent()
Getting an OP's grand-parent parent(2)
Getting an OP's name me.name
Getting an OP's parent's name parent().name
Getting digits of an OP's name from its parameters me.digits
Getting digits of an OP's parent's
name from its parameters parent().digits
Getting an OP's type # returns an OP object, not a string
type(op('moviein1'))
getting a unique random number each frame tdu.rand(absTime.frame+.1)
getting a unique random number per numbered operator tdu.rand(me.digits+.17)
Checking for an OP's existence if op('moviein1'):
or

bool(op('moviein1'))

Getting the number of children of a COMP len(op('geo1').children)
Getting the number of inputs of a multi-input OP len(op('switch1').inputs)
Getting Info CHOP channels from an OP, width is a member op('moviein1').width
Conditional "if" in one line of a parameter 22 if me.time.frame<100 else 33
Conditional "if" alternative [33,22][me.time.frame<100]
Convert space separated string to a list tdu.split('Space separated string with "two word item"')
List comprehension [c.name for c in root.children]
Conditional list comprehension [c.name for c in root.children if c.name != 'perform']
Test operator type type(root) == baseCOMP
Test operator family isinstance(root, TOP)

## Time

"Absolute Time" is the time since you started your TouchDesigner process, not counting when your power button was off (top bar).

# Python

Retrieving a node's local frame number me.time.frame
Retrieving a node's local time in seconds me.time.seconds
Retrieving absolute time in frames absTime.frame
Retrieving absolute time in seconds absTime.seconds

## Storage in Python

Storage is the preferred way to work with persistent global data in Python, since it can store anything data type.

# Python

Setting a value in storage of a component n n.store('keyname', 0.0)
Getting a value from storage n.fetch('keyname')
Directly access the storage dictionary n.storage
Directly access a key in the storage dictionary n.storage['keyname']
Test if a key exists in the storage dictionary 'keyname' in n.storage

## Commands

# Python

Creating an OP (Sphere SOP) op('/project1').create(sphereSOP)
Creating a named OP op('/project1').create(sphereSOP, 'mysphere')
Copying OPs (Nodes) op('/project1').copy(op('out1'), name='out2')
Deleting an OP op('mysphere').destroy()
Renaming an OP op('mysphere').name = 'thesphere'
Changing an OP's type op('mysphere').changeType(boxSOP)
Changing multiple OPs' types list = ops('*sphere*')
[s.changeType(boxSOP) for s in list]
Setting an OP's comment op('mysphere').comment = 'this is a sphere'
Changing an OP's parameter op('mysphere').par.frequency = 10
Changing an OP's parameter
with more than 1 value s = op('mysphere')
s.par.tx = 1
s.par.ty = 2
s.par.tz = 3
Pulsing a parameter value op('moviein1').par.cue.pulse()
Cooking an OP op('mysphere').cook()
Saving an OP's data to a file op('mysphere').save('sphere.tog')
Changing an OP's Render and Display Flags on s = op('mysphere')
s.render = True
s.display = True
Loading a .tox file into a COMP op('/project1').loadTox('geo1.tox')
Wiring operators together Refer to the Connector Class
Clicking gadgets (panel components) op('slider1').click(.6, .7)
Timeline Play/Pause me.time.play = True/False
Run asynchronous or delayed Python code run('print("hello, world")', delayMilliSeconds=2000)

## Variables

Variables are always text strings.

# Python

Setting a value me.var('DESKTOP')
Setting a Root Variable root.setVar('MEDIA', 'c:/MEDIA')
Setting a Component Variable
at the current component parent().setVar('MEDIA', 'c:/MEDIA')
Setting a Component Variable
at another component op('/project1/geo1').setVar('MEDIA', 'c:/MEDIA')
Setting a Path Variable Set the Path Variable parameter of any parent component and use me.var('name') in the same way.

## CHOPs

# Expressions

Evaluate channel chan1 at the current frame op['pattern1']('chan1').eval()
or if in parameter, simply: op['pattern1']('chan1')
Get sample 8 of channel chan1 op['pattern1']('chan1').eval(8)
Get the number of CHOP Channels op('pattern1').numChans
Get the CHOP length op('pattern1').numSamples
Get the third sample from the first channel op['pattern1'][0](2)
Get the name of the 2nd channel op['pattern1'](1).name
Get the channel index of channel chan1 op['pattern1']('chan1').index

## DATs

# Expressions

# See also

[PY_Working_with_OPs_in_Python.md](PY_Working_with_OPs_in_Python.md)

Get a cell value by index op['table1'](2,3)
Get a cell value by label op['table1']('r1', 'c1')
Get a cell value by row index, col label op['table1'](2, 'product')
Cast cell to integer and float int(op['table1']('month', 3))
float(op['table1']('speed', 4))
Get the number of table rows op('table1').numRows
Get the number of table columns op('table1').numCols
Set a cell value by indeces or labels op['table1'](3,4) = 'hello'
op['table1'](2, 'answer') = 'hello'
op['table1']('month', 3) = 'july'
Set a cell value by label op['table1']('r1', 'c1') = 'abc'
Copy a table to another table op('table1').copy(op('fromTable'))
Append a row to a table op('table1').appendRow(['s1','s2', num])
Append a column to a table op('table1').appendCol(['s1','s2', num])
Access current cell in an Evaluate DAT me.inputCell
Access neighboring cells in an Evaluate DAT me.inputCell.offset(1,2)
