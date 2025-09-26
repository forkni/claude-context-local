---
title: "Syncing Multiple Computers"
category: HARDWARE
document_type: guide
difficulty: beginner
time_estimate: 15-25 minutes

# Enhanced metadata
user_personas: ["hardware_specialist", "system_administrator", "advanced_user", "technical_artist"]
completion_signals: ["configures_multi_computer_sync", "understands_hardware_synchronization", "can_implement_cluster_systems", "manages_network_synchronization"]

operators:
- Sync_In_CHOP
- Sync_Out_CHOP
- OSC_In_CHOP
- OSC_Out_CHOP
- Particle_SOP
- Feedback_TOP
concepts:
- multi-computer_synchronization
- software_sync
- hardware_sync
- frame_lock
- genlock
- deterministic_rendering
- client_server_architecture
- network_synchronization
prerequisites:
- networking_basics
- REF_ComponentTime
- multi_computer_concepts
workflows:
- multi-computer_installations
- video_walls
- synchronized_playback
- cluster_rendering
- large_scale_installations
keywords:
- multi-computer
- multi-machine
- sync
- frame lock
- genlock
- software sync
- hardware sync
- deterministic
- cluster
- server
- client
- network sync
- Quadro Sync
- OSC
- multicast
- real-time
tags:
- multi-computer
- sync
- networking
- hardware
- nvidia
- quadro
- frame_lock
- real-time
- installation
relationships:
  REF_HardwareFrameLock: strong
  CLASS_SyncInCHOP: strong
  CLASS_SyncOutCHOP: strong
  REF_ComponentTime: strong
  HARDWARE_Multiple_Monitors: medium
  REF_Environment_Variables: medium
related_docs:
- REF_HardwareFrameLock
- CLASS_SyncInCHOP
- CLASS_SyncOutCHOP
- REF_ComponentTime
- HARDWARE_Multiple_Monitors
- REF_Environment_Variables
# Enhanced search optimization
search_optimization:
  primary_keywords: ["sync", "computer", "multi", "hardware"]
  semantic_clusters: ["hardware_configuration", "multi_computer_systems", "synchronization_setup"]
  user_intent_mapping:
    beginner: ["what is computer sync", "basic sync setup", "multi computer basics"]
    intermediate: ["sync configuration", "cluster setup", "network synchronization"]
    advanced: ["complex sync systems", "large installations", "advanced synchronization"]

hierarchy:
  secondary: synchronization
  tertiary: multi_computer_sync
question_patterns:
- Hardware setup guide?
- Multi-monitor configuration?
- Installation requirements?
- Hardware compatibility?
common_use_cases:
- multi-computer_installations
- video_walls
- synchronized_playback
- cluster_rendering
---

# Syncing Multiple Computers

<!-- TD-META
category: HARDWARE
document_type: guide
operators: [Sync_In_CHOP, Sync_Out_CHOP, OSC_In_CHOP, OSC_Out_CHOP, Particle_SOP, Feedback_TOP]
concepts: [multi-computer_synchronization, software_sync, hardware_sync, frame_lock, genlock, deterministic_rendering, client_server_architecture, network_synchronization]
prerequisites: [networking_basics, REF_ComponentTime, multi_computer_concepts]
workflows: [multi-computer_installations, video_walls, synchronized_playback, cluster_rendering, large_scale_installations]
related: [REF_HardwareFrameLock, CLASS_SyncInCHOP, CLASS_SyncOutCHOP, REF_ComponentTime, HARDWARE_Multiple_Monitors, REF_Environment_Variables]
relationships: {
  "REF_HardwareFrameLock": "strong",
  "CLASS_SyncInCHOP": "strong",
  "CLASS_SyncOutCHOP": "strong",
  "REF_ComponentTime": "strong",
  "HARDWARE_Multiple_Monitors": "medium",
  "REF_Environment_Variables": "medium"
}
hierarchy:
  primary: "hardware"
  secondary: "synchronization"
  tertiary: "multi_computer_sync"
keywords: [multi-computer, multi-machine, sync, frame lock, genlock, software sync, hardware sync, deterministic, cluster, server, client, network sync, Quadro Sync, OSC, multicast, real-time]
tags: [multi-computer, sync, networking, hardware, nvidia, quadro, frame_lock, real-time, installation]
TD-META -->

## 🎯 Quick Reference

**Purpose**: Hardware setup guide for TouchDesigner installations
**Difficulty**: Beginner
**Time to read**: 15-25 minutes
**Use for**: multi-computer_installations, video_walls, synchronized_playback

**Common Questions Answered**:

- "Hardware setup guide?" → [See relevant section]
- "Multi-monitor configuration?" → [See relevant section]
- "Installation requirements?" → [See relevant section]
- "Hardware compatibility?" → [See relevant section]

## 🔗 Learning Path

**Prerequisites**: [Networking Basics] → [Ref Componenttime] → [Multi Computer Concepts]
**This document**: HARDWARE reference/guide
**Next steps**: [REF HardwareFrameLock] → [CLASS SyncInCHOP] → [CLASS SyncOutCHOP]

**Related Topics**: multi-computer installations, video walls, synchronized playback

## Summary

Guide covering software and hardware synchronization methods for multi-computer TouchDesigner installations, including frame lock and deterministic rendering concepts.

