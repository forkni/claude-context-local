---
title: "SudoMagic Style Guide: GLSL Comments"
category: STYLEGUIDES
document_type: "guide"
difficulty: "beginner"
time_estimate: "5-10 minutes"
user_personas: ["script_developer", "technical_artist"]
operators: ["glslTOP", "glslMAT"]
concepts: ["style_guide", "best_practices", "glsl", "comments", "documentation"]
prerequisites: ["GLSL_fundamentals"]
workflows: ["code_style", "project_organization", "documentation"]
keywords: ["style guide", "coding standards", "touchdesigner", "glsl", "comments", "header"]
tags: ["guide", "style", "glsl", "documentation", "comments"]
related_docs: ["GLSL_Write_a_GLSL_TOP", "GLSL_Write_a_GLSL_Material"]
---

# SudoMagic Style Guide: GLSL Comments

This guide provides a template for commenting and organizing your GLSL code in TouchDesigner for better readability and collaboration.

## GLSL Comment Template

```glsl
// SudoMagic LLC
//
// contributing programmers
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
// programmer | programmer@domain.com
 
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
// DEFINITIONS
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
 
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
// UNIFORMS
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
 
uniform float uName;
 
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
// FUNCTIONS
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
 
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
// OTHER
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
 
// * * * * * * * * * * * * * * * * * * * * * * * * * * * * *

out vec4 fragColor;

void main(){
    // vec4 color     = texture(sTD2DInputs[0], vUV.st);
    vec4 color        = vec4(1.0);
    fragColor         = TDOutputSwizzle(color);
}
```
