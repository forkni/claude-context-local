---
title: "SudoMagic Style Guide: Preferences"
category: STYLEGUIDES
document_type: "guide"
difficulty: "beginner"
time_estimate: "5-10 minutes"
user_personas: ["script_developer", "technical_artist", "beginner_user"]
operators: []
concepts: ["style_guide", "best_practices", "preferences", "configuration"]
prerequisites: ["TouchDesigner_basics"]
workflows: ["development_environment", "ide_setup"]
keywords: ["style guide", "coding standards", "touchdesigner", "preferences", "configuration", "grid snap", "external editor"]
tags: ["guide", "style", "preferences", "configuration"]
related_docs: ["REF_Touchdesigner_startup_configuration_with_Environmental_Variables"]
---

# SudoMagic Style Guide: Preferences

This guide covers recommended preference settings in TouchDesigner to ensure consistency and a better development experience.

## Preferences Overview

Preferences in TouchDesigner are personal default settings for various options, accessible through the **Edit** menu or the shortcut **Alt + P**.

## Recommended Settings

*   **Grid Snap**: Set to "fine" to maintain alignment with existing projects.
*   **Resize**: Turn off "Resize TOPs and COMPs" in the Network preferences to ensure a uniform look for operators.
*   **External Editors**: Configure an external text editor like Sublime Text or VS Code in the DATs tab for better syntax highlighting and advanced features.

## Preferences File Location

You can find the preferences file at:
*   **Windows**: `C:/Users/{username}/AppData/Local/Derivative/TouchDesigner/pref.txt`
*   **macOS**: `~Library/Application Support/Derivative/TouchDesigner/pref.txt`
