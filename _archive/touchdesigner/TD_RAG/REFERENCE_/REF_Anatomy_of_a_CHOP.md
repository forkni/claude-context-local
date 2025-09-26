---
title: "Anatomy of a CHOP"
category: "REF_"
document_type: "guide"
difficulty: "beginner"
time_estimate: "15 minutes"
user_personas: ["vj", "motion_graphics_artist", "developer", "beginner"]
completion_signals: ["understands_chop_structure", "knows_how_to_import_export_channels"]
operators: ["AudioFileInCHOP", "AudioMovieCHOP", "AudioPlayCHOP", "AudioDeviceInCHOP", "AudioDeviceOutCHOP"]
concepts: ["chop", "channel", "sample", "clip", "interval", "sample_rate", "exporting", "importing"]
prerequisites: []
workflows: ["audio_processing", "motion_control", "data_manipulation"]
keywords: ["chop", "channel", "audio", "motion", "sample", "export", "import"]
tags: ["core", "concept", "chop", "operator"]
related_docs:
- "TD_CHOPs"
---

# Anatomy of a CHOP

## Content
- [Inside a CHOP](#inside-a-chop)
- [CHOP Inputs, Parameters and Outputs](#chop-inputs-parameters-and-outputs)
- [Parts of a CHOP](#parts-of-a-chop)
- [CHOP Networks](#chop-networks)
- [Importing / Exporting CHOP Channels](#importing--exporting-chop-channels)
  - [Object, SOP and COP Channels Imported from CHOPs](#object-sop-and-cop-channels-imported-from-chops)
  - [CHOPs Exported to Component, SOP and TOP Channels](#chops-exported-to-component-sop-and-top-channels)
- [Channel Index and Value](#channel-index-and-value)
- [CHOPs for Audio](#chops-for-audio)

## Inside a CHOP

- A [CHOP] contains a set of channels defined over a start-end interval.
- The channels of a [CHOP] can represent motion, MIDI, audio, color maps, rolloff curves or lookup tables.
- Each channel is one array of raw samples, which is simply a list of numbers.
- Each channel of a [CHOP] has a channel name that can be set by the user.
- The group of [CHOP] channels is known as a clip.
- A [CHOP] contains a clip plus control parameters, a sample rate, some on/off flags, and a start/end interval.
- The [CHOP] can have any start/end indexes. All channels in a [CHOP] share the same start-end interval.
- The interval goes from the start position to the end position.
- The interval of a [CHOP] is not restricted to be the length of the animation.
- Each [CHOP] has a sample rate, used if the [CHOP] contains time-dependent motion or audio data.
- Audio has a high sample rates when compared to animated motion.

## CHOP Inputs, Parameters and Outputs

- [CHOPs] have "parameters" used to define the data, plus the data channels, which are input/output from the [CHOP] as its data stream.
- The [CHOP] parameters are usually constant-valued, but can be time-dependent expressions.
- Each [CHOP] receives channels at its inputs. When the [CHOP] cooks, the channels of the inputs are combined. The [CHOP] outputs the resulting channels to other [CHOPs].
- [CHOPs] output their data channels as arrays of numbers, not interpolated segments. Some [CHOPs] retain interpolated segments internally, but all [CHOPs] always output their data as raw samples.
- If the [CHOP]'s inputs are not changing and the control parameters are not time-dependent, the [CHOP] will be non-time-dependent and it will not cook every time the animation frame advances.
- Some [CHOPs] have Local Variables:
  - `$I` (the array index within the CHOP)
  - `$C` (the channel number within the CHOP)
- Some [CHOPs] output or use [CHOP] attributes, such as channels grouped as quaternion rotation channels.

## Parts of a CHOP

- Each [CHOP] has a set of parameters.
- [CHOPs]' parameters can be expressed in different units: samples (indexes), frames or seconds. These units are selected by the user in a menu to the right of such parameters.
- Each [CHOP] has flags:
  - The `Graph` flag marks the [CHOP] to be displayed in the Graph of the CHOP Editor.
  - The `Export` flag causes the [CHOP] channels to override channels of objects, [SOPs].
  - The `Lock` flag causes the [CHOP] can be locked and hand-edited. The Channel Editor is the interactive editor of parameter channels in [CHOPs].
  - The `Bypass` flag is a convenient way for a [CHOP]'s effect to be disabled.
- Each [CHOP] has an info pop-up menu accessible by middle-mouse clicking on the [CHOP]. This lists channel names and values, sample rate and interval.
- Each [CHOP] has a comment field.

## CHOP Networks

[CHOPs] are arranged in OP networks in components, where [CHOP] outputs are connected to the inputs of other [CHOPs].

## Importing / Exporting CHOP Channels

### Object, SOP and COP Channels Imported from CHOPs

Parameters of [SOPs], [TOPs] and objects (components) are able to get values from [CHOP] channels with expressions like the following:

```python
chop(CHOPchannelpath)
chopi(CHOPchannelpath, index)
```

However, exporting is preferred where possible. It is faster and involves less typing.

### CHOPs Exported to Component, SOP and TOP Channels

- [CHOP] data channels are exported to Components, [SOPs], etc. to drive their parameters. [CHOPs] can be exported to any TouchDesigner parameter.
- Each [CHOP] has an `Export` flag (and an `Export Prefix`, infrequently used), causing the [CHOP] to attach its channels to Components, [SOPs], [TOPs] and so on.
- The `Export` flag and `Export Prefix` are used to connect channels of an object or [SOP] directly to a [CHOP]. It uses automatic matching of channels names. For example, a [CHOP] "tx" channel could map to an Geometry Component's `tx` parameter.
- When a [CHOP] exports to an object, [SOP] or [TOP], the latters' channels are said to be overridden. An [OP]'s Override menu lists what is overridden.

## Channel Index and Value

- The horizontal axis is called the `i-axis` or the `index-axis`.
- The vertical axis is called the `v-axis` or the `value-axis`.
- An index is a point along the `i-axis`, denoted by `i`.
- A value is a point along the `v-axis`, denoted by `v`.
- A sample is an index-value pair `(i,v)`. i.e. the value of a channel at a certain index.
- A sample is made of a sample index and a sample value.
- An interval is an index range, which goes from a start index to an end index.
- A value range goes from a start value to an end value.
- The index duration is the end index minus the start index + 1.
- [CHOP] data channels are arrays of raw samples, in 32-bit floating point format.
- Channels in a [CHOP] may be control (parameter) channels or data channels. [CHOPs] manupulate the data channels.
- [CHOPs] can be evaluated at integer and non-integer indexes.
- Frame is used when the index corresponds to time.
- When speaking of animation frames, you can refer to start frame, end frame and frame range.

## CHOPs for Audio

- `Audio File In CHOP`
- `Audio Movie CHOP`
- `Audio Play CHOP`
- `Audio Device In CHOP`
- `Audio Device Out CHOP`
