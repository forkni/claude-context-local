---
title: "Page Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "technical_artist", "automation_specialist", "advanced_user"]
completion_signals: ["can_access_page_properties", "understands_custom_parameter_creation", "can_implement_ui_customization", "manages_parameter_organization"]

operators:
- COMP
- Base_COMP
- Script_CHOP
- Script_SOP
- Script_DAT
- Script_TOP
- Parameter_Execute_DAT
- Script_COMP
concepts:
- custom_parameter_creation
- ui_customization
- parameter_management
- component_development
- parameter_organization
- dynamic_interfaces
prerequisites:
- MODULE_td_Module
- parameter_basics
- component_development_basics
workflows:
- component_customization
- custom_tool_development
- dynamic_ui_generation
- operator_interface_design
- tool_development
keywords:
- page
- custom parameter
- append
- parameter page
- ui
- component
- par
- sort
- destroy
- appendFloat
- appendStr
- appendMenu
- dynamic parameters
tags:
- python
- api
- parameter
- custom_ui
- component_development
- tool_development
- interface_design
relationships:
  CLASS_scriptDAT_Class: strong
  MODULE_td_Module: strong
  PY_Python_Reference: medium
related_docs:
- CLASS_scriptDAT_Class
- MODULE_td_Module
- PY_Python_Reference
# Enhanced search optimization
search_optimization:
  primary_keywords: ["page", "parameter", "custom", "ui"]
  semantic_clusters: ["ui_development", "parameter_management", "component_customization"]
  user_intent_mapping:
    beginner: ["what is page class", "basic parameter pages", "how to add parameters"]
    intermediate: ["custom parameters", "ui customization", "parameter organization"]
    advanced: ["dynamic interfaces", "tool development", "advanced parameter control"]

hierarchy:
  secondary: ui_development
  tertiary: parameter_management
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- component_customization
- custom_tool_development
- dynamic_ui_generation
- operator_interface_design
---

# Page Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [COMP, Base_COMP, Script_CHOP, Script_SOP, Script_DAT, Script_TOP, Parameter_Execute_DAT, Script_COMP]
concepts: [custom_parameter_creation, ui_customization, parameter_management, component_development, parameter_organization, dynamic_interfaces]
prerequisites: [MODULE_td_Module, parameter_basics, component_development_basics]
workflows: [component_customization, custom_tool_development, dynamic_ui_generation, operator_interface_design, tool_development]
related: [CLASS_scriptDAT_Class, MODULE_td_Module, PY_Python_Reference]
relationships: {
  "CLASS_scriptDAT_Class": "strong",
  "MODULE_td_Module": "strong",
  "PY_Python_Reference": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "ui_development"
  tertiary: "parameter_management"
keywords: [page, custom parameter, append, parameter page, ui, component, par, sort, destroy, appendFloat, appendStr, appendMenu, dynamic parameters]
tags: [python, api, parameter, custom_ui, component_development, tool_development, interface_design]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: component_customization, custom_tool_development, dynamic_ui_generation

**Common Questions Answered**:
- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Module Td Module] → [Parameter Basics] → [Component Development Basics]
**This document**: CLASS reference/guide
**Next steps**: [CLASS scriptDAT Class] → [MODULE td Module] → [PY Python Reference]

**Related Topics**: component customization, custom tool development, dynamic ui generation
## Summary

API reference for creating and managing custom parameter pages in components. Essential for building custom tools and components with user-friendly interfaces.

## Relationship Justification

Strong connection to Script DAT class since custom parameters are often created in Script DAT callbacks. Links to core td module and Python reference for foundational understanding.

## Overview

The Page Class describes the list of custom parameters contained on a page. Pages are created on components via the COMP Class. See also the guide Custom Parameters.

Methods that create parameters return a ParGroup that was created.

To view individual attributes of each parameter such as default, min, max, etc, see the [CLASS_Par_Class.md](CLASS_Par_Class.md) documentation.

Pages can be accessed like a Python list of parameters:

```python
page = op('button1').pages[0] # get the page object
print(len(page)) # number of parameters on the page 
debug(page[0]) # first parameter on the page
for p in pages:
	debug(m.description) # print all the parameters on the page
```

## Content

