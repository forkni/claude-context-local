---
title: "SudoMagic Style Guide: Logging"
category: STYLEGUIDES
document_type: "guide"
difficulty: "intermediate"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "technical_artist"]
operators: []
concepts: ["style_guide", "best_practices", "logging", "debugging"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics"]
workflows: ["debugging", "logging", "project_organization"]
keywords: ["style guide", "coding standards", "touchdesigner", "logging", "debugging", "textport"]
tags: ["guide", "style", "logging", "debugging", "python"]
related_docs: ["MODULE_DebugModule"]
---

# SudoMagic Style Guide: Logging

This guide covers the SudoMagic approach to logging for events and debugging in TouchDesigner.

## Logging - Events and Debugging

SudoMagic utilizes a modified version of Python's standard `logging` module to log events to both the TouchDesigner textport and external files.

### Key Practices:

*   **Dual Output:** The system is configured to send messages to both the standard output (visible in the textport) and to a log file.
*   **Daily Log Files:** New log files are generated each day to keep them manageable.
*   **Log Directory:** Log files are saved in a `_public/logs` directory. The location of the `_public` folder is derived from the TouchDesigner project file's path and may not be directly alongside the `.toe` file.
*   **Avoid `print()`:** While `print()` is useful during development, it should be removed or commented out in the final project. The `logging` module should be used for any persistent or important messages.
*   **Importing:** To use logging in a script or extension, you must import the module:
    ```python
    import logging
    ```
*   **Traceable Messages:** Log messages should clearly identify their source to be easily traceable. For example:
    ```python
    logging.info("PROJECT | System settings loded sucessfully")
    ```
