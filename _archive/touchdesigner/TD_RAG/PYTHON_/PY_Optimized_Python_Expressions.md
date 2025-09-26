---
category: PY
document_type: guide
difficulty: advanced
time_estimate: 15-25 minutes
operators:
- Perform_CHOP
- Expression_CHOP
- waveCHOP
- pointSOP
- primitiveSOP
- Parameter_Execute_DAT
concepts:
- performance_optimization
- expression_optimization
- cached_expressions
- parameter_expressions
- python_engine_optimization
- performance_profiling
prerequisites:
- Python_fundamentals
- parameter_basics
- MODULE_td_Module
workflows:
- performance_tuning
- expression_optimization
- parameter_expression_development
- large_project_optimization
keywords:
- optimized expressions
- cached expressions
- expression engine
- performance
- parameter optimization
- python tokens
- expression performance
- optimization engine
tags:
- python
- performance
- optimization
- expressions
- parameters
- caching
- engine
- profiling
relationships:
  MODULE_td_Module: strong
  PY_Python_Tips: medium
  PERF_Optimize: strong
  CLASS_Project_Class: medium
related_docs:
- MODULE_td_Module
- PY_Python_Tips
- PERF_Optimize
- CLASS_Project_Class
hierarchy:
  secondary: expression_performance
  tertiary: python_optimization
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- performance_tuning
- expression_optimization
- parameter_expression_development
- large_project_optimization
---

# Optimized Python Expressions

<!-- TD-META
category: PY
document_type: guide
operators: [Perform_CHOP, Expression_CHOP, waveCHOP, pointSOP, primitiveSOP, Parameter_Execute_DAT]
concepts: [performance_optimization, expression_optimization, cached_expressions, parameter_expressions, python_engine_optimization, performance_profiling]
prerequisites: [Python_fundamentals, parameter_basics, MODULE_td_Module]
workflows: [performance_tuning, expression_optimization, parameter_expression_development, large_project_optimization]
related: [MODULE_td_Module, PY_Python_Tips, PERF_Optimize, CLASS_Project_Class]
relationships: {
  "MODULE_td_Module": "strong",
  "PY_Python_Tips": "medium",
  "PERF_Optimize": "strong",
  "CLASS_Project_Class": "medium"
}
hierarchy:
  primary: "optimization"
  secondary: "expression_performance"
  tertiary: "python_optimization"
keywords: [optimized expressions, cached expressions, expression engine, performance, parameter optimization, python tokens, expression performance, optimization engine]
tags: [python, performance, optimization, expressions, parameters, caching, engine, profiling]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Advanced
**Time to read**: 15-25 minutes
**Use for**: performance_tuning, expression_optimization, parameter_expression_development

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Python Fundamentals] → [Parameter Basics] → [Module Td Module]
**This document**: PY reference/guide
**Next steps**: [MODULE td Module] → [PY Python Tips] → [PERF Optimize]

**Related Topics**: performance tuning, expression optimization, parameter expression development

## Summary

Technical documentation explaining TouchDesigner's optimized Python expression engine, including supported tokens, cached expressions, and performance optimization for parameter expressions.

## Relationship Justification

Connected to performance optimization as core functionality, and td module since it explains optimized access to module functions. Related to Project class for performance settings control.

## Content

