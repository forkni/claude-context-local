---
title: "Project Class"
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes

# Enhanced metadata
user_personas: ["script_developer", "system_administrator", "automation_specialist", "advanced_user"]
completion_signals: ["can_access_project_properties", "understands_session_management", "can_implement_project_automation", "manages_performance_settings"]

operators: []
concepts:
- project_management
- file_io
- session_control
- performance_settings
- window_management
- privacy_control
- debugging_tools
- path_management
- automation
prerequisites:
- Python_fundamentals
- MODULE_td_Module
workflows:
- project_automation
- dynamic_file_loading
- performance_management
- deployment_setup
- debugging_scripts
- render_automation
- session_management
keywords:
- project
- toe
- file
- load
- save
- quit
- path
- cookRate
- fps
- realTime
- perform
- window
- privacy
- stack
- project object
- automation
- session
tags:
- python
- global
- project
- file
- session
- performance
- window
- debug
- automation
relationships:
  CLASS_App_Class: strong
  MODULE_td_Module: strong
  PY_Python_Reference: medium
  PERF_Optimize: medium
related_docs:
- CLASS_App_Class
- MODULE_td_Module
- PY_Python_Reference
- PERF_Optimize
# Enhanced search optimization
search_optimization:
  primary_keywords: ["project", "session", "file", "performance"]
  semantic_clusters: ["project_management", "session_control", "file_operations"]
  user_intent_mapping:
    beginner: ["what is project class", "basic project control", "how to save project"]
    intermediate: ["project automation", "session management", "performance settings"]
    advanced: ["deployment automation", "advanced project control", "performance optimization"]

hierarchy:
  secondary: global_objects
  tertiary: project_session
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- project_automation
- dynamic_file_loading
- performance_management
- deployment_setup
---

# Project Class

