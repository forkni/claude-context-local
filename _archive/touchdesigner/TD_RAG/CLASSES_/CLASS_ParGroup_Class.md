---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- Script_CHOP
- Script_TOP
- Script_SOP
- Base_COMP
concepts:
- parameter_management
- operator_control
- python_scripting
- data_binding
- custom_parameters
- sequential_parameters
- parameter_modes
- parameter_groups
- multi_value_parameters
prerequisites:
- Python_fundamentals
- CLASS_Par_Class
- CLASS_OP_Class
- parameter_basics
workflows:
- component_building
- tool_development
- dynamic_parameter_control
- ui_creation
- custom_operator_development
- automated_parameter_management
keywords:
- parameter group class
- tuplet
- multi-value parameter
- parameter scripting
- custom parameter
- parameter binding
- parameter modes
- parameter evaluation
- sequence parameters
- XYZ
- RGBA
- UVW
- eval()
- val
- expr
- mode
- binding
- export
- copy()
- destroy()
tags:
- python
- api_reference
- parameter
- scripting
- core
- group
- tuplet
- multi_value
- binding
- evaluation
relationships:
  CLASS_Par_Class: strong
  CLASS_OP_Class: strong
  CLASS_Page_Class: strong
  CLASS_Sequence_Class: medium
  PY_Python_Tips: medium
related_docs:
- CLASS_Par_Class
- CLASS_OP_Class
- CLASS_Page_Class
- CLASS_Sequence_Class
- PY_Python_Tips
hierarchy:
  secondary: parameter_system
  tertiary: parameter_group_class
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- component_building
- tool_development
- dynamic_parameter_control
- ui_creation
---

# ParGroup Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [Script_CHOP, Script_TOP, Script_SOP, Base_COMP]
concepts: [parameter_management, operator_control, python_scripting, data_binding, custom_parameters, sequential_parameters, parameter_modes, parameter_groups, multi_value_parameters]
prerequisites: [Python_fundamentals, CLASS_Par_Class, CLASS_OP_Class, parameter_basics]
workflows: [component_building, tool_development, dynamic_parameter_control, ui_creation, custom_operator_development, automated_parameter_management]
related: [CLASS_Par_Class, CLASS_OP_Class, CLASS_Page_Class, CLASS_Sequence_Class, PY_Python_Tips]
relationships: {
  "CLASS_Par_Class": "strong",
  "CLASS_OP_Class": "strong",
  "CLASS_Page_Class": "strong",
  "CLASS_Sequence_Class": "medium",
  "PY_Python_Tips": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "parameter_system"
  tertiary: "parameter_group_class"
keywords: [parameter group class, tuplet, multi-value parameter, parameter scripting, custom parameter, parameter binding, parameter modes, parameter evaluation, sequence parameters, XYZ, RGBA, UVW, eval(), val, expr, mode, binding, export, copy(), destroy()]
tags: [python, api_reference, parameter, scripting, core, group, tuplet, multi_value, binding, evaluation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: component_building, tool_development, dynamic_parameter_control

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Class Par Class] → [Class Op Class]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Par Class] → [CLASS OP Class] → [CLASS Page Class]

**Related Topics**: component building, tool development, dynamic parameter control

## Summary

Parameter group class for managing multi-value parameters like XYZ, RGBA coordinates. Essential for parameter scripting and custom component development.This class inherits from the Par class. It references a specific ParGroup.

## Relationship Justification