- [Overview](#overview)
- [Optimized Python Expressions](#optimized-python-expressions)
- [Cached Python Expressions](#cached-python-expressions)
- [What can the engine evaluate](#what-can-the-engine-evaluate)

## Overview

## Optimized Python Expressions

Starting with the 2018.20000 series of builds, a custom Python expression execution engine has been incorporated into TouchDesigner. This engine will parse Python expressions that are in parameters. Assuming the members and methods used in that expression fall into the range of members and methods the engine is aware of, it will evaluate the expression without having to use Python's engine. This generally results in a the expression evaluating in about 1/4 of the time than it does if it was evaluated through the regular Python engine.

The goal of this feature isn't to evaluate every parameter expression using this engine, but to evaluate the most commonly used expressions. You can determine if an expression is evaluated using this engine by holding the mouse over the parameter name. It will show either (Optimized) or (Unoptimized) in the popup that will show up. The Perform CHOP has a parameter to monitor the number of optimized expressions.

If an expression ever ends up causing an error, the engine will stop being used for that expression and the Python engine will be used instead. If the expression is changed, or on the next time the file is loaded, TouchDesigner will once again try to use the engine to evaluate the parameter.

## Cached Python Expressions

In addition to optimized expressions, a new system that caches expression results will keep them from re-calculating every frame. The Perform CHOP has a parameters to monitor the number cached expressions.

## What can the engine evaluate

When a Python expression is parsed it is broken up into tokens. A token can be for example a constant boolean value True or a constant string. Tokens are also the methods, members and variable names that are part of an expression. The engine has a set of tokens it recognizes, and if the expression contains only those tokens, then it can evaluate the expression. If there are any tokens it does not recognize in the expression, then it will not try to evaluate the expression and the regular Python engine will be used.

As long as the expression contains only tokens recognized by the engine, the there is no limit to how large the expression and be or how complex the expression can be.

For example this expression can be evaluated by the optimized expression engine:

 op(‘geo1’).par.tx + math.max(parent().par.tx + op[‘speed1’](0), 10) / int(op['table1']('header', 5))
The types of supported tokens are:

the me variable
Constants:
Strings
Booleans (True, False)
Integers
Floats
Comparison operators
==

!=
<
>
>=
<=
Unary operators:

- (negate)

-

~ (invert)
Boolean operators:
and
or
Binary operators, for numerical and string operations:
+
-

-

/
% (modulus)
** (power), as long as both arguments aren't integers.
// (floor division)
single line if expressions
Global td module functions:
op()
parent()
passive()
Tdu Module functions:
remap()
rand()
AbsTime Class methods and members:
frame
seconds
OP Class methods and members:
name
par
digits
time
path
inputs
inputCOMPs
outputCOMPs
fetch(), in some cases.
TimeCOMP Class methods and members:
frame
seconds
rate
CHOP Class methods and members:
rate
numSamples
start
end
[] operator to access a Channel Class object.
DAT Class methods and members:
[] operator access a Cell Class object.
TOP Class methods and members:
width
height
aspectWidth
aspectHeight
Panel Class methods and members:
width
height
ParCollection Class methods and members:
. operator to get a Par Class object.
[] operator to get a Par Class object.
Par Class methods and members:
eval()
evalNorm()
normVal
default
menuIndex
automatic casting to int/float/string
Channel Class methods and members:
eval()
[] operator to get a single sample from a CHOP channel.
automatic casting
Cell Class methods and members:
eval()
[r,c] operator to get a cell from a DAT table.
automatic casting
Python list class methods and members:
[] operator
any(list)
len(list)
all(list)
Python math module functions:
abs()
max()
min()
round()
Python global functions:
pow()
int()
str()
bool()
float()
getattr() (In limited cases)
Project Class methods and members:
cookRate (get only)
SOP Class methods and members:
center
numPrims
numPoints
primitiveSOP Class the me.inputPrim Prim Class has these members optimized:
me.inputPrim.index
me.inputPrim.center
me.inputPrim.direction
me.inputPrim.weight
me.inputPrim.normal
len(me.inputPrim)
pointSOP Class has these special cases optimized:
Includes inputPoint2, inputColor2, inputNormal2 and inputTexture2 as well.
me.inputPoint.index
me.inputPoint.normP
me.inputPoint.P
me.inputPoint.x
me.inputPoint.y
me.inputPoint.z
me.inputPoint.normal
me.inputPoint.color
me.inputPoint.sopCenter
me.inputColor (Deprecated)
me.inputNormal (Deprecated)
me.inputTexture
Vector Class :
[] operator
x, y and z members
Position Class :
[] operator
x, y and z members
Color Class :
[] operator
r, g, b and a members
Panel Class :
Access to Panel Values.
PanelValue Class
Automatic casting
val member
expressionCHOP Class methods and members :
inputVal
chanIndex
sampleIndex
waveCHOP Class methods and members :
chanIndex
sampleIndex
Python Math Module constants and functions :

pi
sin()
cos()
tan()
asin()
acos()
ceil()
floor()
sqrt()
degrees()
radians()
