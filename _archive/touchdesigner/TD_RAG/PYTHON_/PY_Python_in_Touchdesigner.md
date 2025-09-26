---
category: PY
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators:
- Execute_DAT
- Script_DAT
- Script_CHOP
- Script_SOP
- Script_TOP
- ParameterExecute_DAT
- CHOPExecute_DAT
- SOPExecute_DAT
- TOPExecute_DAT
concepts:
- python_environment_setup
- package_management
- dependency_management
- cross-platform_scripting
- troubleshooting
- external_libraries
prerequisites:
- scripting_basics
- system_administration_basics
workflows:
- third_party_library_integration
- advanced_scripting_setup
- cross-platform_project_deployment
- development_environment_setup
keywords:
- python
- install
- package
- pip
- anaconda
- homebrew
- sys.path
- PYTHONPATH
- external library
- ImportError
- DLL load failed
- python 3.11
- site-packages
- dependency
- environment setup
- troubleshooting
tags:
- python
- environment
- setup
- windows
- macos
- arm
- intel
- pip
- dependency_management
- troubleshooting
- installation
- cross_platform
relationships:
  PY_Python_Reference: strong
  MODULE_td_Module: strong
  CLASS_App_Class: medium
  CLASS_Project_Class: medium
related_docs:
- PY_Python_Reference
- MODULE_td_Module
- CLASS_App_Class
- CLASS_Project_Class
hierarchy:
  secondary: environment_setup
  tertiary: installation_configuration
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- third_party_library_integration
- advanced_scripting_setup
- cross-platform_project_deployment
- development_environment_setup
---

# Python In TouchDesigner

<!-- TD-META
category: PY
document_type: guide
operators: [Execute_DAT, Script_DAT, Script_CHOP, Script_SOP, Script_TOP, ParameterExecute_DAT, CHOPExecute_DAT, SOPExecute_DAT, TOPExecute_DAT]
concepts: [python_environment_setup, package_management, dependency_management, cross-platform_scripting, troubleshooting, external_libraries]
prerequisites: [scripting_basics, system_administration_basics]
workflows: [third_party_library_integration, advanced_scripting_setup, cross-platform_project_deployment, development_environment_setup]
related: [PY_Python_Reference, MODULE_td_Module, CLASS_App_Class, CLASS_Project_Class]
relationships: {
  "PY_Python_Reference": "strong",
  "MODULE_td_Module": "strong",
  "CLASS_App_Class": "medium",
  "CLASS_Project_Class": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "environment_setup"
  tertiary: "installation_configuration"
keywords: [python, install, package, pip, anaconda, homebrew, sys.path, PYTHONPATH, external library, ImportError, DLL load failed, python 3.11, site-packages, dependency, environment setup, troubleshooting]
tags: [python, environment, setup, windows, macos, arm, intel, pip, dependency_management, troubleshooting, installation, cross_platform]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: third_party_library_integration, advanced_scripting_setup, cross-platform_project_deployment

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Scripting Basics] → [System Administration Basics]
**This document**: PY reference/guide
**Next steps**: [PY Python Reference] → [MODULE td Module] → [CLASS App Class]

**Related Topics**: third party library integration, advanced scripting setup, cross-platform project deployment

## Summary

Essential setup and troubleshooting guide for TouchDesigner Python environment. Critical for users working with external libraries and cross-platform deployment.

## Relationship Justification

Connected to Python Reference as foundational knowledge and td Module for core understanding. Links to App and Project classes since they provide system information useful for troubleshooting.

## Content

