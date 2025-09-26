---
category: REF
document_type: tutorial
difficulty: intermediate
time_estimate: 30-45 minutes
operators:
- MovieFileOut_TOP
- Timer_CHOP
- Parameter_CHOP
- CHOP_Execute_DAT
- Noise_TOP
- Rectangle_TOP
concepts:
- image_sequence_rendering
- non-real-time_rendering
- file_management
- python_automation
- component_building
- timer-based_control
- procedural_naming
- batch_rendering
prerequisites:
- TOP_basics
- CHOP_basics
- PY_Custom_Parameters
- python_scripting
workflows:
- pre-rendering_content
- archiving_generative_art
- high_quality_offline_rendering
- automated_rendering
- batch_processing
keywords:
- render to file
- export frames
- save image sequence
- non-real-time
- baking textures
- automated recording
- file naming
- python automation
- pre-render
- batch rendering
- N index
- timer control
tags:
- python
- automation
- export
- file_io
- non-real-time
- component
- tutorial
- batch
relationships:
  REF_MovieFileOut_TOP: strong
  CLASS_Timer_CHOP: strong
  CLASS_CHOPExecute_DAT: strong
  PY_Custom_Parameters: strong
  REF_Cache_TOP: medium
related_docs:
- REF_MovieFileOut_TOP
- CLASS_Timer_CHOP
- CLASS_CHOPExecute_DAT
- PY_Custom_Parameters
- REF_Cache_TOP
hierarchy:
  secondary: rendering
  tertiary: image_sequence_automation
question_patterns: []
common_use_cases:
- pre-rendering_content
- archiving_generative_art
- high_quality_offline_rendering
- automated_rendering
---

# Rendering Image Sequences Tutorial

<!-- TD-META
category: REF
document_type: tutorial
operators: [MovieFileOut_TOP, Timer_CHOP, Parameter_CHOP, CHOP_Execute_DAT, Noise_TOP, Rectangle_TOP]
concepts: [image_sequence_rendering, non-real-time_rendering, file_management, python_automation, component_building, timer-based_control, procedural_naming, batch_rendering]
prerequisites: [TOP_basics, CHOP_basics, PY_Custom_Parameters, python_scripting]
workflows: [pre-rendering_content, archiving_generative_art, high_quality_offline_rendering, automated_rendering, batch_processing]
related: [REF_MovieFileOut_TOP, CLASS_Timer_CHOP, CLASS_CHOPExecute_DAT, PY_Custom_Parameters, REF_Cache_TOP]
relationships: {
  "REF_MovieFileOut_TOP": "strong",
  "CLASS_Timer_CHOP": "strong",
  "CLASS_CHOPExecute_DAT": "strong",
  "PY_Custom_Parameters": "strong",
  "REF_Cache_TOP": "medium"
}
hierarchy:
  primary: "tutorials"
  secondary: "rendering"
  tertiary: "image_sequence_automation"
keywords: [render to file, export frames, save image sequence, non-real-time, baking textures, automated recording, file naming, python automation, pre-render, batch rendering, N index, timer control]
tags: [python, automation, export, file_io, non-real-time, component, tutorial, batch]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical tutorial for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 30-45 minutes
**Use for**: pre-rendering_content, archiving_generative_art, high_quality_offline_rendering

## 🔗 Learning Path

**Prerequisites**: [Top Basics] → [Chop Basics] → [Py Custom Parameters]
**This document**: REF reference/guide
**Next steps**: [REF MovieFileOut TOP] → [CLASS Timer CHOP] → [CLASS CHOPExecute DAT]

**Related Topics**: pre-rendering content, archiving generative art, high quality offline rendering

## Summary

Tutorial demonstrating automated image sequence rendering using Movie File Out TOP with Python automation and timer-based controls.

## Relationship Justification

Strong connection to Movie File Out TOP as the primary tool demonstrated. Links to Cache TOP for related caching workflows in rendering pipelines.

## Content

