---
title: "Window Placement Dialog"
category: "TD_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "10 minutes"
user_personas: ["developer", "designer", "live_performer", "installation_artist"]
completion_signals: ["can_configure_windows_for_perform_mode", "knows_how_to_set_startup_mode"]
operators: ["WindowCOMP"]
concepts: ["window_placement", "perform_mode", "designer_mode", "multiple_monitors", "ui"]
prerequisites: ["TD_Perform_Mode", "TD_DesignerMode"]
workflows: ["multi_window_setups", "performance_configuration", "kiosk_mode_setup"]
keywords: ["window", "placement", "dialog", "perform", "designer", "monitor", "alt-w"]
tags: ["core", "concept", "ui", "workflow", "windowing"]
related_docs:
- "COMP_WindowCOMP"
- "TD_Perform_Mode"
- "TD_DesignerMode"
- "REF_MultipleMonitors"
- "CLASS_UI_Class"
---

# Window Placement Dialog

## Content
- [Description](#description)
- [Designer and Perform Mode](#designer-and-perform-mode)
- [Multiple Monitor Settings](#multiple-monitor-settings)
- [Tips](#tips)

## Description

The Window Placement Dialog (`Alt-w`) manages window placement and determines whether TouchDesigner starts in [TD_Perform_Mode] or [TD_Designer_Mode].

Normally you press `F1` and `Esc` to get in and out of Perform Mode, which uses the single `Window Component` `/perform`. The default .toe file contains one `Window Component` located at `/perform` which has parameters to customize the location, look and behavior of the window when you go into Perform Mode.

The Window Placement Dialog at `Dialogs -> Window Placement` (`Alt-w`) helps with managing one or more `Window` components.

Here you see the list of existing `Window Components`, and for each you can open and close the window, choose it as the one that opens in Perform Mode, open its Parameter dialogs (`P` button) or open the network containing the `Window Component`.

It displays one row for each `Window` component in your entire .toe file. It is harmonized with the parameters of the `Window Component`: What you see/control in Window Placement is a summary of what you see/control in all the `Window Components` of your project.

The `Main Perform` column lets you choose which `Window` component it will use in Perform Mode, the default being `/perform`.

You can open the parameter dialog of each `Window` component (the `P` button), or open the network where the `Window` components are located (the arrow), or just open the window itself (`Open` button).

The `Start in Perform Mode` flag lets you choose to start TouchDesigner in Perform Mode or Designer Mode.

In the `Start Position` and `Custom Settings` sections, the Window Placement Dialog determines the position of the Designer Mode window.

The `Window Component` uses separate on/off pulse buttons to open and close the window, which can be triggered also with the `Open/Close` parameter `.pulse()` python method.

The `Window Component` also has a pulse parameter to temporarily open any `Window` component in Perform Mode, versus the one specified in the Window Placement Dialog.

The `Window Component` has a parameter (`Redraw`) to inform a window to not draw anything. It is useful when no output is needed on the main monitors, for example when you use the Oculus Rift, or when your system only outputs data via the network operators, or via the `Video Device Out TOP`, or other processes that do not render, such as audio processing or driving LED strips that don't use the video outs.

## Designer and Perform Mode

See [TD_Designer_Mode] and [TD_Perform_Mode] for more information.

## Multiple Monitor Settings

To setup multiple monitors, see [REF_MultipleMonitors] and use the `Window COMP`. For maximum performance, it is generally recommended to put your UI and all your outputs images into one large container for one `Window Component`, where possible.

## Tips

- You can go into/out-from Perform Mode using python: For example, `ui.PerformMode = True`. See [CLASS_UI_Class].
- You can make a window not appear in the list by putting a tag `'hide'` in the `Window Component`.
