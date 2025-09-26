---
title: "Custom Parameters"
category: PY
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes

# Enhanced metadata
user_personas: ["script_developer", "technical_artist", "intermediate_user", "automation_specialist"]
completion_signals: ["can_create_custom_parameters", "understands_parameter_management", "can_implement_ui_customization", "manages_component_interfaces"]

operators:
- Script_SOP
- Script_CHOP
- Script_DAT
- Base_COMP
- Parameter_CHOP
- Parameter_Execute_DAT
concepts:
- custom_parameters
- parameter_management
- component_customization
- ui_design
- operator_scripting
- parameter_modes
- python_expressions
prerequisites:
- Python_fundamentals
- COMP_basics
- CLASS_Page_Class
- CLASS_Par_Class
- parameter_basics
workflows:
- component_building
- ui_design
- tool_creation
- operator_scripting
- preset_systems
- parameter_automation
keywords:
- custom parameter
- add parameter
- parameter page
- customize component
- appendFloat
- appendPulse
- destroyCustomPars
- parameter tuplet
- script op parameters
- component editor
- parameter naming
- parameter attributes
tags:
- python
- parameters
- ui
- scripting
- component
- editor
- customization
relationships:
  PY_Extensions: strong
  CLASS_Page_Class: strong
  CLASS_Par_Class: strong
  UI_ComponentEditorDialog: strong
  REF_Parameter: strong
related_docs:
- PY_Extensions
- CLASS_Page_Class
- CLASS_Par_Class
- UI_ComponentEditorDialog
- REF_Parameter
# Enhanced search optimization
search_optimization:
  primary_keywords: ["custom", "parameter", "ui", "component"]
  semantic_clusters: ["ui_development", "parameter_management", "component_customization"]
  user_intent_mapping:
    beginner: ["what are custom parameters", "basic parameter creation", "how to add parameters"]
    intermediate: ["parameter scripting", "ui customization", "component building"]
    advanced: ["complex parameter systems", "tool development", "advanced ui design"]

hierarchy:
  secondary: component_customization
  tertiary: custom_parameters
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- component_building
- ui_design
- tool_creation
- operator_scripting
---

# Custom Parameters

<!-- TD-META
category: PY
document_type: guide
operators: [Script_SOP, Script_CHOP, Script_DAT, Base_COMP, Parameter_CHOP, Parameter_Execute_DAT]
concepts: [custom_parameters, parameter_management, component_customization, ui_design, operator_scripting, parameter_modes, python_expressions]
prerequisites: [Python_fundamentals, COMP_basics, CLASS_Page_Class, CLASS_Par_Class, parameter_basics]
workflows: [component_building, ui_design, tool_creation, operator_scripting, preset_systems, parameter_automation]
related: [PY_Extensions, CLASS_Page_Class, CLASS_Par_Class, UI_ComponentEditorDialog, REF_Parameter]
relationships: {
  "PY_Extensions": "strong",
  "CLASS_Page_Class": "strong",
  "CLASS_Par_Class": "strong",
  "UI_ComponentEditorDialog": "strong",
  "REF_Parameter": "strong"
}
hierarchy:
  primary: "scripting"
  secondary: "component_customization"
  tertiary: "custom_parameters"
keywords: [custom parameter, add parameter, parameter page, customize component, appendFloat, appendPulse, destroyCustomPars, parameter tuplet, script op parameters, component editor, parameter naming, parameter attributes]
tags: [python, parameters, ui, scripting, component, editor, customization]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: component_building, ui_design, tool_creation

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Comp Basics] → [Class Page Class]
**This document**: PY reference/guide
**Next steps**: [PY Extensions] → [CLASS Page Class] → [CLASS Par Class]

**Related Topics**: component building, ui design, tool creation

## Summary

Comprehensive guide for creating and managing custom parameters on components and script operators. Essential for component building and tool creation workflows.

## Relationship Justification

Strong connection to REF_Parameter as it provides fundamental parameter concepts. Enhanced relationships with Page and Par classes as these are core to parameter creation and management.

## Content