- [Introduction](#introduction)
- [Setup and Basic Animation](#setup-and-basic-animation)
- [Movie File Out Configuration](#movie-file-out-configuration)
  - [Image Type Selection](#image-type-selection)
  - [FPS Settings](#fps-settings)
  - [File Path Configuration](#file-path-configuration)
- [Component Parameters](#component-parameters)
  - [Folder Parameter](#folder-parameter)
  - [Record Parameter](#record-parameter)
  - [File Naming with N Index](#file-naming-with-n-index)
- [Automated Index Incrementing](#automated-index-incrementing)
- [Timer-Based Recording](#timer-based-recording)
  - [Record Length Parameter](#record-length-parameter)
  - [Timer Setup](#timer-setup)
  - [Parameter CHOP Integration](#parameter-chop-integration)
- [CHOP Execute Automation](#chop-execute-automation)
  - [Timer Initialization](#timer-initialization)
  - [Record Start Trigger](#record-start-trigger)
  - [Auto-Stop on Timer Complete](#auto-stop-on-timer-complete)
- [Final Implementation](#final-implementation)
- [Use Cases](#use-cases)

## Introduction

This tutorial covers how to render image sequences to a series of files using TouchDesigner's [CLASS_MovieFileOutTOP]. This technique is useful for non-real-time rendering, performance optimization, technical assessments, and client proposals. The approach demonstrates practical Python integration and file management within TouchDesigner.

## Setup and Basic Animation

Create a basic animated scene for testing:

1. Add a [CLASS_NoiseTOP] with `absTime.seconds*0.05` animation
2. Set resolution to 1024x1024 with period of 4
3. Create a second [CLASS_NoiseTOP] and wire into the second input
4. Add a [CLASS_RectangleTOP] for motion tracking
5. Animate the rectangle center with `(absTime.seconds % 1) - 0.5` for continuous looping

This setup provides visible motion to verify the image sequence rendering.

## Movie File Out Configuration

### Image Type Selection

Configure the [CLASS_MovieFileOutTOP] for image sequence output:

- **Type:** Set to `Image Sequence`
- **Image File Type:** Choose based on needs:
  - `JPEG` - Smaller file sizes
  - `PNG` - Better for transparency backgrounds

### FPS Settings

Set the target frame rate for the sequence using the `Movie FPS` parameter.

### File Path Configuration

Configure the output path using folder parameters for flexibility.

## Component Parameters

### Folder Parameter

Create a custom component with folder management:

1. Add a `Folder` parameter type
2. Set default value to `.` (current directory)
3. Use `parent.par.folder.eval()` in file path expressions

### Record Parameter

Add a `Record` parameter to control recording state:

```python
# In Movie File Out TOP file parameter:
parent.par.folder.eval() + "/" + "filename"
```

### File Naming with N Index

The `N` parameter controls iteration numbering:

- Small index: Individual frame numbers (0, 1, 2, 3...)
- Large index (N): Series numbers for different takes
- File naming pattern: `N.frame.ext` (e.g., `0.0.jpg`, `0.1.jpg`, `1.0.jpg`)

## Automated Index Incrementing

Set up automatic N incrementing for new recording sessions:

1. Add a [CLASS_ParameterCHOP] selecting the `record` parameter
2. Configure `Count` mode
3. Connect output to the Movie File Out TOP's `N` parameter
4. Each record session creates a new series automatically

## Timer-Based Recording

### Record Length Parameter

Add time-controlled recording:

1. Create a `Record Length` float parameter (default: 30)
2. Set label to include units: `"Record Length (S)"`

### Timer Setup

Configure a [CLASS_TimerCHOP] for duration control:

```python
# Timer length parameter:
parent.par.recordLength.eval()
```

### Parameter CHOP Integration

Use [CLASS_ParameterCHOP] to monitor both:

- `record` parameter
- `recordLength` parameter

## CHOP Execute Automation

### Timer Initialization

Create a [CLASS_CHOPExecuteDAT] to handle parameter changes:

```python
# When record length changes:
if channel.name == 'recordLength':
    op('timer1').par.initialize.pulse()
```

### Record Start Trigger

Start timer when recording begins:

```python
# When record goes from off to on:
if channel.name == 'record' and channel.val == 1:
    op('timer1').par.start.pulse()
```

### Auto-Stop on Timer Complete

Configure timer callback in [CLASS_TimerCHOP]:

```python
# Timer "On Done" callback:
parent.par.record.val = 0
```

## Final Implementation

The complete system provides:

- **Flexible file output** to any specified folder
- **Automatic series numbering** for multiple takes
- **Time-controlled recording** with customizable duration
- **Automatic start/stop** based on timer completion
- **Python-driven automation** for file management

## Use Cases

This image sequence rendering system is ideal for:

- **Performance optimization** - Pre-render heavy content for real-time playback
- **Technical assessments** - Demonstrate TouchDesigner proficiency
- **Client proposals** - Create high-quality preview materials
- **Non-real-time rendering** - Generate content at higher quality than real-time allows
- **Archival purposes** - Save specific iterations of generative content

The implementation showcases practical [PY_TouchDesigner] file management and Python integration patterns useful across many projects.
