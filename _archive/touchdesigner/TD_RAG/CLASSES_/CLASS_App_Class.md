---
title: "App Class"
category: "CLASS"
document_type: "reference"
difficulty: "intermediate"
time_estimate: "10-15 minutes"

# Enhanced metadata
user_personas: ["script_developer", "system_administrator", "automation_specialist"]
completion_signals: ["can_access_app_properties", "understands_system_introspection", "can_manage_licensing"]

concepts:
  - "application_information"
  - "system_environment"
  - "scripting_environment"
  - "global_control"
  - "license_management"
  - "resource_management"
  - "path_management"
  - "system_introspection"

prerequisites:
  - "Python_fundamentals"
  - "MODULE_td_Module"

workflows:
  - "system_introspection"
  - "dynamic_configuration"
  - "kiosk_setup"
  - "debugging"
  - "environment_query"
  - "cross_platform_development"

related_docs:
  - "CLASS_Project_Class"
  - "MODULE_td_Module"
  - "PY_Python_in_Touchdesigner"
  - "PY_Python_Reference"

hierarchy:
  primary: "scripting"
  secondary: "global_objects"
  tertiary: "application_context"

# Enhanced search optimization
search_optimization:
  primary_keywords: ["app", "application", "version", "system"]
  semantic_clusters: ["system_information", "environment_access", "licensing"]
  user_intent_mapping:
    beginner: ["what is app", "touchdesigner version", "system info"]
    intermediate: ["app properties", "system introspection", "path management"]
    advanced: ["license management", "cross platform deployment", "environment automation"]

keywords:
  - "application"
  - "system info"
  - "version"
  - "build"
  - "path"
  - "folder"
  - "os"
  - "process id"
  - "architecture"
  - "python"
  - "power"
  - "license"
  - "non-commercial"
  - "resolution"
  - "app object"
  - "environment"
tags:
- python
- global
- system
- environment
- versioning
- paths
- licensing
- windows
- macos
- cross_platform
question_patterns:
  - "How to get TouchDesigner version?"
  - "How to check system information?"
  - "Where are TouchDesigner files installed?"
  - "How to access application folders?"
  - "How to check if running commercial license?"
  - "What's my TouchDesigner build number?"
  - "How to find installation directory?"

common_use_cases:
  - "Version checking for compatibility"
  - "Path resolution for file operations"
  - "System information for debugging"
  - "License management for deployment"
  - "Environment detection for cross-platform scripts"
  - "Automated kiosk configuration"
operators: []
relationships:
  CLASS_Project_Class: strong
  MODULE_td_Module: strong
  PY_Python_in_Touchdesigner: medium
  PY_Python_Reference: medium
---



# App Class

