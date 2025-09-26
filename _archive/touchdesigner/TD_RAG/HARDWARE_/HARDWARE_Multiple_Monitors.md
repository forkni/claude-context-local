---
title: "Multiple Monitors"
category: HARDWARE
document_type: guide
difficulty: beginner
time_estimate: 15-25 minutes

# Enhanced metadata
user_personas: ["hardware_specialist", "system_administrator", "beginner_user", "technical_artist"]
completion_signals: ["configures_multi_display_systems", "understands_hardware_setup", "can_implement_video_walls", "manages_display_configuration"]

operators:
- Window_COMP
- Container_COMP
- Monitors_DAT
concepts:
- multi-monitor_setup
- perform_mode
- window_management
- display_spanning
- hardware_configuration
- performance_optimization
prerequisites:
- perform_mode_basics
- hardware_setup_fundamentals
workflows:
- video_walls
- multi-projector_installations
- live_performance_setup
- large_scale_displays
- installation_art
- projection_mapping
keywords:
- multi-display
- multi-monitor
- video wall
- projector
- spanning
- Nvidia Mosaic
- Nvidia Surround
- AMD EyeFinity
- QuadHead2Go
- Datapath
- extended desktop
- hardware setup
tags:
- windows
- macos
- nvidia
- amd
- perform_mode
- display
- projection
- hardware
- installation
- video_wall
relationships:
  PERF_Optimize: medium
  CLASS_App_Class: weak
related_docs:
- PERF_Optimize
- CLASS_App_Class
# Enhanced search optimization
search_optimization:
  primary_keywords: ["monitor", "display", "multi", "hardware"]
  semantic_clusters: ["hardware_configuration", "multi_display_systems", "installation_setup"]
  user_intent_mapping:
    beginner: ["what is multi monitor", "basic display setup", "hardware requirements"]
    intermediate: ["video wall setup", "display configuration", "hardware optimization"]
    advanced: ["complex installations", "multi projector systems", "advanced display management"]

hierarchy:
  secondary: display_output
  tertiary: multi_monitor_setup
question_patterns:
- Hardware setup guide?
- Multi-monitor configuration?
- Installation requirements?
- Hardware compatibility?
common_use_cases:
- video_walls
- multi-projector_installations
- live_performance_setup
- large_scale_displays
---


# Multiple Monitors

<!-- TD-META
category: HARDWARE
document_type: guide
operators: [Window_COMP, Container_COMP, Monitors_DAT]
concepts: [multi-monitor_setup, perform_mode, window_management, display_spanning, hardware_configuration, performance_optimization]
prerequisites: [perform_mode_basics, hardware_setup_fundamentals]
workflows: [video_walls, multi-projector_installations, live_performance_setup, large_scale_displays, installation_art, projection_mapping]
related: [PERF_Optimize, CLASS_App_Class]
relationships: {
  "PERF_Optimize": "medium",
  "CLASS_App_Class": "weak"
}
hierarchy:
  primary: "hardware"
  secondary: "display_output"
  tertiary: "multi_monitor_setup"
keywords: [multi-display, multi-monitor, video wall, projector, spanning, Nvidia Mosaic, Nvidia Surround, AMD EyeFinity, QuadHead2Go, Datapath, extended desktop, hardware setup]
tags: [windows, macos, nvidia, amd, perform_mode, display, projection, hardware, installation, video_wall]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Hardware setup guide for TouchDesigner installations
**Difficulty**: Beginner
**Time to read**: 15-25 minutes
**Use for**: video_walls, multi-projector_installations, live_performance_setup

**Common Questions Answered**:

- "Hardware setup guide?" → [See relevant section]
- "Multi-monitor configuration?" → [See relevant section]
- "Installation requirements?" → [See relevant section]
- "Hardware compatibility?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Perform Mode Basics] → [Hardware Setup Fundamentals]
**This document**: HARDWARE reference/guide
**Next steps**: [PERF Optimize] → [CLASS App Class]