Core parameter system class working closely with Par and OP classes. Connected to Page class for parameter organization and Sequence class for sequential parameters. Links to Python Tips for practical parameter manipulation examples.

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [Binding Properties](#binding-properties)
    - [bindExpr](#bindexpr)
    - [bindMaster](#bindmaster)
    - [bindRange](#bindrange)
    - [bindReferences](#bindreferences)
  - [Clamping Properties](#clamping-properties)
    - [clampMax](#clampmax)
    - [clampMin](#clampmin)
  - [Collapsing Properties](#collapsing-properties)
    - [collapsable](#collapsable)
    - [collapser](#collapser)
  - [Default Properties](#default-properties)
    - [default](#default)
    - [defaultExpr](#defaultexpr)
    - [defaultBindExpr](#defaultbindexpr)
    - [defaultMode](#defaultmode)
  - [Enable Properties](#enable-properties)
    - [enable](#enable)
    - [enableExpr](#enableexpr)
  - [Export Properties](#export-properties)
    - [exportOP](#exportop)
    - [exportSource](#exportsource)
  - [Expression Properties](#expression-properties)
    - [expr](#expr)
  - [Help Properties](#help-properties)
    - [help](#help)
  - [State Properties](#state-properties)
    - [isDefault](#isdefault)
    - [isCustom](#iscustom)
    - [isFloat](#isfloat)
    - [isInt](#isint)
    - [isMenu](#ismenu)
    - [isMomentary](#ismomentary)
    - [isNumber](#isnumber)
    - [isOP](#isop)
    - [isPulse](#ispulse)
    - [isPython](#ispython)
    - [isSequence](#issequence)
    - [isString](#isstring)
    - [isToggle](#istoggle)
  - [Display Properties](#display-properties)
    - [label](#label)
  - [Range Properties](#range-properties)
    - [max](#max)
    - [min](#min)
    - [normMax](#normmax)
    - [normMin](#normmin)
    - [normVal](#normval)
  - [Menu Properties](#menu-properties)
    - [menuIndex](#menuindex)
    - [menuLabels](#menulabels)
    - [menuNames](#menunames)
    - [menuSource](#menusource)
  - [Mode Properties](#mode-properties)
    - [mode](#mode)
    - [prevMode](#prevmode)
  - [Name Properties](#name-properties)
    - [name](#name)
    - [baseName](#basename)
  - [Organization Properties](#organization-properties)
    - [order](#order)
    - [owner](#owner)
    - [page](#page)
  - [Security Properties](#security-properties)
    - [password](#password)
    - [readOnly](#readonly)
  - [Section Properties](#section-properties)
    - [startSection](#startsection)
  - [Style Properties](#style-properties)
    - [style](#style)
    - [subLabel](#sublabel)
  - [Value Properties](#value-properties)
    - [val](#val)
    - [valid](#valid)
  - [Index Properties](#index-properties)
    - [index](#index)
  - [Sequence Properties](#sequence-properties)
    - [sequence](#sequence)
    - [sequenceBlock](#sequenceblock)
    - [blockIndex](#blockindex)
    - [sequenceIndex](#sequenceindex)
  - [Size Properties](#size-properties)
    - [size](#size)
- [Methods](#methods)
  - [copy()](#copy)
  - [destroy()](#destroy)
  - [eval()](#eval)
  - [evalExport()](#evalexport)
  - [evalExpression()](#evalexpression)
  - [evalNorm()](#evalnorm)
  - [evalOPs()](#evalops)
  - [pars()](#pars)
  - [reset()](#reset)
  - [isSameParGroup()](#issamepargroup)
- [See Also](#see-also)

## Introduction

The ParGroup class describes an instance of a single ParGroup.

## Members

### Binding Properties

#### bindExpr

bindExpr → tuple[str, ...]:

Get or set expressions that return a [CLASS_Parameter] object. This can be used to bind this parameter's constant values to the referenced parameters.

Example:

```python
p.bindExpr = ("op('geo1').par.tx", "op('geo1').par.ty", "op('geo1').par.tz")
```

**Note:** The outside quotes, as bindExpr is an expression, not an object.

#### bindMaster

bindMaster → tuple (Read Only):

The objects to which this parameter is bound to, possibly None.

#### bindRange

bindRange → bool:

Get or set parameter's range binding state. If True, min, max, clampMin, clampMax, normMin, normMax, normVal values will be based on master bind parameter. Can only be set on Custom Parameters.

#### bindReferences

bindReferences → tuple (Read Only):

The (possibly empty) lists of objects which bind to this parameter.

### Clamping Properties

#### clampMax

clampMax → tuple[float, ...]:

Get or set the parameter's numerical clamping behaviors. If set to clampMax = True, the parameter will clamp on the upper end at the value specified in max. Can only be set on Custom Parameters.

#### clampMin

clampMin → tuple[bool, ...]:

Get or set the parameter's numerical clamping behaviors. If set to clampMin = True, the parameter will clamp on the lower end at the value specified in min. Can only be set on Custom Parameters.

### Collapsing Properties

#### collapsable

collapsable → bool (Read Only):

Returns True if the parameter is collapsable.

#### collapser

collapser → bool (Read Only):

Returns True if the parameter is a parent of collapsable parameters (ie. a collapser).

### Default Properties

#### default

default → tuple:

Get or set the parameter's default values. Can only be set on Custom Parameters.

#### defaultExpr

defaultExpr → tuple[str, ...]:

Get or set the parameter's default expressions. Can only be set on Custom Parameters.

Example:

```python
# value defaults to this expression.
op('base1').parGroup.Size.defaultExpr = ('me.time.frame', 'me.time.frame', 'me.time.frame')
```

#### defaultBindExpr

defaultBindExpr → tuple[str, ...]:

Get or set the parameter's default bind expressions. Can only be set on Custom Parameters.

Example:

```python
# value defaults to this expression.
op('base1').parGroup.Size.defaultBindExpr = ('me.par.tx', 'me.par.ty', 'me.par.tz')
```

#### defaultMode

defaultMode → tuple[[CLASS_ParMode], ...]:

Get or set the parameter's evaluation modes.

```python
op('geo1').parGroup.t.defaultMode = (ParMode.EXPRESSION, ParMode.EXPRESSION, ParMode.EXPRESSION)
```

The modes are one of: ParMode.CONSTANT, ParMode.EXPRESSION, or ParMode.EXPORT, or ParMode.BIND.

See [REF_ParameterDialog] for more information.

### Enable Properties

#### enable

enable → bool:

Get or set the parameter's enable state. Can only be set on Custom Parameters.

#### enableExpr

enableExpr → str:

Get or set an expression that controls the enable state for this parameter group.

```python
p.enableExpr = "me.par.X.menuIndex == 5"
```

**Note:** The outside quotes, as this is an expression, not an object.

### Export Properties

#### exportOP

exportOP → tuple[[CLASS_OP] | None, ...] (Read Only):

The operators exporting to this parameter.

#### exportSource

exportSource → tuple[[CLASS_Cell] | [CLASS_Channel] | None, ...] (Read Only):

Tuple of objects exporting to this parameter. Examples: [CLASS_Cell], [CLASS_Channel] or None.

### Expression Properties

#### expr

expr → tuple[str, ...]:

Get or set the non-evaluated expressions only. To get the parameter's current values, regardless of the Parameter Mode (constant, expression, export or bound), use the eval() method described below.

```python
op('geo1').parGroup.t.expr = ('absTime.frame', 'absTime.frame', 'absTime.frame')  
# set to match current frame
```

When setting this member, the parameter will also be placed in expression mode. See mode member below.

**NOTE:** For convenience, the expression is placed in double-quotes so you can safely put in expressions containing single quotes. 'a' and "a" have the same effect of enclosing strings in python.

### Help Properties

#### help

help → str:

Get or set a custom parameter's help text. To see any parameter's help, rollover the parameter while holding the Alt key.

### State Properties

#### isDefault

isDefault → bool (Read Only):

True when the parameter value, expression and mode are in their default settings.

#### isCustom

isCustom → bool (Read Only):

True for Custom Parameters.

#### isFloat

isFloat → bool (Read Only):

True for floating point numeric parameters.

#### isInt

isInt → bool (Read Only):

True for integer numeric parameters.

#### isMenu

isMenu → bool (Read Only):

True for menu parameters.

#### isMomentary

isMomentary → bool (Read Only):

True for momentary parameters.

#### isNumber

isNumber → bool (Read Only):

True for numeric parameters.

#### isOP

isOP → bool (Read Only):

True for OP parameters.

#### isPulse

isPulse → bool (Read Only):

True for pulse parameters.

#### isPython

isPython → bool (Read Only):

True for python parameters.

#### isSequence

isSequence → bool (Read Only):

True for sequence header parameters.

#### isString

isString → bool (Read Only):

True for string parameters.

#### isToggle

isToggle → bool (Read Only):

True for toggle parameters.

### Display Properties

#### label

label → str:

Get or set the parameter's label.

```python
op('myOperator').parGroup.Custompar.label = 'Translate'
```

Can only be set on Custom Parameters.

### Range Properties

#### max

max → tuple[float, ...]:

Get or set the parameter's numerical maximum values. The parameter's values will be clamped at that maximum if clampMax = True. Can only be set on Custom Parameters.

#### min

min → tuple[float, ...]:

Get or set the parameter's numerical minimum values. The parameter's values will be clamped at that minimum if clampMin = True for the particular Par. Can only be set on Custom Parameters.

#### normMax

normMax → tuple[float, ...]:

Get or set the parameter's maximum slider values if the parameter is a numerical slider. Can only be set on Custom Parameters.

#### normMin

normMin → tuple[float, ...]:

Get or set the parameter's minimum slider values if the parameter is a numerical slider. Can only be set on Custom Parameters.

#### normVal

normVal → tuple[float, ...]:

Get or set the parameter's values as a normalized slider position. Can only be set on Custom Parameters.

### Menu Properties

#### menuIndex

menuIndex → tuple[int, ...]:

Get or set a tuple of menu constant values by their indices.

#### menuLabels

menuLabels → tuple[list[str], ...]:

Get or set a tuple of lists of all possible menu choice labels. In the case of non menu parameters, None(s) are returned. Can only be set on Custom Parameters.

#### menuNames

menuNames → tuple[list[str], ...]:

Get or set a tuple of lists of all possible menu choice names. In the case of non menu parameters, None(s) are returned. Can only be set on Custom Parameters.

#### menuSource

menuSource → tuple[str, ...]:

Get or set a tuple of expressions that returns objects with .menuItems .menuNames members. This can be used to create a custom menu whose entries dynamically follow that of another menu for example.

### Mode Properties

#### mode

mode → tuple[[CLASS_ParMode], ...]:

Get or set the parameter's evaluation modes.

```python
op('geo1').parGroup.t.mode = (ParMode.EXPRESSION, ParMode.EXPRESSION, ParMode.EXPRESSION)
```

The modes are one of: ParMode.CONSTANT, ParMode.EXPRESSION, or ParMode.EXPORT, or ParMode.BIND.

See [REF_ParameterDialog] for more information.

#### prevMode

prevMode → tuple (Read Only):

The parameter's previous evaluation modes.

### Name Properties

#### name

name → str:

Get or set the parameter's unique name.

```python
op('myOperator').parGroup.Custompar.name = 'Translate'
```

Can only be set on Custom Parameters.

#### baseName

baseName → str:

Get or set the parameter's base name. This excludes any sequence prefixes, sequence indices or name suffixes. Can only be set on Custom Parameters.

### Organization Properties

#### order

order → int:

Get or set the parameter's position on the parameter page. Can only be set on Custom Parameters.

#### owner

owner → [CLASS_OP] (Read Only):

The [CLASS_OP] to which this object belongs.

#### page

page → [CLASS_Page]:

Get or set the parameter page the custom parameter is part of. Can only be set on Custom Parameters.

### Security Properties

#### password

password → bool:

Get or set the parameter's password mode. When True all text is rendered as asterisks. Can only be set on Custom string, int or float parameters. Custom Parameters.

#### readOnly

readOnly → bool:

Get or set the parameter's read only status. When True the parameter cannot be modified through the UI, only scripting.

### Section Properties

#### startSection

startSection → bool:

Get or set the parameter's separator status. When True a visible separator is drawn between this parameter and the ones preceding it. Can only be set on Custom Parameters.

### Style Properties

#### style

style → str (Read Only):

Describes the behavior and contents of the custom parameter. Example 'Float', 'Int', 'Pulse', 'XYZ', etc.

#### subLabel

subLabel → tuple (Read Only):

Returns the names of the sub-label.

### Value Properties

#### val

val → tuple:

Get or set the constant values of the parameter only. To get the parameter's current values, regardless of the Parameter Modes (constant, expression, export or bound), use the eval() method described below.

```python
op('geo1').parGroup.t.val   # the constant values 
op('geo1').parGroup.t.eval()   # the evaluated parameter
op('geo1').parGroup.t.val = (1,2,3)
op('geo1').parGroup.t = (1,2,3)  #equivalent to above, more concise form
```

When setting this member, the parameter will also be placed in constant mode. See mode member below.

To set a menu value by its index, use the menuIndex member as described below.

#### valid

valid → bool (Read Only):

True if the referenced parameter currently exists, False if it has been deleted.

### Index Properties

#### index

index → int (Read Only):

The parameter's order in the list.

### Sequence Properties

#### sequence

sequence → [CLASS_Sequence] | None (Read Only):

The [CLASS_Sequence] this parGroup is a part of. None if not in a sequence.

#### sequenceBlock

sequenceBlock → [CLASS_SequenceBlock] | None (Read Only):

The [CLASS_SequenceBlock] this parGroup belongs to. None if not in a sequence.

#### blockIndex

blockIndex → int (Read Only):

The index of the parGroup within its [CLASS_SequenceBlock]. None if not in a sequence.

#### sequenceIndex

sequenceIndex → int (Read Only):

The index of the parGroup's [CLASS_SequenceBlock] in its [CLASS_Sequence]. None if not in a sequence.

### Size Properties

#### size

size → int:

Get or set the parameter's vector size.

## Methods

### copy()

copy(ParGroup)→ None:

Copy the specified parameter.

- `ParGroup` - The parameter to copy.

```python
op('geo1').parGroup.t.copy( op('geo2').parGroup.t )
```

### destroy()

destroy()→ None:

Destroy the parameter referenced by this ParGroup. An exception will be raised if the parameter has already been destroyed. Only custom and sequential parameters can be destroyed. Destroying a sequential parameter will destroy its entire block. Note: When any parameter is destroyed, any existing parameter objects will be invalid and should be re-fetched.

### eval()

eval()→ tuple:

Evaluate a parameter group. This value may be derived by the parameter group's constant value, expression, or export, dependent on its mode.

```python
a = op('geo1').parGroup.t.eval()
```

### evalExport()

evalExport()→ tuple:

Evaluate the export portions of a parameter, if it contains any. This will ignore any expressions, etc.

```python
a = op('geo1').parGroup.t.evalExport()
```

### evalExpression()

evalExpression()→ tuple:

Evaluate the expression portions of a parameter, if it contains any. This will ignore any exports, etc.

```python
a = op('geo1').parGroup.t.evalExpression()
```

To evaluate an arbitrary expression string, that is not inside a parameter, see [CLASS_OP].evalExpression.

### evalNorm()

evalNorm()→ tuple[float, ...]:

Similar to eval() but the returns the normalized slider values.

### evalOPs()

evalOPs()→ tuple[list[op], ...]:

Evaluate each parameter as a series of operators. This is useful for a custom parameter that specifies a list of operator paths for example.

```python
a = op('base1').parGroup.Paths.evalOPs()
```

### pars()

pars(pattern)→ list:

Returns a (possibly empty) list of parameter objects that match the pattern.

- `pattern` - Is a string following the [REF_PatternMatching] rules, specifying which parameters to return.

```python
# translate parameters
newlist = op('geo1').parGroup.t.pars('t?')
```

### reset()

reset()→ bool:

Resets the parameter group to its default state.

Returns true if anything was changed.

```python
op('geo1').parGroup.t.reset()
```

### isSameParGroup()

isSameParGroup(parGroup : ParGroup)→ bool:

True if the provided parGroup is the same ParGroup on the same operator. Because `op('container1').parGroup.x == op('container2').parGroup.x` compares values and `op('container1').parGroup.x is op('container1').parGroup.x` is always False (because of TouchDesigner internals), you must use isSameParGroup to compare ParGroup objects.

- `parGroup` - The ParGroup to compare identity with.

## See Also

See also [REF_CustomParameters].
