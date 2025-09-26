---
title: "CLASS_Preferences_Class"
category: CLASS
document_type: reference
difficulty: intermediate
# Enhanced metadata
user_personas: ["script_developer", "intermediate_user", "automation_specialist"]
completion_signals: ["can_access_class_properties", "understands_class_management", "can_implement_class_functionality"]

time_estimate: 10-15 minutes
operators: []
concepts:
- preference_management
- configuration_persistence
- settings_storage
- session_management
- default_restoration
- application_configuration
- user_customization
- settings_backup_restore
- programmatic_configuration
prerequisites:
- Python_fundamentals
- CLASS_UI_Class
- dictionary_access
workflows:
- preference_configuration
- settings_management
- configuration_backup
- default_restoration
- session_persistence
- application_customization
- settings_migration
- automated_setup
keywords:
- preferences class
- configuration settings
- session persistence
- ui configuration
- settings storage
- preference defaults
- configuration persistence
- application settings
- user preferences
- settings management
- preference restoration
- save()
- load()
- resetToDefaults()
- dictionary access
tags:
- python
- api_reference
- ui_interface
- configuration
- settings_persistence
- session_management
- preference_system
- dictionary_access
- automation
relationships:
  CLASS_UI_Class: strong
  CLASS_App_Class: medium
  MODULE_td_Module: medium
related_docs:
- CLASS_UI_Class
- CLASS_App_Class
- MODULE_td_Module
hierarchy:
  secondary: global_objects
  tertiary: preferences
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- preference_configuration
- settings_management
- configuration_backup
- default_restoration
---

# Preferences Class

<!-- TD-META
category: CLASS
document_type: reference
operators: []
concepts: [preference_management, configuration_persistence, settings_storage, session_management, default_restoration, application_configuration, user_customization, settings_backup_restore, programmatic_configuration]
prerequisites: [Python_fundamentals, CLASS_UI_Class, dictionary_access]
workflows: [preference_configuration, settings_management, configuration_backup, default_restoration, session_persistence, application_customization, settings_migration, automated_setup]
related: [CLASS_UI_Class, CLASS_App_Class, MODULE_td_Module]
relationships: {
  "CLASS_UI_Class": "strong",
  "CLASS_App_Class": "medium",
  "MODULE_td_Module": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "global_objects"
  tertiary: "preferences"
keywords: [preferences class, configuration settings, session persistence, ui configuration, settings storage, preference defaults, configuration persistence, application settings, user preferences, settings management, preference restoration, save(), load(), resetToDefaults(), dictionary access]
tags: [python, api_reference, ui_interface, configuration, settings_persistence, session_management, preference_system, dictionary_access, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: preference_configuration, settings_management, configuration_backup

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Class Ui Class] → [Dictionary Access]
**This document**: CLASS reference/guide
**Next steps**: [CLASS UI Class] → [CLASS App Class] → [MODULE td Module]

**Related Topics**: preference configuration, settings management, configuration backup

## Summary

Application preferences management class providing programmatic access to TouchDesigner settings. Essential for configuration automation and session persistence.

## Relationship Justification

Accessed through UI class as ui.preferences object. Connected to App class for application-level configuration and td module as a global object. Essential for programmatic configuration management and automated setup workflows.

## Content

- [Introduction](#introduction)
- [Members](#members)
- [Methods Overview](#methods-overview)
  - [save()](#save)
  - [resetToDefaults()](#resettodefaults)
  - [load()](#load)
- [Special Functions](#special-functions)
  - [len()](#len)
  - [[preference name]](#preference-name)
  - [Iterator](#iterator)

## Introduction

The Preferences class describes the set of configurable preferences that are retained between sessions. It can be accessed with the `ui.preferences` object or through the Preferences Dialog.

## Members

`defaults` → `dict` **(Read Only)**:
A dictionary of preferences with their default values.

## Methods Overview

### save()

save()→ `None`:

Save preference values to disk. Unless saved, changes to preferences will be lost, next time application is started.

### resetToDefaults()

resetToDefaults()→ `None`:

Reset all preferences to their default values.

### load()

load()→ `None`:

Restore preference values from disk.

## Special Functions

### len()

len(Preferences)→ `int`:

Returns the total number of preferences.

```python
a = len(ui.preferences)
```

### [preference name]

[<preference name>]→ `value`:

Get or set specific preference given a preference name key.

```python
v = ui.preferences['dats.autoindent']
ui.preferences['dats.autoindent'] = 0
```

### Iterator

Iterator→ `str`:

Iterate over each preference name.

```python
for p in ui.preferences:
    print(p) # print the name of all preferences
```
