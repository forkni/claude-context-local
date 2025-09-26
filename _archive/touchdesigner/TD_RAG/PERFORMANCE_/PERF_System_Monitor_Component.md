---
category: PERF
document_type: guide
difficulty: intermediate
time_estimate: 20-30 minutes
operators:
- Text_DAT
- Table_DAT
- Parameter_Execute_DAT
- Timer_CHOP
- Execute_DAT
- Base_COMP
- Container_COMP
concepts:
- performance_monitoring
- memory_leak_detection
- resource_management
- profiling
- python_extensions
- external_libraries
- system_diagnostics
prerequisites:
- component_basics
- PY_Python_in_Touchdesigner
- performance_fundamentals
workflows:
- performance_tuning
- project_debugging
- memory_leak_troubleshooting
- long_run_stability_testing
- system_health_monitoring
keywords:
- memory leak
- diagnostics
- profiling
- resource monitor
- system health
- cpu usage
- gpu usage
- ram
- vram
- psutil
- pynvml
- performance tool
- debug
- troubleshooting
- garbage collector
- extension
- python_dependencies
tags:
- python
- component
- tool
- diagnostics
- memory
- cpu
- gpu
- nvidia
- pip
- external_dependencies
- real_time
relationships:
  PERF_Optimize: strong
  PY_Python_in_Touchdesigner: strong
  PERF_Performance_Monitor_Dialog: strong
  REF_Perform_DAT: medium
  CLASS_SysInfo_Class: medium
related_docs:
- PERF_Optimize
- PERF_Performance_Monitor_Dialog
- PY_Python_in_Touchdesigner
- REF_Perform_DAT
- CLASS_SysInfo_Class
hierarchy:
  secondary: profiling_tools
  tertiary: system_monitor_component
question_patterns:
- How to optimize performance?
- TouchDesigner performance tips?
- Bottleneck identification?
- Real-time optimization?
common_use_cases:
- performance_tuning
- project_debugging
- memory_leak_troubleshooting
- long_run_stability_testing
---

# System Monitor Component

<!-- TD-META
category: PERF
document_type: guide
operators: [Text_DAT, Table_DAT, Parameter_Execute_DAT, Timer_CHOP, Execute_DAT, Base_COMP, Container_COMP]
concepts: [performance_monitoring, memory_leak_detection, resource_management, profiling, python_extensions, external_libraries, system_diagnostics]
prerequisites: [component_basics, PY_Python_in_Touchdesigner, performance_fundamentals]
workflows: [performance_tuning, project_debugging, memory_leak_troubleshooting, long_run_stability_testing, system_health_monitoring]
related: [PERF_Optimize, PERF_Performance_Monitor_Dialog, PY_Python_in_Touchdesigner, REF_Perform_DAT, CLASS_SysInfo_Class]
relationships: {
    "PERF_Optimize": "strong", 
    "PY_Python_in_Touchdesigner": "strong", 
    "PERF_Performance_Monitor_Dialog": "strong",
    "REF_Perform_DAT": "medium",
    "CLASS_SysInfo_Class": "medium"
}
hierarchy:
    primary: "optimization"
    secondary: "profiling_tools"
    tertiary: "system_monitor_component"
keywords: [memory leak, diagnostics, profiling, resource monitor, system health, cpu usage, gpu usage, ram, vram, psutil, pynvml, performance tool, debug, troubleshooting, garbage collector, extension, python_dependencies]
tags: [python, component, tool, diagnostics, memory, cpu, gpu, nvidia, pip, external_dependencies, real_time]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Performance optimization guide for real-time systems
**Difficulty**: Intermediate
**Time to read**: 20-30 minutes
**Use for**: performance_tuning, project_debugging, memory_leak_troubleshooting

**Common Questions Answered**:

- "How to optimize performance?" → [See relevant section]
- "TouchDesigner performance tips?" → [See relevant section]
- "Bottleneck identification?" → [See relevant section]
- "Real-time optimization?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Component Basics] → [Py Python In Touchdesigner] → [Performance Fundamentals]
**This document**: PERF reference/guide
**Next steps**: [PERF Optimize] → [PERF Performance Monitor Dialog] → [PY Python in Touchdesigner]

**Related Topics**: performance tuning, project debugging, memory leak troubleshooting

## Summary

This document describes a diagnostic tool for performance monitoring and memory leak detection. It provides comprehensive setup instructions and usage guidelines for tracking system health and operator-specific memory usage over time.

## Relationship Justification

Enhanced relationships to include Perform DAT for alternative profiling approaches and SysInfo class for system information access. Strengthened connection to Performance Monitor Dialog as they serve complementary diagnostic functions.

## Content