- [Members](#members)
- [Methods](#methods)
- [appendOP](#appendop)
- [appendCOMP](#appendcomp)
- [appendObject](#appendobject)
- [appendPanelCOMP](#appendpanelcomp)
- [appendTOP](#appendtop)
- [appendCHOP](#appendchop)
- [appendSOP](#appendsop)
- [appendMAT](#appendmat)
- [appendDAT](#appenddat)
- [appendInt](#appendint)
- [appendFloat](#appendfloat)
- [appendXY](#appendxy)
- [appendXYZ](#appendxyz)
- [appendXYZW](#appendxyzw)
- [appendWH](#appendwh)
- [appendUV](#appenduv)
- [appendUVW](#appenduvw)
- [appendRGB](#appendrgb)
- [appendRGBA](#appendrgba)
- [appendStr](#appendstr)
- [appendStrMenu](#appendstrmenu)
- [appendMenu](#appendmenu)
- [appendFile](#appendfile)
- [appendFileSave](#appendfilesave)
- [appendFolder](#appendfolder)
- [appendPulse](#appendpulse)
- [appendMomentary](#appendmomentary)
- [appendToggle](#appendtoggle)
- [appendPython](#appendpython)
- [appendPar](#appendpar)
- [appendHeader](#appendheader)
- [appendSequence](#appendsequence)
- [destroy](#destroy)
- [sort](#sort)
- [resetPars](#resetpars)




## Members

name → bool :

Get or set the name of the page.

owner → OP (Read Only):

The OP to which this object belongs.

parGroups → list (Read Only):

- A list of parameter groups on this page. A ParGroup is the set of parameters on one line.

pars → list (Read Only):

The list of parameters on this page.

index → int (Read Only):

The numeric index of this page.

isCustom → bool (Read Only):

Boolean for whether this page is custom or not.

## Methods

### appendOP()

# appendOP(name, label=None, order=None, replace=True)→ ParGroup:

Create a node reference type parameter. This parameter will accept references to any operator.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendCOMP()

# appendCOMP(name, label=None, order=None, replace=True)→ ParGroup:

- Create a COMP node reference type parameter. This parameter will only accept references to COMPs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendObject()

# appendObject(name, label=None, order=None, replace=True)→ ParGroup:

- Create a 3D Object COMP node reference type parameter. This parameter will only accept references to 3D Object COMPs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendPanelCOMP()

# appendPanelCOMP(name, label=None, order=None, replace=True)→ ParGroup:

- Create a Panel COMP node reference type parameter. This parameter will only accept references to Panel COMPs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendTOP()

# appendTOP(name, label=None, order=None, replace=True)→ ParGroup:

- Create a TOP node reference type parameter. This parameter will only accept references to TOPs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendCHOP()

# appendCHOP(name, label=None, order=None, replace=True)→ ParGroup:

- Create a CHOP node reference type parameter. This parameter will only accept references to CHOPs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendSOP()

# appendSOP(name, label=None, order=None, replace=True)→ ParGroup:

- Create a SOP node reference type parameter. This parameter will only accept references to SOPs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendMAT()

# appendMAT(name, label=None, order=None, replace=True)→ ParGroup:

- Create a MAT node reference type parameter. This parameter will only accept references to MATs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendDAT()

# appendDAT(name, label=None, order=None, replace=True)→ ParGroup:

- Create a DAT node reference type parameter. This parameter will only accept references to DATs, and will refuse operators of other families.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendInt()

# appendInt(name, label=None, size=1, order=None, replace=True)→ ParGroup:

- Create a integer type parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
size - (Keyword, Optional) Set the number of values associated with the parameter. When greater than 1, the parameter will be shown as multiple float fields without a slider and multiple parameters will be created with the index of the parameter appended to the parameter name, starting at 1.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendFloat()

# appendFloat(name, label=None, size=1, order=None, replace=True)→ ParGroup:

- Create a float type parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
size - (Keyword, Optional) Set the number of values associated with the parameter. When greater than 1, the parameter will be shown as multiple float fields without a slider and multiple parameters will be created with the index of the parameter appended to the parameter name, starting at 1.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendXY()

# appendXY(name, label=None, order=None, replace=True)→ ParGroup:

- Create a XY position type parameter. Similar to creating a float parameter with size=2, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendXYZ()

# appendXYZ(name, label=None, order=None, replace=True)→ ParGroup:

- Create a XYZ position type parameter. Similar to creating a float parameter with size=3, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.


### appendXYZW()

# appendXYZW(name, label=None, order=None, replace=True)→ ParGroup:

- Create a XYZW position type parameter. Similar to creating a float parameter with size=4, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendWH()

# appendWH(name, label=None, order=None, replace=True)→ ParGroup:

- Create a WH size type parameter. Similar to creating a float parameter with size=2, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.


### appendUV()

# appendUV(name, label=None, order=None, replace=True)→ ParGroup:

- Create a UV 2D texture type parameter. Similar to creating a float parameter with size=2, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendUVW()

# appendUVW(name, label=None, order=None, replace=True)→ ParGroup:

- Create a UVW 3D texture type parameter. Similar to creating a float parameter with size=3, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendRGB()

# appendRGB(name, label=None, order=None, replace=True)→ ParGroup:

- Create a RGB color type parameter. Similar to creating a float parameter with size=3, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendRGBA()

# appendRGBA(name, label=None, order=None, replace=True)→ ParGroup:

- Create a RGBA color type parameter. Similar to creating a float parameter with size=4, but with more appropriate default naming.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendStr()

# appendStr(name, label=None, order=None, replace=True)→ ParGroup:

- Create a string type parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendStrMenu()

# appendStrMenu(name, label=None, order=None, replace=True)→ ParGroup:

- Create a menu type parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendMenu()

# appendMenu(name, label=None, order=None, replace=True)→ ParGroup:

- Create a menu type parameter. Returns the created parameter group object.

To set the actual menu entries, use the Par members: .menuNames and .menuLabels.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.


### appendFile()

# appendFile(name, label=None, order=None, replace=True)→ ParGroup:

- Create a file reference type parameter. Has built-in functionality to open a new file picker window.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.


### appendFileSave()

# appendFileSave(name, label=None, order=None, replace=True)→ ParGroup:

- Create a file save reference type parameter. Has built-in functionality to open a new file picker window.

Returns the created parameter objects.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.


### appendFolder()

# appendFolder(name, label=None, order=None, replace=True)→ ParGroup:

- Create a folder reference type parameter. Has built-in functionality to open a new folder picker window.

Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.


### appendPulse()

# appendPulse(name, label=None, order=None, replace=True)→ ParGroup:

- Create a pulse button type parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendMomentary()

# appendMomentary(name, label=None, order=None, replace=True)→ ParGroup:

- Create a momentary button type parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendToggle()

# appendToggle(name, label=None, order=None, replace=True)→ ParGroup:

- Create a toggle button type parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendPython()

# appendPython(name, label=None, order=None, replace=True)→ ParGroup:

- Create a python expression parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendPar()

# appendPar(name, par=None, label=None, order=None, replace=True)→ ParGroup:

- Create a parameter with attributes copied from an existing parameter. Returns the created parameter group object.

name - The name of the parameter. Built-in names can be used as they will be automatically adjusted to match proper custom name casing (begin with uppercase letter followed by lowercase letters and numbers only).
par - (Keyword, Optional) The parameter to copy attributes from. If none specified, a default parameter created.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendHeader()

# appendHeader(name, label=None, order=None, replace=True)→ ParGroup:

- Create a header parameter. Returns the created parameter group object. Only the value will be shown, not its label.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### appendSequence()

# appendSequence(name, label=None, order=None, replace=True)→ ParGroup:

- Create a Sequence header parameter. Returns the created parameter group object.

name - The name of the parameter.
label - (Keyword, Optional) The displayed label of the parameter, default will use the name argument.
order - (Keyword, Optional) Specify the display order of the parameter, default is highest.
replace - (Keyword, Optional) By default, replaces parameter with fresh attributes. If False, it errors if the parameter already exists.

### destroy()→ None:

- Destroy the page this object refers to, and all its parameters.

### sort(*pars)→ None:

- Reorder custom parameter groups or parameters in specified order.

n = op('base1')
page = n.appendCustomPage('Custom1')
page.appendFloat('Value')
page.appendFloat('Speed')
page.appendFloat('Color')
page.sort('Speed','Color','Value')

### resetPars()→ bool:

- Resets all the parameters in the page.

Returns true if anything was changed.

op('geo1').pages[0].resetPars() 
op('player').customPages['Setup'].resetPars()