<!-- TD-META
category: CLASS
document_type: reference
operators: []
concepts: [application_information, system_environment, scripting_environment, global_control, license_management, resource_management, path_management, system_introspection]
prerequisites: [Python_fundamentals, MODULE_td_Module]
workflows: [system_introspection, dynamic_configuration, kiosk_setup, debugging, environment_query, cross_platform_development]
related: [CLASS_Project_Class, MODULE_td_Module, PY_Python_in_Touchdesigner, PY_Python_Reference]
relationships: {
  "CLASS_Project_Class": "strong", 
  "MODULE_td_Module": "strong",
  "PY_Python_in_Touchdesigner": "medium",
  "PY_Python_Reference": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "global_objects"
  tertiary: "application_context"
keywords: [application, system info, version, build, path, folder, os, process id, architecture, python, power, license, non-commercial, resolution, app object, environment]
tags: [python, global, system, environment, versioning, paths, licensing, windows, macos, cross_platform]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Core class providing access to application-level information and system environment
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: System introspection, version checking, path resolution, license management

**Common Questions Answered**:

- "What version of TouchDesigner am I running?" → `app.version`
- "Where is TouchDesigner installed?" → `app.installFolder`
- "How to check system information?" → `app.osName`, `app.osVersion`
- "How to manage licensing programmatically?" → `app.addNonCommercialLimit()`

## 🔗 Learning Path

**Prerequisites**: [Python fundamentals] → [td Module basics]
**This document**: App Class reference
**Next steps**: [Project Class] → [System debugging guides]

**Related Topics**: System environment, debugging, cross-platform development

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: version checking for compatibility, path resolution for file operations, system information for debugging

**Common Questions Answered**:

- "How to get TouchDesigner version?" → [See relevant section]
- "How to check system information?" → [See relevant section]
- "Where are TouchDesigner files installed?" → [See relevant section]
- "How to access application folders?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Project Class] → [MODULE td Module] → [PY Python in Touchdesigner]

**Related Topics**: system introspection, dynamic configuration, kiosk setup

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: version checking for compatibility, path resolution for file operations, system information for debugging

**Common Questions Answered**:

- "How to get TouchDesigner version?" → [See relevant section]
- "How to check system information?" → [See relevant section]
- "Where are TouchDesigner files installed?" → [See relevant section]
- "How to access application folders?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [CLASS Project Class] → [MODULE td Module] → [PY Python in Touchdesigner]

**Related Topics**: system introspection, dynamic configuration, kiosk setup

## Summary

Core class providing access to application-level information and system environment. Essential for system introspection and environment-aware scripting.

## Relationship Justification

Maintains strong connection to Project class and td module. Added connection to Python environment guide since app object is crucial for troubleshooting Python installations.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods Overview](#methods-overview)
  - [addNonCommercialLimit()](#addnoncommerciallimit)
  - [removeNonCommercialLimit()](#removenoncommerciallimit)
  - [addResolutionLimit()](#addresolutionlimit)
  - [removeResolutionLimit()](#removeresolutionlimit)
- [Notes](#notes)

## Introduction

This class contains specific application details, such as its version and installation folders. It can be accessed with the `app` object, found in the automatically imported td module. [MODULE_td_Module](MODULE_td_Module.md).

## Members

`applicationsFolder` → `str` **(Read Only)**:
The primary location for installing applications on the system eg. 'C:/Program Files' on Windows.

`architecture` → `str` **(Read Only)**:
The architecture of the compile. Generally 32 or 64 bit.

`binFolder` → `str` **(Read Only)**:
Installation folder containing the binaries.

`build` → `str` **(Read Only)**:
Application build number.

`compileDate` → `Tuple[int, int, int]` **(Read Only)**:
The date the application was compiled, expressed as a tuple (year, month, day).

`configFolder` → `str` **(Read Only)**:
Installation folder containing configuration files.

`desktopFolder` → `str` **(Read Only)**:
Current user's desktop folder.

`enableCachedParameters` → `bool`:
Get or set caching parameter values instead of always evaluating.

`enableOptimizedExprs` → `bool`:
Get or set if Python expression optimization is enabled. Defaults to True every time TouchDesigner starts.

`experimental` → `bool` **(Read Only)**:
Returns true if the App is an experimental build, false otherwise.

`installFolder` → `str` **(Read Only)**:
Main installation folder.

`launchTime` → `float` **(Read Only)**:
Total time required to launch and begin playing the toe file, measured in seconds.

`logExtensionCompiles` → `bool`:
Get or set if extra messages for starting and ending compiling extensions is sent to the textport. Additional error stack will be printed if compilation fails. Defaults to False every time TouchDesigner starts.

`osName` → `str` **(Read Only)**:
The operating system name.

`osVersion` → `str` **(Read Only)**:
The operating system version.

`power` → `bool`:
Get or set the overall processing state of the process. When True, processing is enabled. When False processing is halted. This is identical to pressing the power button on the main interface. This has a greater effect than simply pausing or stopping the playbar.

app.power = False # turn off the power button.

`preferencesFolder` → `str` **(Read Only)**:
Folder where the preferences file is located.

`processId` → `int` **(Read Only)**:
The ID of the current running process.

`product` → `str` **(Read Only)**:
Type of executable the project is running under. Values are 'TouchDesigner', 'TouchPlayer' or 'TouchEngine'.

`pythonExecutable` → `str` **(Read Only)**:
Path to TouchDesigner's Python executable. This executable is not used directly by TouchDesigner but can be used to test pure Python code in an environment with all the packages and modules included with TouchDesigner. The executable can also be used to run external Python scripts without installing a separate Python installation.

`recentFiles` → `list`:
Get or set the list of most recently saved or loaded files.

`samplesFolder` → `str` **(Read Only)**:
Installation folder containing configuration files.

`paletteFolder` → `str` **(Read Only)**:
Installation folder containing palette files.

`userPaletteFolder` → `str` **(Read Only)**:
Folder where custom user palettes are located.

`version` → `str` **(Read Only)**:
Application version number.

`windowColorBits` → `int` **(Read Only)**:
The number of color bits per color channel the TouchDesigner window is running at. By default this will be 8-bits per channel, but can be increased to 10-bits by settings env var TOUCH_10_BIT_COLOR=1. Only works on displays that support 10-bit color.

`systemFolder` → `str` **(Read Only)**:
Installation folder containing system files.

`tempFolder` → `str` **(Read Only)**:
Folder used for temporary files.

## Methods Overview

### addNonCommercialLimit()

addNonCommercialLimit(password=None)→ `None`:

Limits the application to operate at non-commercial license level. Multiple calls can be made, but each can be undone with a matching `removeNonCommercialLimit(password)`. If the password is blank the operation cannot be undone. (See also [CLASS_licenses.disablePro] member).

- `password` - (Keyword, Optional) Password to later remove the restriction.

```python
app.addNonCommercialLimit(password='secret123')  # undoable with password
app.addNonCommercialLimit()  # permanent during length of session.
```

### removeNonCommercialLimit()

removeNonCommercialLimit(password=None)→ `bool`:

Removes the restriction previously added. Returns True if successful.

- `password` - (Keyword) Password previously used when restriction added.

```python
app.removeNonCommercialLimit(password='secret123')
```

### addResolutionLimit()

addResolutionLimit(x, y, password=None)→ `None`:

Limits all textures to the specified amount. Multiple calls can be made, but each can be undone with a matching `removeResolutionLimit(password)`. The final resolution limit will be the minimum of all calls. If the password is blank the operation cannot be undone.

- `x` - Width of maximum texture resolution, measured in pixels.
- `y` - Height of maximum texture resolution, measured in pixels.
- `password` - (Keyword, Optional) Password to later remove the restriction.

```python
app.addResolutionLimit(600, 480, password='secret123')  # undoable with password
app.addResolutionLimit()  # permanent during length of session.
```

### removeResolutionLimit()

removeResolutionLimit(password=None)→ `bool`:

Removes the restriction previously added. Returns True if successful.

- `password` - (Keyword) Password previously used when restriction added.

```python
app.removeResolutionLimit(password='secret123')
```

## Notes

**Note:** See also [REF_Variables](REF_Variables.md) where more built-in paths and strings are available via expressions in the form `var('DESKTOP')`, `var('MYDOCUMENTS')` and `var('TOENAME')`.
