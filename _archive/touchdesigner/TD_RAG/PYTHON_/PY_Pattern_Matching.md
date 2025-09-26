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
- Render_TOP
concepts:
- pattern_matching
- wildcard_search
- operator_selection
- channel_selection
- procedural_workflows
- string_manipulation
- selection_syntax
prerequisites:
- operator_basics
- MODULE_td_Module
workflows:
- dynamic_operator_selection
- batch_processing
- channel_filtering
- procedural_scripting
- automated_selection
keywords:
- pattern
- matching
- wildcard
- glob
- select
- filter
- '*'
- '?'
- ^
- '[]'
- ops()
- selection syntax
- wildcard patterns
- operator selection
tags:
- python
- string
- pattern
- procedural
- selection
- filtering
- fundamentals
- automation
relationships:
  PY_Pattern_Expansion: strong
  MODULE_td_Module: strong
  PY_Python_Tips: medium
related_docs:
- PY_Pattern_Expansion
- MODULE_td_Module
- PY_Python_Tips
hierarchy:
  secondary: pattern_system
  tertiary: pattern_matching
question_patterns:
- Python scripting in TouchDesigner?
- How to use Python API?
- Scripting best practices?
- Python integration examples?
common_use_cases:
- dynamic_operator_selection
- batch_processing
- channel_filtering
- procedural_scripting
---

# Pattern Matching

<!-- TD-META
category: PY
document_type: guide
operators: [Select_CHOP, Rename_CHOP, Parameter_CHOP, Script_CHOP, Evaluate_DAT, Table_DAT, Expression_CHOP, Render_TOP]
concepts: [pattern_matching, wildcard_search, operator_selection, channel_selection, procedural_workflows, string_manipulation, selection_syntax]
prerequisites: [operator_basics, MODULE_td_Module]
workflows: [dynamic_operator_selection, batch_processing, channel_filtering, procedural_scripting, automated_selection]
related: [PY_Pattern_Expansion, MODULE_td_Module, PY_Python_Tips]
relationships: {
  "PY_Pattern_Expansion": "strong",
  "MODULE_td_Module": "strong",
  "PY_Python_Tips": "medium"
}
hierarchy:
  primary: "fundamentals"
  secondary: "pattern_system"
  tertiary: "pattern_matching"
keywords: [pattern, matching, wildcard, glob, select, filter, *, ?, ^, [], ops(), selection syntax, wildcard patterns, operator selection]
tags: [python, string, pattern, procedural, selection, filtering, fundamentals, automation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Python scripting guide for TouchDesigner automation
**Difficulty**: Intermediate
**Time to read**: 15-25 minutes
**Use for**: dynamic_operator_selection, batch_processing, channel_filtering

**Common Questions Answered**:

- "Python scripting in TouchDesigner?" → [See relevant section]
- "How to use Python API?" → [See relevant section]
- "Scripting best practices?" → [See relevant section]
- "Python integration examples?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Operator Basics] → [Module Td Module]
**This document**: PY reference/guide
**Next steps**: [PY Pattern Expansion] → [MODULE td Module] → [PY Python Tips]

**Related Topics**: dynamic operator selection, batch processing, channel filtering

## Summary

Fundamental guide explaining wildcard patterns used throughout TouchDesigner for selecting operators, channels, and other objects. Essential knowledge for advanced procedural workflows and automation.

## Relationship Justification

Forms pattern system trio with Pattern Expansion. Strong connection to td module since pattern matching is used in ops() and other core functions. Links to Python Tips for practical usage examples.

## Content

- [What is Pattern Matching?](#what-is-pattern-matching)
- [Examples](#examples)
- [See Also](#see-also)

Many parameters allow patterns to specify multiple sources to be selected or acted upon. CHOPs, channels, DATs, Geometry COMPs are examples of things that some parameters may allow multiple of. The Render TOP allows for multiple lights, geometry COMPs and cameras. The Join CHOP and Composite TOP accept multiple sources. These patterns allow wild cards which will match all or parts of strings. Patterns are also used in various Python methods such as ops(), to allow specifying more than one OP by a single string.

Multiple patterns can be specified, separated by spaces. The patterns will be ORed together, so a source that matches any of listed patterns will be selected.

- - Match any sequence of characters
? - Match any single character
^ - Do not match.
[alphaset] - Match any one of alphabetic characters enclosed in the square brackets. In TouchDesigner, the [a-g] format is not currently supported, the characters must be listed as [abcdefg].
[num1-num2] or [num1-num2:increment] - Match any integer numbers enclosed in the number range, with the optional increment.
[num1,num2,num3] - Match the specific integers given.
@groupname - Expands all the items in the group. Since each group belongs to a network, you can specify a path before the @groupname identifier.
NOTE: The opposite of pattern matching is Pattern Expansion, takes a short string and generates a longer string from it. See also Pattern Replacement.

Pattern matching is also often used to match channel names. It uses the following kinds of patterns to select existing channels in an input CHOP, used in CHOPs like the Select CHOP and the Math CHOP's Scope parameter, where you only want to affect certain channels and leave the rest as-is.

Pattern matching is used to match object names in the Render TOP, and OPs/channel names in the Select CHOP.

## Examples

chan2 Matches a single channel name
chan3 tx ty tz Matches four channel names, separated by spaces
chan* Matches each channel that starts with "chan" and ends with anything
*foot* Matches each channel that has "foot" in it, with anything or nothing before or after
t? The ? matches a single character. t? matches two-character channels starting with t, like the translate channels tx, ty and tz
r[xyz] Matches channels rx, ry and rz. that is, "r" followed by any character between the [ ]
blend[3-7:2] Matches number ranges giving blend3, blend5, and blend7. (3 to 7 in steps of 2)
blend[2-3,5,13] Matches channels blend2, blend3, blend5, blend13
t[uvwxyz] [uvwxyz] matches characters between u and z, giving channels tu, tv, tw, tx, ty and tz

## See Also

[Pattern Expansion](PY_Pattern_Expansion.md),
[Pattern Replacement](PY_Pattern_Replacement.md)
