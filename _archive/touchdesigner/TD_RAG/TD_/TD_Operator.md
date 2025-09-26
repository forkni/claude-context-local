---
title: "Operator"
category: "TD_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "10 minutes"
user_personas: ["beginner", "developer", "designer"]
completion_signals: ["understands_operator_families", "knows_how_to_create_operators"]
operators: ["TOPtoCHOP", "CHOPtoTOP", "CHOPtoDAT", "CHOPtoSOP", "DATtoCHOP", "DATtoSOP", "SOPtoCHOP", "SOPtoDAT", "ObjectCHOP"]
concepts: ["operator", "node", "family", "comp", "top", "chop", "sop", "dat", "mat", "path", "exporting"]
prerequisites: []
workflows: ["network_building", "data_conversion"]
keywords: ["operator", "node", "family", "comp", "top", "chop", "sop", "dat", "mat"]
tags: ["core", "concept", "beginner", "operator"]
related_docs:
- "CLASS_OP_Class"
- "TD_Node"
- "TD_Wire"
- "TD_Link"
- "TD_Flag"
- "TD_Connector"
- "TD_Viewer"
- "TD_OPCreateDialog"
---

# Operator

## Content
- [Introduction](#introduction)
- [Operator Families](#operator-families)
- [Creating Operators](#creating-operators)
- [Converting data between OP Families](#converting-data-between-op-families)
- [See Also](#see-also)

## Introduction

Operators are the "Nodes" in TouchDesigner networks, and they output data to other operators. Each operator is customized with its Parameters and Flags.

## Operator Families

There are six Families of built-in Operators. Of the six families, five are basic operator families and one is the Component family which can further contain networks of operators. Components containing components form the TouchDesigner hierarchy and give rise to the operator Paths.

- **[COMPs]** - Components - Object Components (3D objects), Panel Components (2D UI gadgets), and other miscellaneous components. Components contain other operators.
- **[TOPs]** - Texture Operators - all 2D image operations.
- **[CHOPs]** - Channel Operators - motion, audio, animation, control signals.
- **[SOPs]** - Surface Operators - 3D points, polygons and other 3D "primitives".
- **[DATs]** - Data Operators - ASCII text as plain text, scripts, XML, or organized in tables of cells.
- **[MATs]** - Material Operators - materials and shaders.

Within each operator family, "generator" operators have 0 inputs and create data, and "filter" operators have 1 or more input and filter data.

Each operator family is a unique color. Only operators of the same family (color) can be Wired together. Many operators have parameters that are references to operators in other families: Links. Also Exporting flows numeric data from [CHOPs] to all operators.

`Custom Operators` of type [TOP], [CHOP], [SOP], and [DAT] can be created using C++, allowing you to extend TouchDesigner's functionality. They will show up in the OP Create Dialog under the 'Custom' tab.

See also: [CLASS_OP_Class]

## Creating Operators

To add new operators to a network, use the [TD_OPCreateDialog]. The OP Create Dialog can be opened by pressing the `<tab>` key, double-clicking on the network background, clicking the `+` button in the Pane Bar, selecting `Add Operator` from the right-click menu in any network, or by right-clicking on the input or output of another operator.

## Converting data between OP Families

You can convert data between different Operator families using the following conversion operators. For example, you can convert geometry into a [DAT] list of point positions using the `SOP to DAT` operator, or convert a [TOP] image's pixel values into red, green, and blue channels in [CHOP] using the `TOP to CHOP` operator.

- `TOP to CHOP`
- `CHOP to TOP`
- `CHOP to DAT`
- `CHOP to SOP`
- `DAT to CHOP`
- `DAT to SOP`
- `SOP to CHOP`
- `SOP to DAT`
- `Object CHOP`

## See Also

- [TD_Node]
- [TD_Wire]
- [TD_Link]
- [TD_Flag]
- [TD_Connector]
- [TD_Viewer]
- [TD_OPCreateDialog]
