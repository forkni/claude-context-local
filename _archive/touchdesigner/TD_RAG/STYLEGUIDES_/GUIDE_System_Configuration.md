---
title: "SudoMagic Style Guide: System Configuration"
category: STYLEGUIDES
document_type: "guide"
difficulty: "advanced"
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "technical_artist", "system_architect"]
operators: ["baseCOMP", "cacheTOP", "texture3DTOP"]
concepts: ["style_guide", "best_practices", "system_configuration", "startup", "parameters", "ipar", "prefill"]
prerequisites: ["TouchDesigner_basics", "PY_Extensions", "PY_Python_in_Touchdesigner"]
workflows: ["project_setup", "system_architecture", "configuration_management"]
keywords: ["style guide", "coding standards", "touchdesigner", "configuration", "startup", "ipar", "parameters", "prefill", "touch_start"]
tags: ["guide", "style", "configuration", "startup", "architecture"]
related_docs: ["PY_Custom_Parameters", "REF_Cache_TOP", "CLASS_Texture3DTOP_Class"]
---

# SudoMagic Style Guide: System Configuration

This guide covers the SudoMagic approach to system configuration in TouchDesigner, focusing on start-up behavior, parameter management, and best practices for ensuring projects initialize correctly.

## System Configuration Philosophy

System configuration is a complex topic, and the nuanced behavior of start-up often depends on what a given project is being used for. A toy-network, for example, rarely needs a configuration schema as it's intended as the sandbox for exploring a single idea or concept. Project TOE files, however, often require some degree of configuration to ensure that they start up with the correct settings, request their operating state from another machine, or correctly load the last saved UI state. With this in mind, there are some general practices used across projects.

## IPAR Settings

Projects typically use a set of internal parameters located in the `/base_scaffold/base_project`. This set of internal parameters is called `Settings`, and allows pars to be accessed with the pattern `ipar.Settings.Somepar`. SudoMagic typically uses `ipar.Settings` as the primary interface for states that need to be set at start-up. All parameters on this base are saved out to file and loaded from file on start-up.

## Read-Only Pars

The notable exception for saved and loaded pars are those marked as read-only. Read-Only pars are not saved to file, and they are not set when a file is loaded from disk. This provides a stable interface for parameters that are referenced across the project, while also ensuring that some pars are private to the TOE file.

### No Expressions Please
Expressions, generally, should not be used for any parameters in `ipar.Settings`. This general practice is to ensure that pars with expressions are not unexpectedly overwritten by the contents on disk. The exception to this rule is read-only pars - since read-only marked parameters are not loaded from disk, it is safe to use expressions in these parameters.

More here from the official Derivative documentation about [Internal Parameters](https://docs.derivative.ca/Internal_Parameters).

## Sane Defaults

There are some cases when the contents of `ipar.Settings` should be overridden with consistent and sane start-up defaults. For this reason, there is an additional json file in `_public\data` labeled `defaults.json` - the contents of this file will override any parameter that might otherwise be loaded from disk.

## Prefill

The `prefill` parameter on the Texture 3D TOP and the Cache TOP have a reliable mechanic for loading frames into memory. The prefill operation happens during project start-up and reliably provides a cook and load pattern for frames that need to be cached. This is helpful for elements like images for slide-shows, but also useful for elements that may be used for UIs or other system-wide display. It's important to consider that this loading step blocks the launching of a project or loading of a TOX; anytime a Texture3D or Cache loads many frames there is a high probability that it will delay the start-up of your project.

## Touch_start

`Touch_start()` is a SudoMagic convention that arises out of the specific need for a reliable class object restart that does not require reinitializing the entire class object. Python object initialization is difficult to reliably predict, and our internal solution to address this need is to use an explicit class method that can be explicitly called. Because of the interplay of pull-based mechanics and Python's integration, `Touch_start()` may not necessarily contain any methods. Calling a method in an Extension ensures that the class is initialized in the order desired.

---

### Links to Derivative's Official Docs

*   [Internal Parameters](https://docs.derivative.ca/Internal_Parameters)
*   [Cache TOP](https://docs.derivative.ca/Cache_TOP)
*   [Texture 3D TOP](https://docs.derivative.ca/Texture_3D_TOP)

---

### Footnotes

¹ SudoMagic uses the term toy-network to mean a simplified example of an idea or concept that is not intended for production use. These small format networks often are used to tease out the subtlety of an idea, or concept before working out the production implementation process. Toy-networks are typically located in the root of a repo in a directory called `/prototypes` or `/sandbox`.
