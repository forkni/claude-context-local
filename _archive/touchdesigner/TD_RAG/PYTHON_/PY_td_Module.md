---
category: MODULE
document_type: reference
difficulty: intermediate
time_estimate: 15-20 minutes
operators:
- Text_DAT
concepts:
- python_scripting
- global_scope
- operator_referencing
- api_structure
- asynchronous_execution
- global_objects
prerequisites:
- Python_fundamentals
workflows:
- scripted_automation
- dynamic_network_control
- parameter_expressions
- debugging
keywords:
- td module
- python api
- global objects
- op()
- ops()
- me
- parent()
- root
- absTime
- project
- ui
- app
- run()
- debug()
- passive()
tags:
- python
- scripting
- global
- api
- core
- module
relationships:
  PY_Python_Classes_and_Modules: strong
  CLASS_OP_Class: strong
  CLASS_App_Class: strong
  CLASS_Project_Class: strong
  CLASS_UI_Class: strong
  TDU_Module: medium
related_docs:
- PY_Python_Classes_and_Modules
- TDU_Module
- CLASS_OP_Class
- CLASS_App_Class
- CLASS_Project_Class
- CLASS_UI_Class
hierarchy:
  secondary: fundamentals
  tertiary: td_module
question_patterns: []
common_use_cases:
- scripted_automation
- dynamic_network_control
- parameter_expressions
- debugging
---

# td Module

## 🎯 Quick Reference

**Purpose**: Module reference for TouchDesigner Python API
**Difficulty**: Intermediate
**Time to read**: 15-20 minutes
**Use for**: scripted_automation, dynamic_network_control, parameter_expressions

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals]
**This document**: MODULE reference/guide
**Next steps**: [PY Python Classes and Modules] → [TDU Module] → [CLASS OP Class]

**Related Topics**: scripted automation, dynamic network control, parameter expressions

<!-- TD-META
category: MODULE
document_type: reference
operators: [Text_DAT]
concepts: [python_scripting, global_scope, operator_referencing, api_structure, asynchronous_execution, global_objects]
prerequisites: [Python_fundamentals]
workflows: [scripted_automation, dynamic_network_control, parameter_expressions, debugging]
related: [PY_Python_Classes_and_Modules, TDU_Module, CLASS_OP_Class, CLASS_App_Class, CLASS_Project_Class, CLASS_UI_Class]
relationships: {
"PY_Python_Classes_and_Modules": "strong", 
"CLASS_OP_Class": "strong", 
"CLASS_App_Class": "strong", 
"CLASS_Project_Class": "strong", 
"CLASS_UI_Class": "strong", 
"TDU_Module": "medium"
}
hierarchy:
  "primary": "scripting"
  "secondary": "fundamentals"
  "tertiary": "td_module"
keywords: [td module, python api, global objects, op(), ops(), me, parent(), root, absTime, project, ui, app, run(), debug(), passive()]
tags: [python, scripting, global, api, core, module]
TD-META -->

## Content