<!-- TD-META
category: CLASS
document_type: reference
operators: []
concepts: [project_management, file_io, session_control, performance_settings, window_management, privacy_control, debugging_tools, path_management, automation]
prerequisites: [Python_fundamentals, MODULE_td_Module]
workflows: [project_automation, dynamic_file_loading, performance_management, deployment_setup, debugging_scripts, render_automation, session_management]
related: [CLASS_App_Class, MODULE_td_Module, PY_Python_Reference, PERF_Optimize]
relationships: {
  "CLASS_App_Class": "strong",
  "MODULE_td_Module": "strong",
  "PY_Python_Reference": "medium",
  "PERF_Optimize": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "global_objects"
  tertiary: "project_session"
keywords: [project, toe, file, load, save, quit, path, cookRate, fps, realTime, perform, window, privacy, stack, project object, automation, session]
tags: [python, global, project, file, session, performance, window, debug, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: project_automation, dynamic_file_loading, performance_management

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [CLASS App Class] → [MODULE td Module] → [PY Python Reference]

**Related Topics**: project automation, dynamic file loading, performance management

## Summary

Core class for project-level control including file operations, performance settings, and session management. Critical for project automation and deployment scenarios.

## Relationship Justification

Connected to performance optimization since project object controls performance settings. Links to Python reference for comprehensive API understanding.

## Overview

The Project class describes the current session. It can be accessed with the `project` object, found in the automatically imported [MODULE_td_Module](MODULE_td_Module.md) module. Members changed in this such as the 'paths' member will be written to disk when the project is saved.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods Overview](#methods-overview)
  - [load()](#load)
  - [save()](#save)
  - [quit()](#quit)
  - [addPrivacy()](#addprivacy)
  - [removePrivacy()](#removeprivacy)
  - [accessPrivateContents()](#accessprivatecontents)
  - [applyWindowSettings()](#applywindowsettings)
  - [stack()](#stack)
  - [pythonStack()](#pythonstack)

## Introduction

The Project class describes the current session. It can be accessed with the `project` object, found in the automatically imported [MODULE_td_Module](MODULE_td_Module.md) module. Members changed in this such as the 'paths' member will be written to disk when the project is saved.

## Members

`folder` → `str` **(Read Only)**:
The folder at which the project resides.

`name` → `str` **(Read Only)**:
The filename under which the project is saved.

`saveVersion` → `str` **(Read Only)**:
The App version number when the project was last saved.

`saveBuild` → `str` **(Read Only)**:
The App build number when the project was last saved.

`saveTime` → `str` **(Read Only)**:
The time and date the project was last saved.

`saveOSName` → `str` **(Read Only)**:
The App operating system name when the project was last saved.

`saveOSVersion` → `str` **(Read Only)**:
The App operating system version when the project was last saved.

`paths` → `dict` **(Read Only)**:
A dictionary which can be used to define URL-syntax path prefixes, enabling you to move your media to different locations easily. This dictionary is saved and loaded in the .toe file. Example: Run `project.paths['movies'] = 'C:/MyMovies'`, and reference it with a parameter expression: `movies://butterfly.jpg`. To manually convert between expanded and collapsed paths, use tdu.collapsePath and tdu.expandPath, for example `tdu.expandPath('movies://butterfly.jpg')` expands to `C:/MyMovies/butterfly.jpg`. If you already have your paths setup, choosing files from file browsers in OPs will create paths using these shortcuts rather than full paths. Additionally, to enable you to have different media locations on different machines, you can put a JSON file in the same folder as your .toe that gets read on startup. This will override any existing locations saved in `projects.paths` to the new machine specific file paths specified in the .json. Only existing entries in `project.paths` will be used. If the .json contains path names not specified in `project.paths`, those will be ignored. It would contain something like `{ "project.paths": { "movies": "M:/MyMovies" } }`. If your .toe file is called MyProject.10.toe, the JSON file must be called MyProject.Settings.json. The idea is that this .json would be unique to machines, and not commited to version control or shared between machines.

`cookRate` → `float`:
Get or set the maximum number of frames processed each second. In general you should not need to use this. It is preferred to look at the FPS of the root component to know the cooking rate. Individual components may have their own rates, specified by rate.

```python
a = project.cookRate # get the current cook rate 
project.cookRate = 30 # set the cook rate to 30 FPS
```

**Note:** This is displayed and set in the user interface at the bottom-left: the "FPS" field.

`realTime` → `bool`:
Get or set the real time cooking state. When True, frames may be skipped in order to maintain the cookRate. When False, all frames are processed sequentially regardless of duration. This is useful to render movies out using the [CLASS_MovieFileOutTOP_Class](CLASS_MovieFileOutTOP_Class.md) without dropping any frames for example.

```python
a = project.realTime
project.realTime = False # turn off real time playback.
```

`isPrivate` → `bool` **(Read Only)**:
True when the project networks cannot be directly viewed.

`isPrivateKey` → `bool` **(Read Only)**:
True when the private networks are accessible by a pass phrase.

`cacheParameters` → `bool`:
Cache parameter values instead of always evaluating.

`externalToxModifiedInProject` → `bool` **(Read Only)**:
Callback for when an external tox has been modified in the current project and there are other instances of the same tox loaded elsewhere in the project.

`externalToxModifiedOnDisk` → `bool` **(Read Only)**:
Callback for when an external tox file has been modified on disk.

`windowOnTop` → `bool`:
Get or set the window on top state.

`windowStartMode` → `[CLASS_WindowStartMode]`:
Get or set the window start mode. The mode is one of: `WindowStartMode.AUTO`, `WindowStartMode.FULL`, `WindowStartMode.LEFT`, `WindowStartMode.RIGHT` or `WindowStartMode.CUSTOM`.

`windowDraw` → `bool`:
Get or set the window drawing state.

`windowStartCustomWidth` → `int`:
Get or set the window start width. Only used when windowStartMode is `WindowStartMode.CUSTOM`.

`windowStartCustomHeight` → `int`:
Get or set the window start height. Only used when windowStartMode is `WindowStartMode.CUSTOM`.

`windowStartCustomX` → `int`:
Get or set the window start X position. Only used when windowStartMode is `WindowStartMode.CUSTOM`.

`windowStartCustomY` → `int`:
Get or set the window start Y position. Only used when windowStartMode is `WindowStartMode.CUSTOM`.

`performOnStart` → `bool`:
Get or set the perform on start state.

`performWindowPath` → `[CLASS_OP]`:
Get or set the perform window path.

`resetAudioOnDeviceChange` → `bool`:
Get or set whether audio devices momentarily reset when devices are added or removed to the system.

## Methods Overview

### load()

load(path)→ `None`:

Load a specific .toe file from disk.

- `path` - (Optional) The path of the file to load. If not specified, loads the default.toe file, as specified in preferences.

```python
project.load('test_demo.toe')
```

### save()

save(path, saveExternalToxs=False)→ `bool`:

Save the current session to disk. Returns True if a file was saved, False otherwise (eg, if the file exists, and when prompted, the user selects to not overwrite).

- `path` - (Optional) If not provided the default/current filename is incremented and used. The current file is `project.name` under folder `project.folder`.
- `saveExternalToxs` - (Keyword, Optional) If set to True, will save out the contents of any COMP that references an external .tox into the referenced .tox file.

```python
project.save('test_demo.toe')
project.save()
```

### quit()

quit(force=False, crash=False)→ `None`:

Quit the project.

- `force` - (Keyword, Optional) If set to True, unsaved changes will be discarded without prompting.
- `crash` - (Keyword, Optional) If set to True, the application will terminate unexpectedly. This is used for system testing.

```python
project.quit()  # quit project, possibly prompting for unsaved changes if 'Prompt to Save on Exit' in Preferences dialog is enabled.
project.quit(force=True)  # quit project immediately.
```

### addPrivacy()

addPrivacy(key)→ `bool`:

Add privacy to a toe file with the given key.

Privacy can only be added to toes that currently have no privacy, and are using a Pro license.

- `key` - The key phrase. This should resolve to a non-blank string.

```python
project.addPrivacy('secret')
```

### removePrivacy()

removePrivacy(key)→ `bool`:

Completely remove privacy from a toe file.

- `key` - The current privacy key phrase.

```python
project.removePrivacy('secret')
```

### accessPrivateContents()

accessPrivateContents(key)→ `bool`:

Gain access to a private file. The file will still be private the next time it is saved or re-opened.

- `key` - The current privacy key phrase.

```python
project.accessPrivateContents('secret')
```

### applyWindowSettings()

applyWindowSettings()→ `None`:

Applies the project's window start settings to the current TouchDesigner window.

### stack()

stack()→ `str`:

Formatted contents of current cook and parameter evaluation stack.

```python
print(project.stack())
```

### pythonStack()

pythonStack()→ `str`:

Formatted contents of current python stack.

```python
print(project.pythonStack())
```
