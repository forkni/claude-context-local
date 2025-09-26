---
title: "Safe Mode"
category: "TD_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "2 minutes"
user_personas: ["developer", "debugger"]
completion_signals: ["knows_how_to_open_a_file_in_safe_mode"]
operators: []
concepts: ["safe_mode", "crash", "debugging", "autosave"]
prerequisites: []
workflows: ["crash_recovery", "debugging"]
keywords: ["safe", "mode", "crash", "autosave", "debug"]
tags: ["core", "concept", "workflow", "debugging"]
related_docs: []
---

# Safe Mode

## Content
- [Overview](#overview)

## Overview

Safe Mode is enabled when you open a `CrashAutoSave.toe` file which is created when TouchDesigner crashes.

This mode opens the file in a static state where nothing will cook. This allows you to edit and navigate the file to investigate the cause of the crash, without the file crashing again.

You can rename any file and put "CrashAutoSave" at the beginning of the name to make it open in safe-mode. For example: `CrashAutoSave_myfilename.toe` will open in safe mode.