## Relationship Justification

Strong connection to hardware synchronization as the primary topic. Links to related articles for specific OPs that utilize synchronization. Strong relationship with Component Time for timeline management in sync scenarios.

## Content

- [Overview](#overview)
- [Source of Sync Errors](#source-of-sync-errors)
  - [Content Generation](#content-generation)
  - [Displaying Content](#displaying-content)
- [Types of Sync](#types-of-sync)
  - [Software Sync](#software-sync)
  - [Hardware Sync](#hardware-sync)
- [See Also](#see-also)

## Overview

It is always simpler to keep projects on a single computer with a single GPU. However if a situation arises where work must be split up between more GPUs or computers, it possible that some level of synchronization between the systems will be necessary. What level of sync is necessary is highly situation dependent on the display setup and content. You may need very tight sync at the hardware level or in other cases basic sync at the software level will be sufficient.

For projects with very slow moving content, or displays that are far apart from each other, a very basic sync may be fine and perfect sync/hardware sync would be overkill. For other projects with fast moving content and displays that are very close to each other, you may require perfect sync to make it look good.

## Source of Sync Errors

From the start of rendering a frame to when it finally gets displayed it to a monitor there are various stages where sync errors can be introduced.

### Content Generation

For multiple computers to be outputting synced images, they must first be generating the same images for the same frame. If you are playing a video this means ensuring they are playing the same frame of video. If you are rendering a scene this means ensuring all the objects and cameras are using the same transforms and geometry on that frame. These problems are solved with software sync. Some algorithms for generating content do not lend themselves well to sync, such as the [CLASS_ParticleSOP], or generating images using a network with a [CLASS_FeedbackTOP]. This is because these methods use information from the previous frame to calculate the current frame. If at any time one of the computers drops a frame its content may start to diverge from the other machine's content. Even a single dropped frame can result in drastically different results after a few seconds of more rendering.

Ideally the project is being build should be able to guarantee that if it's given a certain command or a certain set of control channels, it will always output the same thing. This is called a 'deterministic' project. This is often achieved by having everything driving by a single frame index, or a set of channels that controls the state of everything in the project.

Once you have a project that is 'deterministic', the next step is to ensure the computers get the commands/control channels at the same time, or as close to the same time as possible. This is done using Software Sync. Simple software sync can often have a sync error of between 1-3 frames. Perfect software sync should have 0 frame sync errors for content generation. There may still be a 1 frame sync error caused by the displays though, described in the next section.

**Detail**: The [CLASS_SyncOutCHOP] is the server, and the [CLASS_SyncInCHOP] are the clients. The Out node waits for messages from the In nodes telling it they have finished a frame, before send out a new frame worth of data. As noted, Particle systems are tricky since if every client is calculating their own data, just diverging their calculations for one frame will results in drastically different results. So if you need perfection you should run your server and clients with realtime off, so it never skips a frame (which may affect the visual smoothness), and make sure all the clients are always using the exact same input when doing their calculations. Often people want to have one of their render nodes be the server, which is OK but you need to ensure the work that generates your time.absframe ($F) etc. is separate from all the nodes that do your rendering. This is doable using [REF_ComponentTime]. Put the [CLASS_SyncOutCHOP] in one COMP with it's own timeline, and use a [CLASS_SyncInCHOP] in the same file with that's reading values from that [CLASS_SyncOutCHOP]. It should be in another COMP with it's own time again, and it should use the values from the [CLASS_SyncInCHOP] to do it's rendering, not anything direct coming from the [CLASS_SyncOutCHOP]'s network. All the other clients will only have a [CLASS_SyncInCHOP] active.

### Displaying Content

Even if the computers are generating content in perfect sync, displaying the images may introduce up to 1 frame of sync errors. This is because the refresh interval of the displays on different machines will not be in phase. If you are running at 60fps, then the time when each display starts doing it's refresh may be offset by up to 16.6ms from each other. This is solved with Hardware Sync/Hardware Frame Lock.

## Types of Sync

### Software Sync

Software sync ensures that all the processes are generating the same content at the same time.

Pro users can get perfect software sync by using the [CLASS_SyncInCHOP], [CLASS_SyncOutCHOP].

Commercial and Non-Commercial users will not be able to get guaranteed perfect software sync, but can get sync that is usually within 1-3 frames by using network nodes such as the [CLASS_OSCInCHOP]/[CLASS_OSCOutCHOP] or [CLASS_OSCInDAT]/[CLASS_OSCOutDAT], and make sure to use Multicast as the network protocol. For the OSC CHOPs, but sure to turn off queuing to ensure there is no latency added to your data by the [CLASS_OSCInCHOP]. The vast majority of projects use this type of sync, because the content and/or display setup doesn't display 1-3 frame sync errors. If displays are far apart, or content moves slowly, perfect sync often isn't needed.

### Hardware Sync

Hardware sync is used to ensure that all displays update their content at the same time, and ensure that one doesn't update it's content without the others being ready to update their content. This may be necessary for arrays of displays (such as a Christie Microtile Wall) with fast moving content. Without hardware sync displays may refresh at different times, adding up to 1 frame of sync error to the content. To achieve hardware sync you will need Quadro GPUs with Quadro Sync cards. For more information on hardware sync refer to the [REF_HardwareFrameLock] article.

## See Also
