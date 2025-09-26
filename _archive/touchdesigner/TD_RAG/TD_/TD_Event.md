---
title: "Event"
category: "TD_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "10-15 minutes"
user_personas: ["script_developer", "visual_programmer", "interactive_designer"]
completion_signals: ["understands_event_driven_logic", "can_identify_event_operators"]
operators: ["CHOPExecuteDAT", "ParameterExecuteDAT", "DATExecuteDAT", "ExecuteDAT", "OPExecuteDAT", "OPFindDAT", "PanelExecuteDAT", "RenderPickDAT", "RenderPickCHOP", "MultiTouchInDAT", "KeyboardInDAT", "MIDIInDAT", "MIDIEventDAT", "OSCInDAT", "SerialDAT", "TCPIP_DAT", "WebsocketDAT", "WebClientDAT", "WebServerDAT", "UDPInDAT", "ArtNetDAT", "FolderDAT", "MonitorsDAT", "MQTTClientDAT", "TimerCHOP", "EventCHOP", "TriggerCHOP", "SpeedCHOP", "CountCHOP"]
concepts: ["event", "callback", "push_system", "pull_system", "procedural", "cooking", "pulse"]
prerequisites: ["TD_Procedural"]
workflows: ["interactive_systems", "device_integration", "ui_scripting"]
keywords: ["event", "callback", "execute", "dat", "pulse", "trigger"]
tags: ["core", "concept", "event", "scripting"]
related_docs:
- "TD_Cook"
- "TD_EventCHOP"
- "TD_Procedural"
---

# Event

## Content
- [Introduction](#introduction)
- [Operators that Respond to Events](#operators-that-respond-to-events)
- [Other Causes of Scripts Running](#other-causes-of-scripts-running)
- [Notes](#notes)
- [See Also](#see-also)

## Introduction

Events in TouchDesigner are single-moment occurrences that are generated from a variety of conditions - from input actions that a user causes, from external devices and software, and from internal TouchDesigner states caused by things like timers and values crossing thresholds.

A variety of operators (mostly [DATs]) respond to events. Each one has python callback functions in a [DAT] that enable a user to write code to react to events.

TouchDesigner is a [TD_Procedural] pull-based system (outputs to displays, audio devices and other destinations cook the nodes it needs to generate the outputs). But it is also a push system based on operators that respond to events.

The event operators respond to events they receive via their python callback functions. The callbacks can cause other operators to change and cook via their parameters, table cells, extension properties, storage.

## Operators that Respond to Events

The operators that respond to events are:

- The groups of "Execute" [DATs] that respond to changes within TouchDesigner:
  - `CHOP Execute DAT`
  - `Parameter Execute DAT`
  - `DAT Execute DAT`
  - `Execute DAT`
  - `OP Execute DAT`
  - `OP Find DAT`

- The [DATs] that respond to user interface interactions:
  - `Panel Execute DAT`
  - `Render Pick DAT`, `Render Pick CHOP`, `Multi Touch In DAT`
  - `Keyboard In DAT`

- Operators that react to external events:
  - `MIDI In DAT`, `MIDI Event DAT`
  - `OSC In DAT`
  - `Serial DAT`
  - `TCP/IP DAT`
  - `WebSocket DAT`
  - `Web Client DAT`
  - `Web Server DAT`
  - `UDP In DAT`
  - `Art-Net DAT`
  - `Folder DAT`
  - `Monitors DAT`
  - `MQTT Client DAT`

- Operators that run scripts when some of their their parameters are pulsed:
  - `Timer CHOP`
  - `Event CHOP`

- And operators that react to event pulses:
  - `Trigger CHOP`
  - `Speed CHOP`
  - `Count CHOP`
  - The numerous operators that react to Initialize and Start pulses.

Operators like `OP Find DAT` and `Folder DAT`, have callbacks that are called when conditions change. The callbacks can then change parameters and subsequently cause nodes to cook.

Pulse type parameters of operators can be pulsed using `OP.par.parname.pulse()`. Custom Pulse type parameters can cause the pulse callback in a `Parameter Execute DAT`.

## Other Causes of Scripts Running

The Script operators (`Script CHOP`, `Script DAT`, `Script TOP`, `Script SOP`) are not event nodes - they are part of the pull system and will cook when TouchDesigner determines it depends on some other data in TouchDesigner - channels, parameters, table cells, extension properties, storage.

When the event operators change parameters or other data, the target nodes will then cook according to the pull-system cooking rules.

## Notes

> **Note:** You can force a node to cook by calling `OP.cook()`. Its data is passed downstream according to the cooking rules.

## See Also

- [TD_Cook]
- [TD_EventCHOP]
- [TD_Procedural]