- [Introduction](#introduction)
- [Naming Conventions](#naming-conventions)
- [Creating Custom Parameters on COMPs](#creating-custom-parameters-on-comps)
  - [Quick Start](#quick-start)
  - [Python Implementation](#python-implementation)
  - [Single Parameter Example](#single-parameter-example)
  - [Multi-Value Parameters](#multi-value-parameters)
- [Creating Custom Parameters on Script OPs](#creating-custom-parameters-on-script-ops)
- [Accessing Custom Parameters on Script OPs](#accessing-custom-parameters-on-script-ops)
  - [Button Parameters](#button-parameters)
  - [Slider Parameters](#slider-parameters)
- [Editing Custom Parameters](#editing-custom-parameters)
- [Deleting Custom Parameters](#deleting-custom-parameters)
- [Enabling and Disabling Custom Parameters](#enabling-and-disabling-custom-parameters)
- [Sorting Custom Parameters](#sorting-custom-parameters)
- [Moving Parameters between Pages](#moving-parameters-between-pages)
- [Deleting Custom Parameter Pages](#deleting-custom-parameter-pages)
- [Reordering Custom Parameter Pages](#reordering-custom-parameter-pages)
- [List Custom Parameters](#list-custom-parameters)
- [List Custom Parameter Pages](#list-custom-parameter-pages)
- [Access Custom Parameters from Inside Network](#access-custom-parameters-from-inside-network)
- [Using Custom Parameter Values](#using-custom-parameter-values)
- [Custom Parameter in Clones](#custom-parameter-in-clones)
- [References](#references)
- [See Also](#see-also)

## Introduction

Custom parameters enable you to create a variety of parameters on user-defined Parameter Pages of the [UI_ParameterDialog].

You can create custom parameters in three ways:

1. On Components as described below.
2. On script operators like the [CLASS_ScriptSOP], [CLASS_ScriptCHOP] and [CLASS_ScriptDAT], described below.
3. On C++ operators. Please refer to the [REF_WriteCPlusPlusPlugin] page.

The easiest way to see and edit parameters of components is through the [UI_ComponentEditorDialog]: right-click on a component node and select Customize...

## Naming Conventions

A custom parameter is distinguished from a built-in parameter by the capitalization of the first letter of its otherwise lower-case name (example: Divisions) versus all built-in parameters which are fully lowercase (example: brightness), and the custom parameter's appearance under the second row of pages on the [UI_ParametersDialog]. The standard to follow is to capitalize the first letter while having all remaining letters of the name in lower case. If the first letter of the custom parameter is not uppercase, the creation will fail and an error is returned. Also all parameter names contain no underscores.

**Examples:**

- A string parameter for a search term: `Searchterm`
- A distance value: `Distance`

Keep the number of characters in custom parameter names below 12, preferably 10, as they are unreadable if you open up the parameter with the + icon by the parameter name.

Labels for parameters are of the form: "Rotate to X Axis", where words are capitalized except those between nouns, verbs, adjectives, adverbs, such as from, if, and, to.

## Creating Custom Parameters on COMPs

### Quick Start

**QUICK START:** Custom parameters are most easily created and managed using the RMB -> Customize... dialog on any component or Script Operator. First you add a new custom page by providing a page name and pressing Add Page. Then select that page under Pages and enter a parameter name (upper case first letter, lower case remaining characters, no spaces, such as "Speed") and parameter type (such as Float), then click Add Par to create the parameter. Then you can change the label that appears on the parameter dialog, the default value and more. Inside the component you can access the parameter using in this example `parent().par.Speed`.

### Python Implementation

Creating custom parameters on a component is a two-stage process. The first step is creating the parameter. The second step is defining its behavior. Custom Parameters will exist as a part of the Component until they are explicitly deleted, and the code to create them only needs to be run once.

A list of all the available parameter types and their arguments are available at the [CLASS_Page] page.

Internally, custom parameters are created and managed with python functions. What follows is the python equivalent to working with the Customize dialog.

### Single Parameter Example

The following code will create a pulse type button on a Parameter Page called 'Controls' with a scripting name of 'Startsearch' and the label 'Click to Start Search'. The following code can be entered in a [CLASS_TextDAT] in the same Network as a [CLASS_BaseCOMP] named base1 or it can also be entered in the Textport if base1 is created at the root (/) level:

```python
# create a pulse button parameter on the Base COMP node called base1
baseOp = op('base1')
newPage = baseOp.appendCustomPage('Controls')

# create a tuplet containing one pulse parameter
newTuplet = newPage.appendPulse('Startsearch', label='Click to Start Search')
```

A tuplet is a list of related parameters that will appear on one row of the parameter interface. You can interact with the Pulse button above just as you would with any other pulse parameter:

```python
baseOp.par.Startsearch.pulse()
```

The following code will create a float slider type parameter on a Parameter Page called 'Car Controls' with a label of 'Speed of Car' and a scripting name 'Speed'. It will have a slider minimum value of -2 and a maximum value of 2. The parameter will be clamped at a minimum of -10 and a maximum of 10 preventing the entry of lower and higher values. (These values are initially 0 and 1.)

```python
# create a float parameter on the Base COMP node called base1
baseOp = op('base1')
newPage = baseOp.appendCustomPage('Car Controls')
newTuplet = newPage.appendFloat('Speed', label='Speed of Car', size=1)
# get the first (and only) parameter of this tuplet
p = newTuplet[0]

# define attributes of the newly created parameter

# normMin member defines the slider minimum value
p.normMin = -2

# normMax member defines the slider maximum value
p.normMax = 2

# default member defines the default value of the parameter
p.default = 0.1

# min member defines the absolute minimum value of the parameter
# clampMin member prevents lower values than set in min
p.min = -10
p.clampMin = True

# max member defines the absolute maximum value of the parameter
# clampMax member prevents higher values than set in max
p.max = 10
p.clampMax = True
```

### Multi-Value Parameters

You can also create multi-value parameters either by specifying the size keyword for integer or float type parameters. This is useful for creating parameters which, for example, have multiple facets to a single parameter. There are a number of pre-built multi-value parameter types that come with a more convenient naming schemes for regularly used arrays, such as RGB, RGBA, XYZ, and more.

The method to create these parameters will return a tuple of parameter instances which can be used to define the parameters' attributes. In the following example the created parameter names will use the name as specified plus an index indicating the parameters order in the list, here 'Vector1', 'Vector2' and 'Vector3'. The maximum size for any parameter is 4. A for loop is used to iterate through all the vectors and set their parameters quickly.

```python
# create 3 float parameters on the Base COMP node called base1
baseOp = op('base1')
newPage = baseOp.appendCustomPage('Car Controls')
newTuplet = newPage.appendFloat('Vector', label='Movement Vector', size=3)

# define attributes of the newly created parameters
for p in newTuplet:
 # normMin member defines the sliders minimum value
 p.normMin = 0

 # normMax member defines the sliders maximum value
 p.normMax = 1

 # default member defines the default value of the parameter
 p.default = 0.1

 # min member defines the absolute minimum value of the parameter
 # clampMin member prevents lower values than set in min
 p.min = 0
 p.clampMin = True

 # max member defines the absolute maximum value of the parameter
 # clampMax member prevents higher values than set in max
 p.max = 10
 p.clampMax = True
```

For a complete overview of custom parameter types, please refer to the Custom Parameter section of the [CLASS_COMP].

## Creating Custom Parameters on Script OPs

Similar to custom parameters on COMPs, Script OPs like the [CLASS_ScriptCHOP], [CLASS_ScriptSOP] or [CLASS_ScriptDAT] let you define custom parameters via the Script OPs callbacks:

```python
def setupParameters(scriptOp):
 page = scriptOp.appendCustomPage('Custom')
 page.appendFloat('Valuea', label='Value A')
 page.appendFloat('Valueb', label='Value B')
 return
```

After modifying the `setupParameters()` callback function, pulse the Script OPs 'Setup Parameters' parameter to execute the parameter creation.

Custom parameter names must begin with a capital letter, and be followed by lowercase letters, numbers or underscores only.

## Accessing Custom Parameters on Script OPs

### Button Parameters

Parameters in the Script OPs can be accessed a number of ways. The first is to access button type parameters through the `onPulse()` callback. In the example below, the Script OP has two custom pulse buttons. The `onPulse()` callback prints the name of the button that is pressed.

```python
# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def setupParameters(scriptOp):
 page = scriptOp.appendCustomPage('Custom')
 page.appendPulse('Buttona')
 page.appendPulse('Buttonb')
 return

# called whenever custom pulse parameter is pushed
def onPulse(par):
 print(par.name)
 return
```

### Slider Parameters

Accessing the value of sliders is done by calling the parameter by its scripting name. In the example below two sliders are defined, and their values are accessed on every cook by adding the `print()` functions to the `cook()` callback:

```python
# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def setupParameters(scriptOp):
 page = scriptOp.appendCustomPage('Custom')
 page.appendFloat('Slidera')
 page.appendFloat('Sliderb')
 return

def cook(scriptOP):
 scriptOp.clear()
 print(scriptOp.par.Slidera)
 print(scriptOp.par.Sliderb)
 return
```

## Editing Custom Parameters

Custom parameters are instances of the [CLASS_Par] and as such can be modified using the [CLASS_Par] Members.

For example, the following script is used to create 2 float parameter sliders with the labels 'Value0' and 'Value1':

```python
# create 2 float parameters on the Base COMP node called base1
baseOp = op('base1')
newPage = baseOp.appendCustomPage('Custom')
newPar = newPage.appendFloat('Valuea', label='Value A')
newPar = newPage.appendFloat('Valueb', label='Value B')
```

All the attributes of the parameters are editable after the fact by accessing the [CLASS_Par]. For example, the script below changes the labels of the two float parameter sliders to 'Float Slider 1' and 'Float Slider 2':

```python
# edit the labels on the 2 float parameters on the Base COMP node called base1
baseOp = op('base1')
baseOp.par.Valuea.label = 'Float Slider A'
baseOp.par.Valueb.label = 'Float Slider B'
```

The scripting names assigned to the parameters can be changed to 'Floatsliderx' and 'Floatslidery', as well using the script below:

```python
# edit the labels on the 2 float parameters on the Base COMP node called base1
baseOp = op('base1')
baseOp.par.Valuea.name = 'Floatsliderx'
baseOp.par.Valueb.name = 'Floatslidery'
```

## Deleting Custom Parameters

Custom parameters can be removed by calling the parameters `destroy()` method as such:

```python
# this will remove the custom parameter called 'Speed' from the Base COMP 'base1'
baseOp = op('base1')
baseOp.par.Speed.destroy()
```

Or by removing all custom parameters from an Operator:

```python
# this will remove all custom parameters from the Base COMP 'base1'
baseOp = op('base1')
baseOp.destroyCustomPars()
```

## Enabling and Disabling Custom Parameters

Custom Parameters can be set to an Enabled or Disabled state using the following script:

```python
# create a pulse button parameter on the Base COMP node called base1
baseOp = op('base1')
newPage = baseOp.appendCustomPage('Controls')
newPar = newPage.appendPulse('Startsearch', label='Click to start search')

# disable the pulse button
baseOp.par.Startsearch.enable = False

# enable the pulse button
baseOp.par.Startsearch.enable = True
```

You can use a [CLASS_ParameterExecuteDAT] to watch another parameter, and when it changes, alter the enable state of the parameter.

## Sorting Custom Parameters

Custom parameters can be reordered on one Parameter Page as follows:

```python
# assuming the Base COMP 'base1' has 3 custom parameters displayed in this order 'Color', 'Speed', 'Value'
baseOp = op('base1')
page = baseOp.customPages[0]  # assume on first page
page.sort('Speed','Color','Value')
```

If the parameters are not on the same page, the order will not be affected.

## Moving Parameters between Pages

Custom parameters can be moved between Parameter Pages by just assigning a new value to their page member. The moved parameter preserves all of its attributes, including all of its members, such as min, max, and default values. All parameters in a tuplet are displayed on the same page.

```python
# create a parameter on page 'Car Controls'
baseOp = op('base1')
p = baseOp.par.Size
p.page = 'Car Spec'  # other parameters in tuplet will follow.
```

## Deleting Custom Parameter Pages

A custom Parameter Page is deleted when by calling its `destroy()` method directly.

```python
baseOp = op('base1')
page = baseOp.customPages[0]
page.destroy()
```

## Reordering Custom Parameter Pages

Custom Parameter Pages can be reordered by specifying the new order:

```python
baseOp = op('base1')
baseOp.sortCustomPages('Car Controls', 'Car Spec')
```

## List Custom Parameters

A list of all Custom Parameters added to an Operator can be returned using the method `customPars`. The list is ordered by their appearance in the Parameter Dialog:

```python
baseOp = op('base1')
baseOp.customPars
```

## List Custom Parameter Pages

A list of all Custom Parameters Pages added to an Operator can be returned using the method `customPages`. The list is ordered by their appearance in the Parameter Dialog:

```python
baseOp = op('base1')
baseOp.customPages
```

## Access Custom Parameters from Inside Network

When in a component containing custom parameters, right-click on the network and select Open Parent Parameters.

## Using Custom Parameter Values

Once created, Custom Parameters function the same as any built-in parameter of the same type. There are a number of ways to access the values of a parameter, including Custom Parameters.

The first is directly, within a component, with an expression like `parent().par.Length`.

The second is through the use of the [CLASS_ParameterCHOP]. The [CLASS_ParameterCHOP] will fetch custom parameters and standard parameters by category or name patterns from the Component being referenced. This will create a CHOP channel from each parameter selected.

The third method is through the use of the [CLASS_ParameterExecuteDAT]. This DAT provides Python callback functions for the parameters referenced by it.

## Custom Parameter in Clones

We are referring here to parameters on the clones of components that have their Clone parameter set, not parameters inside these clones.

Normally, custom parameter attributes, like label, default value, max/min and menu entries, propagate to all clones. This feature can be turned off by setting a custom parameter's `styleCloneImmune` property to True.

Parameters' current value and their Parameter Mode do not propagate to all clones. They remain unique for each clone, like any other parameter or Flag of the master node.

The parameter order propagates to clones automatically. The page order propagates to clones automatically.

## References

For a list of parameter attributes (members) and settings: [CLASS_Par] Members

For a list of parameter types and their arguments: [CLASS_Page]

**Tip:** See also [REF_InternalParameters].

## See Also

See also [REF_InternalParameters].
