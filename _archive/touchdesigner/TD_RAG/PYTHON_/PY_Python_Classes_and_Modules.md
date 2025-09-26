---
category: PY
document_type: index
difficulty: intermediate
time_estimate: 5-10 minutes
operators: []
concepts:
- python_api
- class_reference
- module_reference
- api_navigation
- comprehensive_index
- python_ecosystem
prerequisites:
- Python_fundamentals
workflows:
- api_exploration
- documentation_navigation
- learning_path_discovery
- comprehensive_reference
keywords:
- python classes
- python modules
- API reference
- class index
- module index
- TouchDesigner API
- python documentation
- comprehensive reference
- class list
- module list
tags:
- python
- api
- reference
- index
- documentation
- comprehensive
- classes
- modules
- navigation
relationships:
  PY_Python_Reference: strong
  MODULE_td_Module: strong
  CLASS_DAT_Class: medium
  CLASS_Vector_Class: medium
  CLASS_Matrix_Class: medium
related_docs:
- PY_Python_Reference
- MODULE_td_Module
- CLASS_DAT_Class
- CLASS_Vector_Class
- CLASS_Matrix_Class
hierarchy:
  secondary: api_reference
  tertiary: comprehensive_index
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- api_exploration
- documentation_navigation
- learning_path_discovery
- comprehensive_reference
---

# Python Classes and Modules

<!-- TD-META
category: PY
document_type: index
operators: []
concepts: [python_api, class_reference, module_reference, api_navigation, comprehensive_index, python_ecosystem]
prerequisites: [Python_fundamentals]
workflows: [api_exploration, documentation_navigation, learning_path_discovery, comprehensive_reference]
related: [PY_Python_Reference, MODULE_td_Module, CLASS_DAT_Class, CLASS_Vector_Class, CLASS_Matrix_Class]
relationships: {
  "PY_Python_Reference": "strong",
  "MODULE_td_Module": "strong",
  "CLASS_DAT_Class": "medium",
  "CLASS_Vector_Class": "medium",
  "CLASS_Matrix_Class": "medium"
}
hierarchy:
  primary: "scripting"
  secondary: "api_reference"
  tertiary: "comprehensive_index"
keywords: [python classes, python modules, API reference, class index, module index, TouchDesigner API, python documentation, comprehensive reference, class list, module list]
tags: [python, api, reference, index, documentation, comprehensive, classes, modules, navigation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting index for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 5-10 minutes
**Use for**: api_exploration, documentation_navigation, learning_path_discovery

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals]
**This document**: PY reference/guide
**Next steps**: [PY Python Reference] → [MODULE td Module] → [CLASS DAT Class]

**Related Topics**: api exploration, documentation navigation, learning path discovery

## Summary

Comprehensive index document listing all Python classes and modules available in TouchDesigner. Serves as a master reference and navigation aid for the entire Python API.

## Relationship Justification

Serves as comprehensive complement to Python Reference. Strong connection to td module as the core. Medium connections to major class examples to provide entry points into specific documentation.

## Content

