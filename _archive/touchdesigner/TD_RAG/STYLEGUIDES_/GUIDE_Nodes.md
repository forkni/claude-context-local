---
title: "SudoMagic Style Guide: Nodes"
category: STYLEGUIDES
document_type: "guide"
difficulty: "beginner"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "technical_artist", "beginner_user"]
operators: []
concepts: ["style_guide", "best_practices", "naming_conventions", "node_organization"]
prerequisites: ["TouchDesigner_basics"]
workflows: ["code_style", "project_organization", "collaboration"]
keywords: ["style guide", "coding standards", "touchdesigner", "nodes", "naming", "sizing", "wires"]
tags: ["guide", "style", "nodes", "organization"]
related_docs: []
---

# SudoMagic Style Guide: Nodes

This guide covers the SudoMagic style conventions for TouchDesigner nodes, including naming, sizing, and wiring.

## Naming Patterns

The standard naming convention for operators is `{operator}_{descriptor}_{name}{#}`. This pattern uses underscores instead of camelCase.

*   **`operator`**: The type of the operator (e.g., `moviefilein`).
*   **`descriptor_name`**: A description of the node's purpose, using underscores for spaces.
*   **`#`**: A number if the node is part of a series.

**Examples:**
*   `base_com`
*   `script_inst_data1`
*   `null_final` (at the end of a render chain)
*   `moviefilein_a`, `moviefilein_b` (for A/B decks)
*   `null_ui_thumbnail1`, `null_ui_thumbnail2` (for instancing)

**Exception:**
For local modules (`mod`), the `text_` prefix can be omitted from the DAT's name to shorten expressions. For example, `mod.system_configuration.start_up()` is preferred over `mod.text_system_configuration.start_up()`.

## Sizing

*   **Consistency is Key:** Avoid resizing nodes unnecessarily. Inconsistent sizing can mislead others into thinking larger nodes are more important, hindering their ability to read the network flow objectively.
*   **Standardization:** If you must resize a node, consider using a script to set a consistent, standardized size. This can be done via the `op` class:
    *   `op('opName').nodeHeight = int`
    *   `op('opName').nodeWidth = int`
    (100 units = 1 grid square).
*   **Best Practices:**
    *   Use consistent spacing and default node sizes.
    *   Group related operations and consider modularizing them.
    *   Do not use extremely large nodes, as it disrupts network organization.

## Wires

*   **Clarity:** Arrange nodes to create clear, understandable wire paths. Avoid crossing, obscuring, or hiding wires.
*   **Flow:** Maintain a logical left-to-right flow. Avoid vertical stacking that creates "S-curves" and reverse-order connections.
*   **Docking:** Do not dock and hide essential network elements like scripts or shaders. This makes debugging significantly harder for others.

## Visual Debugging

*   **Animation:** Animated wires and links (the dotted lines for parameter connections) indicate that an operator is actively "cooking" or processing. This is a useful visual cue for debugging and identifying unnecessary processing.
*   **Docked:** Docked operators are connected by a straight line and maintain a fixed offset from each other.
*   **Network Flow:** There is an implied left-to-right data flow. While other orientations are possible, they can make the network harder to interpret at a glance. Top-to-bottom or bottom-to-top arrangements are particularly discouraged as they obscure the flow of operations.
