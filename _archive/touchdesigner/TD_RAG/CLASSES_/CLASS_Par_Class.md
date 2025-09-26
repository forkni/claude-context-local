---
title: "Par Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "intermediate_user", "automation_specialist", "technical_artist"]
completion_signals: ["can_access_parameter_properties", "understands_parameter_management", "can_implement_parameter_control", "manages_data_binding"]

operators: []
concepts:
- parameter_management
- operator_control
- python_expressions
- data_binding
- chop_exports
- custom_parameters
- parameter_modes
- parameter_evaluation
prerequisites:
- CLASS_OP_Class
- parameter_basics
workflows:
- procedural_animation
- component_building
- interactive_control
- data_driven_networks
- tool_development
- preset_systems
keywords:
- parameter
- par
- mode
- constant
- expression
- export
- bind
- eval
- val
- expr
- custom parameter
- pulse
- reset
- menu
- scripting
- isDefault
- isCustom
tags:
- python
- api
- parameter
- scripting
- core
relationships:
  CLASS_OP_Class: strong
  CLASS_Page_Class: strong
  PY_Custom_Parameters: medium
related_docs:
- CLASS_OP_Class
- CLASS_Page_Class
- PY_Custom_Parameters
# Enhanced search optimization
search_optimization:
  primary_keywords: ["parameter", "par", "value", "expression"]
  semantic_clusters: ["api_programming", "parameter_management", "data_binding"]
  user_intent_mapping:
    beginner: ["what is parameter", "basic parameter access", "how to get parameter value"]
    intermediate: ["parameter methods", "expression evaluation", "parameter modes"]
    advanced: ["custom parameters", "parameter binding", "advanced parameter control"]

hierarchy:
  secondary: operator_control
  tertiary: parameter
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- procedural_animation
- component_building
- interactive_control
- data_driven_networks
---

# Par Class

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: procedural_animation, component_building, interactive_control

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Class Op Class] → [Parameter Basics]
**This document**: CLASS reference/guide
**Next steps**: [CLASS OP Class] → [CLASS Page Class] → [PY Custom Parameters]

**Related Topics**: procedural animation, component building, interactive control

<!-- TD-META
category: CLASS
document_type: reference
operators: []
concepts: [parameter_management, operator_control, python_expressions, data_binding, chop_exports, custom_parameters, parameter_modes, parameter_evaluation]
prerequisites: [CLASS_OP_Class, parameter_basics]
workflows: [procedural_animation, component_building, interactive_control, data_driven_networks, tool_development, preset_systems]
related: [CLASS_OP_Class, CLASS_Page_Class, PY_Custom_Parameters]
relationships: {
  "CLASS_OP_Class": "strong",
  "CLASS_Page_Class": "strong",
  "PY_Custom_Parameters": "medium"
}
hierarchy:
  "primary": "scripting"
  "secondary": "operator_control"
  "tertiary": "parameter"
