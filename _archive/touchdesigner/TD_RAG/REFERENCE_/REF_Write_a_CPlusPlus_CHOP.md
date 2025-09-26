---
title: "Write a CPlusPlus CHOP"
category: "REF_"
document_type: "guide"
difficulty: "advanced"
time_estimate: "5 minutes"
user_personas: ["c++_developer", "plugin_developer", "data_processor"]
completion_signals: ["understands_chop_plugin_specifics"]
operators: ["CPlusPlusCHOP"]
concepts: ["c++", "plugin", "chop", "time_slicing", "channel"]
prerequisites: ["REF_Write_a_CPlusPlus_Plugin", "TD_TimeSlicing"]
workflows: ["custom_chop_development", "realtime_data_processing"]
keywords: ["c++", "plugin", "chop", "channel", "time_slice"]
tags: ["c++", "sdk", "plugin", "development", "advanced", "chop"]
related_docs:
- "REF_WriteACPlusPlusPlugin"
- "REF_WriteACPlusPlusTOP"
- "REF_UpgradingCustomOperators"
- "TD_TimeSlicing"
---

# Write a CPlusPlus CHOP

## Content
- [Overview](#overview)
- [Output Channels](#output-channels)
- [Time Sliced Data](#time-sliced-data)
- [See Also](#see-also)

## Overview

Make sure you've read through [REF_WriteACPlusPlusPlugin] first for general information about writing a plugin for a `CPlusPlus CHOP`.

The `CPlusPlus CHOP` allows you to manipulate [CHOP] data using custom code, or bring in/output [CHOP] data to and from external sources or file formats.

## Output Channels

You can use one of the [CHOP]'s inputs to determine the number of channels, channel names, sample rate etc. of the output, or you can specify them in code (in `getOutputInfo()`).

To get started it is much easier to output non-Time Sliced data, where you specify the length of the channels and you just fill that much data every frame. The example that comes with the TouchDesigner installer outputs a Time Slice for illustration though.

## Time Sliced Data

If you are unfamiliar with what a time slice is, see the [TD_TimeSlicing] article.

If the plugin is outputting time sliced data then TouchDesigner will tell you how many samples it wants you to output. The number of samples depends on how long it's been since TouchDesigner last cooked (due to skipped frames), and the sample rate of the Time Slice vs the sample rate of the [CHOP]. For example let's say the [CHOP] is outputting 120hz sample rate data and the Timeline is running at 60hz. If TouchDesigner skipped cooking the last frame the Time Slice size will be 2 frames long. Since the [CHOP]s sample rate is 120hz vs. the 60hz of the timeline, you will be asked to provide 4 samples of data per channel to fill the Time Slice.

## See Also

- [REF_WriteACPlusPlusPlugin]
- [REF_WriteACPlusPlusTOP]
- [REF_UpgradingCustomOperators]
