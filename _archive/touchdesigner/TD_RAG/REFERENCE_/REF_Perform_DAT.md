---
category: REF
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- Perform_DAT
- Info_CHOP
- Panel_COMP
- Render_TOP
- Render_Pass_TOP
concepts:
- performance_profiling
- cook_time_logging
- frame_rate_analysis
- bottleneck_detection
- performance_diagnostics
- timing_analysis
prerequisites:
- performance_fundamentals
- REF_Cook
- DAT_basics
- profiling_concepts
workflows:
- performance_tuning
- troubleshooting_frame_drops
- identifying_bottlenecks
- logging_performance_data
- system_monitoring
keywords:
- performance
- profiling
- diagnostics
- benchmark
- cook time
- frame rate
- fps
- logging
- bottleneck
- trigger
- draw time
- cpu time
- gpu time
- trigger threshold
- timing data
tags:
- cpu
- gpu
- performance
- real-time
- profiling
- cook
- bottleneck
- fps
- diagnostics
- logging
- monitoring
relationships:
  PERF_Performance_Monitor_Dialog: strong
  REF_Cook: strong
  PERF_Optimize: strong
  PERF_System_Monitor_Component: medium
  CLASS_Probe_COMP: medium
related_docs:
- PERF_Performance_Monitor_Dialog
- PERF_Optimize
- REF_Cook
- PERF_System_Monitor_Component
- CLASS_Probe_COMP
hierarchy:
  secondary: profiling
  tertiary: perform_dat
question_patterns: []
common_use_cases:
- performance_tuning
- troubleshooting_frame_drops
- identifying_bottlenecks
- logging_performance_data
---

# Perform DAT

<!-- TD-META
category: REF
document_type: reference
operators: [Perform_DAT, Info_CHOP, Panel_COMP, Render_TOP, Render_Pass_TOP]
concepts: [performance_profiling, cook_time_logging, frame_rate_analysis, bottleneck_detection, performance_diagnostics, timing_analysis]
prerequisites: [performance_fundamentals, REF_Cook, DAT_basics, profiling_concepts]
workflows: [performance_tuning, troubleshooting_frame_drops, identifying_bottlenecks, logging_performance_data, system_monitoring]
related: [PERF_Performance_Monitor_Dialog, PERF_Optimize, REF_Cook, PERF_System_Monitor_Component, CLASS_Probe_COMP]
relationships: {
  "PERF_Performance_Monitor_Dialog": "strong",
  "REF_Cook": "strong",
  "PERF_Optimize": "strong",
  "PERF_System_Monitor_Component": "medium",
  "CLASS_Probe_COMP": "medium"
}
hierarchy:
  primary: "dats"
  secondary: "profiling"
  tertiary: "perform_dat"
keywords: [performance, profiling, diagnostics, benchmark, cook time, frame rate, fps, logging, bottleneck, trigger, draw time, cpu time, gpu time, trigger threshold, timing data]
tags: [cpu, gpu, performance, real-time, profiling, cook, bottleneck, fps, diagnostics, logging, monitoring]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical reference for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: performance_tuning, troubleshooting_frame_drops, identifying_bottlenecks

## 🔗 Learning Path

**Prerequisites**: [Performance Fundamentals] → [Ref Cook] → [Dat Basics]
**This document**: REF reference/guide
**Next steps**: [PERF Performance Monitor Dialog] → [PERF Optimize] → [REF Cook]

**Related Topics**: performance tuning, troubleshooting frame drops, identifying bottlenecks

## Summary

Reference for Perform DAT which logs various performance metrics in table format for diagnostic and profiling purposes.

## Relationship Justification

Strong connections to other performance monitoring tools. Added connection to System Monitor Component and Probe COMP for comprehensive performance analysis workflows.

## Content

- [Summary](#summary)
- [Parameters - Perform Page](#parameters---perform-page)
  - [Active](#active)
  - [Active Pulse](#active-pulse)
  - [Trigger Mode](#trigger-mode)
  - [Trigger Threshold](#trigger-threshold)
  - [Logging Options](#logging-options)
- [Parameters - Common Page](#parameters---common-page)
- [Info CHOP Channels](#info-chop-channels)
  - [Common DAT Info Channels](#common-dat-info-channels)
  - [Common Operator Info Channels](#common-operator-info-channels)

## Summary

The Perform DAT logs various performance times in a Table DAT format. These benchmarks are similar to those reported by the [REF_PerformanceMonitor].

## Parameters - Perform Page

### Active

**Active** `active` - Turns logging on/off. The DAT will continuously log while Active is On.

### Active Pulse

**Active Pulse** `activepulse` - Use resetpulse button to grab a single frame snapshot.

### Trigger Mode

**Trigger Mode** `triggermode` - Offers two options for when to trigger a refresh of the logs.

### Trigger Threshold

**Trigger Threshold** `triggerthreshold` - This is the amount of time, in milliseconds, that a frame must exceed to cause the DAT to log and output the frame's timing. For example to see what happens when a frame takes more that 33 ms to cook, put this parameter to 33.

### Logging Options

**Cook Time** `logcook` - Logs the cook time of operators.

**Export Time** `logexport` - Logs time spent exporting CHOP channels.

**Viewport Draw Time** `logviewport` - Logs time to draw 3D geometry and SOP viewers.

**Movie Time** `logmovie` - Logs time taken to read video and audio from movie files.

**Draw Channels Time** `logdrawchannels` - Logs time to draw channels in CHOP viewers.

**Object View Time** `logobjectview` - Logs time to draw objects in 3D viewers.

**Custom Panel Time** `logcustompanel` - Logs time taken by custom panels build with [CLASS_PanelCOMP]s.

**MIDI Time** `logmidi` - Logs time spent on MIDI.

**Graphics Time** `loggraphics` - Logs various graphics system calls, such as time spent waiting for the graphics card, calls to the graphic driver, converting TOP data to CHOPs, etc.

**Frame Length** `logframelength` - Logs total frame time in milliseconds (ms).

**Misc** `logmisc` - Logs miscellaneous times that do not fit into other categories.

**Script** `logscript` - Logs time spent running scripts.

**Render** `logrender` - Logs time spend by [CLASS_RenderTOP] or [CLASS_RenderPassTOP]s.

## Parameters - Common Page

**Language** `language` - Select how the DAT decides which script language to operate on.

**Edit/View Extension** `extension` - Select the file extension this DAT should expose to external editors.

**Custom Extension** `customext` - Specifiy the custom extension.

**Word Wrap** `wordwrap` - Enable Word Wrap for Node Display.

## Info CHOP Channels

Extra Information for the Perform DAT can be accessed via an [CLASS_InfoCHOP].

### Common DAT Info Channels

- `num_rows` - Number of rows in this DAT.
- `num_cols` - Number of columns in this DAT.

### Common Operator Info Channels

- `total_cooks` - Number of times the operator has cooked since the process started.
- `cook_time` - Duration of the last cook in milliseconds.
- `cook_frame` - Frame number when this operator was last cooked relative to the component timeline.
- `cook_abs_frame` - Frame number when this operator was last cooked relative to the absolute time.
- `cook_start_time` - Time in milliseconds at which the operator started cooking in the frame it was cooked.
- `cook_end_time` - Time in milliseconds at which the operator finished cooking in the frame it was cooked.
- `cooked_this_frame` - 1 if operator was cooked this frame.
- `warnings` - Number of warnings in this operator if any.
- `errors` - Number of errors in this operator if any.
