---
category: PY
document_type: guide
difficulty: intermediate
time_estimate: 15-25 minutes
operators:
- Select_CHOP
- Rename_CHOP
- Parameter_CHOP
- Script_CHOP
- Evaluate_DAT
- Table_DAT
- Expression_CHOP
- Constant_CHOP
- Noise_CHOP
- Wave_CHOP
- LFO_CHOP
concepts:
- pattern_expansion
- procedural_generation
- channel_naming
- string_manipulation
- batch_creation
- pattern_syntax
prerequisites:
- parameter_basics
- basic_pattern_concepts
workflows:
- procedural_channel_creation
- batch_renaming
- dynamic_naming
- procedural_network_building
keywords:
- pattern
- expansion
- generate names
- channel creation
- name expansion
- numeric range
- '[1-3]'
- procedural naming
- tdu.expand
- pattern syntax
- range expansion
tags:
- python
- string
- pattern
- procedural
- naming
- generation
- fundamentals
- pattern_system
relationships:
  PY_Python_Tips: medium
  MODULE_td_Module: medium
related_docs:
- PY_Python_Tips
- MODULE_td_Module
hierarchy:
  secondary: pattern_system
  tertiary: pattern_expansion
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- procedural_channel_creation
- batch_renaming
- dynamic_naming
- procedural_network_building
---

# Pattern Expansion

<!-- TD-META
category: PY
document_type: guide
operators: [Select_CHOP, Rename_CHOP, Parameter_CHOP, Script_CHOP, Evaluate_DAT, Table_DAT, Expression_CHOP, Constant_CHOP, Noise_CHOP, Wave_CHOP, LFO_CHOP]
concepts: [pattern_expansion, procedural_generation, channel_naming, string_manipulation, batch_creation, pattern_syntax]
prerequisites: [parameter_basics, basic_pattern_concepts]
workflows: [procedural_channel_creation, batch_renaming, dynamic_naming, procedural_network_building]
related: [PY_Python_Tips, MODULE_td_Module]
relationships: {
  "PY_Python_Tips": "medium",
  "MODULE_td_Module": "medium"
}
hierarchy:
  primary: "fundamentals"
  secondary: "pattern_system"
  tertiary: "pattern_expansion"
keywords: [pattern, expansion, generate names, channel creation, name expansion, numeric range, [1-3], procedural naming, tdu.expand, pattern syntax, range expansion]
tags: [python, string, pattern, procedural, naming, generation, fundamentals, pattern_system]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: procedural_channel_creation, batch_renaming, dynamic_naming

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Parameter Basics] → [Basic Pattern Concepts]
**This document**: PY reference/guide
**Next steps**: [PY Python Tips] → [MODULE td Module]

**Related Topics**: procedural channel creation, batch renaming, dynamic naming

## Summary

Fundamental guide for understanding pattern expansion syntax used throughout TouchDesigner for procedural naming and batch operations. Essential for advanced workflows involving multiple channels or operators.

## Relationship Justification

Connected to Python Tips for practical usage examples and td module since pattern expansion is used throughout the API. Fundamental concept for procedural workflows.

## Content

- [Overview](#overview)
- [Pattern Syntax](#pattern-syntax)
- [Examples](#examples)
- [See Also](#see-also)

## Overview

Pattern Expansion takes a short string and expands it to generate a longer string of individual elements. Example: chan[1-3] generates chan1 chan2 chan3.

Pattern Replacement uses Pattern Expansion, along with having some of it's own syntax on-top of Pattern Expansion. The opposite of Pattern Expansion is "Pattern Matching" where you are looking for patterns in a longer string or a large set of strings.

Expansion is done by using putting the data to expand into []. Valid syntax is

[<letters>] - Where letters is one or more letters (not numbers), each of which will be split out into it's own result.
[<startNumber>-<endNumber>] - Where startNumber and endNumber form a range of numbers. A result will be created for each number in the range.
[<startNumber>-<endNumber>:<increment>] - Similar to the previous one, but increment allows for skipping numbers in the range, so less results are created, and numbers are skipped.
Each expansion will be expanded against every possible other expansion in the string. So one expansion with 2 results followed by one with 3 results, will result in a final result containing 6 results.

For example, the pattern:

[tr][xyz]
expands to:

 tx ty tz rx ry rz
While the pattern:

chan[1-11:2]
expands to:

chan1 chan3 chan5 chan7 chan9 chan11
Note that the [1,2,3] syntax available in Pattern Matching is not available here.

Pattern expansion occurs in:

Rename CHOP, Select CHOP and Panel CHOP - where channels are renamed.
Constant CHOP, Noise CHOP, Wave CHOP, LFO CHOP, Pulse CHOP and Joystick CHOP - where channels are created using patterns.
Merge DAT - where DATs are selected for merging.
Note: See tdu.expand()

Note: To expand a list of operators that is in a parameter type that is a list of operators, see .evalOPs() in Par Class

## See also

[Pattern Replacement](PY_Pattern_Replacement.md),
[Pattern Matching](PY_Pattern_Matching.md)
