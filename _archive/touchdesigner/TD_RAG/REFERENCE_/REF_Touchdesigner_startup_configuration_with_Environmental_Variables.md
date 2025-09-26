---
category: REF
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators: []
concepts:
- startup_configuration
- environment_variables
- multi-gpu_setup
- system_integration
- dynamic_project_loading
- automation
- deployment_strategies
prerequisites:
- command_line_basics
- python_scripting
- os_environment_variables
- system_administration
workflows:
- multi-computer_installations
- automated_project_launch
- dynamic_role_assignment
- gpu_affinity_management
- deployment_automation
keywords:
- environment variable
- startup
- configuration
- batch script
- .bat
- .cmd
- python
- os.environ
- var()
- gpu affinity
- multi-gpu
- launch script
- deployment
- automation
- system configuration
tags:
- python
- windows
- startup
- configuration
- multi-gpu
- scripting
- automation
- system
- deployment
relationships:
  REF_Variables: strong
  HARDWARE_Multiple_Graphics_Cards: medium
  HARDWARE_Syncing_Multiple_Computers: medium
  REF_TouchPlayer: medium
related_docs:
- REF_Variables
- HARDWARE_Multiple_Graphics_Cards
- HARDWARE_Syncing_Multiple_Computers
- REF_TouchPlayer
hierarchy:
  secondary: system_integration
  tertiary: environment_variables
question_patterns: []
common_use_cases:
- multi-computer_installations
- automated_project_launch
- dynamic_role_assignment
- gpu_affinity_management
---

# Environment Variables

<!-- TD-META
category: REF
document_type: guide
operators: []
concepts: [startup_configuration, environment_variables, multi-gpu_setup, system_integration, dynamic_project_loading, automation, deployment_strategies]
prerequisites: [command_line_basics, python_scripting, os_environment_variables, system_administration]
workflows: [multi-computer_installations, automated_project_launch, dynamic_role_assignment, gpu_affinity_management, deployment_automation]
related: [REF_Variables, HARDWARE_Multiple_Graphics_Cards, HARDWARE_Syncing_Multiple_Computers, REF_TouchPlayer]
relationships: {
  "REF_Variables": "strong", 
  "HARDWARE_Multiple_Graphics_Cards": "medium", 
  "HARDWARE_Syncing_Multiple_Computers": "medium",
  "REF_TouchPlayer": "medium"
}
hierarchy:
  primary: "fundamentals"
  secondary: "system_integration"
  tertiary: "environment_variables"
keywords: [environment variable, startup, configuration, batch script, .bat, .cmd, python, os.environ, var(), gpu affinity, multi-gpu, launch script, deployment, automation, system configuration]
tags: [python, windows, startup, configuration, multi-gpu, scripting, automation, system, deployment]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Technical guide for TouchDesigner development
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: multi-computer_installations, automated_project_launch, dynamic_role_assignment

## 🔗 Learning Path

**Prerequisites**: [Command Line Basics] → [Python Scripting] → [Os Environment Variables]
**This document**: REF reference/guide
**Next steps**: [REF Variables] → [HARDWARE Multiple Graphics Cards] → [HARDWARE Syncing Multiple Computers]

**Related Topics**: multi-computer installations, automated project launch, dynamic role assignment

## Summary

Guide for using environment variables to configure TouchDesigner startup behavior, particularly useful for multi-GPU setups and automated deployments.

## Relationship Justification

Strong connection to startup configuration and environment variables. Strong connection to multiple GPU setups for comprehensive system integration.

## Introduction

Environment Variables can be a handy way of passing in information to Touch without setting up a complicated file opening process. Some approaches benefit from using external files to indicate configuration, and at other times setting an environment variable is a better approach. One caution here is that working with Environment Variables can be invisible to the user – so in some cases while this is highly convenient, it can make trouble shooting slightly more complicated. A consideration for working around this challenge would be to set your environment variable at start programmatically. On Windows you might use a .bat or .cmd file. You can do the same operations with Python – of course this requires that you have Python installed on your machine, but it does provide for handy cross platform solution that’s easier to read.