keywords: [parameter, par, mode, constant, expression, export, bind, eval, val, expr, custom parameter, pulse, reset, menu, scripting, isDefault, isCustom]
tags: [python, api, parameter, scripting, core]
TD-META -->

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [Value and Expression Properties](#value-and-expression-properties)
    - [val](#val)
    - [expr](#expr)
    - [enableExpr](#enableexpr)
  - [Export Properties](#export-properties)
    - [exportOP](#exportop)
    - [exportSource](#exportsource)
  - [Binding Properties](#binding-properties)
    - [bindExpr](#bindexpr)
    - [bindMaster](#bindmaster)
    - [bindReferences](#bindreferences)
    - [bindRange](#bindrange)
  - [Display Properties](#display-properties)
    - [hidden](#hidden)
    - [index](#index)
    - [vecIndex](#vecindex)
    - [name](#name)
    - [label](#label)
    - [subLabel](#sublabel)
    - [startSection](#startsection)
    - [readOnly](#readonly)
    - [help](#help)
  - [Group Properties](#group-properties)
    - [parGroup](#pargroup)
  - [Range Properties](#range-properties)
    - [min](#min)
    - [max](#max)
    - [clampMin](#clampmin)
    - [clampMax](#clampmax)
    - [normMin](#normmin)
    - [normMax](#normmax)
    - [normVal](#normval)
  - [Default Properties](#default-properties)
    - [default](#default)
    - [defaultBindExpr](#defaultbindexpr)
    - [defaultExpr](#defaultexpr)
    - [defaultMode](#defaultmode)
  - [State Properties](#state-properties)
    - [enable](#enable)
    - [order](#order)
    - [page](#page)
    - [password](#password)
    - [mode](#mode)
    - [prevMode](#prevmode)
  - [Menu Properties](#menu-properties)
    - [menuNames](#menunames)
    - [menuLabels](#menulabels)
    - [menuIndex](#menuindex)
    - [menuSource](#menusource)
  - [Validation Properties](#validation-properties)
    - [valid](#valid)
  - [Sequence Properties](#sequence-properties)
    - [sequence](#sequence)
    - [sequenceBlock](#sequenceblock)
  - [Owner Properties](#owner-properties)
    - [owner](#owner)
  - [Style Properties](#style-properties)
    - [styleCloneImmune](#stylecloneimmune)
    - [lastScriptChange](#lastscriptchange)
- [Type Members](#type-members)
  - [isDefault](#isdefault)
  - [isCustom](#iscustom)
  - [isPulse](#ispulse)
  - [isMomentary](#ismomentary)
  - [isMenu](#ismenu)
  - [isNumber](#isnumber)
  - [isFloat](#isfloat)
  - [isInt](#isint)
  - [isOP](#isop)
  - [isPython](#ispython)
  - [isSequence](#issequence)
  - [isString](#isstring)
  - [isToggle](#istoggle)
  - [style](#style)
  - [collapser](#collapser)
  - [collapsable](#collapsable)
- [Menu Parameters](#menu-parameters)
- [Methods](#methods)
  - [copy()](#copy)
  - [eval()](#eval)
  - [evalNorm()](#evalnorm)
  - [evalExpression()](#evalexpression)
  - [evalExport()](#evalexport)
  - [evalOPs()](#evalops)
  - [evalFile()](#evalfile)
  - [pulse()](#pulse)
  - [destroy()](#destroy)
  - [reset()](#reset)
  - [isPar()](#ispar)
- [Casting to a Value](#casting-to-a-value)
- [See Also](#see-also)

## Introduction

The Par class describes an instance of a single Parameter.

## Members

### Value and Expression Properties

#### val

val → Any:

Get or set the constant mode value of the parameter only. **Important:** To get the parameter's current working value, regardless of the Parameter Mode (constant, expression, export or bound), always use the eval() method described below.

```python
op('geo1').par.tx.val   # the constant value 
op('geo1').par.tx.eval()   # the evaluated parameter
op('geo1').par.tx.val = 5
op('geo1').par.tx = 5  # equivalent to above, more concise form
op('parexec1').par.op = [parent(), parent(2)] # you can assign a list of ops to a parameter that allows multiple operators
```

When setting this member, the parameter will also be placed in constant mode. See mode member below.

To set a menu value by its index, use the menuIndex member as described below.

#### expr

expr → str:

Get or set the non-evaluated expression only. To get the parameter's current value, regardless of the Parameter Mode (constant, expression, export or bound), use the eval() method described below.

```python
op('geo1').par.tx.expr = 'absTime.frame'  # set to match current frame
```

When setting this member, the parameter will also be placed in expression mode. See mode member below.

**NOTE:** For convenience, the expression is placed in double-quotes so you can safely put in expressions containing single quotes. 'a' and "a" have the same effect of enclosing strings in python.

#### enableExpr

enableExpr → str:

Get or set an expression that controls the enable state for this parameter.

```python
p.enableExpr = "me.par.X.menuIndex == 5"
# Note the outside quotes, as this is an expression, not an object.
```

### Export Properties

#### exportOP

exportOP → [CLASS_OP] (Read Only):

The operator exporting to this parameter.

#### exportSource

exportSource → [CLASS_Channel] (Read Only):

The object exporting to this parameter. Examples: [CLASS_Cell], [CLASS_Channel] or None.

### Binding Properties

#### bindExpr

bindExpr → str:

Get or set an expression that returns a bindable object. This can be used to bind this parameter's constant value to the referenced object's value.

```python
p.bindExpr = "op('geo1').par.tx"
```

**Note:** The outside quotes, as bindExpr is an expression, not an object.

#### bindMaster

bindMaster → [CLASS_OP] (Read Only):

The object to which this parameter is bound to, possibly None.

#### bindReferences

bindReferences → list (Read Only):

The (possibly empty) list of objects which bind to this parameter.

#### bindRange

bindRange → bool:

Get or set parameter's range binding state. If True, min, max, clampMin, clampMax, normMin, normMax, normVal values will be based on master bind parameter. Can only be set on Custom Parameters.

### Display Properties

#### hidden

hidden → bool (Read Only):

Get the parameter's hidden status. When True the parameter is considered obsolete or irrelevant and should not be modified. They are not shown in the dialog but only maintained for backward compatibility.

#### index

index → int (Read Only):

A unique identifier for the parameter. May change in the case of custom parameters.

#### vecIndex

vecIndex → int (Read Only):

The parameter's vector index. For example, `op('geo1').par.tz` would have a value of 2.

#### name

name → str:

Get or set the parameter's unique name.

```python
op('myOperator').par.Custompar.name = 'Translate'
```

Can only be set on Custom Parameters.

#### label

label → str:

Get or set the parameter's label.

```python
op('myOperator').par.Custompar.label = 'Translate'
```

Can only be set on Custom Parameters.

#### subLabel

subLabel → str (Read Only):

Returns the name of the sub-label.

#### startSection

startSection → bool:

Get or set the parameter's separator status. When True a visible separator is drawn between this parameter and the ones preceding it. Can only be set on Custom Parameters.

#### readOnly

readOnly → bool:

Get or set the parameter's read only status. When True the parameter cannot be modified through the UI, only scripting.

#### help

help → str (Read Only):

Get or set a custom parameter's help text. To see any parameter's help, rollover the parameter while holding the Alt key. For built-in parameters this can be used to get the parameter's help text.

### Group Properties

#### parGroup

parGroup → [CLASS_ParGroup] (Read Only):

The [CLASS_ParGroup] of parameters this parameter belongs to. A ParGroup is a set of parameters sharing one line on a parameter dialog with a common label, example: Translate (x, y, z).

### Range Properties

#### min

min → int:

Get or set the parameter's numerical minimum value. The parameter's value will be clamped at that minimum if clampMin = True. Can only be set on Custom Parameters.

#### max

max → int:

Get or set the parameter's numerical maximum value. The parameter's value will be clamped at that maximum if clampMax = True. Can only be set on Custom Parameters.

#### clampMin

clampMin → bool:

Get or set the parameter's numerical clamping behavior. If set to clampMin = True, the parameter will clamp on the lower end at the value specified in min. Can only be set on Custom Parameters.

#### clampMax

clampMax → bool:

Get or set the parameter's numerical clamping behavior. If set to clampMax = True, the parameter will clamp on the upper end at the value specified in max. Can only be set on Custom Parameters.

#### normMin

normMin → int:

Get or set the parameter's minimum slider value if the parameter is a numerical slider. Can only be set on Custom Parameters.

#### normMax

normMax → int:

Get or set the parameter's maximum slider value if the parameter is a numerical slider. Can only be set on Custom Parameters.

#### normVal

normVal → float:

Get or set the parameter's value as a normalized slider position. Can only be set on Custom Parameters.

### Default Properties

#### default

default → Any:

Get or set the parameter's default value. Can only be set on Custom Parameters.

#### defaultBindExpr

defaultBindExpr → str:

Get or set the parameter's default bind expression. Can only be set on Custom Parameters.

```python
op('base1').par.Size.defaultBindExpr = 'me.par.tx'
```

#### defaultExpr

defaultExpr → str:

Get or set the parameter's default expression. Can only be set on Custom Parameters.

```python
# value defaults to this expression.
op('base1').par.Size.defaultExpr = 'me.time.frame'
```

#### defaultMode

defaultMode → [CLASS_ParMode]:

Get or set the parameter's default evaluation mode.

```python
op('geo1').par.tx.defaultMode = ParMode.EXPRESSION
```

The mode is one of: ParMode.CONSTANT, ParMode.EXPRESSION, or ParMode.EXPORT, or ParMode.BIND.

See [REF_ParameterDialog] for more information.

### State Properties

#### enable

enable → bool:

Get or set the parameter's enable state. Can only be set on Custom Parameters.

#### order

order → float:

Get or set the parameter's position on the parameter page. Can only be set on Custom Parameters.

#### page

page → [CLASS_Page]:

Get or set the parameter page the custom parameter is part of. Can only be set on Custom Parameters.

#### password

password → bool:

Get or set the parameter's password mode. When True all text is rendered as asterisks. Can only be set on Custom string, int or float parameters. Custom Parameters.

#### mode

mode → [CLASS_ParMode]:

Get or set the parameter's evaluation mode.

```python
op('geo1').par.tx.mode = ParMode.EXPRESSION
```

The mode is one of: ParMode.CONSTANT, ParMode.EXPRESSION, or ParMode.EXPORT, or ParMode.BIND.

See [REF_ParameterDialog] for more information.

#### prevMode

prevMode → [CLASS_ParMode] (Read Only):

The parameter's previous evaluation mode.

### Menu Properties

#### menuNames

menuNames → list:

Get or set a list of all possible menu choice names. In the case of non menu parameters, None is returned. Can only be set on Custom Parameters.

#### menuLabels

menuLabels → list:

Get or set a list of all possible menu choice labels. In the case of non menu parameters, None is returned. Can only be set on Custom Parameters.

#### menuIndex

menuIndex → int:

Get or set a menu constant value by its index.

#### menuSource

menuSource → str:

Get or set an expression that returns an object with `.menuItems` `.menuNames` members. This can be used to create a custom menu whose entries dynamically follow that of another menu for example. Simple menu sources include another parameter with a menu c, an object created by [PY_tdu].TableMenu, or an object created by [PY_TDFunctions].parMenu.

```python
p.menuSource = "op('audiodevin1').par.device"
```

**Note:** The outside quotes, as menuSource is an expression, not an object.

### Validation Properties

#### valid

valid → bool (Read Only):

True if the referenced parameter currently exists, False if it has been deleted.

### Sequence Properties

#### sequence

sequence → [CLASS_Sequence] | None (Read Only):

The [CLASS_Sequence] this parameter belongs to. None if not in a sequence.

#### sequenceBlock

sequenceBlock → [CLASS_SequenceBlock] | None (Read Only):

The [CLASS_SequenceBlock] this parameter belongs to. None if not in a sequence.

### Owner Properties

#### owner

owner → [CLASS_OP] (Read Only):

The [CLASS_OP] to which this object belongs.

### Style Properties

#### styleCloneImmune

styleCloneImmune → bool:

Get or set the parameter's style clone immunity. When False, the parameter definition is matched to any matching master parameter its operator is cloned to. When True, it is left unchanged.

#### lastScriptChange

lastScriptChange → tuple (Read Only):

Return information about when this parameter was last modified by a script. Cleared when the parameter is updated via the UI.

```python
>>> op('/level1').par.invert.lastScriptChange
SetInfo(dat=type:textDAT path:/text1, function='<module>', line=1, frame=300061, timeStamp=1613150878)
```

## Type Members

#### isDefault

isDefault → bool (Read Only):

True when the parameter value, expression and mode are in their default settings.

#### isCustom

isCustom → bool (Read Only):

True for Custom Parameters.

#### isPulse

isPulse → bool (Read Only):

True for pulse parameters.

#### isMomentary

isMomentary → bool (Read Only):

True for momentary parameters.

#### isMenu

isMenu → bool (Read Only):

True for menu parameters.

#### isNumber

isNumber → bool (Read Only):

True for numeric parameters.

#### isFloat

isFloat → bool (Read Only):

True for floating point numeric parameters.

#### isInt

isInt → bool (Read Only):

True for integer numeric parameters.

#### isOP

isOP → bool (Read Only):

True for OP parameters.

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

#### style

style → str (Read Only):

Describes the behavior and contents of the custom parameter. Example 'Float', 'Int', 'Pulse', 'XYZ', etc.

#### collapser

collapser → bool (Read Only):

Returns True if the parameter is a parent of collapsable parameters (ie. a collapser).

#### collapsable

collapsable → bool (Read Only):

Returns True if the parameter is collapsable.

## Menu Parameters

Menu parameters can be get or set by specifying either the string value of the menu, or its numeric index. For example, the following are equivalent:

```python
op('geo1').par.xord = 'trs'
op('geo1').par.xord = 5
```

Alternatively, the menu can be accessed more directly:

```python
n = op('geo1')
n.par.xord.menuIndex = 5  # trs
a = n.menuNames[0]  # returns 'srt'
b = n.menuLabels[0] # returns 'Scale Rotate Translate'
```

## Methods

### copy()

copy(Par)→ None:

Copy the specified parameter.

- `Par` - The parameter to copy.

```python
op('geo1').par.tx.copy( op('geo2').par.tx )
```

### eval()

eval()→ Any:

Evaluate a parameter. This value may be derived by the parameter's constant value, expression, export, or bind, dependent on its mode.

```python
a = op('geo1').par.tx.eval()
```

Calling eval on an OP parameter that can hold multiple OPs will return a single OP if there is only 1 result, a list of OPs if there are more than 1, and None if there are no results.

### evalNorm()

evalNorm()→ float:

Similar to eval() but the returns the normalized slider value.

### evalExpression()

evalExpression()→ Any:

Evaluate the expression portion of a parameter, if it contains one. This will ignore any exports, etc.

```python
a = op('geo1').par.tx.evalExpression()
```

**Note:** The results of evalExpression is always the expression's Python return value, which can be slightly different than Par.eval(). For example, in parameters that hold an operator, .eval() will always return an operator if it exists, even if the expression actually returns a string path. The evalExpression function would return the string path.

To evaluate an arbitrary expression string, that is not inside a parameter, see [CLASS_OP].evalExpression.

### evalExport()

evalExport()→ Any:

Evaluate the export portion of a parameter, if it contains one. This will ignore any expressions, etc.

```python
a = op('geo1').par.tx.evalExport()
```

### evalOPs()

evalOPs()→ List[[CLASS_OP]]:

Evaluate the parameter as series of operators. This is useful for a custom parameter that specifies a list of operator paths for example.

```python
a = op('base1').par.Paths.evalOPs()
```

### evalFile()

evalFile()→ [PY_tdu].FileInfo:

Evaluate the parameter as a file path. This returns a FileInfo object with the full path.

```python
a = op('moviefilein1').par.file.evalFile()
print(a.ext)
print(a.baseName)
print(a.exists)
```

### pulse()

pulse(value=1, frames=0, seconds=0)→ None:

Pulsing sets a parameter to the specific value, cooks the operator, then restores the parameter to its previous value.

For pulse type parameters no value or time is specified or used.

- `value` - (Optional) The value to pulse this parameter with, default is 1.
- `frames` - (Optional) Number of frames before restoring the parameter to its original value.
- `seconds` - (Optional) Number of seconds before restoring the parameter to its original value.

```python
op('moviein1').par.reload.pulse(1) # set the reload toggle, then cook
op('glsl1').par.loadvariablenames.pulse() # activate the pulse parameter
op('geo1').par.ty.pulse(2, frames=120) # pulse geometry ty for 120 frames
op('text1').par.text.pulse('GO!', seconds=3) # pulse text TOP string field, for 3 seconds
op('noise').par.type.pulse('random', seconds=0.5) # pulse noise meny type for half a second
```

### destroy()

destroy()→ None:

Destroy the parameter referenced by this Par. An exception will be raised if the parameter has already been destroyed. Only custom and sequential parameters can be destroyed. Destroying a sequential parameter will destroy its entire block. Note: When any parameter is destroyed, any existing parameter objects will be invalid and should be re-fetched.

### reset()

reset()→ bool:

Resets the parameter to its default state.

Returns true if anything was changed.

```python
op('geo1').par.tx.reset()
```

### isPar()

isPar(par : Par)→ bool:

True if the provided Par is the same parameter on the same operator. Because `op('container1').par.x == op('container2').par.x` compares values and `op('container1').par.x is op('container1').par.x` is always False (because of TouchDesigner internals), you must use isPar to compare parameter objects.

- `par` - The parameter to compare identity with.

## Casting to a Value

The Par Class implements all necessary methods to be treated as a number or string, which in this case gets or sets its value. Therefore, an explicit call to eval() or set() is unnecessary when used in a parameter, or in a numeric expression.

For example, the following are equivalent in a parameter:

```python
(float)me.par.tx
me.par.tx.eval()
me.par.tx
```

The following are also equivalent:

```python
me.par.tx.eval() + 1
me.par.tx + 1
```

As are the following:

```python
me.par.tx.val = 3
me.par.tx = 3
```

**Note:** However, you can't use functions belonging to the cast object type without evaluating the parameter:

```python
me.par.tx.hex() # doesn't work
me.par.tx.eval().hex() # works!
```

## See Also

See also
[PY_Custom_Parameters](PY_Custom_Parameters.md).