- [Members](#members)
- [Methods](#methods)
- [Python Classes and Modules](#python-classes-and-modules)
- [Operator Related Classes](#operator-related-classes)
- [Helper Classes](#helper-classes)
- [Standard Python Modules](#standard-python-modules)
- [TouchDesigner Utility Modules and Python Utilities](#touchdesigner-utility-modules-and-python-utilities)
- [3rd Party Packages](#3rd-party-packages)
- [Installing Custom Packages and Modules](#installing-custom-packages-and-modules)

The td module contains all TouchDesigner related Python classes and utilities. All td module members and methods are imported when the application launches and are automatically available in scripts, expressions, and the textport.

For additional helpful Python classes and utilities not directly related to TouchDesigner, see the Tdu Module

## Members

me → OP (Read Only):

Reference to the current operator that is being executed or evaluated. This can be used in parameter expressions, or DAT scripts.

absTime → AbsTime (Read Only):

Reference to the AbsTime object.

app → App (Read Only):

Reference to the application installation.

debug(*args)→ None:

Print all args and extra debug info (default is DAT and line number) to texport. To change behavior, use the debugControl component or tdu.debug.setStyle function. See debug module for more info
TIP: Use debug instead of print when debugging Python scripts in order to see object types and the source of the output.

ext → Ext (Read Only):

Reference to the extension searching object. See extensions for more information.

families → dict (Read Only):

A dictionary containing a list of operator types for each operator family.

for a in families['SOP']:

# do something with a

licenses → Licenses (Read Only):

Reference to the currently installed licences.

mod → MOD (Read Only):

Reference to the Module On Demand object.

monitors → Monitors (Read Only):

Reference to the group of available monitors.

op → Shortcut (Read Only):

The operator finder object, for accessing operators through paths or shortcuts. Note: a version of this method that searches relative to a specific operator is also in OP Class.

op(pattern1, pattern2..., includeUtility=False) → OP or None

Returns the first OP whose path matches the given pattern, relative to root. Will return None if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.

pattern - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
includeUtility (Optional) - if True, allow Utility nodes to be returned. If False, Utility operators will be ignored.
b = op('project1')
b = op('foot*', 'hand*')
b = op(154)
op.shortcut → OP

An operator specified with by a Global OP Shortcut. If no operator exists an exception is raised. These shortcuts are global, and must be unique. That is, cutting and pasting an operator with a Global OP Shortcut specified will lead to a name conflict. One shortcut must be renamed in that case. Furthermore, only components can be given Global OP Shortcuts.
shortcut - Corresponds to the Global OP Shortcut parameter specified in the target operator.
b = op.Videoplayer
To list all Global OP Shortcuts:

for x in op:
 print(x)
opex → Shortcut (Read Only):

An operator finder object, for accessing operators through paths or shortcuts. Works like the op() shortcut method, except it will raise an exception if it fails to find the node instead of returning None as op() does. This is now the recommended way to get nodes in parameter expressions, as the error will be more useful than, for example, NoneType has no attribute "par", that is often seen when using op(). Note: a version of this method that searches relative to '/' is also in the global td module.

op(pattern1, pattern2..., includeUtility=False) → OP

Returns the first OP whose path matches the given pattern, relative to the inside of this operator. Will return None if nothing is found. Multiple patterns may be specified which are all added to the search. Numeric OP ids may also be used.

pattern - Can be string following the Pattern Matching rules, specifying which OP to return, or an integer, which must be an OP Id. Multiple patterns can be given, the first matching OP will be returned.
includeUtility (Optional) - if True, allow Utility nodes to be returned. If False, Utility operators will be ignored.
parent → Shortcut (Read Only):

The Parent Shortcut object, for accessing parent components through indices or shortcuts.

Note: a version of this method that searches from a specific operator is also in OP Class.

parent(n) OP or None

The nth parent of the current operator. If n not specified, returns the parent. If n = 2, returns the parent of the parent, etc. If no parent exists at that level, None is returned.

n - (Optional) n is the number of levels up to climb. When n = 1 it will return the operator's parent.
p = parent(2) #grandfather
parent.shortcut OP

A parent component specified with a shortcut. If no parent exists an exception is raised.

shortcut - Corresponds to the Parent Shortcut parameter specified in the target parent.
   n = parent.Videoplayer
See also Parent Shortcut for more examples.

iop → Shortcut (Read Only):

The Internal Operator Shortcut object, for accessing internal shortcuts. Note: a version of this method that searches from a specific operator is also in OP Class.

ipar → Shortcut (Read Only):

The Internal Operator Parameter Shortcut object, for accessing internal shortcuts. Note: a version of this method that searches from a specific operator is also in OP Class.

project → Project (Read Only):

Reference to the project session.

root → baseCOMP (Read Only):

Reference to the topmost root operator.

runs → Runs (Read Only):

Reference to the runs object, which contains delayed executions.

sysinfo → SysInfo (Read Only):

Reference to the system information.

ui → UI (Read Only):

Reference to the ui options.

## Methods

ops(pattern1, pattern2.., includeUtility=False)→ List[OP]:

Returns a (possibly empty) list of OPs that match the patterns, relative to this OP.

Multiple patterns may be provided. Numeric OP ids may also be used.

pattern - Can be string following the Pattern Matching rules, specifying which OPs to return, or an integer, which must be an OP Id. Multiple patterns can be given and all matched OPs will be returned.
includeUtility (Optional) - if True, allow Utility nodes to be returned. If False, Utility operators will be ignored.
Note a version of this method that searches relative to an operator is also in the OP Class.

newlist = n.ops('arm*', 'leg*', 'leg5/foot*')
passive(OP)→ OP:

Returns a passive version of the operator. Passive OPs do not cook before their members are accessed.

run(script, arg1, arg2..., endFrame=False, fromOP=None, asParameter=False, group=None, delayFrames=0, delayMilliSeconds=0, delayRef=me)→ Run:

Run the script, returning a Run object which can be used to optionally modify its execution. This is most often used to run a script with a delay, as specified in the delayFrames or delayMilliSeconds arguments. See Run Command Examples for more info.

script - A string that is the script code to execute.
arg - (Optional) One or more arguments to be passed into the script when it executes. They are accessible in the script using a tuple named args.
endFrame - (Keyword, Optional) If True, the execution will be delayed until the end of the current frame.
fromOP - (Keyword, Optional) Specifies an optional operator from which the execution will be run relative to.
asParameter - (Keyword, Optional) When fromOP used, run relative to a parameter of fromOP.
group - (Keyword, Optional) Can be used to specify a string label for the group of Run objects this belongs to. This label can then be used with the td.runs object to modify its execution.
delayFrames - (Keyword, Optional) The number of frames to wait before executing the script.
delayMilliSeconds - (Keyword, Optional) The number of milliseconds to wait before executing the script. This value is rounded to the nearest frame.
delayRef - (Keyword, Optional) Specifies an optional operator from which the delay time is derived. You can use your own independent time component or op.TDResources, a built-in independent time component.
fetchStamp(key, default)→ value:

Return an object from the global stamped parameters. If the item is not found, the default is returned instead. Parameters can be stamped with the Copy SOP.

key - The name of the entry to retrieve.
default - If no item is found then the passed value is returned instead.
v = fetchStamp('sides', 3)
var(varName)→ str:

Find the value for the given variable.

varExists(varName)→ bool:

Returns true if the variable is defined.

varOwner(varName)→ OP | None:

Returns the operator that defines the variable, or None if it's not defined.

isMainThread()→ bool:

Is True when called from the main application editing thread. Any calls that access operators, etc., must be called from the main thread.

clear()→ None:

Clear the textport of all text.

## Python Classes and Modules

More detailed information about the contents of td module:

The following list of important Python classes and modules is roughly grouped together by subject.

## See also

[PY_Python_Classes_and_Modules.md](PY_Python_Classes_and_Modules.md)

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
[PY_Python_in_Touchdesigner.md](PY_Python_in_Touchdesigner.md)