- [Operator Related Classes](#operator-related-classes)
- [Helper Classes](#helper-classes)
- [Standard Python Modules](#standard-python-modules)
- [TouchDesigner Utility Modules and Python Utilities](#touchdesigner-utility-modules-and-python-utilities)
- [3rd Party Packages](#3rd-party-packages)
- [Installing Custom Packages and Modules](#installing-custom-packages-and-modules)

The following list of important Python classes and modules is roughly grouped together by subject:
[Python Reference](PY_Python_Reference.md)

Python Reference has an alphabetical list of all TouchDesigner Python pages on this wiki.

## Operator Related Classes

The following classes are Python interfaces for operators and objects that operators use. Individual operator classes (e.g. TextTOP Class and RampTOP Class) are not listed but do exist in the td module, and links to each can be found here or by clicking on the Python Help button in their parameter dialog. These classes are found in the td module so do not need to be imported.

OP Class - a TouchDesigner operator.
Connector Class - a wire connector for an OP. Lists of these can be found in OP.inputConnectors and OP.outputConnectors. Components also have COMP.inputCOMPConnectors and COMP.outputCOMPConnectors.
Page Class - a parameter page. Lists of these can be found in OP.pages and, on components and script operators, OP.customPages.
ParCollection Class (OP.par) - holds all the parameters for an OP.
Par Class - an individual parameter.
ParGroupCollection Class (OP.par) - holds all the parameter groups for an OP.
ParGroup Class - an individual parameter group.
SequenceCollection Class (OP.seq) - holds all the sequences for an OP.
Sequence Class - describes and controls a set of sequential parameters. Sequential parameters will have a reference to one of these objects in their sequence member.
SequenceBlock Class - used to access the parGroups of a specific block (set of parGroups) in a sequence.
CHOP Class - subclass of OPs defining CHOP operators.
Channel Class - a channel object. Accessed through a CHOP index or other CHOP members such as chan, chans etc.
Segment Class - describes a single segment from a Timer CHOP.
COMP Class - a subclass of OPs defining component operators.
ObjectCOMP Class - a subclass of COMPs defining Objects, used to create and render 3D scenes.
PanelCOMP Class - a subclass of COMPS defining Panel Components, used to create 2D UI elements.
Panel Class - a member of panelCOMPs containing all associated panel values. Accessed through panelCOMP.panel.
PanelValue Class - individual panel values. Accessed through the panel member of panelCOMPS and also in callbacks in the Panel Execute DAT.
ListAttributes Class - a collection of list attributes used in a ListCOMP.
ListAttribute Class - contains attributes defining a cell in a ListCOMP.
Actors Class - describes the set of all Actor COMPs used by the Bullet Solver COMP and Nvidia Flex Solver COMP. used in a BulletsolverCOMP or flexsolverCOMP.
Bodies Class - a collection of bodies used in an ActorCOMP.
Body Class - a single body (physics object) used in an ActorCOMP.
VFS Class - a COMP's Virtual File System
VFSFile Class - a virtual file contained within a Virtual File System.
DAT Class - a subclass of OPs defining DAT operators.
Cell Class - defines an individual cell of a DAT table.
Peer Class - describes the network connection originating a message in the callback functions found in oscinDAT, tcpipDAT, udpinDAT, udtinDAT.
MAT Class - a subclass of OPs defining MAT operators.
SOP Class - a subclass of OPs defining SOP operators.
Attributes Class - a collection of SOP attributes
Attribute Class - information about an entity such as its color, velocity, normal, and so on.
AttributeData Class - contains specific geometric Attribute values, associated with a Prim Class, Point Class, or Vertex Class.
Group Class - describes groups lists of Prim Class or Point Class.
Points Class - a collection of points.
Point Class - a single geometry point.
InputPoint Class - a special point object used in Point SOP parameters.
Prims Class - a collection of primitives.
Prim Class - a single geometry primitive.
Poly Class - a subclass of Prim defining a geometry polygon.
Mesh Class - a subclass of Prim defining a geometry mesh.
Bezier Class - a subclass of Prim defining a set of Bezier curves.
Vertex Class - a member of Prim defining a single geometry vertex.
TOP Class - a subclass of OPs defining TOP operators.
CUDAMemory Class - holds a reference to CUDA memory.
CUDAMemoryShape Class - describes the shape of a CUDA memory segment.
TextLine Class - a line of text in the Text TOP or Text SOP, after it has been formatted. Contains various members about the line such as it's text, position etc.

## Helper Classes

The following helper objects are part of the td module and can thus be accessed anywhere, including expressions, without imports (e.g. absTime.frame).

AbsTime Class (absTime) - information about absolute time
App Class (app) - information about the TouchDesigner app, including version, installation folders, etc.
Project Class (project) - information about the current TouchDesigner session
Tdu Module (tdu) - generic utilities for TouchDesigner not relating directly to TD objects.
ArcBall Class (tdu.ArcBall) - encapsulates many aspects of 3D viewer interaction.
Camera Class (tdu.Camera) - maintains a 3D position and orientation for a camera and provides multiple methods for manipulating the camera's position and direction.
Color Class (tdu.Color) - holds a 4 component color
Dependency Class (tdu.Dependency) - used to create Dependable Python data.
Matrix Class (tdu.Matrix) - holds a single 4x4 matrix for use in transformations. See ObjectCOMP Class for transforms of 3D objects.
Position Class (tdu.Position) - holds a 3 component position
Quaternion Class (tdu.Quaternion) - holds a quaternion object for 3D rotations
Timecode Class (tdu.Timecode) - holds a timecode value
Vector Class (tdu.Vector) - holds a 3 component vector
Licenses Class (licenses) - information about installed license objects
DongleList Class (licenses.dongles) - list of attached dongles
Dongle Class - an individual dongle connected to the system
License Class - a single instance of an installed license
ProductEntry Class - a dongle entry for a single dongle connected to the system
MOD Class (mod) - access to modules located in TouchDesigner DATs
Monitors Class (monitors) - access to information about all connected display devices
Monitor Class - an individual display device
Runs Class (runs) - information about all delayed run objects
Run Class - an individual delayed run object
SysInfo Class (sysInfo) - current system/hardware information
UI Class (ui) - information about application ui elements
Colors Class (ui.colors) - application colors
Options Class (ui.options) - configurable ui options
Panes Class (ui.panes) - collection of all panes open in the editor
Pane Class - an individual pane object
NetworkEditor Class - subclass of Pane that displays a network editor
Preferences Class (ui.preferences) - collection of TouchDesigner preferences
Undo Class (ui.undo) - tools for interacting with the undo system, including creating script-based undo steps

## Standard Python Modules

The td module also automatically imports a number of helpful standard modules, allowing them to be accessed in expressions through their namespace (e.g. math.cos(math.pi)):

collections - container datatypes
enum - support for enumerations
inspect - inspect live objects
math - mathematical functions
re - regular expression operations
sys - OS specific data and functions
traceback - stack utilities
warnings - warning control

## TouchDesigner Utility Modules and Python Utilities

The following contain extended Python utilities for use with TouchDesigner.

TDFunctions - A variety of utilities for advanced Python coding in TouchDesigner.
TDJSON - JSON utilities specific to TouchDesigner.
TDStoreTools - utilities for use with TouchDesigner's Storage and Dependency system.
TDResources (op.TDResources...) - not a module, but does contain system resources that can be accessed via Python. It includes system pop-up menu, button pop-up menu, pop-up dialog, and mouse resources.

## 3rd Party Packages

The following 3rd party packages are automatically installed with TouchDesigner. They are not in the td module, so must be imported explicitly to be used in scripts. The name in parentheses is the actual package name used (e.g. to use OpenCV, write this at top of script: import cv2). For information on adding or installing other Python modules, see Importing Modules.

attr 22.2.0 (attr) - Classes without boilerplate (legacy).
attrs 22.2.0 (attrs) - Classes without boilerplate.
Certifi 2022.12.07 (certifi) - Root Certificates for validating the trustworthiness of SSL certificates while verifying the identity of TLS hosts.
Chardet 5.1.0 (chardet) - The Universal Character Encoding Detector.
charset-normalizer 3.0.1 (charset_normalizer) - A library that helps you read text from an unknown charset encoding.
decorator 5.1.1 (decorator) - Define signature-preserving function decorators and decorator factories.
opencv-python (cv2) 4.8.0 - Pre-built CPU-only OpenCV packages for Python.
depthai (depthai) 2.24.0.0.dev0+7b57b28305368582d004d5c6ec2cffb66562f2e0 - Python bindings for C++ depthai-core library.
idna (idna) 3.4 - Support for the Internationalised Domain Names in Applications (IDNA) protocol.
jsonpath (jsonpath_ng) 1.5.3 - JSONPath tools for accessing and altering JSON structures.
jsonschema (jsonschema) 4.23.0 - jsonschema is an implementation of the JSON Schema specification for Python.
MWParserFromHell (mwparserfromhell) 0.6.4 - An easy-to-use and outrageously powerful parser for MediaWiki wikicode.
NumPy (numpy) 1.24.1 - Fundamental package for scientific computing with Python.
OAuthlib (oauthlib) 3.2.2 - Library to build OAuth and OpenID Connect servers.
packaging (packaging) 23.0 - Package tools including version handling, specifiers, markers, requirements, tags, utilities. Used for version string comparison.
pip (pip) 22.3.1 - pip is the package installer for Python. You can use pip to install packages from the Python Package Index and other indexes.
ply (ply) 3.11 - Parsing tools for lex and yacc.
Pygments (pygments) 2.14.0 - A syntax highlighting package written in Python.
pyparsing (pyparsing) 3.0.9 - A library of classes that client code uses to construct parsing grammar directly in Python code.
pyrankvote (pyrankvote) 2.0.5 - PyRankVote is a python library for different ranked-choice voting systems (sometimes called preferential voting systems) created by Jon Tingvold in June 2019.
pyrfc6266 (pyrfc6266) 1.0.2 - A python implementation of RFC 6266.
pyrsistent (pyrsistent) 0.19.3 - Pyrsistent is a number of persistent collections (by some referred to as functional data structures). Persistent in the sense that they are immutable.
Requests (requests) 2.28.2 - The only Non-GMO HTTP library for Python, safe for human consumption
Requests OAuthlib (requests_oauthlib) 1.3.1 - Easy-to-use Python interface for building OAuth1 and OAuth2 clients
six (six) 1.16.0 - Python 2 and 3 compatibility utilities.
smartypants (smartypants) 2.0.1 - a Python fork of SmartyPants.
tabulate (tabulate) 0.9.0 - Pretty-print tabular data in Python.
urllib3 (urllib3) 1.26.14 - HTTP client.
whats-that-code (whats_that_code) 0.1.4 - programming language detection library.
PyYAML (yaml) 6.0 - YAML parser and emitter.

## Installing Custom Packages and Modules

You can also install your own Python packages that are not included with TouchDesigner. For instructions, go here:
[Python in Touchdesigner](PY_Python_in_Touchdesigner.md)
