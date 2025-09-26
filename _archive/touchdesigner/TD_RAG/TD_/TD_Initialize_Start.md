---
title: "Initialize Start"
category: "TD_"
document_type: "guide"
difficulty: "intermediate"
time_estimate: "15-20 minutes"
user_personas: ["script_developer", "component_builder", "show_control_designer"]
completion_signals: ["can_implement_a_timed_process", "understands_the_init_ready_run_done_states"]
operators: ["TimerCHOP", "FBXCOMP", "USDCOMP", "BulletSolverCOMP", "NvidiaFlowTOP", "NvidiaFlexTOP", "NotchTOP", "AnimationCOMP", "EngineCOMP", "FeedbackPOP", "ParticlePOP", "InfoCHOP"]
concepts: ["initialize_start", "state_machine", "cooking", "callbacks", "procedural", "timer"]
prerequisites: ["TD_Event", "TD_Procedural"]
workflows: ["show_control", "timed_events", "simulation_setup", "generative_systems"]
keywords: ["initialize", "start", "timer", "state", "ready", "running", "done", "callback"]
tags: ["core", "concept", "workflow", "state_machine", "timer"]
related_docs:
- "TD_Event"
- "TD_TimerCHOP"
---

# Initialize Start

## Content
- [Introduction](#introduction)
- [Examples](#examples)
- [Control Parameters](#control-parameters)
- [Info Channels](#info-channels)
- [Behavior](#behavior)
- [Callbacks](#callbacks)
- [Errors and Warnings](#errors-and-warnings)
- [See Also](#see-also)

## Introduction

Initialize Start is an approach in TouchDesigner to prepare and run timed processes. It applies to any system where there first needs to be an initialization (the `initializing` state), like reading files into memory, querying servers, pre-simulating dynamics or starting external processes. When initializing is complete, it goes into the `ready` state. Then it is signaled to start via a `Start` pulse parameter.

Upon Start, it goes into the `running` state, and when complete (when a timer reaches its length and it's not looping, or when `Go to Done` is pulsed) it goes into a `done` state.

The `ready` state has to be fully-primed and ready-to-go such that when `Start` is pressed, the first frame is perfectly valid and suffers no frame drops or delays.

Initialization often takes more than one frame to complete, so there is usually provision to initialize over several frames without substantially stalling TouchDesigner. The `initializing` state may last several frames.

> **Note:** The convention is, if you press `Start` when it is already running or when it is done, it is equivalent to going to done, pressing `Initialize` and then starting. That is, the Initialize stage automatically goes to completion before it starts again.

Initialize Start is based on the `Timer CHOP`.

## Examples

Examples of parts of TouchDesigner where the Initialize Start approach is used are:

- `Timer CHOP`
- `FBX COMP`
- `USD COMP`
- `Bullet Solver COMP`
- `Nvidia Flow TOP`, `Nvidia Flex TOP`
- `Notch TOP`
- `Animation COMP`
- `Palette:moviePlayer` COMP
- `Palette:particlesGpu` COMP
- `Engine COMP`
- `Feedback POP`
- `Particle POP`

There is a component in the palette called `initalizeStart` that you can use to convert any of your components to use the same mechanism.

## Control Parameters

- `Initialize` (pulse) - prepares all data, in `initializing` state.
- `Start` (pulse) - starts all the timers, puts in `running` state.
- `Play` (toggle) - used to pause while playing.
- `Speed` (float) - speed or slows the timer or simulation clock while running.
- `Cue` (toggle), `Cue Pulse` (pulse), `Cue Point` (float with menu % index, frames, seconds) - allows you to put/scrub system at specified time.
- `Length` (float) - if behavior is fixed-length, length is sometimes pre-determined like a movie file, sometimes user-set.
- `Pre-Roll` (float) - if behavior is a procedural simulation, at initialization, it may run the sim a few seconds to get it going.
- `Initialize Time` (float) - for fixed-length systems, where implemented, this initializes part-way into its internal timeline.
- `Go to Done` (pulse) - stops all the timers, possibly goes to an end-state, puts in `done` state.

## Info Channels

This is often achieved by attaching an `Info CHOP` to the operator. It is the actual output in the `Timer CHOP` and the `initializeStart` palette COMP.

- **States**
  - `initializing` (0 if operator currently initializes in the same-frame)
  - `ready` (after Initialize complete and before Start pressed)
  - `running` goes on after Start, stays on until Done or Initialize
  - `done` where applicable

- **Counters** - used to drive animations, index lookups, etc.
  - `timer_fraction` (where applicable) For fixed-length setups, it is `timer_seconds / length_seconds`. (For infinite length setups or length is not known, it is set to 0.)
  - `timer_seconds` (seconds) It is affected by Speed and Play. If the length is known and you loop, your `timer_seconds` goes back to 0. It’s really your calculated `index / (end - start) / (file_sample_rate)`
  - `timer_frames` (where available - number of frames based on the timeline frames per second.)
  - `cumulative_seconds` (seconds) counts from 0 when you Start. It is slowed down and sped up by the `Speed` parameter, and paused by the `Play` parameter. It continues to increase if there is any looping, jumping or scrubbing around.
  - `master_seconds` (seconds) - counts time from 0 when you Start, it is slowed down and sped up by the `Speed` parameter, and is paused by the `Play` parameter. This is the main clock. (It will jumps to the appropriate time if there is provision for scrubbing or jumping.)
  - `running_seconds` (seconds) - It keeps counting up after Start and is not affected by changing the `Speed` or pausing `Play` or scrubbing. It is basically the "wall clock" after pressing Start. It stops when you `Go to Done`. It doesn't reset to 0 until you `Initialize` or `Start` again.
  - `playing_seconds` (seconds) - counts from 0 when you Start, is like `running_seconds` but it is paused when `Play` pauses.
  - `length_seconds` for operators with known length
  - `cycles` (where applicable)

## Behavior

Fixed-length vs infinite (unknown) length. An example of infinite length would be a particle simulation. There are two flavors of fixed-length - user-specified length or media-determined length (like an audio file).

## Callbacks

In some cases, like the `Timer CHOP`, there are callbacks where you can run python code when events occur, such as the end of initialization, or the end of a fixed-length behavior. The common ones are:

- `onInitialize()` called when the Initialize is pulsed, and is called every frame thereafter until you return 0, in order for multi-frame initializations to occur.
- `onReady()` is called when initialization is complete.
- `onStart()` is called when Start is pressed.
- `onDone()` is called when fixed-length systems complete, and when `Go to Done` is pulsed.

## Errors and Warnings

In some cases, the operator reports errors or warnings, like failure to initialize.

## See Also

- [TD_Event]
