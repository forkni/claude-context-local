---
title: "Sync"
category: "REF_"
document_type: "guide"
difficulty: "intermediate"
time_estimate: "10 minutes"
user_personas: ["live_performer", "installation_artist", "systems_integrator"]
completion_signals: ["understands_different_levels_of_sync", "knows_which_ops_to_use_for_sync"]
operators: ["TouchInCHOP", "TouchInTOP", "TouchOutCHOP", "TouchOutTOP", "OSCOutDAT", "OSCOutCHOP", "SyncInCHOP", "SyncOutCHOP", "WindowCOMP", "AudioMovieCHOP", "AudioDeviceOutCHOP"]
concepts: ["sync", "synchronization", "frame_lock", "vertical_sync", "tearing", "multi_computer"]
prerequisites: []
workflows: ["multi_computer_setup", "video_wall", "projection_mapping", "audio_video_sync"]
keywords: ["sync", "synchronize", "frame", "lock", "tearing", "multi-computer"]
tags: ["core", "concept", "performance", "hardware", "sync"]
related_docs:
- "HARDWARE_SyncingMultipleComputers"
- "HARDWARE_HardwareFrameLock"
- "TD_VerticalSync"
---

# Sync

## Content
- [Synchronizing Multiple Computers](#synchronizing-multiple-computers)
- [Syncing on One Computer](#syncing-on-one-computer)
- [Syncing Movie Audio and Video](#syncing-movie-audio-and-video)
- [Syncing Generative Content](#syncing-generative-content)

## Synchronizing Multiple Computers

The levels of synchronizing computers are:

- **No Sync**
- **Weak Software Sync** (`Touch In CHOP`, `Touch In TOP`, `Touch Out CHOP`, `Touch Out TOP`) sending data streams with queues to assure continuity.
- **Medium Software Sync** (`OSC Out DAT` or `OSC Out CHOP`) nodes sending frame number, time code, etc. to other processes.
- **Tight Software Sync** (`Sync In CHOP`/`Sync Out CHOP`)
- **Tight Software Sync + Hardware Sync** (`Sync In`/`Out CHOPs` + Hardware Frame Lock in the `Window COMP` + Quadro Sync cards)

`Sync In`/`Out CHOPs` is a software sync that syncs the creation of the content. Hardware Sync/Frame Lock syncs the presentation of the content to the displays. Hardware Frame lock is the method to achieve hardware sync. But we can use the terms interchangeably as well.

It is not effective to use Hardware Sync if you don’t have Tight Software Sync going since the content presented to the hardware will not be in sync in the first place. However, it can be effective to use Tight Software Sync without Hardware Sync: the content will arrive to the hardware in-sync but the vertical refresh phase of the displays may be out of sync. Additionally, Hardware Frame Lock ensures that the displays only update when they are all ready to update. So if one machine drops a frame, they all drop a frame. This may or may not be desirable, depending on the content and the display setup.

See also: [HARDWARE_SyncingMultipleComputers], [HARDWARE_HardwareFrameLock].

## Syncing on One Computer

See [TD_VerticalSync] and Horizontal Tearing, [COMP_WindowCOMP].

## Syncing Movie Audio and Video

Since audio and video from a movie file take different paths, see `Audio Sync Offset` adjustments in `Audio Movie CHOP` and `Buffer Length` in `Audio Device Out CHOP`. There will also be further delay in the audio hardware to your speakers and ears. Video delays go through double-triple buffering on your graphics card, and delays in your display monitor and your video cabling/routing.

## Syncing Generative Content

TBD
