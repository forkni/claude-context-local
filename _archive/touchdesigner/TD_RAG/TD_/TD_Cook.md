---
title: "Cook"
category: "TD_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "visual_programmer", "performance_tuner", "beginner"]
completion_signals: ["understands_pull_based_cooking", "can_use_performance_monitor", "knows_what_triggers_a_cook"]
operators: ["TouchOutCHOP", "OSCOutCHOP", "NDIOutTOP", "VideoDeviceOutTOP", "AudioDeviceOutCHOP", "ConstantCHOP", "MathCHOP", "TimeSliceCHOP", "VideoDeviceInTOP", "RenderTOP", "NullCHOP"]
concepts: ["cooking", "dependency", "pull_system", "push_system", "event", "performance", "optimization"]
prerequisites: ["TD_Procedural", "TD_Event"]
workflows: ["performance_monitoring", "network_optimization", "debugging"]
keywords: ["cook", "cooking", "performance", "dependency", "pull", "optimize"]
tags: ["core", "concept", "performance", "cooking", "dependency"]
related_docs:
- "PERF_Optimize"
- "TD_Procedural"
- "TD_Event"
- "CHOP_NullCHOP"
---

# Cook

## Content
- [Introduction](#introduction)
- [Cooking Mechanism](#cooking-mechanism)
  - [What Causes Cooking](#what-causes-cooking)
  - [The Order of Cooking](#the-order-of-cooking)
- [Event-Driven Cooking](#event-driven-cooking)
- [Forced Cooking](#forced-cooking)
- [See Also](#see-also)

## Introduction

Cooking is the term in TouchDesigner used for computing or calculating the operators of networks. Middle-click on a node to see how long it last cooked, and how many times it cooked since you started TouchDesigner.

TouchDesigner will cook a node only when it needs to - it doesn't cook every node every frame.

For each frame, TouchDesigner will consider cooking:

- Nodes whose viewers are visible in the Network.
- Nodes that contribute to panels being displayed in a panel or a `Window COMP`.
- Nodes that contribute to network operators sending data out from TouchDesigner, such as `Touch Out CHOP`, `OSC Out CHOP`.
- Nodes that contribute to sending video/audio out via nodes such as `NDI Out TOP`, `Video Device Out TOP`, `Audio Device Out CHOP`.

When you see the Wires between nodes animating (dashed lines animating), it means the upstream node is cooking. the downstream node(s) may or may not be cooking. Middle mouse-click on any node and see in the info pop-up if the cook count is rising.

`Dialogs -> Performance Monitor` will show you what has cooked in one frame. Making your synth run at 30 or 60 frames per second involves minimizing the number of nodes that cook.

The `Probe` component in `Tools` in the palette lets you watch what is cooking live.

## Cooking Mechanism

### What Causes Cooking

For a node to cook two things need to be true: (1) The node needs to have a cook request (something asking it to cook), and (2) it needs to have a reason to cook.

**Things that cause a cook request:**

- A node connected to that node's output wants to cook.
- A node referencing that node via a parameter wants to cook.
- A viewer is looking at the node's data.
- A node that a [CHOP] or [DAT] is exporting to wants to cook.
- Calling the `cook()` method on an [OP].

**Things that give a node a reason to cook:**

- One of that node's inputs has cooked.
- A node it points to via a parameter has cooked.
- One of the node's parameters change.
- Specific scripting commands are run on the node.
- The result of an expression may have changed.
- A variable the node refers to changes values.
- A node that one of its parameter's expressions points to has cooked.
- The node is time dependent, that is to say each frame it can output different data, even if none of its inputs or parameters change (like the `Time Slice CHOP`, or a `Video Device In TOP`).
- A user interacts with it, but only if it is a Panel Component.

When a node receives a cook request, it requests that all of its inputs cook, which may or may not cause them to cook. If any of them cook, then it has been given a reason to cook, and it'll cook. If none of them cook then it'll check for other possible reasons to cook. If none of those are present, it won't cook (and you won't see it in the Performance Monitor).

For example, if you are looking at the viewer for a default `Constant CHOP` (one channel with no expressions), that node is constantly getting cook requests (every time the UI redraws for example), but it never cooks, because it has no reason to cook.

### The Order of Cooking

TouchDesigner is a "pull system". A common misconception with cooking in TouchDesigner is that cooking starts upstream and moves downstream. For example if you have `Constant CHOP` connected to a `Math CHOP`, most people assume if you change a value in the `Constant CHOP` then the `Math CHOP` is forced to cook. This is incorrect. Almost all operators will only cook when something is interested in their data. What this means in our example is that while changing a parameter in the `Constant CHOP` will make it 'dirty', it won't cook until someone asks for its data. So the `Constant CHOP` won't cook until the `Math CHOP` asks for its data. The `Constant CHOP` may cook for other reasons, like if its viewer is on (ie. the user is asking to see its data).

What pulls? All your display devices that want an image every frame will pull all the [TOPs] and other [OPs] that contribute to a frame of image. Same for your audio output devices that want samples to go to your audio hardware every frame.

## Event-Driven Cooking

See [TD_Event]. All the "Execute" [DATs] respond to events they receive, and via their python callback functions, they can cause parameters of other operators to change or other operators to cook. The groups of "Execute" [DATs] includes `Panel Execute DAT`, `CHOP Execute DAT`, `Parameter Execute DAT`, `DAT Execute DAT`, `Render Pick DAT`. Other operators like `Monitors DAT`, `OP Find DAT`, `Folder DAT` have callbacks that are called when conditions change that can also change parameters and cook nodes. When parameters are changed, the target nodes will only cook according to the above pull-system cooking rules. And when any nodes is forced to cook by calling `OP.cook()`, its data is passed downstream, also according to the above cooking rules.

## Forced Cooking

Some nodes, specifically nodes like the `Movie File Out TOP`, `Touch Out` [OPs] and other *Out [OPs] will cook every frame, regardless of any of their inputs or parameters changing. This behavior ensures that the recipient of their output (a movie, a network pipe, etc.) gets a continuous stream of data.

Other nodes, if asked to cook, will cook even if none of their inputs or parameters have changed. These are mainly special nodes like the `Render TOP`, and *In [OPs] (like the `Touch In` and `Pipe In CHOPs`, but not `In CHOPs` and `In SOPs`). The nodes have so many possible input changes to monitor (for the `Render TOP`: materials, geometry position, geometry render flags, etc.) that instead of trying to figure out if they should cook, they just do. Always cooking saves computation cycles 99% of the time for these nodes, as most of the time something is changing in the rendered scene.

## See Also

- [PERF_Optimize]
- [TD_Procedural]
- [TD_Event]
- [CHOP_NullCHOP]