The bit that’s worth thinking about is if you’re going to be running on systems with multiple GPUs. On those systems you have to set your GPU affinity at start. Derivative recommends doing this with a .bat or .cmd file. The trick for us here is that our schema of using a separate python file to indicate our indication will break – in the case of using a system with multiple GPUs, you likely want those two networks configured slightly differently. We can address this by using environment variables instead of a stand alone .json file. Depending on your workflow you might want to move this direction generally, but it’s a little more advanced than we have time to cover in this workshop.

At the 2019 TouchDesigner Summit in Montreal, Zoe and I are going to talk through a number of pieces about large system design and architecture. There’s always more to cover than there are hours in a day, and this little tid-bit, while very handy isn’t one that we have a lot of time to talk about at the workshop. Instead, I thought it would be handy to can leave this little reference here so you can come back to this part when you’re ready to push a little harder on start-up configuration. The big idea is that rather than using that outputlist.json file to tell us how to configure our project, we can instead use environment variables. Touch will read environment variables that are called before the application starts with the Python syntax:

var.("my_var_name")

We’d have to re-arrange a little logic in our project, but once we did that we’d be able to set our project’s configuration from another script at start-up. You could do this either with a .cmd script or with Python script. For the more advanced users, if you have another watcher application keeping tabs on your Touch project you’d want to add a mechanism to set an environment variable before starting the target application.

Here’s a quick run down of what this might look like if you’re running a batch script or a python script.

## Setting environment variables in a windows batch script

:: echo
:: Display messages on screen, turn command-echoing on or off.

:: "%~dp0"
:: The %~dp0 (that's a zero) variable when referenced within a Windows batch file will expand to
:: the drive letter and path of that batch file. The variables %0-%9 refer to the command line
:: parameters of the batch file. %1-%9 refer to command line arguments after the batch file name.
:: %0 refers to the batch file itself.

:: as a note this CMD or BAT needs to run as admin in order to work correctly

@echo off

set STARTUP=controller
timeout /t 1
start "%programfiles%\derivative\touchdesigner099\bin\touchdesigner099.exe" "%~dp0\your-toe-file-name.toe"

set STARTUP=node
timeout /t 1
start "%programfiles%\derivative\touchdesigner099\bin\touchdesigner099.exe" "%~dp0\your-toe-file-name.toe"
view rawenv-var-example.cmd hosted with ❤ by GitHub
Sample Batch Script
Looking closer a the syntax here, we can see that we point to the directory where our TouchDesigner executable is located (the appliaction we want to use), and then point to the file we want to open. But, what is %~dp0?! A little browsing through stack overflow can help illustrate what’s going on here:

The %~dp0 Variable
The %~dp0 (that’s a zero) variable when referenced within a Windows batch file will expand to the drive letter and path of that batch file.

The variables %0-%9 refer to the command line parameters of the batch file. %1-%9 refer to command line arguments after the batch file name. %0 refers to the batch file itself.

If you follow the percent character (%) with a tilde character (~), you can insert a modifier(s) before the parameter number to alter the way the variable is expanded. The d modifier expands to the drive letter and the p modifier expands to the path of the parameter.

Example: Let’s say you have a directory on C: called bat_files, and in that directory is a file called example.bat. In this case, %~dp0 (combining the d and p modifiers) will expand to C:\bat_files.

Read the Thread on stackoverflow
In other words, that little bit says that file we want to open is at the same location as the script we’re running.

## Setting environment variables with Python

import os

toe_file = 'path\\to\\your\\file.toe'

# set environment variable

toe_env_var             = 'controller'
os.environ['STARTUP']   = toe_env_var
os.startfile(toe_file)
print("startting file with {}".format(toe_env_var))

# set environment variable

toe_env_var             = 'node'
os.environ['STARTUP']   = toe_env_var
os.startfile(toe_file)
print("startting file with {}".format(toe_env_var))
