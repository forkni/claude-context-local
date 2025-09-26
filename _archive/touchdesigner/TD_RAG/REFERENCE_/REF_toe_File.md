---
title: ".toe File"
category: "REF_"
document_type: "reference"
difficulty: "beginner"
time_estimate: "2 minutes"
user_personas: ["developer", "beginner"]
concepts: ["toe", "project_file", "file_format", "toeexpand", "toecollapse"]
keywords: ["toe", "project", "file", "environment"]
tags: ["core", "file_format"]
related_docs:
- "REF_tox"
- "REF_toeexpand"
- "REF_toecollapse"
---

# .toe File

A TouchDesigner Environment file (`.toe`), or "Project file", is the file type used to save your TouchDesigner projects. It contains your networks, operators, parameters, Pane layouts and optionally MIDI settings.

External to the `.toe` file are media files like images, movies, 3D geometry, audio and other data files. However, these media files can also be embedded into `.toe` files or `.tox` files.

A `.tox` (component) file is used to save particular components of a `.toe` so one file can be shared between projects, archived or simply transported to another project. The `.toe` files can refer to `.tox` files and load them in when you start TouchDesigner.

A `.toe` file can be converted to ASCII-readable form using [REF_toeexpand]. After editing in ASCII form, the `.toe` file can be recreated using [REF_toecollapse] to a format which TouchDesigner can use.

## See Also

- [REF_tox]
- [REF_toeexpand]
- [REF_toecollapse]
