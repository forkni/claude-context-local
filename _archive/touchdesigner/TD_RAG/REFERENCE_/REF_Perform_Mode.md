---
category: REF
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators:
- Window_COMP
concepts:
- perform_mode
- designer_mode
- window_management
- application_modes
- live_performance_setup
- fullscreen_exclusive_mode
- performance_optimization
- deployment
prerequisites:
- CLASS_WindowCOMP_Class
- ui_navigation
- perform_basics
workflows:
- live_performance
- interactive_installation
- kiosk_applications
- project_deployment
- fullscreen_presentation
keywords:
- perform
- live
- presentation
- kiosk
- designer mode
- F1
- Esc
- fullscreen
- exclusive mode
- window placement
- stutter-free
- deployment
- privacy mode
tags:
- performance
- live
- presentation
- fullscreen
- windows
- ui
- deployment
- optimization
relationships:
  CLASS_WindowCOMP_Class: strong
  REF_WindowPlacementDialog: strong
  REF_TouchPlayer: strong
  CLASS_UI_Class: strong
  HARDWARE_Multiple_Monitors: medium
related_docs:
- CLASS_WindowCOMP_Class
- REF_WindowPlacementDialog
- REF_TouchPlayer
- CLASS_UI_Class
- REF_Multiple_Monitors
- HARDWARE_Multiple_Monitors
hierarchy:
  secondary: application_modes
  tertiary: perform_mode
question_patterns: []
common_use_cases:
- live_performance
- interactive_installation
- kiosk_applications
- project_deployment
---

# Perform Mode

<!-- TD-META
category: REF
document_type: guide
operators: [Window_COMP]
concepts: [perform_mode, designer_mode, window_management, application_modes, live_performance_setup, fullscreen_exclusive_mode, performance_optimization, deployment]
prerequisites: [CLASS_WindowCOMP_Class, ui_navigation, perform_basics]
workflows: [live_performance, interactive_installation, kiosk_applications, project_deployment, fullscreen_presentation]
related: [CLASS_WindowCOMP_Class, REF_WindowPlacementDialog, REF_TouchPlayer, CLASS_UI_Class, REF_Multiple_Monitors, HARDWARE_Multiple_Monitors]
relationships: {
  "CLASS_WindowCOMP_Class": "strong",
  "REF_WindowPlacementDialog": "strong",
  "REF_TouchPlayer": "strong",
  "CLASS_UI_Class": "strong",
  "HARDWARE_Multiple_Monitors": "medium"
}
hierarchy:
  primary: "ui"
  secondary: "application_modes"
  tertiary: "perform_mode"
keywords: [perform, live, presentation, kiosk, designer mode, F1, Esc, fullscreen, exclusive mode, window placement, stutter-free, deployment, privacy mode]
tags: [performance, live, presentation, fullscreen, windows, ui, deployment, optimization]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical guide for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: live_performance, interactive_installation, kiosk_applications

## 🔗 Learning Path

**Prerequisites**: [Class Windowcomp Class] → [Ui Navigation] → [Perform Basics]
**This document**: REF reference/guide
**Next steps**: [CLASS WindowCOMP Class] → [REF WindowPlacementDialog] → [REF TouchPlayer]

**Related Topics**: live performance, interactive installation, kiosk applications

## Summary

Guide to TouchDesigner's Perform Mode for live performance and deployment scenarios, covering window management and optimization settings.

## Relationship Justification

Strong connections to other performance monitoring tools. Strong connection to multiple monitor setups as Perform Mode is commonly used with multi-display configurations. Strong ties to window management and deployment workflows.

## Content

- [Introduction](#introduction)
- [Using Perform Mode](#using-perform-mode)
- [Configuration Options](#configuration-options)
- [Startup Options](#startup-options)
- [Full-Screen Exclusive Mode (Windows Only)](#full-screen-exclusive-mode-windows-only)
- [Tips](#tips)
- [See Also](#see-also)

## Introduction

Perform Mode is an optimized mode for live performance that only renders one specified [CLASS_WindowCOMP](CLASS_windowCOMP_Class.md) which is one window that contains your video outputs and your (optional) control interface. In Perform Mode the network editing window is not open - you edit your networks in Designer Mode. The function key F1 and the Esc key alternate between the two modes. See [REF_WindowPlacement] and `/perform`.

**Tip**: Pause/unpause the timeline using Shift-Spacebar in Perform Mode and in [REF_TouchPlayer].

## Using Perform Mode

By default, the [CLASS_WindowCOMP](CLASS_windowCOMP_Class.md) `/perform` is set up in Edit - Window Placement to render in Perform Mode.

**Enter Perform Mode** - click the button on the left side of the Layout bar or use the F1 function key to enter Perform Mode. You will now only be able to interact with the window specified in the [CLASS_WindowCOMP](CLASS_windowCOMP_Class.md).

**Exit Perform Mode** - press the **Esc**ape key while your cursor is over perform window to leave Perform mode and go back to the full TouchDesigner network editing interface. **Tip**: You may need to press **Shift-Esc** if the [CLASS_WindowCOMP] has the parameter 'Close on Escape Key' turned off.

## Configuration Options

In the Window Placement Dialog you can view all [CLASS_WindowCOMP]s in your project and configure them. The first column in the list, called **Perform Window**, lets you set which Window Component will be used by default for Perform Mode. This controls which will open when using the UI Perform Mode button or pressing F1.

The settings (size, location, behavior) for the window which opens are all set in [CLASS_WindowCOMP]'s parameters.

## Startup Options

A default TouchDesigner starts in Designer Mode, which is where you edit your network, nodes and parameters.

In the Window Placement Dialog, you can turn on "Start in Perform Mode" to force TouchDesigner to start in Perform Mode for this project. After changing this setting, save the project file and on restart the project will open directly into Perform Mode.

When TouchDesigner starts in Perform mode, the extra memory the Designer interface requires will not be used.

## Full-Screen Exclusive Mode (Windows Only)

Some GPU drivers (Nvidia notably) have the ability to enter a full-screen exclusive mode if the Perform Window is border-less and covers 100% of the desktop. Additionally, the desktop may need to be a 'single' monitor, either by being a single output, or by being joined into a combined output using features such as Nvidia Mosaic or AMD EyeFinity. When in full-screen exclusive mode, the output will be running in a higher performant state. The most important benefit of this is that you can achieve stutter-free playback. Without full-screen exclusive mode the Windows Desktop Compositor may not always show all of the frames TouchDesigner is generating. So even if you are running a perfect 60FPS, you may see stutters/frame drops, if not in full-screen exclusive mode.

You can tell that you are in this mode because if you alt-tab or switch windows, the entire desktop will flash/flicker as it switches back to normal desktop compositing mode.

## Tips

[REF_TouchPlayer] runs exclusively in Perform Mode. Your project's perform mode settings will determine how it runs in [REF_TouchPlayer].

If the project file has Privacy option is set, you cannot exit Perform mode back into Designer Mode.

You can also enter Perform Mode using python: `ui.performMode = True`. See [CLASS_UI](CLASS_UI_Class.md).

## See Also

[CLASS_WindowCOMP](CLASS_windowCOMP_Class.md), [REF_TouchPlayer](REF_TouchPlayer.md)