- [Introduction](#introduction)
- [Features](#features)
- [Setup and Configuration](#setup-and-configuration)
  - [Internal Operators](#internal-operators)
  - [External Dependencies](#external-dependencies)
- [Component Parameters](#component-parameters)
- [Usage Instructions](#usage-instructions)
- [Output Tables](#output-tables)
  - [SystemStats Table DAT](#systemstats-table-dat)
  - [OperatorMemoryLog Table DAT](#operatormemorylog-table-dat)
- [Troubleshooting](#troubleshooting)

## Introduction

The System Monitor is a diagnostic tool designed to help developers and artists identify performance bottlenecks and memory leaks within a TouchDesigner project. It provides both a high-level overview of system-wide resource usage and a precision tool for tracking down memory consumption on a per-operator basis.

This component is designed to be portable; you can drop it into any part of your network to analyze that specific section, making it invaluable for debugging large and complex projects.

## Features

- **System Health Overview:** Monitors system-wide CPU, RAM, GPU Utilization, and GPU Memory usage.
- **Targeted Memory Leak Detection:** Logs the specific CPU memory usage of individual operators within a defined scope, allowing you to pinpoint the source of a leak over time.
- **Configurable Search Scope:** The memory logging can be targeted to the component's parent container with a user-defined search depth.
- **Manual Memory Release:** Includes a function to manually trigger Python's garbage collector to free up unreferenced memory.
- **UI-Driven Controls:** All major functions are controlled via custom parameters on the component's UI.

## Setup and Configuration

For the component to function correctly, it must contain the following internal operators with these exact names:

### Internal Operators

- `SystemMonitorExt` ([CLASS_TextDAT_Class](CLASS_TextDAT_Class.md)): Contains the main Python extension class.
- `SystemStats` ([CLASS_TableDAT_Class](CLASS_TableDAT_Class.md)): Displays the general system health snapshot.
- `OperatorMemoryLog` ([CLASS_TableDAT_Class](CLASS_TableDAT_Class.md)): Logs the memory usage of individual operators over time.
- `parexec1` ([CLASS_ParameterExecuteDAT_Class](CLASS_ParameterExecuteDAT_Class.md)): Handles the UI button controls.
- `timer1` ([CLASS_TimerCHOP_Class](CLASS_TimerCHOP_Class.md)): Drives the periodic logging.
- `timer_callbacks` ([CLASS_ExecuteDAT_Class](CLASS_ExecuteDAT_Class.md)): Script that runs when the timer1 completes a cycle.
- `on_exit_callbacks` ([CLASS_ExecuteDAT_Class](CLASS_ExecuteDAT_Class.md)): Ensures clean shutdown when the project closes.

### External Dependencies

This component requires two external Python libraries. You must install them into TouchDesigner's Python environment for the component to work.

**psutil:** For accessing system and process information.

```bash
# In a command prompt/terminal
pip install psutil
```

**pynvml:** For accessing NVIDIA GPU information. **Note:** This is for NVIDIA GPUs only.

```bash
# In a command prompt/terminal
pip install pynvml
```

## Component Parameters

The component is controlled by a set of custom parameters, typically found on a "Settings" or "Actions" page.

| Parameter Label | par.Name | Description |
|---|---|---|
| Log Threshold (KB) | `Logthreshold` | Sets the minimum memory usage (in Kilobytes) an operator must have to be included in the OperatorMemoryLog. Lower this to 1 or 5 to detect slow leaks. |
| Search Depth | `Searchdepth` | Controls how many levels deep the logger will search from its parent container. A value of 1 checks only the direct children. |
| Resource Snapshot | `Resoursesnapshot` | (Pulse) Manually updates the SystemStats table and prints the results to the Textport. |
| Release Memory | `Releasememory` | (Pulse) Manually triggers Python's garbage collector to free unreferenced memory. |
| Clear Operator Log | `Clearlog` | (Pulse) Clears all data from the OperatorMemoryLog table to start a fresh session. |

## Usage Instructions

This is the primary workflow for diagnosing a slow memory leak:

1. **Place the Component:** Drag the `SystemMonitorExt` component inside the container ([CLASS_BaseCOMP_Class](CLASS_BaseCOMP_Class.md) or [CLASS_ContainerCOMP_Class](CLASS_ContainerCOMP_Class.md)) where you suspect the leak is occurring.

2. **Configure Parameters:**
   - Set the `Log Threshold (KB)` to a low value, like 5.
   - Set the `Search Depth` to a value that covers the complexity of the container you are analyzing (e.g., 3 or 4).

3. **Start Monitoring:** The [CLASS_TimerCHOP_Class](CLASS_TimerCHOP_Class.md) inside the component should be running. It will automatically trigger the `log_operator_memory` function at its set interval.

4. **Wait and Observe:** Let your project run for an extended period (several hours or more). The `OperatorMemoryLog` DAT will gradually accumulate data.

5. **Analyze the Results:**
   - Right-click the `OperatorMemoryLog` DAT and save its contents as a `.csv` file.
   - Open the `.csv` file in a spreadsheet application (Excel, Google Sheets, etc.).
   - Sort the data by the `path` column, then by the `timestamp` column.
   - Look for an operator whose `cpu_memory_kb` value consistently increases with each timestamp. This is the source of your leak.

## Output Tables

### SystemStats Table DAT

This table provides a high-level snapshot of your system's health. It is useful for understanding the overall context in which your project is running.

- `td_process_memory` - The RAM used by the TouchDesigner process only.
- `system_cpu_usage` - Total CPU usage by all applications.
- `system_ram_usage` - Total RAM usage by all applications.
- `gpu_utilization` - Total workload on the GPU.
- `gpu_memory_usage` - Total VRAM used on the GPU.

### OperatorMemoryLog Table DAT

This is the precision tool for finding leaks. It logs the memory usage of individual operators over time.

- `path` - The full path to the operator.
- `name` - The name of the operator.
- `cpu_memory_kb` - The operator's specific CPU memory usage in Kilobytes. This is the value to watch for increases.
- `timestamp` - The time the log entry was recorded.

## Troubleshooting

**Error on Startup: "Table DAT not found":** This means the extension initialized before the required [CLASS_TableDAT_Class](CLASS_TableDAT_Class.md)]s (`SystemStats`, `OperatorMemoryLog`) were created or named correctly. Ensure the nodes exist with the correct names inside the component and re-initialize the extension by pulsing the `Re-Init Extensions` parameter on the component's "Extensions" page.

**OperatorMemoryLog is empty:** The `Log Threshold (KB)` parameter is likely set too high. Lower it to a smaller value to capture operators with low memory usage.
