---
title: "SudoMagic Style Guide: External TOX Files"
category: STYLEGUIDES
document_type: "guide"
difficulty: "intermediate"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "technical_artist", "system_architect"]
operators: ["baseCOMP", "containerCOMP"]
concepts: ["style_guide", "best_practices", "project_organization", "version_control", "git", "tox"]
prerequisites: ["TouchDesigner_basics", "git_basics"]
workflows: ["project_setup", "system_architecture", "version_control", "collaboration"]
keywords: ["style guide", "coding standards", "touchdesigner", "organization", "architecture", "tox", "external", "git", "version control"]
tags: ["guide", "style", "organization", "architecture", "tox", "git"]
related_docs: ["REF_tox_File", "REF_toe_File"]
---

# SudoMagic Style Guide: External TOX Files

This guide covers the SudoMagic approach to externalizing `.tox` files for better project organization, modularity, and version control.

## A TOX-Centric Approach

In our current general networking building strategy, as many elements as possible are externalized. The strategy of externalizing the contents of a network helps:

*   **Reduce .toe file size.**
*   **Focus on modular design:** This encourages creating interchangeable modules, assuming a standard for input and output communication is established.
*   **Allow for better git tracking:** Since .tox and .toe files are binary, traditional git diffing is ineffective. Externalizing modules allows for easier tracking of changes, rollbacks to previous versions, and better version control.
*   **Allow for multiple developer contributions via git:** By focusing on individual .tox files as the unit of change, multiple developers can work on a project without merge conflicts, as long as they aren't editing the same .tox file simultaneously.

## Directories and Saving

Structurally, repository directories should mirror the network structure within the `.toe` file. For example, if a component is located at `/software_project_name/base_communication` inside the TouchDesigner project, its external `.tox` file should be saved at a matching path in the repository.

This parallel structure helps other programmers locate files easily. If you know where a module is in the network, you know where to find its corresponding file in the repository. This convention aids in debugging and code exchange.