- [Python In TouchDesigner](#python-in-touchdesigner)
- [Python Classes and Modules Available in TouchDesigner](#python-classes-and-modules-available-in-touchdesigner)
- [td: TouchDesigner's Main Python Module](#td-touchdesigners-main-python-module)
- [TouchDesigner Utility Modules](#touchdesigner-utility-modules)
- [List of Python Utility Modules and Python Utilities](#list-of-python-utility-modules-and-python-utilities)
- [3rd Party Packages](#3rd-party-packages)
- [Installing Custom Python Packages](#installing-custom-python-packages)
- [Windows](#windows)
- [MacOS](#macos)
- [Intel Macs](#intel-macs)
- [ARM Macs](#arm-macs)
- [Python Gotchas](#python-gotchas)

## Python In TouchDesigner

TouchDesigner uses Python for scripting tasks. A custom Python build is included, with most of the features of a standard Python installation and a huge number of tools and utilities specific to working in the software.

Quick Start: Tutorial: Introduction to Python in TouchDesigner.
Common script examples: Python Tips
List of TouchDesigner Python Classes and Modules
Index of all Python pages in this wiki: Python Reference
In addition, selecting Help -> Python Examples in the TouchDesigner UI takes you to the PythonExamples.toe file with 100+ working examples.

## Python Classes and Modules Available in TouchDesigner

TouchDesigner includes all the modules in a standard Python installation plus the following:

## td: TouchDesigner's Main Python Module

All td module members and methods are available in scripts, expressions, and the textport. There is no need to import the module or its members explicitly. This is especially important in expressions, which don't allow import statements.

The following can be found in the td module:

Main TouchDesigner utilities - the most basic starting points for interacting with TouchDesigner, such as me and op().
TouchDesigner Python helper classes - important helper objects used to organize functions and information pertaining to a specific part of TouchDesigner.
Operator related classes - every Operator in TouchDesigner has an associated Python class in the td module. Their wiki pages can be accessed by clicking on the Python Help button in their parameter dialog. There are also a number of associated Python objects that are used when working with Operators.
Useful standard Python modules - the td module also automatically imports a number of helpful standard modules (e.g. math), allowing them to be accessed in expressions through their namespace.

## TouchDesigner Utility Modules

TouchDesigner also contains utility modules for advanced Python programming. Utility modules are not imported into the td module automatically. Instructions for their use can be found on their wiki pages.

## List of Python Utility Modules and Python Utilities

[Python Classes and Modules](PY_Python_Classes_and_Modules.md)

## 3rd Party Packages

TouchDesigner includes a number of 3rd party Python packages that are generally useful when working with the software. These are not included in the td module so must be imported explicitly.

List of 3rd party Python Packages.

## Installing Custom Python Packages

Part of the great power of Python is its access to the countless number of modules that have been created. If you want to use modules that are not included in the above, use the following steps:

Note: When adding your own version for a package that is already shipped with TouchDesigner, you might encounter unexpected behaviors. Many of our internal tools and palette components rely on NumPy and/or OpenCV. Loading different versions of Numpy and/or OpenCV is at your own risk. Some other issue could be with the following: considering a Package A with a dependency B, if updating your sys.path cause a different version of dependency B to load first, it could cause issues with Package A.

## Windows

Install a parallel copy of the same version of Python to the hard disk. The current version of Python shipped with TouchDesigner is 3.11. It can be found here. Use the most recent subversion of 3.11.
Alternatively, you can use a Python package and environment manager, such as Anaconda.
Install the package to the parallel python installation, following its normal installation procedure.
Launch Python and import the module manually to make sure there are no errors outside of the TouchDesigner context.
Once the module is successfully installed, you can import it in TouchDesigner following those next steps:

Under the Edit->Preferences menu, tick "Add External Python to Search Path". You can add the search path by modifying the Preference labelled "Python 32/64 bit Module Path". Multiple paths are separated by semicolons (;).

Finally you can modify the search path directly by either modifying the system environment variable PYTHONPATH or by firing an Execute DAT onStart() with the code snippet below.

import sys
mypath = "C:/Python311/Lib/site-packages" # use the correct path to your installation, sometimes in a user folder
if mypath not in sys.path:
 sys.path = [mypath] + sys.path
This script will prepend your custom Python install site-packages folder to your PATH. Prepending will make sure that your custom packages, when being imported, will have priority over any other package with a matching package name found in the path. If the package is not found in the custom path, but a package of the same name is found in the TouchDesigner Python site-packages folder then it will fall back on this package.

Users can also import packages from Python installations that weren't installed with the official Python installer but with alternative Python package and environment managers, such as Anaconda.

Examples of other useful Python modules are here.

## MacOS

On MacOS, use Homebrew to manage your Python installations. Follow the instructions on Homebrew's website to get started.

When Homebrew is installed, you can use the command brew install python@3.11 to install Python on your system. The @3.11 after python sets the version, which must be the same as TouchDesigner's.

## Intel Macs

On Intel's Macs, your default Homebrew path should be /usr/local/bin/brew

## ARM Macs

On ARM's Macs, your Homebrew path should be /opt/homebrew/bin/brew, for the native ARM homebrew. That is, when using the default Homebrew install command.

NOTE: In some cases, you might want to run Homebrew Rosetta. It is required if you are using the non-native / Intel TouchDesigner build and require a Python version that is not available as an ARM installer on MacOS.

To install Homebrew Rosetta, use the following command: arch -x86_64 /bin/bash -c "$(curl -fsSL <https://raw.githubusercontent.com/Homebrew/install/master/install.sh>)". Your Homebrew Rosetta path should be /usr/local/bin/brew.

If you have both Homebrew versions installed on your system, it is advised to add an alias for the Homebrew Rosetta installation. Use the following command in your terminal alias ibrew="arch -x86_64 /usr/local/bin/brew" where ibrew stands for Intel Brew. You can add this alias to your terminal profile so that it is persistent.

You can now use either brew install YOUR_APP_NAME or ibrew install YOUR_APP_NAME to install ARM or Intel formulas or casks respectively.

Continue with your python installation, matching TouchDesigner's Python, as described at the top of this MacOS section. Remember, if you followed the previous steps: when your are using the ARM native TouchDesigner build, use brew, if it's the Intel build running with Rosetta, use ibrew.

It can also be useful to add extra aliases, and precede them with an i when they are related to Intel / Rosetta, for Python itself, and pip:

alias iPY311=/usr/local/opt/python@3.11/bin/python3
alias iPIP311=/usr/local/opt/python@3.11/bin/pip3
Now, all you have to do is install your custom (Intel) Python 3.11 packages using iPIP311 install YOUR_PACKAGE_NAME.

Once the module is successfully installed, you can import it in TouchDesigner following these next steps:

Under the Edit->Preferences menu, tick "Add External Python to Search Path". You can add the search path by modifying the Preference labelled "Python 32/64 bit Module Path". Multiple paths are separated by semicolons (;). You can enter the path to your Python packages (usually <python install>/Lib/site-packages)

If the preferences method doesn't work for you, there are a couple other methods: you can modify the Python search path directly by either modifying the system environment variable PYTHONPATH or by setting up an Execute DAT onStart() with the code snippet below.

import sys
mypath = "/usr/local/lib/python3.11/site-packages" # TIP: This path is printed out in the terminal when installing this Python version with Homebrew
if mypath not in sys.path:
 sys.path = [mypath] + sys.path
This script will prepend your custom Python install site-packages folder to your PATH. Prepending will make sure that your custom packages, when being imported, will have priority over any other package with a matching package name found in the path. If the package is not found in the custom path, but a package of the same name is found in the TouchDesigner Python site-packages folder then it will fall back on this package.

## I am getting the following ImportError, what should I do ? ImportError: DLL load failed while importing […]

For most cases, it is better to document your environment and to share the project and steps to reproduced with the Derivative team at forum.derivative.ca

If you feel adventurous, what is likely to happen is that there is a dependency conflict causing an issue between TouchDesigner and the Python library you are attempting to use.

You can use a tool such as Dependencies to get an idea of which libraries your package is depending on. You drag n drop your python package binary, pyd, to the tool and you can see what are the libraries it is depending on. Then you investigate further to find what library might already be used by TouchDesigner, going through the dependencies of dependencies. Tedious.

## Python Gotchas

There are a few things in standard Python that can trip you up in TouchDesigner. If you find anything that's not included here, post in the forum!

Some TouchDesigner objects (especially parameters and CHOP channels) will try to act as the correct data type for their context. For example, a Float parameter object (myOp.par.Float1) will act like a floating point number in most cases, but it is still a parameter object. For example round(myOp.par.Float1) will not work. To get the actual value of a parameter or channel, use its .eval() method. If you think you may be encountering this problem, you can tell the difference by using the repr function. For example repr(myOp.par.Float1) will show that this is a parameter and not a number.
same goes with operator parameter types. if a parameter is a path to a CHOP, n.par.Chop usually works, but to be safe, n.par.Chop.eval() always works.
subprocess.Popen doesn't work with file-like objects. See this forum post for details.
Python threads don't have access to TouchDesigner objects. Search "threading" in the forum to see some workarounds. As of TouchDesigner 2023.31500+, see Python threading in TouchDesigner and Thread Manager.
