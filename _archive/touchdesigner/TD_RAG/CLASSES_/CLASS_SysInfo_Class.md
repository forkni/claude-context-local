---
category: CLASS
document_type: reference
difficulty: intermediate
time_estimate: 10-15 minutes
operators:
- MIDI_In_CHOP
- MIDI_Out_CHOP
- Monitors_DAT
concepts:
- system_introspection
- hardware_information
- environment_query
- midi_device_listing
- display_configuration
- cross_platform_compatibility
prerequisites:
- Python_fundamentals
- MODULE_td_Module
workflows:
- dynamic_configuration
- system_diagnostics
- hardware_dependent_setup
- multi_monitor_configuration
- midi_device_discovery
- cross_platform_deployment
keywords:
- system information
- hardware info
- cpu cores
- ram memory
- monitor resolution
- display setup
- midi devices
- tfs directory
- system specs
- numCPUs
- MIDIInputs
- MIDIOutputs
- xres
- yres
- cross platform
tags:
- python
- api_reference
- global
- system
- hardware
- cpu
- ram
- midi
- display
- cross_platform
- automation
relationships:
  MODULE_td_Module: strong
  CLASS_App_Class: strong
  HARDWARE_Multiple_Monitors: medium
related_docs:
- MODULE_td_Module
- CLASS_App_Class
- HARDWARE_Multiple_Monitors
hierarchy:
  secondary: global_objects
  tertiary: system_information
question_patterns:
- How to use CLASS class?
- What methods are available?
- How to access properties?
- Python API reference?
common_use_cases:
- dynamic_configuration
- system_diagnostics
- hardware_dependent_setup
- multi_monitor_configuration
---

# SysInfo Class

<!-- TD-META
category: CLASS
document_type: reference
operators: [MIDI_In_CHOP, MIDI_Out_CHOP, Monitors_DAT]
concepts: [system_introspection, hardware_information, environment_query, midi_device_listing, display_configuration, cross_platform_compatibility]
prerequisites: [Python_fundamentals, MODULE_td_Module]
workflows: [dynamic_configuration, system_diagnostics, hardware_dependent_setup, multi_monitor_configuration, midi_device_discovery, cross_platform_deployment]
related: [MODULE_td_Module, CLASS_App_Class, HARDWARE_Multiple_Monitors]
relationships: {
  "MODULE_td_Module": "strong",
  "CLASS_App_Class": "strong",
  "HARDWARE_Multiple_Monitors": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "global_objects"
  tertiary: "system_information"
keywords: [system information, hardware info, cpu cores, ram memory, monitor resolution, display setup, midi devices, tfs directory, system specs, numCPUs, MIDIInputs, MIDIOutputs, xres, yres, cross platform]
tags: [python, api_reference, global, system, hardware, cpu, ram, midi, display, cross_platform, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python class reference for TouchDesigner API development
**Difficulty**: Intermediate
**Time to read**: 10-15 minutes
**Use for**: dynamic_configuration, system_diagnostics, hardware_dependent_setup

**Common Questions Answered**:

- "How to use CLASS class?" → [See relevant section]
- "What methods are available?" → [See relevant section]
- "How to access properties?" → [See relevant section]
- "Python API reference?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Module Td Module]
**This document**: CLASS reference/guide
**Next steps**: [MODULE td Module] → [CLASS App Class] → [HARDWARE Multiple Monitors]

**Related Topics**: dynamic configuration, system diagnostics, hardware dependent setup

## Summary

System information access class providing hardware and environment details. Critical for dynamic configuration and hardware-dependent application behavior. The SysInfo class describes current system information. It can be accessed with the `sysinfo` object, found in the automatically imported [PY_td_Module](PY_td_Module.md) module.

## Relationship Justification

Part of td module's global objects alongside App class for comprehensive system information. Connected to Multiple Monitors guide for display configuration workflows. Essential for hardware-aware application development.

## Content

- [Introduction](#introduction)
- [Members](#members)
  - [numCPUs](#numcpus)
  - [ram](#ram)
  - [numMonitors](#nummonitors)
  - [xres](#xres)
  - [yres](#yres)
  - [tfs](#tfs)
  - [MIDIInputs](#midiinputs)
  - [MIDIOutputs](#midioutputs)
- [Methods](#methods)

## Introduction

The SysInfo class describes current system information. **Note:** It can be accessed with the `sysinfo` object, found in the automatically imported [PY_td_Module](PY_td_Module.md) module.

```python
# return the amount of available ram
sysinfo.ram
```

## Members

### numCPUs

`numCPUs` → `int` **(Read Only)**:

The number of CPUs/cores on the system.

### ram

`ram` → `float` **(Read Only)**:

Amount of available RAM memory.

### numMonitors

`numMonitors` → `int` **(Read Only)**:

The number of monitors.

### xres

`xres` → `int` **(Read Only)**:

The system's current monitor resolution width.

### yres

`yres` → `int` **(Read Only)**:

The system's current monitor resolution height.

### tfs

`tfs` → `str` **(Read Only)**:

The path to the TFS directory.

### MIDIInputs

`MIDIInputs` → `list[str]` **(Read Only)**:

A list of all MIDI Input device names.

### MIDIOutputs

`MIDIOutputs` → `list[str]` **(Read Only)**:

A list of all MIDI Output device names.

## Methods

No operator specific methods.
