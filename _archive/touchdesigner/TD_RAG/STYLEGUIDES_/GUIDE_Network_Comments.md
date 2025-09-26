---
title: "SudoMagic Style Guide: Network Comments"
category: STYLEGUIDES
document_type: "guide"
difficulty: "beginner"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "technical_artist", "beginner_user"]
operators: ["textDAT"]
concepts: ["style_guide", "best_practices", "documentation", "comments", "network_organization"]
prerequisites: ["TouchDesigner_basics"]
workflows: ["project_organization", "documentation", "collaboration"]
keywords: ["style guide", "coding standards", "touchdesigner", "comments", "documentation", "network", "textdat"]
tags: ["guide", "style", "documentation", "comments", "network"]
related_docs: []
---

# SudoMagic Style Guide: Network Comments

This guide covers best practices for adding comments to your TouchDesigner networks to improve readability and collaboration.

## The Importance of Comments

Comments are essential for future reference and collaboration. While full documentation is ideal, leaving comments is a minimum requirement. The recommended method for commenting in TouchDesigner is using Text DATs.

## Key Recommendations:

*   **Readme for Components:** Add a `readme` Text DAT to any major component to provide a high-level overview of its function and purpose. The guide mentions a helper TOX (`base_network_documentation`) to standardize this process.
*   **Specific, Localized Comments:** Instead of one large Text DAT, use multiple smaller ones placed near the specific operators or network sections they describe. This keeps the explanation tied to the relevant logic.
*   **Standardized Format:** Include your name, contact information, and a timestamp in your comments. This helps track the origin of ideas and provides a point of contact for questions.
*   **Visual Cues:** Use a distinct color for comment DATs so they are easily identifiable when scanning a network.
*   **Formatting:** Always enable "Word Wrap" on Text DATs used for comments to ensure readability. Use plain text formatting and avoid pasting from rich text editors like Word or Google Docs, which can introduce incompatible characters.

## Summary of "Do"s and "Don't"s:

**Do:**
*   Color-code your comments for easy identification.
*   Use a standard format including name, contact info, and a timestamp.
*   Place comments close to the relevant part of the network.
*   Enable the "Word Wrap" feature on Text DATs.

**Don't:**
*   Consolidate all your notes into a single, large Text DAT.
*   Make comment DATs disproportionately sized compared to other operators.
*   Leave no comments at all. Any note is better than none.
