---
title: "SudoMagic Style Guide: Project Organization"
category: STYLEGUIDES
document_type: "guide"
difficulty: "advanced"
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "technical_artist", "system_architect"]
operators: ["baseCOMP", "containerCOMP"]
concepts: ["style_guide", "best_practices", "project_organization", "architecture", "scaffolding"]
prerequisites: ["TouchDesigner_basics", "PY_Extensions", "PY_Python_in_Touchdesigner"]
workflows: ["project_setup", "system_architecture", "code_organization"]
keywords: ["style guide", "coding standards", "touchdesigner", "organization", "architecture", "scaffold", "project structure"]
tags: ["guide", "style", "organization", "architecture", "project"]
related_docs: ["PY_Extensions", "PY_Python_in_Touchdesigner"]
---

# SudoMagic Style Guide: Project Organization

This guide outlines the SudoMagic standard for TouchDesigner project organization, promoting consistency, reusability, and scalability.

## Project Organization Philosophy

The SudoMagic standard project structure uses a two-layered paradigm starting with a root component called `base_scaffold`.

## Top Level: `/BASE_SCAFFOLD`

This component is the root of any project and contains the following:

*   **`BASE_SHADERLIB`**: A reusable shader library, accessible across all projects with a short import path. This ensures that components can be easily ported between projects.
*   **`LOCAL`**: Houses reusable, abstract Python libraries for TouchDesigner located in `local/modules`.
*   **`BASE_PROJECT`**: Contains all the unique elements for a specific project. While it follows a consistent formula, its contents are expected to differ between projects.
*   **`CLOUDPALETTE`**: A component for fast access to materials and snippets from the web, loaded on demand from the cloud.
*   **`BASE_DEV_TOOLS`**: Houses mission-critical development tools like TOX saving components, logging, and performance profiling tools.

## Project Level: `/BASE_SCAFFOLD/BASE_PROJECT`

This component holds the persistent, core elements of a specific project:

*   **`base_startup`**: Holds all start-up scripts and behaviors.
*   **`iparSettings`**: The single source of truth for all project controls and settings, using internal parameters. This simplifies saving and loading all project settings.
*   **`base_com`**: (Short for Communication) The central hub for all network traffic and IO, including communication for multi-machine projects.
*   **`container_output`**: The only `Container COMP` in this layer, linked to the main project window for rendering and display.
*   **`base_icon`**: A non-functional component that stores the project's icon.
*   **`local`**: Similar to the top-level `local`, this holds project-specific Python libraries and all extension code, centralized to allow for code completion across modules.
*   **`base_process`**: Houses any project-specific data processing that needs to be accessible across different components.
*   **`base_data`**: A central component for all project data, such as 3D models, configuration schemas, etc.

## Summary of Network Topology

```
base_scaffold
    ├── base_icon_ui
    ├── local
    │    └── modules
    │        └── SudoMagic
    │
    ├── base_prod_tools
    ├── base_dev_tools
    ├── base_shader_lib
    │
    └── base_project
        ├── base_icon
        ├── base_startup
        ├── iparSettings
        ├── base_com
        ├── container_output
        ├── base_process
        ├── base_data
        └── local
            └── modules
                ├── lookup
                ├── project
                ├── com
                ├── process
                ├── output
                └── data
```