**Related Topics**: video walls, multi-projector installations, live performance setup

## 🎯 Quick Reference

**Purpose**: Hardware setup guide for TouchDesigner installations
**Difficulty**: Beginner
**Time to read**: 15-25 minutes
**Use for**: video_walls, multi-projector_installations, live_performance_setup

**Common Questions Answered**:

- "Hardware setup guide?" → [See relevant section]
- "Multi-monitor configuration?" → [See relevant section]
- "Installation requirements?" → [See relevant section]
- "Hardware compatibility?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Perform Mode Basics] → [Hardware Setup Fundamentals]
**This document**: HARDWARE reference/guide
**Next steps**: [PERF Optimize] → [CLASS App Class]

**Related Topics**: video walls, multi-projector installations, live performance setup

## Summary

Hardware setup guide for multi-monitor configurations and display spanning. Essential for installation and performance setups requiring multiple outputs.

## Relationship Justification

Connected to performance optimization since multi-monitor setups impact performance. Links to App class for system information that's useful in hardware configuration.

## Content

- [Introduction](#introduction)
- [Output to Multiple Monitors](#output-to-multiple-monitors)
- [Spanning Monitors for Best Performance](#spanning-monitors-for-best-performance)
- [Platform-Specific Setup](#platform-specific-setup)
  - [Windows](#windows)
    - [Combining Monitors into a Single Virtual Monitor](#combining-monitors-into-a-single-virtual-monitor)
  - [macOS](#macos)
- [Additional Setup Tips](#additional-setup-tips)
- [See Also](#see-also)

## Introduction

Multiple monitors are also known as: second monitor, multi-monitors, right monitor, dual monitors, multi-display.

TouchDesigner can send video out to multiple projectors, monitors and recorders. TouchDesigner can run single-monitor or across many monitors.

## Output to Multiple Monitors

Most modern graphics cards allow for at least 4 outputs. The easiest way to get more outputs is to use splitters such as QuadHead2Go or Datapath Fx4 monitor expansion devices.

Laptops all have different multi-monitor capabilities based on the manufacturer's specifications. Sometimes a laptop will have many output connections but still have limitations on the number of monitors it can drive simultaneously. Refer to the specifications for your specific laptop to understand its capabilities.

## Spanning Monitors for Best Performance

TouchDesigner will run fastest in [REF_PerformMode] if you combine all your panels into one canvas that spans across all your monitors. This can be done easily with [CLASS_ContainerCOMP]s, then by assigning this to the [CLASS_WindowCOMP] that is set for [REF_PerformMode] in the [REF_WindowPlacementDialog]. Using multiple [CLASS_WindowCOMP]s is not suggested, and will result in poor performance.

Example for two 1920x1080 monitors: `File:PerformMode Windows.toe`

## Platform-Specific Setup

### Windows

On the Desktop background, right-click -> Display Settings -> Multiple Displays -> Extend These Displays.

#### Combining Monitors into a Single Virtual Monitor

If possible, you should also join your monitors together into a single virtual monitor using Nvidia Mosaic, Nvidia Surround or AMD EyeFinity.

### macOS

System Preferences -> Displays -> Arrangement -> Mirror Displays = Off.

To allow monitor spanning on macOS, make sure the following is also set:

System Preferences -> Desktop & Dock -> Mission Control -> Displays have separate Spaces = Off

## Additional Setup Tips

- [REF_WindowPlacementDialog] can be used to quickly assign [REF_PerformMode] to different [CLASS_WindowCOMP]s, and adjust parameters, jump to the network, and open/close the windows.
- [REF_PerformMode] can be turned On and Off with the Shortcut keys F1 (On) and Esc (Off).
- The **Always on Top** parameter in the [CLASS_WindowCOMP] forces TouchDesigner to always be the top-most visible window.

## See Also

[REF_MultipleGraphicCards], [CLASS_WindowCOMP], [REF_WindowPlacementDialog]
