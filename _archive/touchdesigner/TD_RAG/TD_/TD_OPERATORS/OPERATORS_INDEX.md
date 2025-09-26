# TouchDesigner Operators Reference

## Overview

Complete reference for all 422 TouchDesigner operators with descriptions and parameter documentation.

## Quick Navigation by Family

- [CHOP - Channel Operators - Process and manipulate channel data (128)](#family-chop)
- [TOP - Texture Operators - Process and manipulate image/texture data (101)](#family-top)
- [SOP - Surface Operators - Process and manipulate 3D geometry (102)](#family-sop)
- [DAT - Data Operators - Process and manipulate table/text data (57)](#family-dat)
- [COMP - Component Operators - Container and UI components (25)](#family-comp)
- [MAT - Material Operators - Shading and material definitions (9)](#family-mat)

---

## Family: CHOP {#family-chop}

**Channel Operators - Process and manipulate channel data**

**Total Operators**: 128

[View CHOP Family Index](./CHOP/CHOP_INDEX.md)

### Analyze

**Type**: CHOP | **Category**: General
**Description**: Looks at the values of all the values of a channel, and outputs a single-number result into the output.
**Details**: [View Full Documentation](./CHOP/Analyze.md)

### Angle

**Type**: CHOP | **Category**: General
**Description**: Is a general purpose converter between degrees, radians, quaternions and vectors.  Different formats assume a specific ordering of input channels.
**Details**: [View Full Documentation](./CHOP/Angle.md)

### Attribute

**Type**: CHOP | **Category**: General
**Description**: Adds, removes or updates attributes of the input CHOP. Currently there is only one attribute type, a "quaternion".
**Details**: [View Full Documentation](./CHOP/Attribute.md)

### Audio Band EQ

**Type**: CHOP | **Category**: General
**Description**: Is a 16-band equalizer which filters audio input channels in the same way that a conventional band (graphic) equalizer uses a bank of sliders to filter fixed-frequency bands of sound.
**Details**: [View Full Documentation](./CHOP/Audio_Band_EQ.md)

### Audio Device In

**Type**: CHOP | **Category**: General
**Description**: Receives audio from any of the attached audio input devices using DirectSound or ASIO. It always outputs time sliced audio data.
**Details**: [View Full Documentation](./CHOP/Audio_Device_In.md)

### Audio Device Out

**Type**: CHOP | **Category**: General
**Description**: Sends audio to any of the attached audio output devices using DirectSound or ASIO. The audio channels can be routed to any speaker location.
**Details**: [View Full Documentation](./CHOP/Audio_Device_Out.md)

### Audio Dynamics

**Type**: CHOP | **Category**: General
**Description**: Is designed to control the dynamic range of an audio signal. Dynamic range refers to how loud and quiet the audio is over some period of time.
**Details**: [View Full Documentation](./CHOP/Audio_Dynamics.md)

### Audio File In

**Type**: CHOP | **Category**: General
**Description**: Reads audio from files on disk or at http:// addresses. File types .mp3, .aif, .aiff, .au, and .wav files are supported.
**Details**: [View Full Documentation](./CHOP/Audio_File_In.md)

### Audio Filter

**Type**: CHOP | **Category**: General
**Description**: Removes low frequencies, high frequencies, both low and high, or removes a mid-frequency range. A Low pass filter removes the higher frequencies of a sound, while a high pass filter reduces the bass of the sound.
**Details**: [View Full Documentation](./CHOP/Audio_Filter.md)

### Audio Movie

**Type**: CHOP | **Category**: General
**Description**: Plays the audio of a movie file that is played back with a Movie File In TOP . Make the Audio Movie TOP point to a Movie File In TOP via the Movie File In TOP parameter.
**Details**: [View Full Documentation](./CHOP/Audio_Movie.md)

### Audio Oscillator

**Type**: CHOP | **Category**: General
**Description**: Generates sounds in three ways. It repeats common waveforms (sine, triangle), it generates white noise (a random number for each sample), or it repeats a prepared incoming audio clip of any duration.
**Details**: [View Full Documentation](./CHOP/Audio_Oscillator.md)

### Audio Para EQ

**Type**: CHOP | **Category**: General
**Description**: (parametric equalizer ) applies up to 3 parametric filters to the incoming sound. The three filters are in series, where internally, the second filter takes its input from the output of the first filter, and so on.
**Details**: [View Full Documentation](./CHOP/Audio_Para_EQ.md)

### Audio Play

**Type**: CHOP | **Category**: General
**Description**: Plays back a sound file through any attached audio output device using DirectSound. It supports .aif, .
**Details**: [View Full Documentation](./CHOP/Audio_Play.md)

### Audio SDI In

**Type**: CHOP | **Category**: General
**Description**: Is a TouchDesigner Pro only operator. The Audio SDI In CHOP can capture the audio from any SDI In TOP .
**Details**: [View Full Documentation](./CHOP/Audio_SDI_In.md)

### Audio Spectrum

**Type**: CHOP | **Category**: General
**Description**: Calculates and displays the frequency spectrum of the input channels. In the default Visualization Mode the CHOP is set to display the spectrum in a more understandable way by emphasizing the higher frequency levels and the lower frequency ranges.
**Details**: [View Full Documentation](./CHOP/Audio_Spectrum.md)

### Audio Stream In

**Type**: CHOP | **Category**: General
**Description**: Can stream audio into TouchDesigner from any rtsp server.
**Details**: [View Full Documentation](./CHOP/Audio_Stream_In.md)

### Audio Stream Out

**Type**: CHOP | **Category**: General
**Description**: Can stream audio out to any rtsp client such as VideoLAN's VLC media player and Apple's Quicktime. To access the stream in one of these players, open a "Network Stream" or "URL" under the File menu.
**Details**: [View Full Documentation](./CHOP/Audio_Stream_Out.md)

### Beat

**Type**: CHOP | **Category**: General
**Description**: Generates a variety of ramps, pulses and counters that are timed to the beats per minute and the sync produced by the Beat Dialog or the beat Command .
**Details**: [View Full Documentation](./CHOP/Beat.md)

### Blend

**Type**: CHOP | **Category**: General
**Description**: Combines two or more CHOPs in input 2, 3 and so on, by using a set of blending channels in input 1. The blending channels cause different strengths of the CHOPs to contribute to the output of the CHOP.
**Details**: [View Full Documentation](./CHOP/Blend.md)

### CPlusPlus

**Type**: CHOP | **Category**: General
**Description**: Allows you to make custom CHOP operators by writing your own .dll using C++. Note : The CPlusPlus CHOP is only available in TouchDesigner Commercial and TouchDesigner Pro .
**Details**: [View Full Documentation](./CHOP/CPlusPlus.md)

### Clip

**Type**: CHOP | **Category**: General
**Description**: Is a TouchDesigner Pro only operator. See.
**Details**: [View Full Documentation](./CHOP/Clip.md)

### Clip Blender

**Type**: CHOP | **Category**: General
**Description**: Is a TouchDesigner Pro only operator.  It can be used as an animation system that blends between different animation clips, preserving rotation, changing target positions etc.
**Details**: [View Full Documentation](./CHOP/Clip_Blender.md)

### Clock

**Type**: CHOP | **Category**: General
**Description**: Generates channels that reflect the time of year, month, week, day, hour, minute, second and millisecond.
**Details**: [View Full Documentation](./CHOP/Clock.md)

### Composite

**Type**: CHOP | **Category**: General
**Description**: Layers (blends) the channels of one CHOP on the channels of another CHOP. The first input is the base input and the second is the layer input.
**Details**: [View Full Documentation](./CHOP/Composite.md)

### Constant

**Type**: CHOP | **Category**: General
**Description**: Creates up to forty new constant-value channels. Each channel can be named and assigned a different value.
**Details**: [View Full Documentation](./CHOP/Constant.md)

### Copy

**Type**: CHOP | **Category**: General
**Description**: Produces multiple copies of the second input along the timeline of the first input. The first input provides the trigger signals or the convolve levels.
**Details**: [View Full Documentation](./CHOP/Copy.md)

### Count

**Type**: CHOP | **Category**: General
**Description**: Counts the number of times a channel crosses a trigger or release threshold. It operates in either static or realtime ("Cook to Current Frame") mode.
**Details**: [View Full Documentation](./CHOP/Count.md)

### Cross

**Type**: CHOP | **Category**: General
**Description**: Is a multi input OP that blends between 2 inputs at a time. This is similar to a Switch CHOP however the Cross CHOP allows for interpolation between the inputs.
**Details**: [View Full Documentation](./CHOP/Cross.md)

### Cycle

**Type**: CHOP | **Category**: General
**Description**: Creates cycles. It can repeat the channels any number of times before and after the original. It can also make a single cycle have a smooth transition from its end to its beginning, so it loops smoothly.
**Details**: [View Full Documentation](./CHOP/Cycle.md)

### DAT to

**Type**: CHOP | **Category**: General
**Description**: Will create a set of CHOP channels with values derived from a DAT .
**Details**: [View Full Documentation](./CHOP/DAT_to.md)

### DMX In

**Type**: CHOP | **Category**: General
**Description**: Receives channels from DMX or Art-Net devices.  Channel values for DMX are 0-255. NOTE: In TouchDesigner Non-commercial, the DMX Out CHOP is limited to 32 channels.
**Details**: [View Full Documentation](./CHOP/DMX_In.md)

### DMX Out

**Type**: CHOP | **Category**: General
**Description**: Sends channels to DMX or Art-Net devices.  Channel values for DMX are 0-255. The first channel you send into the DMX Out will correspond to the first DMX address (DMX channel) As you add channels to the DMX Out, you will access the next DMX channels in order.
**Details**: [View Full Documentation](./CHOP/DMX_Out.md)

### Delay

**Type**: CHOP | **Category**: General
**Description**: Delays the input. Multiple channels can be fed in to delay each separately and each channels can have a separate delay time.
**Details**: [View Full Documentation](./CHOP/Delay.md)

### Delete

**Type**: CHOP | **Category**: General
**Description**: Removes entire channels and/or individual samples of its input. A first method uses a text string to select channels by name or number ranges.
**Details**: [View Full Documentation](./CHOP/Delete.md)

### Envelope

**Type**: CHOP | **Category**: General
**Description**: Outputs the maximum amplitude in the vicinity of each sample of the input. It takes the absolute value of the input, and uses a sliding window of a number of samples to find the maximum amplitude near each sample.
**Details**: [View Full Documentation](./CHOP/Envelope.md)

### EtherDream

**Type**: CHOP | **Category**: General
**Description**: Takes as input up to five channels interpreted as X and Y (horizontal and vertical) position values in the first 2 channels, and red, green and blue color values in the next 3 channels.
**Details**: [View Full Documentation](./CHOP/EtherDream.md)

### Event

**Type**: CHOP | **Category**: General
**Description**: Manages the birth and life of overlapping events triggered by devices like a MIDI keyboard. It can be seen as a simple particle system designed for MIDI keyboards.
**Details**: [View Full Documentation](./CHOP/Event.md)

### Expression

**Type**: CHOP | **Category**: General
**Description**: Allows you to modify input channels by using math expressions. Up to six expressions are available. Each input channel is modified by exactly one expression, and the expressions are looped for multiple channels.
**Details**: [View Full Documentation](./CHOP/Expression.md)

### Extend

**Type**: CHOP | **Category**: General
**Description**: Only sets the "extend conditions" of a CHOP, which determines what values you get when sampling the CHOP before or after its interval.
**Details**: [View Full Documentation](./CHOP/Extend.md)

### Fan

**Type**: CHOP | **Category**: General
**Description**: Converts one channel out to many channels, or converts many channels down to one. Its first operation, Fan Out, takes one channel and generates 2 or more channels.
**Details**: [View Full Documentation](./CHOP/Fan.md)

### Feedback

**Type**: CHOP | **Category**: General
**Description**: Stores channels from the current frame to be used in a later frame, without forcing recooking back one frame.
**Details**: [View Full Documentation](./CHOP/Feedback.md)

### File In

**Type**: CHOP | **Category**: General
**Description**: Reads in channel and audio files for use by CHOPs. The file can be read in from disk or from the web.
**Details**: [View Full Documentation](./CHOP/File_In.md)

### File Out

**Type**: CHOP | **Category**: General
**Description**: Writes CHOP channel data out to .chan files. The data can be written out every frame or at intervals (set by the Interval parameter) into a log file.
**Details**: [View Full Documentation](./CHOP/File_Out.md)

### Filter

**Type**: CHOP | **Category**: General
**Description**: Smooths or sharpens the input channels. It filters by combining each sample and a range of its neighbor samples to set the new value of that sample.
**Details**: [View Full Documentation](./CHOP/Filter.md)

### Function

**Type**: CHOP | **Category**: General
**Description**: Provides more complicated math functions than found in the Math CHOP : trigonometic functions, logarithmic functions and exponential functions, and also audio decibels (dB)-power-amplitude conversions.
**Details**: [View Full Documentation](./CHOP/Function.md)

### Gesture

**Type**: CHOP | **Category**: General
**Description**: Records a short segment of the first input and loops this segment in time with options as specified in the Gesture Page.
**Details**: [View Full Documentation](./CHOP/Gesture.md)

### Handle

**Type**: CHOP | **Category**: General
**Description**: Is the "engine" which drives Inverse Kinematic solutions using the Handle COMP . The role of the Handle CHOP is to generate rotation values for the bones which will bring their attached handles as close to their respective targets as possible.
**Details**: [View Full Documentation](./CHOP/Handle.md)

### Hog

**Type**: CHOP | **Category**: General
**Description**: Eats up CPU cycles (ie it's a CPU hog - oink!). This can be used to simulate performance on slower machines, or to artifically slow down a synth's frame rate.
**Details**: [View Full Documentation](./CHOP/Hog.md)

### Hold

**Type**: CHOP | **Category**: General
**Description**: Waits for a 0 to 1 step on its second input, at which time it reads the current values from the first input (one value per channel).
**Details**: [View Full Documentation](./CHOP/Hold.md)

### In

**Type**: CHOP | **Category**: General
**Description**: Gets channels that are connected to one of the inputs of the component. For each In CHOP inside a component, there is one input connector added to the In CHOP's parent component.
**Details**: [View Full Documentation](./CHOP/In.md)

### Info

**Type**: CHOP | **Category**: General
**Description**: Gives you extra information about a node. All nodes contain extra inside information, and different types of nodes (TOPs, CHOPs, etc) contain different subsets of information.
**Details**: [View Full Documentation](./CHOP/Info.md)

### Interpolate

**Type**: CHOP | **Category**: General
**Description**: Treats its multiple-inputs as keyframes and interpolates between them. The inputs are usually single-frame CHOP channels like those produced by a Constant CHOP .
**Details**: [View Full Documentation](./CHOP/Interpolate.md)

### Inverse Curve

**Type**: CHOP | **Category**: General
**Description**: Calculates an inverse kinematics simulation for bone objects using a curve object. The Inverse Curve CHOP will stretch and position a set of bones to follow a curve defined by another set of objects (guide).
**Details**: [View Full Documentation](./CHOP/Inverse_Curve.md)

### Inverse Kin

**Type**: CHOP | **Category**: General
**Description**: Calculates an inverse kinematics simulation for Bone objects .
**Details**: [View Full Documentation](./CHOP/Inverse_Kin.md)

### Join

**Type**: CHOP | **Category**: General
**Description**: Takes all its inputs and appends one CHOP after another. It is expected they all have the same channels.
**Details**: [View Full Documentation](./CHOP/Join.md)

### Joystick

**Type**: CHOP | **Category**: General
**Description**: Outputs values for all 6 possible axes on any game controller (joysticks, game controllers, driving wheels, etc.
**Details**: [View Full Documentation](./CHOP/Joystick.md)

### Keyboard In

**Type**: CHOP | **Category**: General
**Description**: Receives ASCII input from the keyboard, and outputs channels for the number of keys specified. It creates a single-frame channel representing the current state of each key.
**Details**: [View Full Documentation](./CHOP/Keyboard_In.md)

### Keyframe

**Type**: CHOP | **Category**: General
**Description**: Uses channel and keys data in an Animation COMP and creates channels of samples at a selectable sample rate (frames per second).
**Details**: [View Full Documentation](./CHOP/Keyframe.md)

### Kinect

**Type**: CHOP | **Category**: General
**Description**: Reads positional and skeletal tracking data from the Kinect and Linect2 sensors.  Up to 6 people's full skeletons can be tracked (2 on the original Kinect), and the center position of an addition 4 people in the camera view is tracked as well.
**Details**: [View Full Documentation](./CHOP/Kinect.md)

### LFO

**Type**: CHOP | **Category**: General
**Description**: (low frequency oscillator) generates waves in real-time in two ways. It synthesizes curves using a choice of common waveforms like Sine or Pulse, or it repeats a prepared incoming curve.
**Details**: [View Full Documentation](./CHOP/LFO.md)

### LTC In

**Type**: CHOP | **Category**: General
**Description**: Reads SMPTE timecode data encoded into an audio signal.  Read the overview Linear Timecode . First bring the audio signal into CHOPs using an Audio Device In CHOP .
**Details**: [View Full Documentation](./CHOP/LTC_In.md)

### LTC Out

**Type**: CHOP | **Category**: General
**Description**: Outputs "linear timecode" which is a SMPTE timecode data encoded into an audio signal.  See also Linear Timecode .
**Details**: [View Full Documentation](./CHOP/LTC_Out.md)

### Lag

**Type**: CHOP | **Category**: General
**Description**: Adds lag and overshoot to channels. It can also limit the velocity and acceleration of channels. Lag slows down rapid changes in the input channels.
**Details**: [View Full Documentation](./CHOP/Lag.md)

### Leap Motion

**Type**: CHOP | **Category**: General
**Description**: Reads hand, finger, tool and gesture data from the Leap Motion controller. It outputs hand, finger and tool positions, rotations and 'tracking' channels that indicate if these values are currently being detected and updated.
**Details**: [View Full Documentation](./CHOP/Leap_Motion.md)

### Limit

**Type**: CHOP | **Category**: General
**Description**: Can limit the values of the input channels to be between a minimum and maximum, and can quantize the input channels in time and/or value such that the value steps over time.
**Details**: [View Full Documentation](./CHOP/Limit.md)

### Logic

**Type**: CHOP | **Category**: General
**Description**: First converts channels of all its input CHOPs into binary (0 = off, 1 = on) channels and then combines the channels using a variety of logic operations.
**Details**: [View Full Documentation](./CHOP/Logic.md)

### Lookup

**Type**: CHOP | **Category**: General
**Description**: Outputs values from a lookup table. The first input (the Index Channel) is an index into the second input (the Lookup Table).
**Details**: [View Full Documentation](./CHOP/Lookup.md)

### MIDI In

**Type**: CHOP | **Category**: General
**Description**: Reads Note events, Controller events, Program Change events, System Exclusive messages and Timing events from both MIDI devices and files.
**Details**: [View Full Documentation](./CHOP/MIDI_In.md)

### MIDI In Map

**Type**: CHOP | **Category**: General
**Description**: See first the MIDI In DAT . The MIDI In Map CHOP reads in specified channels from the MIDI Device Mapper which prepares slider channels starting from s1, s2, etc.
**Details**: [View Full Documentation](./CHOP/MIDI_In_Map.md)

### MIDI Out

**Type**: CHOP | **Category**: General
**Description**: Sends MIDI events to any available MIDI devices when its input channels change. More flexibly, the Python MidioutCHOP Class can be used to send any type of MIDI event to a MIDI device via an existing MIDI Out CHOP.
**Details**: [View Full Documentation](./CHOP/MIDI_Out.md)

### Math

**Type**: CHOP | **Category**: General
**Description**: Performs arithmetic operations on channels. The channels of a CHOP can be combined into one channel, and several CHOPs can be combined into one CHOP.
**Details**: [View Full Documentation](./CHOP/Math.md)

### Merge

**Type**: CHOP | **Category**: General
**Description**: Takes multiple inputs and merges them into the output. All the channels of the input appear in the output.
**Details**: [View Full Documentation](./CHOP/Merge.md)

### Mouse In

**Type**: CHOP | **Category**: General
**Description**: Outputs X and Y screen values for the mouse device and monitors the up/down state of the three mouse buttons.
**Details**: [View Full Documentation](./CHOP/Mouse_In.md)

### Mouse Out

**Type**: CHOP | **Category**: General
**Description**: Forces the mouse position and button status to be driven from TouchDesigner using the incoming CHOP channels.
**Details**: [View Full Documentation](./CHOP/Mouse_Out.md)

### NatNet In

**Type**: CHOP | **Category**: General
**Description**: The NatNet In CHOP.
**Details**: [View Full Documentation](./CHOP/NatNet_In.md)

### Noise

**Type**: CHOP | **Category**: General
**Description**: Makes an irregular wave that never repeats, with values approximately in the range -1 to +1. It generates both smooth curves and noise that is random each sample.
**Details**: [View Full Documentation](./CHOP/Noise.md)

### Null

**Type**: CHOP | **Category**: General
**Description**: Is used as a place-holder and does not alter the data coming in. It is often used to Export channels to parameters, which allows you to experiment with the CHOPs that feed into the Null without having to un-export from one CHOP and re-export from another.
**Details**: [View Full Documentation](./CHOP/Null.md)

### OSC In

**Type**: CHOP | **Category**: General
**Description**: Is used to accept Open Sound Control Messages. OSC In can be used to accept messages from either a 3rd party application which adheres to the Open Sound Control specification ( <http://www>.
**Details**: [View Full Documentation](./CHOP/OSC_In.md)

### OSC Out

**Type**: CHOP | **Category**: General
**Description**: Sends all input channels to a specified network address and port. Each channel name and associated data is transmitted together to the specified location.
**Details**: [View Full Documentation](./CHOP/OSC_Out.md)

### Object

**Type**: CHOP | **Category**: General
**Description**: Compares two objects and outputs channels containing their raw or relative positions and orientations.
**Details**: [View Full Documentation](./CHOP/Object.md)

### Oculus Audio

**Type**: CHOP | **Category**: General
**Description**: Uses the Oculus Audio SDK to take a mono sound channel and create a spatialized stereo pair or channels for that sound.
**Details**: [View Full Documentation](./CHOP/Oculus_Audio.md)

### Oculus Rift

**Type**: CHOP | **Category**: General
**Description**: Connects to an Oculus Rift device and outputs several useful sets of channels that can be used to integrate the Oculus Rift into projects.
**Details**: [View Full Documentation](./CHOP/Oculus_Rift.md)

### Out

**Type**: CHOP | **Category**: General
**Description**: Sends CHOP data from inside a components to other components or CHOPs. It sends channels to one of the outputs of the component.
**Details**: [View Full Documentation](./CHOP/Out.md)

### Override

**Type**: CHOP | **Category**: General
**Description**: Lets you take inputs from several CHOP sources, and uses the most-recently changed input channels to determine the output.
**Details**: [View Full Documentation](./CHOP/Override.md)

### Panel

**Type**: CHOP | **Category**: General
**Description**: Reads Panel Values from Panel Components into CHOP channels. Panel values can also be accessed by using the panel() expression.
**Details**: [View Full Documentation](./CHOP/Panel.md)

### Parameter

**Type**: CHOP | **Category**: General
**Description**: Gets parameter values, including custom parameters, from all OP types. ( In Build 46000 or later . This replaces the Fetch CHOP.
**Details**: [View Full Documentation](./CHOP/Parameter.md)

### Pattern

**Type**: CHOP | **Category**: General
**Description**: Generates a sequence of samples in a channel. Unlike the Wave CHOP its purpose is generating arrays of samples that have no reference to time (seconds or frames).
**Details**: [View Full Documentation](./CHOP/Pattern.md)

### Perform

**Type**: CHOP | **Category**: General
**Description**: Outputs many channels like frames-per-second, describing the current state of the TouchDesigner process.
**Details**: [View Full Documentation](./CHOP/Perform.md)

### Pipe In

**Type**: CHOP | **Category**: General
**Description**: Allows users to input from custom devices into CHOPs. It is implemented as a TCP/IP network connection.
**Details**: [View Full Documentation](./CHOP/Pipe_In.md)

### Pipe Out

**Type**: CHOP | **Category**: General
**Description**: Can be used to transmit data out of TouchDesigner to other processes running on a remote machine using a network connection.
**Details**: [View Full Documentation](./CHOP/Pipe_Out.md)

### Pulse

**Type**: CHOP | **Category**: General
**Description**: Generates pulses in one channel at regular intervals. The amplitude of each pulse can be edited with the CHOP sliders or with handles on the graph.
**Details**: [View Full Documentation](./CHOP/Pulse.md)

### RealSense

**Type**: CHOP | **Category**: General
**Description**: Receives positional data from Intel's RealSense camera. See also RealSense TOP Available in builds 50000 or later.
**Details**: [View Full Documentation](./CHOP/RealSense.md)

### Record

**Type**: CHOP | **Category**: General
**Description**: Takes the channels coming in the first (Position) input, converts and records them internally, and outputs the stored channels as the CHOP output.
**Details**: [View Full Documentation](./CHOP/Record.md)

### Rename

**Type**: CHOP | **Category**: General
**Description**: Renames channels. Channels names from the input CHOP are matched using the From pattern, and are renamed to the corresponding name in the To pattern.
**Details**: [View Full Documentation](./CHOP/Rename.md)

### Render Pick

**Type**: CHOP | **Category**: General
**Description**: Samples a rendering (from a Render TOP or a Render Pass TOP ) and returns 3D information from the geometry at that particular pick location.
**Details**: [View Full Documentation](./CHOP/Render_Pick.md)

### Reorder

**Type**: CHOP | **Category**: General
**Description**: Re-orders the first input CHOP's channels by numeric or alphabetic patterns. Either a channel pattern specifies the new order, or a number sequence specifies the new order.
**Details**: [View Full Documentation](./CHOP/Reorder.md)

### Replace

**Type**: CHOP | **Category**: General
**Description**: Can be used to replace channels very quickly. The output of channels in Input1 will be replaced by channels found in Input2 if a matching channel exists in Input2.
**Details**: [View Full Documentation](./CHOP/Replace.md)

### Resample

**Type**: CHOP | **Category**: General
**Description**: Resamples an input's channels to a new sample rate and/or start/end interval. In all cases, the entire input interval is resampled to match the output interval.
**Details**: [View Full Documentation](./CHOP/Resample.md)

### SOP to

**Type**: CHOP | **Category**: General
**Description**: Uses a geometry object to choose a SOP from which the channels will be created. The channels are created from the point attributes of a SOP, such as the X, Y and Z of the point position.
**Details**: [View Full Documentation](./CHOP/SOP_to.md)

### Scan

**Type**: CHOP | **Category**: General
**Description**: Converts a SOP or TOP to oscilloscope or laser friendly control waves.  The output is usually in the audible range and can be heard directly via an Audio Device Out CHOP, or used to drive the X and Y deflector inputs of an oscilloscope, recreating the imagery.
**Details**: [View Full Documentation](./CHOP/Scan.md)

### Script

**Type**: CHOP | **Category**: General
**Description**: Runs a script each time the Script CHOP cooks. By default, the Script CHOP is created with a docked DAT that contains three Python methods: cook, onPulse, and setupParameters .
**Details**: [View Full Documentation](./CHOP/Script.md)

### Select

**Type**: CHOP | **Category**: General
**Description**: Selects and renames channels from other CHOPs of any CHOP network. You can select the channels from control panel gadgets like sliders and buttons.
**Details**: [View Full Documentation](./CHOP/Select.md)

### Serial

**Type**: CHOP | **Category**: General
**Description**: Is used for serial communication through an external port, using the RS-232 protocol. These ports are usually a 9 pin connector, or a USB port on new machines.
**Details**: [View Full Documentation](./CHOP/Serial.md)

### Shared Mem In

**Type**: CHOP | **Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem In CHOP receives CHOPs from a shared memory segment that is attached to a Shared Mem Out CHOP in another process or the same process.
**Details**: [View Full Documentation](./CHOP/Shared_Mem_In.md)

### Shared Mem Out

**Type**: CHOP | **Category**: General
**Description**: The Shared Mem Out TOP is only available in TouchDesigner Commercial and Pro. The Shared Mem Out CHOP sends CHOPs to a shared memory segment that is attached to a Shared Mem In CHOP in another process or the same process.
**Details**: [View Full Documentation](./CHOP/Shared_Mem_Out.md)

### Shift

**Type**: CHOP | **Category**: General
**Description**: Time-shifts a CHOP, changing the start and end of the CHOP's interval. However, the contents of the channels remain the same.
**Details**: [View Full Documentation](./CHOP/Shift.md)

### Shuffle

**Type**: CHOP | **Category**: General
**Description**: Reorganizes the samples in a set of channels. It is useful for transforming data received by the SOP to CHOP and TOP to CHOPs into channels containing only one row or column.
**Details**: [View Full Documentation](./CHOP/Shuffle.md)

### Slope

**Type**: CHOP | **Category**: General
**Description**: Calculates the slope (or "derivative" in math-speak) of the input channels. If the input CHOP represents position, the slope can be interpreted as speed.
**Details**: [View Full Documentation](./CHOP/Slope.md)

### Sort

**Type**: CHOP | **Category**: General
**Description**: Re-orders the inputs channels samples by value or by random. Specifying a channel to be sorted will reorder all remaining channels samples according to the new order.
**Details**: [View Full Documentation](./CHOP/Sort.md)

### Speed

**Type**: CHOP | **Category**: General
**Description**: Converts speed (units per second) to distance (units) over a time range. More generally, you give it a rate (the CHOP input) and it outputs a cumulative value.
**Details**: [View Full Documentation](./CHOP/Speed.md)

### Spring

**Type**: CHOP | **Category**: General
**Description**: Creates vibrations influenced by the input channels, as if a mass was attached to a spring. It acts as if, for every channel, there is a mass at the end of a spring, affected by a distance from the actual position (the output of the channel at the previous frame) to the desired position (the input channel at the current frame).
**Details**: [View Full Documentation](./CHOP/Spring.md)

### Stretch

**Type**: CHOP | **Category**: General
**Description**: Preserves the shape of channels and the sampling rate, but resamples the channels into a new interval.
**Details**: [View Full Documentation](./CHOP/Stretch.md)

### Switch

**Type**: CHOP | **Category**: General
**Description**: Allows you to control the flow of channels through a CHOPnet. It selects one of the input CHOPs by index and copies it exactly.
**Details**: [View Full Documentation](./CHOP/Switch.md)

### Sync In

**Type**: CHOP | **Category**: General
**Description**: And Sync Out CHOP are used to keep timelines in two or more TouchDesigner processes within a single frame of each other.
**Details**: [View Full Documentation](./CHOP/Sync_In.md)

### Sync Out

**Type**: CHOP | **Category**: General
**Description**: The Sync In CHOP and Sync Out CHOP are used to keep timelines in two or more TouchDesigner processes within a single frame of each other.
**Details**: [View Full Documentation](./CHOP/Sync_Out.md)

### TOP to

**Type**: CHOP | **Category**: General
**Description**: Converts pixels in a TOP image to CHOP channels. It generates one CHOP channel per scanline (row) in the image and per pixel color element (RGBA).
**Details**: [View Full Documentation](./CHOP/TOP_to.md)

### Tablet

**Type**: CHOP | **Category**: General
**Description**: Gets the Wacom tablet X and Y values, and also gets pen tip pressure, X tilt and Y tilt, and the various pen buttons.
**Details**: [View Full Documentation](./CHOP/Tablet.md)

### Time Slice

**Type**: CHOP | **Category**: General
**Description**: Outputs a time slice of samples. It is used to generate smooth in-betweens when TouchDesigner cannot cook/draw fast enough and keep up with the animation's frames per second.
**Details**: [View Full Documentation](./CHOP/Time_Slice.md)

### Timeline

**Type**: CHOP | **Category**: General
**Description**: Outputs time-based CHOP channels for a specific component.  The time channels are defined by a Time Component whose Path can be determined using the expression timepath() .
**Details**: [View Full Documentation](./CHOP/Timeline.md)

### Timer

**Type**: CHOP | **Category**: General
**Description**: Is an engine for running timed processes. It outputs channels such as timing fractions, counters, pulses and timer states, and it calls python functions (callbacks) when various timing events occur.
**Details**: [View Full Documentation](./CHOP/Timer.md)

### Touch In

**Type**: CHOP | **Category**: General
**Description**: Can be used to create a high speed connection between two TouchDesigner processes via CHOPs. Data is sent over TCP/IP.
**Details**: [View Full Documentation](./CHOP/Touch_In.md)

### Touch Out

**Type**: CHOP | **Category**: General
**Description**: Can be used to create high speed connection between two TouchDesigner processes. Data is sent over TCP/IP.
**Details**: [View Full Documentation](./CHOP/Touch_Out.md)

### Trail

**Type**: CHOP | **Category**: General
**Description**: Displays a history of its input channels back in time. A window of time is displayed from the current frame back in time, the size of this window is set by the Window Length parameter.
**Details**: [View Full Documentation](./CHOP/Trail.md)

### Transform

**Type**: CHOP | **Category**: General
**Description**: Takes translate, rotate, and/or scale channels and transforms them using the transform parameters in the CHOP.
**Details**: [View Full Documentation](./CHOP/Transform.md)

### Trigger

**Type**: CHOP | **Category**: General
**Description**: Starts an audio-style attack/decay/sustain/release (ADSR) envelope to all trigger pulses in the input channels.
**Details**: [View Full Documentation](./CHOP/Trigger.md)

### Trim

**Type**: CHOP | **Category**: General
**Description**: Shortens or lengthens the input's channels. A part of the interval can be preserved or removed. If the channels are being lengthened, the extend conditions of the channel will be used to get the new values.
**Details**: [View Full Documentation](./CHOP/Trim.md)

### Warp

**Type**: CHOP | **Category**: General
**Description**: Time-warps the channels of the first input (the Pre-Warp Channels) using one warping channel in the second input (the Warp Curve).
**Details**: [View Full Documentation](./CHOP/Warp.md)

### Wave

**Type**: CHOP | **Category**: General
**Description**: Makes repeating waves with a variety of shapes. It is by default 10-seconds of 1-second sine waves, a total of 600 frames.
**Details**: [View Full Documentation](./CHOP/Wave.md)

---

## Family: TOP {#family-top}

**Texture Operators - Process and manipulate image/texture data**

**Total Operators**: 101

[View TOP Family Index](./TOP/TOP_INDEX.md)

### Add

**Type**: TOP | **Category**: General
**Description**: Composites the input images together by adding the pixel values. Output = Input1 + Input2. It clamps a color channel if the sum exceeds 1.
**Details**: [View Full Documentation](./TOP/Add.md)

### Analyze

**Type**: TOP | **Category**: General
**Description**: Takes any image and determines various characteristics of it, such as the average pixel color, or the pixel with the maximum luminance.
**Details**: [View Full Documentation](./TOP/Analyze.md)

### Anti Alias

**Type**: TOP | **Category**: General
**Description**: The Anti-Alias TOP uses a screen space antialiasing technique called `SMAA: Enhanced Subpixel Morphological Antialiasing´.
**Details**: [View Full Documentation](./TOP/Anti_Alias.md)

### Blob Track

**Type**: TOP | **Category**: General
**Description**: Is implemented using source code from OpenCV, much of which was ported to the GPU for faster performance.
**Details**: [View Full Documentation](./TOP/Blob_Track.md)

### Blur

**Type**: TOP | **Category**: General
**Description**: Blurs the image with various kernel filters and radii. It can do multi-pass blurs and can do horizontal-only or vertical-only blurs.
**Details**: [View Full Documentation](./TOP/Blur.md)

### CHOP to

**Type**: TOP | **Category**: General
**Description**: Puts CHOP channels into a TOP image. The full 32-bit floating point numbers of a CHOP are converted to 32-bit floating point pixel values by setting the TOP's Pixel Format to 32-bit floats.
**Details**: [View Full Documentation](./TOP/CHOP_to.md)

### CPlusPlus

**Type**: TOP | **Category**: General
**Description**: Allows you to make custom TOP operators by writing your own .dll using C++. Note : The CPlusPlus TOP is only available in TouchDesigner Commercial and TouchDesigner Pro .
**Details**: [View Full Documentation](./TOP/CPlusPlus.md)

### CUDA

**Type**: TOP | **Category**: General
**Description**: Runs a CUDA program on a NVIDIA GPU (8000 series and later, full list here ). The use a CUDA TOP, you'll need to write a CUDA DLL .
**Details**: [View Full Documentation](./TOP/CUDA.md)

### Cache

**Type**: TOP | **Category**: General
**Description**: Stores a sequence of images into GPU memory. These cached images can be read by the graphics card much faster than an image cache in main memory or reading images off disk.
**Details**: [View Full Documentation](./TOP/Cache.md)

### Cache Select

**Type**: TOP | **Category**: General
**Description**: Grabs an image from a Cache TOP based on the index parameter. This gives direct, random access to any image stored in a Cache TOP.
**Details**: [View Full Documentation](./TOP/Cache_Select.md)

### Channel Mix

**Type**: TOP | **Category**: General
**Description**: Allows mixing of the input RGBA channels to any other color channel of the output. For example, the pixels in the blue channel of the input can be added to the output's red channel, added or subtracted by the amount in Red parameter's blue column.
**Details**: [View Full Documentation](./TOP/Channel_Mix.md)

### Chroma Key

**Type**: TOP | **Category**: General
**Description**: Pulls a key matte from the image using Hue, Saturation, and Value settings. If a pixel falls between the Min and Max parameters for all three settings, then it is included in the key.
**Details**: [View Full Documentation](./TOP/Chroma_Key.md)

### Circle

**Type**: TOP | **Category**: General
**Description**: Can be used to generate circles, ellipses and N-sided polygons. The shapes can be customized with different sizes, rotation and positioning.
**Details**: [View Full Documentation](./TOP/Circle.md)

### Composite

**Type**: TOP | **Category**: General
**Description**: Is a multi-input TOP that will perform a composite operation for each input. Select the composite operation using the Operation parameter on the Composite parameter page.
**Details**: [View Full Documentation](./TOP/Composite.md)

### Constant

**Type**: TOP | **Category**: General
**Description**: Sets the red, green, blue, and alpha (r, g, b, and a) channels individually. It is commonly used to create a solid color TOP image.
**Details**: [View Full Documentation](./TOP/Constant.md)

### Convolve

**Type**: TOP | **Category**: General
**Description**: Uses a DAT table containing numeric coefficients.  For each pixel, it combines its RGBA values and it's neighboring pixels' RGBA values by multiplying the values by the corresponding coefficients in the table, adding the results together.
**Details**: [View Full Documentation](./TOP/Convolve.md)

### Corner Pin

**Type**: TOP | **Category**: General
**Description**: Can perform two operations. The Extract page lets you specify a sub-section of the image to use by moving 4 points.
**Details**: [View Full Documentation](./TOP/Corner_Pin.md)

### Crop

**Type**: TOP | **Category**: General
**Description**: Crops an image by defining the position of the left, right, bottom, and top edges of the image. The cropped part of the image is discarded, thus reducing the resolution of the image.
**Details**: [View Full Documentation](./TOP/Crop.md)

### Cross

**Type**: TOP | **Category**: General
**Description**: Blends between the two input images based on the value of the Cross parameter (refered to as Cross_value below).
**Details**: [View Full Documentation](./TOP/Cross.md)

### Cube Map

**Type**: TOP | **Category**: General
**Description**: Builds a texture map in the Cube Map internal texture format. It accepts a vertical cross image, or 1 input per side of the cube.
**Details**: [View Full Documentation](./TOP/Cube_Map.md)

### Depth

**Type**: TOP | **Category**: General
**Description**: Reads an image containing depth information from a scene described in a specified Render TOP . The resulting image is black (0) at pixels where the surface is at the near depth value (Camera's parameter "Near").
**Details**: [View Full Documentation](./TOP/Depth.md)

### Difference

**Type**: TOP | **Category**: General
**Description**: Performs a difference composite on its two input images.
**Details**: [View Full Documentation](./TOP/Difference.md)

### DirectX In

**Type**: TOP | **Category**: General
**Description**: Brings DirectX textures from other applications into TouchDesigner.  This feature is only available on Windows 7 or greater, accessed through the DirectX Sharing Resources feature.
**Details**: [View Full Documentation](./TOP/DirectX_In.md)

### DirectX Out

**Type**: TOP | **Category**: General
**Description**: Creates textures that a DirectX application can access, or any instance of TouchDesigner with a DirectX In TOP.
**Details**: [View Full Documentation](./TOP/DirectX_Out.md)

### Displace

**Type**: TOP | **Category**: General
**Description**: Will cause one image to be warped by another image. A pixel of the output image at (Uo,Vo) gets its RGBA value from a different pixel (Ui, Vi) of the Source Image by using the second input image (the Displace Image).
**Details**: [View Full Documentation](./TOP/Displace.md)

### Edge

**Type**: TOP | **Category**: General
**Description**: Finds edges in an image and highlights them. For each pixel, it looks at the values at neighboring pixels, and where differences are greater than a threshold, the output's value is higher.
**Details**: [View Full Documentation](./TOP/Edge.md)

### Emboss

**Type**: TOP | **Category**: General
**Description**: Creates the effect that an image is embossed in a thin sheet of metal. Edges in the image will appear raised.
**Details**: [View Full Documentation](./TOP/Emboss.md)

### Feedback

**Type**: TOP | **Category**: General
**Description**: Can be used to create feedback effects in TOPs. The Feedback TOP's input image will be passed through whenever Feedback is bypassed (by setting the Bypass Feedback parameter = 1).
**Details**: [View Full Documentation](./TOP/Feedback.md)

### Fit

**Type**: TOP | **Category**: General
**Description**: Re-sizes its input to the resolution set on the Common Page using the method specified in the Fit parameter menu.
**Details**: [View Full Documentation](./TOP/Fit.md)

### Flip

**Type**: TOP | **Category**: General
**Description**: Will Flip an image in X and/or Y. It also offers a Flop option to turn each row of pixels into a column.
**Details**: [View Full Documentation](./TOP/Flip.md)

### GLSL

**Type**: TOP | **Category**: General
**Description**: Renders a GLSL shader into a TOP image. Use the Info DAT to check for compile errors in your shaders.
**Details**: [View Full Documentation](./TOP/GLSL.md)

### GLSL Multi

**Type**: TOP | **Category**: General
**Description**: Renders a GLSL shader into a TOP image. Its parameters and functionality are identical to the.
**Details**: [View Full Documentation](./TOP/GLSL_Multi.md)

### HSV Adjust

**Type**: TOP | **Category**: General
**Description**: Adjust color values using hue, saturation, and value controls. If you change the Hue Offset, Saturation Multiplier and Value Multiplier without changing any of the other parameters then you will modify the color of all pixels in the image.
**Details**: [View Full Documentation](./TOP/HSV_Adjust.md)

### HSV to RGB

**Type**: TOP | **Category**: General
**Description**: Converts an image from HSV color channels to RGB color channels.
**Details**: [View Full Documentation](./TOP/HSV_to_RGB.md)

### In

**Type**: TOP | **Category**: General
**Description**: Is used to create a TOP input in a Component. Component inputs are positioned alphanumerically on the left side of the Component.
**Details**: [View Full Documentation](./TOP/In.md)

### Inside

**Type**: TOP | **Category**: General
**Description**: Places Input1 'inside' Input2. The alpha of Input2 is used to determine what parts of the Input1 image are visible.
**Details**: [View Full Documentation](./TOP/Inside.md)

### Kinect

**Type**: TOP | **Category**: General
**Description**: Captures video from the Kinect depth camera or RGB color camera. NOTE: This TOP works with the Kinect for Windows hardware and supports the Kinect2.
**Details**: [View Full Documentation](./TOP/Kinect.md)

### Leap Motion

**Type**: TOP | **Category**: General
**Description**: Gets the image from the Leap Motion Controller's cameras.  To enable this feature the option Allow Images must be turned on in the Leap Motion Control Panel.
**Details**: [View Full Documentation](./TOP/Leap_Motion.md)

### Level

**Type**: TOP | **Category**: General
**Description**: Adjusts image contrast, brightness, gamma, black level, color range, quantization, opacity and more.
**Details**: [View Full Documentation](./TOP/Level.md)

### Lookup

**Type**: TOP | **Category**: General
**Description**: Replaces color values in the TOP image connected to its first input with values derived from a lookup table created from its second intput or a lookup table created using the CHOP parameter.
**Details**: [View Full Documentation](./TOP/Lookup.md)

### Luma Blur

**Type**: TOP | **Category**: General
**Description**: Blurs image on a per-pixel basis depending on the luminance or greyscale value of its second input. The image is blurred with separate parameters for white and black filter sizes, which correspond to the white and black luminance values of the second input.
**Details**: [View Full Documentation](./TOP/Luma_Blur.md)

### Luma Level

**Type**: TOP | **Category**: General
**Description**: Adjusts image brightness, gamma, black level, quantization, opacity and more. It has similar parameters to the Level TOP, but it maintains the hue and saturation more accurately when you use Gamma and Black Level.
**Details**: [View Full Documentation](./TOP/Luma_Level.md)

### Math

**Type**: TOP | **Category**: General
**Description**: Performs specific mathematical operations on the pixels of the input image.
**Details**: [View Full Documentation](./TOP/Math.md)

### Matte

**Type**: TOP | **Category**: General
**Description**: Composites input1 over input2 using the alpha channel of input3 as a matte. White (one) pixels in input3's alpha channel will draw input1 over input2, black (or zero) will make input1 transparent, leaving the input2 image at that pixel.
**Details**: [View Full Documentation](./TOP/Matte.md)

### Monochrome

**Type**: TOP | **Category**: General
**Description**: Changes an image to greyscale colors. You can choose from a number of different methods to convert the image to greyscale using the RGB and Alpha menus.
**Details**: [View Full Documentation](./TOP/Monochrome.md)

### Movie File In

**Type**: TOP | **Category**: General
**Description**: Loads movies, still images, or a sequence of still images into TOPs. It will read images in .jpg, .gif, .
**Details**: [View Full Documentation](./TOP/Movie_File_In.md)

### Movie File Out

**Type**: TOP | **Category**: General
**Description**: Saves a TOP stream out to a QuickTime or MP4 ( .mp4 ) movie in a variety of formats, plus the Animation, Cineform and Hap Q video codecs.
**Details**: [View Full Documentation](./TOP/Movie_File_Out.md)

### Multiply

**Type**: TOP | **Category**: General
**Description**: Performs a multiply operation on Input1 and Input2.
**Details**: [View Full Documentation](./TOP/Multiply.md)

### Noise

**Type**: TOP | **Category**: General
**Description**: Generates a variety of noise patterns including sparse, alligator and random. It currently runs on the CPU and passes its images to the GPU.
**Details**: [View Full Documentation](./TOP/Noise.md)

### Normal Map

**Type**: TOP | **Category**: General
**Description**: Takes an input image and creates a normal map by finding edges in the image. This can then be used for bump mapping (See Phong MAT ).
**Details**: [View Full Documentation](./TOP/Normal_Map.md)

### Null

**Type**: TOP | **Category**: General
**Description**: Has no effect on the image. It is an instance of the TOP connected to its input. The Null TOP is often used when making reference to a TOP network, allowing new TOPs to be added to the network (upstream) without the need to update the reference.
**Details**: [View Full Documentation](./TOP/Null.md)

### OP Viewer

**Type**: TOP | **Category**: General
**Description**: Can display the Node Viewer for any other operator as a TOP image. If the operator source is a Panel Component, panel interaction through the TOP image is also supported.
**Details**: [View Full Documentation](./TOP/OP_Viewer.md)

### Oculus Rift

**Type**: TOP | **Category**: General
**Description**: Note - The Oculus SDK has changed a lot over since the DK1. The original DK1 used the Oculus Rift TOP to do the barrel distortion.
**Details**: [View Full Documentation](./TOP/Oculus_Rift.md)

### Out

**Type**: TOP | **Category**: General
**Description**: Is used to create a TOP output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.
**Details**: [View Full Documentation](./TOP/Out.md)

### Outside

**Type**: TOP | **Category**: General
**Description**: Places Input1 'outside' Input2. Input1 is visible in the output wherever Input2's alpha is <1. This is the opposite operation to the Inside TOP.
**Details**: [View Full Documentation](./TOP/Outside.md)

### Over

**Type**: TOP | **Category**: General
**Description**: Places Input1 'over' Input2. The alpha of Input1 is used to determine what parts of the Input2 image are visible in the result.
**Details**: [View Full Documentation](./TOP/Over.md)

### Pack

**Type**: TOP | **Category**: General
**Description**: Note: Only in builds 48000 or later.
**Details**: [View Full Documentation](./TOP/Pack.md)

### Photoshop In

**Type**: TOP | **Category**: General
**Description**: Can stream the output from Photoshop CS6 into TouchDesigner.  Photoshop can be running on the same computer as TouchDesigner or any other computer on the network.
**Details**: [View Full Documentation](./TOP/Photoshop_In.md)

### Point File In

**Type**: TOP | **Category**: General
**Description**: Loads 3D point data into TOPs from either a single file or a sequence of files. Points are composed of one or more floating point values such as XYZ positions, RGB color values, 3D normals, scanner intensity, etc. Supports OBJ, PLY, EXR, PTS, and more.
**Details**: [View Full Documentation](./TOP/Point_File_In.md)

### Point File Select

**Type**: TOP | **Category**: General
**Description**: Creates additional output images from a point file loaded into a Point File In TOP. Useful when the point data file has more than 4 channels e.g. XYZ position and RGB colors.
**Details**: [View Full Documentation](./TOP/Point_File_Select.md)

### Point Transform

**Type**: TOP | **Category**: General
**Description**: Treats the RGB values of the input image as a point cloud of XYZ positions or vectors and performs 3D transformations and alignments.
**Details**: [View Full Documentation](./TOP/Point_Transform.md)

### Projection

**Type**: TOP | **Category**: General
**Description**: Takes a Cube Map created with a Render TOP and converts that to a fisheye projection suitable for domes, and a "equirectangular" projection, where u-v is latitude-longitude, suitable for spheres.
**Details**: [View Full Documentation](./TOP/Projection.md)

### RGB Key

**Type**: TOP | **Category**: General
**Description**: Pulls a key from the image using Red, Green, and Blue channel settings. If a pixel falls between the Min and Max parameters for all three settings, then it is included in the key.
**Details**: [View Full Documentation](./TOP/RGB_Key.md)

### RGB to HSV

**Type**: TOP | **Category**: General
**Description**: The RGV to HSV TOP converts the image from RGB to HSV colorspace. The R channel becomes Hue, the G channel becomes Saturation, and the B channel becomes Value.
**Details**: [View Full Documentation](./TOP/RGB_to_HSV.md)

### Ramp

**Type**: TOP | **Category**: General
**Description**: Allows you to interactively create vertical, horizontal, radial, and circular ramps. Using the ramp bar and the color picker, you can add as many color tabs to the ramp as you like, each with its own color and alpha values.
**Details**: [View Full Documentation](./TOP/Ramp.md)

### RealSense

**Type**: TOP | **Category**: General
**Description**: Connects to RealSense devices and outputs color, depth and IR data from it. See also RealSense CHOP.
**Details**: [View Full Documentation](./TOP/RealSense.md)

### Rectangle

**Type**: TOP | **Category**: General
**Description**: Can be used to generate Rectangles with rounded corners. The shapes can be customized with different sizes, rotation and positioning.
**Details**: [View Full Documentation](./TOP/Rectangle.md)

### Remap

**Type**: TOP | **Category**: General
**Description**: Uses the second input to warp the first input. For every pixel of the output, it uses the red channel and green channel of the second input to choose which pixel to pick from the first input.
**Details**: [View Full Documentation](./TOP/Remap.md)

### Render

**Type**: TOP | **Category**: General
**Description**: Is used to render all 3D scenes in TouchDesigner. You need to give it a Camera object and a Geometry object as a minimum.
**Details**: [View Full Documentation](./TOP/Render.md)

### Render Pass

**Type**: TOP | **Category**: General
**Description**: Is used along with a Render TOP to achieve multipass rendering. It can build upon its inputs render by using the existing depth/color information in the framebuffers, or it can optionally clear one or both of the depth/color buffers before it does its render.
**Details**: [View Full Documentation](./TOP/Render_Pass.md)

### Render Select

**Type**: TOP | **Category**: General
**Description**: Allows you to select one of the color buffers from any Render TOP .
**Details**: [View Full Documentation](./TOP/Render_Select.md)

### Reorder

**Type**: TOP | **Category**: General
**Description**: Is a multi-input TOP which lets you choose any of the input channels for the R, G, B, and A output. It also gives the option of outputting one, zero or the input luminance to any of the output channels.
**Details**: [View Full Documentation](./TOP/Reorder.md)

### Resolution

**Type**: TOP | **Category**: General
**Description**: Changes the resolution of the TOP image. This can also be done on the Common page of most other TOPs.
**Details**: [View Full Documentation](./TOP/Resolution.md)

### SDI In

**Type**: TOP | **Category**: General
**Description**: Is a TouchDesigner Pro only operator. The SDI In TOP uses NVIDIA's SDI Capture Card to capture video frames directly into GPU memory.
**Details**: [View Full Documentation](./TOP/SDI_In.md)

### SDI Out

**Type**: TOP | **Category**: General
**Description**: Is a TouchDesigner Pro only operator. The SDI Out TOP uses Nvidia's SDI Output card to output video frames directly to the output card, avoid any issues involved with Windows such as vsync, desktop tearing etc.
**Details**: [View Full Documentation](./TOP/SDI_Out.md)

### SDI Select

**Type**: TOP | **Category**: General
**Description**: The SDI In TOP is a TouchDesigner Pro only operator. The SDI Select TOP is used to select video from the 2-4 inputs in the SDI In TOP on the Nvidia SDI Capture card.
**Details**: [View Full Documentation](./TOP/SDI_Select.md)

### SSAO

**Type**: TOP | **Category**: General
**Description**: Performs Screen Space Ambient Occlusion on the output of a Render TOP or Render Pass TOP . Because this technique requires access to the Depth Buffer, no other TOP can be in between the Render/RenderPass TOP and the SSAO TOP.
**Details**: [View Full Documentation](./TOP/SSAO.md)

### Scalable Display

**Type**: TOP | **Category**: General
**Description**: Lets you load calibration data retrieved from running the Scalable Display Calibration Software . Please refer to How-to calibrate your projector with Scalable Displays for a complete guide on TouchDesigners integration of the Scalable Displays SDK.
**Details**: [View Full Documentation](./TOP/Scalable_Display.md)

### Screen

**Type**: TOP | **Category**: General
**Description**: Brightens the underlying layers depending on how bright the screened layer's pixels are. If the screened pixel is black, it will look completely transparent.
**Details**: [View Full Documentation](./TOP/Screen.md)

### Screen Grab

**Type**: TOP | **Category**: General
**Description**: Turns the main screen output into a TOP image. It can be captured in real-time while you work.
**Details**: [View Full Documentation](./TOP/Screen_Grab.md)

### Select

**Type**: TOP | **Category**: General
**Description**: Allows you to reference a TOP from any other location in TouchDesigner. To save graphics memory, the Select TOP creates an instance of the TOP references.
**Details**: [View Full Documentation](./TOP/Select.md)

### Shared Mem In

**Type**: TOP | **Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem In TOP will read image data from a shared memory block.
**Details**: [View Full Documentation](./TOP/Shared_Mem_In.md)

### Shared Mem Out

**Type**: TOP | **Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem Out TOP will write image data out to a shared memory block for use by other TouchDesigner processes or other 3rd party applications.
**Details**: [View Full Documentation](./TOP/Shared_Mem_Out.md)

### Slope

**Type**: TOP | **Category**: General
**Description**: Generates pixels that represent the difference between its value and its neighbouring pixels' values.
**Details**: [View Full Documentation](./TOP/Slope.md)

### Spout In

**Type**: TOP | **Category**: General
**Description**: Will obtain its texture image via shared memory from other applications that support the Spout framework .
**Details**: [View Full Documentation](./TOP/Spout_In.md)

### Spout Out

**Type**: TOP | **Category**: General
**Description**: Will share its input texture with other applications that support the Spout framework . You can download a Spout setup package at <http://spout>.
**Details**: [View Full Documentation](./TOP/Spout_Out.md)

### Subtract

**Type**: TOP | **Category**: General
**Description**: Composites the input images together by subtracting the pixel values. Output = Input1 - Input2. The pixel values below 0 are clammped to 0.
**Details**: [View Full Documentation](./TOP/Subtract.md)

### Switch

**Type**: TOP | **Category**: General
**Description**: Is a multi-input operator which lets you switch which input is passed through using the Input parameter.
**Details**: [View Full Documentation](./TOP/Switch.md)

### Text

**Type**: TOP | **Category**: General
**Description**: Displays text strings in an image. It allows for multiple fonts, sizes, colors, borders, character separation and line separation.
**Details**: [View Full Documentation](./TOP/Text.md)

### Texture 3D

**Type**: TOP | **Category**: General
**Description**: Creates a 3D texture map. It saves a series of images in one array of pixels. This TOP can be used with Time Machine TOP, as well as materials.
**Details**: [View Full Documentation](./TOP/Texture_3D.md)

### Threshold

**Type**: TOP | **Category**: General
**Description**: Creates a matte with pixel values set to 0 for pixels below the threshold value, and 1 for pixels greater than or equal to the threshold value.
**Details**: [View Full Documentation](./TOP/Threshold.md)

### Tile

**Type**: TOP | **Category**: General
**Description**: Tiles images in a repeating pattern. It also has a Crop option which crops an image by defining the position of the left, right, bottom, and top edges of the image.
**Details**: [View Full Documentation](./TOP/Tile.md)

### Time Machine

**Type**: TOP | **Category**: General
**Description**: Combines pixels in a sequence of images stored in a Texture 3D TOP . Whereas "morphing" warps an image "spatially" (in xy), Time Machine warps images only in time.
**Details**: [View Full Documentation](./TOP/Time_Machine.md)

### Touch In

**Type**: TOP | **Category**: General
**Description**: Will read in image data send over a TCP/IP network connection from a Touch Out TOP . The other TouchDesigner process can be on the same computer or from another computer anywhere on the connected network.
**Details**: [View Full Documentation](./TOP/Touch_In.md)

### Touch Out

**Type**: TOP | **Category**: General
**Description**: Sends a TOP image stream over TCP/IP to a Touch In TOP. The Touch In TOP can be in another TouchDesigner session on the same computer or on a computer anywhere on the connected network.
**Details**: [View Full Documentation](./TOP/Touch_Out.md)

### Transform

**Type**: TOP | **Category**: General
**Description**: Applies 2D transformations to a TOP image like translate, scale, rotate, and multi-repeat tiling. The background can be filled with solid color and alpha.
**Details**: [View Full Documentation](./TOP/Transform.md)

### Under

**Type**: TOP | **Category**: General
**Description**: Places Input1 'under' Input2. The alpha of Input2 is used to determine what parts of the Input1 image are visible in the result.
**Details**: [View Full Documentation](./TOP/Under.md)

### Video Device In

**Type**: TOP | **Category**: General
**Description**: Can be used to capture video from an external camera, capture card, or DV decoder connected to the system.
**Details**: [View Full Documentation](./TOP/Video_Device_In.md)

### Video Device Out

**Type**: TOP | **Category**: General
**Description**: Routes video to output devices using their native driver libraries. Devices currently supported: Blackmagic Design devices The Video Device Out TOP is only available in Commercial and Pro .
**Details**: [View Full Documentation](./TOP/Video_Device_Out.md)

### Video Stream In

**Type**: TOP | **Category**: General
**Description**: Creates an RTSP client to receive video and audio across the network.  The URL to connect to the RTSP server is in the form: rtsp://<ipaddress>:<port>/<streamName> e.
**Details**: [View Full Documentation](./TOP/Video_Stream_In.md)

### Video Stream Out

**Type**: TOP | **Category**: General
**Description**: Creates an RTSP server to send H.264 video and MP3 audio across the network. It uses Nvidia's hardware H264 encoder to achieve low-latency encoding.
**Details**: [View Full Documentation](./TOP/Video_Stream_Out.md)

---

## Family: SOP {#family-sop}

**Surface Operators - Process and manipulate 3D geometry**

**Total Operators**: 102

[View SOP Family Index](./SOP/SOP_INDEX.md)

### Add

**Type**: SOP | **Category**: General
**Description**: Can both create new Points and Polygons on its own, or it can be used to add Points and Polygons to an existing input.
**Details**: [View Full Documentation](./SOP/Add.md)

### Align

**Type**: SOP | **Category**: General
**Description**: Aligns a group of primitives to each other or to an auxiliary input, by translating or rotating each primitive along any pivot point.
**Details**: [View Full Documentation](./SOP/Align.md)

### Arm

**Type**: SOP | **Category**: General
**Description**: Creates all the necessary geometry for an arm, and provides a smooth, untwisted skin that connects the arm to the body.
**Details**: [View Full Documentation](./SOP/Arm.md)

### Attribute

**Type**: SOP | **Category**: General
**Description**: Allows you to manually rename and delete point and primitive attributes.
**Details**: [View Full Documentation](./SOP/Attribute.md)

### Attribute Create

**Type**: SOP | **Category**: General
**Description**: Allows you to add normals or tangents to geometry.
**Details**: [View Full Documentation](./SOP/Attribute_Create.md)

### Basis

**Type**: SOP | **Category**: General
**Description**: Provides a set of operations applicable to the parametric space of spline curves and surfaces. The parametric space, also known as the "domain" of a NURBS or Bzier primitive, is defined by one basis in the U direction and, if the primitive is a surface, another basis in the V direction.
**Details**: [View Full Documentation](./SOP/Basis.md)

### Blend

**Type**: SOP | **Category**: General
**Description**: Provides 3D metamorphosis between shapes with the same topology. It can blend between sixteen input SOPs using the average weight of each input's respective channel.
**Details**: [View Full Documentation](./SOP/Blend.md)

### Bone Group

**Type**: SOP | **Category**: General
**Description**: Groups primitives by common bones (shared bones). For more information regarding using Bone Groups for deforming geometry, see this article: Deforming_Geometry_(Skinning) .
**Details**: [View Full Documentation](./SOP/Bone_Group.md)

### Boolean

**Type**: SOP | **Category**: General
**Description**: Takes two closed polygonal sets, A and B. Set these Sources to the SOPs with the 3D shapes that you wish to operate on.
**Details**: [View Full Documentation](./SOP/Boolean.md)

### Box

**Type**: SOP | **Category**: General
**Description**: Creates cuboids. These can be used as geometries by themselves, or they can be sub-divided for use with the Lattice SOP.
**Details**: [View Full Documentation](./SOP/Box.md)

### Bridge

**Type**: SOP | **Category**: General
**Description**: Is useful for skinning trimmed surfaces, holes, creating highly controllable joins between arms and body, branches or tube intersections.
**Details**: [View Full Documentation](./SOP/Bridge.md)

### CHOP to

**Type**: SOP | **Category**: General
**Description**: Takes CHOP channels and generates 3D polygons in a SOP. It reads sample data from a CHOP and converts it into point positions and point attributes.
**Details**: [View Full Documentation](./SOP/CHOP_to.md)

### Cache

**Type**: SOP | **Category**: General
**Description**: Collects its input geometry in a cache for faster random-access playback of multiple SOPs. It should be used when cook times for a chain of SOP s is long and a quicker playback is needed.
**Details**: [View Full Documentation](./SOP/Cache.md)

### Cap

**Type**: SOP | **Category**: General
**Description**: Is used to close open areas with flat or rounded coverings. Meshes are capped by extending the mesh in either the U or V direction (e.
**Details**: [View Full Documentation](./SOP/Cap.md)

### Capture

**Type**: SOP | **Category**: General
**Description**: Is used to weight points in a geometry to capture regions. The weighting scheme is described in the next section, Capture Region SOP .
**Details**: [View Full Documentation](./SOP/Capture.md)

### Capture Region

**Type**: SOP | **Category**: General
**Description**: Defines capture region (cregion), which is a type of primitive which can be thought of as a modified tube primitive (a tube with half a sphere on either end).
**Details**: [View Full Documentation](./SOP/Capture_Region.md)

### Carve

**Type**: SOP | **Category**: General
**Description**: Works with any face or surface type, be that polygon, Bzier, or NURBS. It can be used to slice a primitive, cut it into multiple sections, or extract points or cross-sections from it.
**Details**: [View Full Documentation](./SOP/Carve.md)

### Circle

**Type**: SOP | **Category**: General
**Description**: Creates open or closed arcs, circles and ellipses. If two NURBS circles that are non-rational (i.e. their X and Y radii are unequal) are skinned, more isoparms may be generated than expected.
**Details**: [View Full Documentation](./SOP/Circle.md)

### Clay

**Type**: SOP | **Category**: General
**Description**: Deforms faces and surfaces by pulling points that lie directly on them. As opposed to the Point SOP or other SOPs that manipulate control points (CVs), the Clay SOP operates on the primitive contours themselves, providing a direct, intuitive, and unconstrained way of reshaping geometry.
**Details**: [View Full Documentation](./SOP/Clay.md)

### Clip

**Type**: SOP | **Category**: General
**Description**: Cuts and creases source geometry with a plane.
**Details**: [View Full Documentation](./SOP/Clip.md)

### Convert

**Type**: SOP | **Category**: General
**Description**: Converts geometry from one geometry type to another type. Types include polygon, mesh, Bezier patche, particle and sphere primitive.
**Details**: [View Full Documentation](./SOP/Convert.md)

### Copy

**Type**: SOP | **Category**: General
**Description**: Lets you make copies of the geometry of other SOPs and apply a transformation to each copy. It also allows you to copy geometry to points on an input template.
**Details**: [View Full Documentation](./SOP/Copy.md)

### Creep

**Type**: SOP | **Category**: General
**Description**: Lets you deform and animate Source Input geometry along the surface of the PathInput geometry.
**Details**: [View Full Documentation](./SOP/Creep.md)

### Curveclay

**Type**: SOP | **Category**: General
**Description**: Is similar to the Clay SOP in that you deform a spline surface not by modifying the CVs but by directly manipulating the surface.
**Details**: [View Full Documentation](./SOP/Curveclay.md)

### Curvesect

**Type**: SOP | **Category**: General
**Description**: Finds the intersections or the points of minimum distance between two or more faces (polygons, Bziers, and NURBS curves) or between faces and a polygonal or spline surface.
**Details**: [View Full Documentation](./SOP/Curvesect.md)

### DAT to

**Type**: SOP | **Category**: General
**Description**: Can be used to create geometry from DAT tables, or if a SOP input is specified, to modify attributes on existing geometry.
**Details**: [View Full Documentation](./SOP/DAT_to.md)

### Deform

**Type**: SOP | **Category**: General
**Description**: Takes geometry along with point weights (assigned by the Capture SOP ) and deforms geometry as Capture Regions are moved.
**Details**: [View Full Documentation](./SOP/Deform.md)

### Delete

**Type**: SOP | **Category**: General
**Description**: Deletes input geometry as selected by a group specification or a geometry selection by using either of the three selection options: by entity number, by a bounding volume, and by entity (primitive/point) normals.
**Details**: [View Full Documentation](./SOP/Delete.md)

### Divide

**Type**: SOP | **Category**: General
**Description**: Divides incoming polygonal geometry. It will smooth input polygons, dividing polygons, as well as sub-divide input polygons using the Bricker option.
**Details**: [View Full Documentation](./SOP/Divide.md)

### Extrude

**Type**: SOP | **Category**: General
**Description**: Can be used for: Extruding and bevelling Text and other geometry Cusping the bevelled edges to get sharp edges Making primitives thicker or thinner In order to do so, it uses the normal of the surface to determine the direction of extrusion.
**Details**: [View Full Documentation](./SOP/Extrude.md)

### Facet

**Type**: SOP | **Category**: General
**Description**: Lets you control the smoothness of faceting of a given object. It also lets you consolidate points or surface normals.
**Details**: [View Full Documentation](./SOP/Facet.md)

### File In

**Type**: SOP | **Category**: General
**Description**: Allows you to read a geometry file that may have been previously created in the Model Editor, output geometry from a SOP, or generated from other software such as Houdini .
**Details**: [View Full Documentation](./SOP/File_In.md)

### Fillet

**Type**: SOP | **Category**: General
**Description**: Is used to create smooth bridging geometry between two curves / polygons or two surfaces / meshes. Filleting creates a new primitive between each input pair and never affects the original shapes.
**Details**: [View Full Documentation](./SOP/Fillet.md)

### Fit

**Type**: SOP | **Category**: General
**Description**: Fits a Spline curve to a sequence of points or a Spline surface to an m X n mesh of points. Any type of face or surface represents a valid input.
**Details**: [View Full Documentation](./SOP/Fit.md)

### Font

**Type**: SOP | **Category**: General
**Description**: Allows you to create text in your model from Adobe Type 1 Postscript Fonts. To install fonts, copy the font files to the $TFS/touch/fonts directory of your installation path.
**Details**: [View Full Documentation](./SOP/Font.md)

### Force

**Type**: SOP | **Category**: General
**Description**: Adds force attributes to the input metaball field that is used by either Particle SOP or Spring SOP as attractor or repulsion force fields.
**Details**: [View Full Documentation](./SOP/Force.md)

### Fractal

**Type**: SOP | **Category**: General
**Description**: Allows you created jagged mountain-like divisions of the input geometry. It will create random-looking deviations and sub-divisions along either a specified normal vector (the Direction xyz fields) or the vertex normals of the input geometry.
**Details**: [View Full Documentation](./SOP/Fractal.md)

### Grid

**Type**: SOP | **Category**: General
**Description**: Allows you to create grids and rectangles using polygons, a mesh, Bzier and NURBS surfaces, or multiple lines using open polygons.
**Details**: [View Full Documentation](./SOP/Grid.md)

### Group

**Type**: SOP | **Category**: General
**Description**: Generates groups of points or primitives according to various criteria and allows you to act upon these groups.
**Details**: [View Full Documentation](./SOP/Group.md)

### Hole

**Type**: SOP | **Category**: General
**Description**: Is for making holes where faces are enclosed, even if they are not in the same plane. It can also remove existing holes from the input geometry.
**Details**: [View Full Documentation](./SOP/Hole.md)

### In

**Type**: SOP | **Category**: General
**Description**: Creates a SOP input in a Component. Component inputs are positioned alphanumerically on the left side of the node.
**Details**: [View Full Documentation](./SOP/In.md)

### Inverse Curve

**Type**: SOP | **Category**: General
**Description**: Takes data from an Inverse Curve CHOP and builds a curve from it.
**Details**: [View Full Documentation](./SOP/Inverse_Curve.md)

### Iso Surface

**Type**: SOP | **Category**: General
**Description**: Uses implicit functions to create 3D visualizations of isometric surfaces found in Grade 12 Functions and Relations textbooks.
**Details**: [View Full Documentation](./SOP/Iso_Surface.md)

### Join

**Type**: SOP | **Category**: General
**Description**: Connects a sequence of faces or surfaces into a single primitive that inherits their attributes. Faces of different types can be joined together, and so can surfaces.
**Details**: [View Full Documentation](./SOP/Join.md)

### Joint

**Type**: SOP | **Category**: General
**Description**: Will aid in the creation of circle-based skeletons by creating a series of circles between each pair of input circles.
**Details**: [View Full Documentation](./SOP/Joint.md)

### LOD

**Type**: SOP | **Category**: General
**Description**: Is unusual in so far as it does not actually alter any geometry. Instead it builds a level of detail cache for the input object.
**Details**: [View Full Documentation](./SOP/LOD.md)

### LSystem

**Type**: SOP | **Category**: General
**Description**: The Lsystem SOP implements L-systems (Lindenmayer-systems, named after Aristid Lindenmayer (1925-1989)), allow definition of complex shapes through the use of iteration.
**Details**: [View Full Documentation](./SOP/LSystem.md)

### Lattice

**Type**: SOP | **Category**: General
**Description**: Allows you to create animated deformations of its input geometry by manipulating grids or a subdivided box that encloses the input source's geometry.
**Details**: [View Full Documentation](./SOP/Lattice.md)

### Limit

**Type**: SOP | **Category**: General
**Description**: Creates geometry from samples fed to it by CHOPs . It creates geometry at every point in the sample.
**Details**: [View Full Documentation](./SOP/Limit.md)

### Line

**Type**: SOP | **Category**: General
**Description**: Creates straight lines.
**Details**: [View Full Documentation](./SOP/Line.md)

### Line Thick

**Type**: SOP | **Category**: General
**Description**: Extrudes a surface from a curved line. The line can be of polygon, NURBS, or Bezier geometry type.
**Details**: [View Full Documentation](./SOP/Line_Thick.md)

### Magnet

**Type**: SOP | **Category**: General
**Description**: Allows you to affect deformations of the input geometry with another object using a "magnetic field" of influence, defined by a metaball field.
**Details**: [View Full Documentation](./SOP/Magnet.md)

### Material

**Type**: SOP | **Category**: General
**Description**: Allows the assignment of materials (MATs) to geometry at the SOP level. Note: The Material parameter in Object Components will override material attributes assigned to geometry using the Material SOP.
**Details**: [View Full Documentation](./SOP/Material.md)

### Merge

**Type**: SOP | **Category**: General
**Description**: Merges geometry from multiple SOPs.
**Details**: [View Full Documentation](./SOP/Merge.md)

### Metaball

**Type**: SOP | **Category**: General
**Description**: Creates metaballs and meta-superquadric surfaces. Metaballs can be thought of as spherical force fields whose surface is an implicit function defined at any point where the density of the force field equals a certain threshold.
**Details**: [View Full Documentation](./SOP/Metaball.md)

### Model

**Type**: SOP | **Category**: General
**Description**: Holds the surface modeler in TouchDesigner. It is designed to hold raw model geometry constructed using the SOP Editor (aka Modeler).
**Details**: [View Full Documentation](./SOP/Model.md)

### Noise

**Type**: SOP | **Category**: General
**Description**: Displaces geometry points using noise patterns. It uses the same math as the Noise CHOP .
**Details**: [View Full Documentation](./SOP/Noise.md)

### Null

**Type**: SOP | **Category**: General
**Description**: Has no effect on the geometry. It is an instance of the SOP connected to its input. The Null SOP is often used when making reference to a SOP network, allowing new SOPs to be added to the network (upstream) without the need to update the reference.
**Details**: [View Full Documentation](./SOP/Null.md)

### Object Merge

**Type**: SOP | **Category**: General
**Description**: Allows you to merge the geometry of several SOPs spanning different components.
**Details**: [View Full Documentation](./SOP/Object_Merge.md)

### Out

**Type**: SOP | **Category**: General
**Description**: Is used to create a SOP output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.
**Details**: [View Full Documentation](./SOP/Out.md)

### Particle

**Type**: SOP | **Category**: General
**Description**: Is used for creating and controlling motion of "particles" for particle systems simulations. Particle systems are often used to create simulations of natural events such as rain and snow, or effects such as fireworks and sparks.
**Details**: [View Full Documentation](./SOP/Particle.md)

### Point

**Type**: SOP | **Category**: General
**Description**: Allows you to get right down into the geometry and manipulate the position, color, texture coordinates, and normals of the points in the Source, and other attributes.
**Details**: [View Full Documentation](./SOP/Point.md)

### Polyloft

**Type**: SOP | **Category**: General
**Description**: Generates meshes of triangles by connecting (i.e. lofting/stitching) the points of open or closed faces without adding any new points.
**Details**: [View Full Documentation](./SOP/Polyloft.md)

### Polypatch

**Type**: SOP | **Category**: General
**Description**: Creates a smooth polygonal patch from a mesh primitive or a set of faces (polygons, NURBS or Bezier curves).
**Details**: [View Full Documentation](./SOP/Polypatch.md)

### Polyreduce

**Type**: SOP | **Category**: General
**Description**: Reduces a high detail polygonal model into one consisting of fewer polygons. The second input's polygons represent feature edges.
**Details**: [View Full Documentation](./SOP/Polyreduce.md)

### Polyspline

**Type**: SOP | **Category**: General
**Description**: Fits a spline curve to a polygon or hull and outputs a polygonal approximation of that spline. You can choose either to create divisions between the original points, or to ignore the position of the original points and divide the shape into segments of equal lengths.
**Details**: [View Full Documentation](./SOP/Polyspline.md)

### Polystitch

**Type**: SOP | **Category**: General
**Description**: Attempts to stitch polygonal surfaces together, thereby eliminating cracks that result from evaluating the surfaces at differing levels of detail.
**Details**: [View Full Documentation](./SOP/Polystitch.md)

### Primitive

**Type**: SOP | **Category**: General
**Description**: Is like the Point SOP but manipulates a primitive 's position, size, orientation, color, alpha, in addition to primitive-specific attributes, such as reversing primitive normals.
**Details**: [View Full Documentation](./SOP/Primitive.md)

### Profile

**Type**: SOP | **Category**: General
**Description**: Enables the extraction and manipulation of profiles. You will usually need a Trim SOP, Bridge SOP, or Profile SOP after a Project SOP .
**Details**: [View Full Documentation](./SOP/Profile.md)

### Project

**Type**: SOP | **Category**: General
**Description**: Creates curves on surface (also known as trim or profile curves) by projecting a 3D face onto a spline surface, much like a light casts a 2D shadow onto a 3D surface.
**Details**: [View Full Documentation](./SOP/Project.md)

### Rails

**Type**: SOP | **Category**: General
**Description**: Generates surfaces by stretching cross-sections between two rails. This is similar to the Sweep SOP, but it gives more control over the orientation and scaling of the cross-sections.
**Details**: [View Full Documentation](./SOP/Rails.md)

### Ray

**Type**: SOP | **Category**: General
**Description**: Is used to project one surface onto another. Rays are projected from each point of the input geometry in the direction of its normal.
**Details**: [View Full Documentation](./SOP/Ray.md)

### Rectangle

**Type**: SOP | **Category**: General
**Description**: Creates a 4-sided polygon. It is a planar surface.
**Details**: [View Full Documentation](./SOP/Rectangle.md)

### Refine

**Type**: SOP | **Category**: General
**Description**: Allows you to increase the number of CVs in any NURBS, Bzier, or polygonal surface or face without changing its shape.
**Details**: [View Full Documentation](./SOP/Refine.md)

### Resample

**Type**: SOP | **Category**: General
**Description**: Will resample one or more primitives into even length segments. It only applies to polygons so when presented with a NURBS or Bzier curve input, it first converts it to polygons using the Level of Detail parameter.
**Details**: [View Full Documentation](./SOP/Resample.md)

### Revolve

**Type**: SOP | **Category**: General
**Description**: Revolves faces to create a surface of revolution. The revolution's direction and origin are represented by guide geometry that resembles a thick line with a cross hair at the centre.
**Details**: [View Full Documentation](./SOP/Revolve.md)

### Script

**Type**: SOP | **Category**: General
**Description**: Runs a script each time the Script SOP cooks. By default, the Script SOP is created with a docked DAT that contains three Python methods: cook, onPulse, and setupParameters .
**Details**: [View Full Documentation](./SOP/Script.md)

### Select

**Type**: SOP | **Category**: General
**Description**: Allows you to reference a SOP from any other location in TouchDesigner. To save memory, the Select SOP creates an instance of the SOP references.
**Details**: [View Full Documentation](./SOP/Select.md)

### Sequence Blend

**Type**: SOP | **Category**: General
**Description**: Allows you do 3D Metamorphosis between shapes and Interpolate point position, colors, point normals, and texture coordinates between shapes.
**Details**: [View Full Documentation](./SOP/Sequence_Blend.md)

### Skin

**Type**: SOP | **Category**: General
**Description**: Takes any number of faces and builds a skin surface over them. If given two or more surfaces, however, the SOP builds four skins, one for each set of boundary curves.
**Details**: [View Full Documentation](./SOP/Skin.md)

### Sort

**Type**: SOP | **Category**: General
**Description**: Allows you to sort points and primitives in different ways. Sometimes the primitives are arranged in the desired order, but the point order is not.
**Details**: [View Full Documentation](./SOP/Sort.md)

### Sphere

**Type**: SOP | **Category**: General
**Description**: Generates spherical objects of different geometry types. It is capable of creating non-uniform scalable spheres of all geometry types.
**Details**: [View Full Documentation](./SOP/Sphere.md)

### Spring

**Type**: SOP | **Category**: General
**Description**: Deforms and moves the input geometry using spring "forces" on the edges of polygons and on masses attached to each point.
**Details**: [View Full Documentation](./SOP/Spring.md)

### Sprite

**Type**: SOP | **Category**: General
**Description**: Creates geometry (quad sprites) at point positions defined by the CHOP referenced in the XYZ CHOP parameter.
**Details**: [View Full Documentation](./SOP/Sprite.md)

### Stitch

**Type**: SOP | **Category**: General
**Description**: Is used to stretch two curves or surfaces to cover a smooth area. It can also be used to create certain types of upholstered fabrics such as cushions and parachutes.
**Details**: [View Full Documentation](./SOP/Stitch.md)

### Subdivide

**Type**: SOP | **Category**: General
**Description**: Takes an input polygon surface (which can be piped into one or both inputs), and divides each face to create a smoothed polygon surface using a Catmull-Clark subdivision algorithm.
**Details**: [View Full Documentation](./SOP/Subdivide.md)

### Superquad

**Type**: SOP | **Category**: General
**Description**: Generates an isoquadric surface. This produces a spherical shape that is similar to a metaball, with the difference that it doesn't change it's shape in response to what surrounds it.
**Details**: [View Full Documentation](./SOP/Superquad.md)

### Surfsect

**Type**: SOP | **Category**: General
**Description**: Performs boolean operations with NURBS and Bezier surfaces, or only generates profiles where the surfaces intersect.
**Details**: [View Full Documentation](./SOP/Surfsect.md)

### Sweep

**Type**: SOP | **Category**: General
**Description**: Sweeps primitives in the Cross-section input along Backbone Source primitive(s), creating ribbon and tube-like shapes.
**Details**: [View Full Documentation](./SOP/Sweep.md)

### Switch

**Type**: SOP | **Category**: General
**Description**: Switches between up to 9999 possible inputs. The output of this SOP is specified by the Select Input field.
**Details**: [View Full Documentation](./SOP/Switch.md)

### Text

**Type**: SOP | **Category**: General
**Description**: Creates text geometry from any TrueType font that is installed on the system, or any TrueType font file on disk.
**Details**: [View Full Documentation](./SOP/Text.md)

### Texture

**Type**: SOP | **Category**: General
**Description**: Assigns texture UV and W coordinates to the Source geometry for use in texture and bump mapping. It generates multi-layers of texture coordinates.
**Details**: [View Full Documentation](./SOP/Texture.md)

### Torus

**Type**: SOP | **Category**: General
**Description**: Generates complete or specific sections of torus shapes (like a doughnut).
**Details**: [View Full Documentation](./SOP/Torus.md)

### Trace

**Type**: SOP | **Category**: General
**Description**: Reads an image file and automatically traces it, generating a set of faces around areas exceeding a certain brightness threshold.
**Details**: [View Full Documentation](./SOP/Trace.md)

### Trail

**Type**: SOP | **Category**: General
**Description**: Takes an input SOP and makes a trail of each point of the input SOP over the past several frames, and connects the trails in different ways.
**Details**: [View Full Documentation](./SOP/Trail.md)

### Transform

**Type**: SOP | **Category**: General
**Description**: Translates, rotates and scales the input geometry in "object space" or local to the SOP. The Model Editor and the Transform SOP both work in "object space", and change the X Y Z positions of the points.
**Details**: [View Full Documentation](./SOP/Transform.md)

### Trim

**Type**: SOP | **Category**: General
**Description**: Cuts out parts of a spline surface, or uncuts previously cut pieces. When a portion of the surface is trimmed, it is not actually removed from the surface; instead, that part is made invisible.
**Details**: [View Full Documentation](./SOP/Trim.md)

### Tristrip

**Type**: SOP | **Category**: General
**Description**: Convert geometry into triangle strips. Triangle strips are faster to render than regular triangles or quads.
**Details**: [View Full Documentation](./SOP/Tristrip.md)

### Tube

**Type**: SOP | **Category**: General
**Description**: Generates open or closed tubes, cones, or pyramids along the X, Y or Z axes. It outputs as meshes, polygons or simply a tube primitive .
**Details**: [View Full Documentation](./SOP/Tube.md)

### Twist

**Type**: SOP | **Category**: General
**Description**: Performs non-linear deformations such as bend, linear taper, shear, squash and stretch, taper and twist.
**Details**: [View Full Documentation](./SOP/Twist.md)

### Vertex

**Type**: SOP | **Category**: General
**Description**: Allows you to edit/create attributes on a per-vertex (rather than per-point) basis. It is similar to the Point SOP in this respect.
**Details**: [View Full Documentation](./SOP/Vertex.md)

### Wireframe

**Type**: SOP | **Category**: General
**Description**: Converts edges to tubes and points to spheres, creating the look of a wire frame structure in renderings.
**Details**: [View Full Documentation](./SOP/Wireframe.md)

---

## Family: DAT {#family-dat}

**Data Operators - Process and manipulate table/text data**

**Total Operators**: 57

[View DAT Family Index](./DAT/DAT_INDEX.md)

### Art-Net

**Type**: DAT | **Category**: General
**Description**: Polls and lists all devices on the network.
**Details**: [View Full Documentation](./DAT/Art-Net.md)

### CHOP Execute

**Type**: DAT | **Category**: General
**Description**: Will run its script when the values of a specified CHOP change. You can specify which channels to look at, and trigger based on their values changing in various ways.
**Details**: [View Full Documentation](./DAT/CHOP_Execute.md)

### CHOP to

**Type**: DAT | **Category**: General
**Description**: Allows you to get CHOP channel values into a DAT in table format.
**Details**: [View Full Documentation](./DAT/CHOP_to.md)

### Clip

**Type**: DAT | **Category**: General
**Description**: Contains information about motion clips that are manipulated by a Clip CHOP and Clip Blender CHOP . The Clip DAT can hold any command or script text, which can be triggered based on the settings on the Execute parameter page (This is where the Clip DAT and the Text DAT are different).
**Details**: [View Full Documentation](./DAT/Clip.md)

### Convert

**Type**: DAT | **Category**: General
**Description**: Changes the text format from simple text to table form and vice-versa.
**Details**: [View Full Documentation](./DAT/Convert.md)

### DAT Execute

**Type**: DAT | **Category**: General
**Description**: Monitors another DAT's contents and runs a script when those contents change. The other DAT is usually a table.
**Details**: [View Full Documentation](./DAT/DAT_Execute.md)

### Error

**Type**: DAT | **Category**: General
**Description**: Lists the most recent TouchDesigner errors in its FIFO (first in/first out) table. You can filter our messages using pattern matching on some of the columns like Severity, Type and path of the node containing the error.
**Details**: [View Full Documentation](./DAT/Error.md)

### EtherDream

**Type**: DAT | **Category**: General
**Description**: Polls and lists all EtherDream devices connected. See also: EtherDream CHOP, Scan CHOP.
**Details**: [View Full Documentation](./DAT/EtherDream.md)

### Evaluate

**Type**: DAT | **Category**: General
**Description**: Changes the cells of the incoming DAT using string-editing and math expressions. It outputs a table with the same number of rows and columns.
**Details**: [View Full Documentation](./DAT/Evaluate.md)

### Examine

**Type**: DAT | **Category**: General
**Description**: Lets you inspect an operator's python storage, locals, globals, expressions, and extensions.
**Details**: [View Full Documentation](./DAT/Examine.md)

### Execute

**Type**: DAT | **Category**: General
**Description**: Lets you edit scripts and run them based on conditions. It can be executed at the start or end of every frame, or at the start or end of the TouchDesigner process.
**Details**: [View Full Documentation](./DAT/Execute.md)

### FIFO

**Type**: DAT | **Category**: General
**Description**: The FIFO DAT maintains a user-set maximum number of rows in a table. You add rows using the appendRow() method found in DAT Class. When its capacity is reached, the first row is removed. After the maximum number of rows is reached, the oldest row is discarded when a new row is added.
**Details**: [View Full Documentation](./DAT/FIFO.md)

### File In

**Type**: DAT | **Category**: General
**Description**: Reads in .txt text files and .dat table files. It will attempt to read any other file as raw text. The file can be located on disk or on the web.
**Details**: [View Full Documentation](./DAT/File_In.md)

### File Out

**Type**: DAT | **Category**: General
**Description**: Allows you to write out DAT contents to a .dat file or a .txt file. A .dat file is one of the File Types of TouchDesigner that is used to hold the arrays of the Table DAT .
**Details**: [View Full Documentation](./DAT/File_Out.md)

### Folder

**Type**: DAT | **Category**: General
**Description**: Lists the files and subfolders found in a file system folder and monitors any changes. For each item found, a row is created in the table with optional columns for the following information: Name Extension Type Size Depth Folder Path Date Created Date Modified.
**Details**: [View Full Documentation](./DAT/Folder.md)

### In

**Type**: DAT | **Category**: General
**Description**: Is used to create a DAT input in a Component. Component inputs are positioned alphanumerically on the left side of the Component.
**Details**: [View Full Documentation](./DAT/In.md)

### Indices

**Type**: DAT | **Category**: General
**Description**: Creates a series of numbers in a table, ranging between the start and end values.  These values are suitable for display along a graph horizontal or vertical axis.
**Details**: [View Full Documentation](./DAT/Indices.md)

### Info

**Type**: DAT | **Category**: General
**Description**: Gives you string information about a node. Only some nodes contain additional string information which can be accessed by the Info DAT.
**Details**: [View Full Documentation](./DAT/Info.md)

### Insert

**Type**: DAT | **Category**: General
**Description**: Allows you to insert a row or column into an existing table.  If the input DAT is not a table, it will be converted to a table.
**Details**: [View Full Documentation](./DAT/Insert.md)

### Keyboard In

**Type**: DAT | **Category**: General
**Description**: Lists the most recent key events in its FIFO (first in/first out) table. There is one row for every key press down and every key-up, including Shift, Ctrl and Alt, with distinction between left and right side.
**Details**: [View Full Documentation](./DAT/Keyboard_In.md)

### MIDI Event

**Type**: DAT | **Category**: General
**Description**: Logs all MIDI messages coming into TouchDesigner from all MIDI devices. It outputs columns in a table format: message, type, channel, index, value.
**Details**: [View Full Documentation](./DAT/MIDI_Event.md)

### MIDI In

**Type**: DAT | **Category**: General
**Description**: Logs all MIDI messages coming into TouchDesigner from a specified MIDI device. It outputs columns in a table format - message, type, channel, index, value.
**Details**: [View Full Documentation](./DAT/MIDI_In.md)

### Merge

**Type**: DAT | **Category**: General
**Description**: The Merged DAT is a multi-input DAT which merges the text or tables from the input DATs together.
**Details**: [View Full Documentation](./DAT/Merge.md)

### Monitors

**Type**: DAT | **Category**: General
**Description**: Is a table of data about all currently detected monitors with information on the resolution, screen positioning, monitor name and description, and a flag indicating whether it is a primary monitor or not.
**Details**: [View Full Documentation](./DAT/Monitors.md)

### Multi Touch In

**Type**: DAT | **Category**: General
**Description**: Is used for receiving messages and events from the Windows 7+ standard multi-touch API. It captures all the messages, where each new message changes the table it outputs.
**Details**: [View Full Documentation](./DAT/Multi_Touch_In.md)

### Null

**Type**: DAT | **Category**: General
**Description**: Has no effect on the data. It is an instance of the DAT connected to its input. The Null DAT is often used when making reference to a DAT network, allowing new DATs to be added to the network (upstream) without the need to update the reference.
**Details**: [View Full Documentation](./DAT/Null.md)

### OP Execute

**Type**: DAT | **Category**: General
**Description**: Runs a script when the state of an operator changes. OP Execute DATs are created with default python method placeholders.
**Details**: [View Full Documentation](./DAT/OP_Execute.md)

### OP Find

**Type**: DAT | **Category**: General
**Description**: Traverses the component hierarchy starting at one component and looking at all nodes within that component, and outputs a table with one row per node that matches criteria the user chooses.
**Details**: [View Full Documentation](./DAT/OP_Find.md)

### OSC In

**Type**: DAT | **Category**: General
**Description**: Receives and parses full Open Sound Control packets using UDP.  Each packet is parsed and appended as a row in the DAT's table.
**Details**: [View Full Documentation](./DAT/OSC_In.md)

### OSC Out

**Type**: DAT | **Category**: General
**Description**: Is used for sending information over a OSC connection between remotely located computers. Use the send Command to initiate the data output.
**Details**: [View Full Documentation](./DAT/OSC_Out.md)

### Out

**Type**: DAT | **Category**: General
**Description**: Is used to create a DAT output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.
**Details**: [View Full Documentation](./DAT/Out.md)

### Panel Execute

**Type**: DAT | **Category**: General
**Description**: Will run its script when the values of a specified panel component changes. You can specify which Panel Values to monitor, and trigger scripts based on their values changing in various ways.
**Details**: [View Full Documentation](./DAT/Panel_Execute.md)

### Parameter Execute

**Type**: DAT | **Category**: General
**Description**: The Parm Execute DAT runs a  script when a parameter of any node changes state. There are 4 ways a parameter can trigger the script: if its value, expression, export, or enable state changes.
**Details**: [View Full Documentation](./DAT/Parameter_Execute.md)

### Perform

**Type**: DAT | **Category**: General
**Description**: Logs various performance times in a Table DAT format. These benchmarks are similar to those reported by the Performance Monitor .
**Details**: [View Full Documentation](./DAT/Perform.md)

### Render Pick

**Type**: DAT | **Category**: General
**Description**: Allows you to do multi-touch on a 3D rendered scene. It samples a rendering (from a Render TOP or a Render Pass TOP ) and returns 3D information from the geometry at the specified pick locations.
**Details**: [View Full Documentation](./DAT/Render_Pick.md)

### Reorder

**Type**: DAT | **Category**: General
**Description**: Allows you to reorder the rows and columns of the input table.  You can also use In Specified Order option to get duplicate copies of rows and columns.
**Details**: [View Full Documentation](./DAT/Reorder.md)

### SOP to

**Type**: DAT | **Category**: General
**Description**: Allows you to extract point and primitive data and attributes. Data is output in columns, with the first column being index.
**Details**: [View Full Documentation](./DAT/SOP_to.md)

### Script

**Type**: DAT | **Category**: General
**Description**: Runs a script each time the Script DAT cooks.  By default, the Script DAT is created with a docked DAT that contains three Python methods: cook, onPulse, and setupParameters .
**Details**: [View Full Documentation](./DAT/Script.md)

### Select

**Type**: DAT | **Category**: General
**Description**: Allows you to fetch a DAT from any other location in TouchDesigner, and to select any subset of rows and columns if it is a table.
**Details**: [View Full Documentation](./DAT/Select.md)

### Serial

**Type**: DAT | **Category**: General
**Description**: Is used for serial communication through an external port, using the RS-232 protocol.  These ports are usually a 9 pin connector, or a USB port on new machines.
**Details**: [View Full Documentation](./DAT/Serial.md)

### Sort

**Type**: DAT | **Category**: General
**Description**: Will sort table DAT data by row or column.
**Details**: [View Full Documentation](./DAT/Sort.md)

### Substitute

**Type**: DAT | **Category**: General
**Description**: Changes the cells of the incoming DAT using pattern matching and substitution strings. It outputs a table with the same number of rows and columns.
**Details**: [View Full Documentation](./DAT/Substitute.md)

### Switch

**Type**: DAT | **Category**: General
**Description**: Is a multi-input operator which lets you choose which input is output by using the Input parameter.
**Details**: [View Full Documentation](./DAT/Switch.md)

### TCP/IP

**Type**: DAT | **Category**: General
**Description**: Is used for sending and receiving information over a TCP/IP connection between two remotely located computers.
**Details**: [View Full Documentation](./DAT/TCPIP.md)

### TUIO In

**Type**: DAT | **Category**: General
**Description**: Receives and parses TUIO messages (received over network) into columns in the table. TUIO packets OSC bundles, so TUIO data can also be viewed in it's more raw form in an OSC In DAT.
**Details**: [View Full Documentation](./DAT/TUIO_In.md)

### Table

**Type**: DAT | **Category**: General
**Description**: Lets you create a table of rows and columns of cells, each cell containing a text string. A "table" is one of the two forms of DATs (the other being simply lines of "free-form" text via the Text DAT ).
**Details**: [View Full Documentation](./DAT/Table.md)

### Text

**Type**: DAT | **Category**: General
**Description**: Lets you edit free-form, multi-line ASCII text. It is used for scripts, GLSL shaders, notes, XML and other purposes.
**Details**: [View Full Documentation](./DAT/Text.md)

### Touch In

**Type**: DAT | **Category**: General
**Description**: Receives full tables across the network from the Touch Out DAT, as opposed to messages with the other network based DATs.
**Details**: [View Full Documentation](./DAT/Touch_In.md)

### Touch Out

**Type**: DAT | **Category**: General
**Description**: Sends full DAT tables across the network to the Touch In DAT in another TouchDesigner process, as opposed to messages with the other network based DATs.
**Details**: [View Full Documentation](./DAT/Touch_Out.md)

### Transpose

**Type**: DAT | **Category**: General
**Description**: Converts rows into columns. The number of rows becomes the number of columns, and vice versa.
**Details**: [View Full Documentation](./DAT/Transpose.md)

### UDP In

**Type**: DAT | **Category**: General
**Description**: Is used for receiving information over a UDP connection between two remotely located computers. It captures all the messages without any queuing or buffering, and allows you to send it any messages you want.
**Details**: [View Full Documentation](./DAT/UDP_In.md)

### UDP Out

**Type**: DAT | **Category**: General
**Description**: Is used to send information over a UDP connection to/from a remotely-located computer.  Use the send Command in a DAT script or the textport to initiate the data output.
**Details**: [View Full Documentation](./DAT/UDP_Out.md)

### UDT In

**Type**: DAT | **Category**: General
**Description**: Is used for receiving information over a UDT connection between two remotely located computers. It captures all the messages without any queuing or buffering, and allows you to send it any messages you want.
**Details**: [View Full Documentation](./DAT/UDT_In.md)

### UDT Out

**Type**: DAT | **Category**: General
**Description**: Is used for sending information over a UDT connection between remotely located computers. Send messages using the udtoutDAT_Class .
**Details**: [View Full Documentation](./DAT/UDT_Out.md)

### Web

**Type**: DAT | **Category**: General
**Description**: Fetches pages of data from a web connection. The data should be ASCII-readable. The Web DAT will automatically uncompress any gzip compressed page transfers.
**Details**: [View Full Documentation](./DAT/Web.md)

### WebSocket

**Type**: DAT | **Category**: General
**Description**: Receives and parses WebSocket messages.  WebSockets are fast an efficient two way communication protocol used by web servers and clients.
**Details**: [View Full Documentation](./DAT/WebSocket.md)

### XML

**Type**: DAT | **Category**: General
**Description**: Can be used to parse arbitrary XML and SGML/HTML formatted data. Once formatted, selected sections of the text can be output for further processing.
**Details**: [View Full Documentation](./DAT/XML.md)

---

## Family: COMP {#family-comp}

**Component Operators - Container and UI components**

**Total Operators**: 25

[View COMP Family Index](./COMP/COMP_INDEX.md)

### Ambient Light

**Type**: COMP | **Category**: General
**Description**: The Ambient Light Component controls the color and intensity of the environmental light in a given scene.
**Details**: [View Full Documentation](./COMP/Ambient_Light.md)

### Animation

**Type**: COMP | **Category**: General
**Description**: The Animation Component is a special component used for creating keyframe animation channels. The component contains a pre-defined network utilizing a Keyframe CHOP and a number of Table DATs to define the animated CHOP channels.
**Details**: [View Full Documentation](./COMP/Animation.md)

### Base

**Type**: COMP | **Category**: General
**Description**: The Base Component has no panel parameters and no 3D object parameters. You would use it for a component that has no panel associated with it, nor any 3D, such as component that converted RGB channels to HSV channels.
**Details**: [View Full Documentation](./COMP/Base.md)

### Blend

**Type**: COMP | **Category**: General
**Description**: The Blend Component allows various effects such as blended inputs, animating the parents of Components, sequencing, partial transformation inheritance, three-point orientation, and other effects.
**Details**: [View Full Documentation](./COMP/Blend.md)

### Bone

**Type**: COMP | **Category**: General
**Description**: The Bone Component is the foundation of all of the Character Tools . It is a Component with most of the properties of a Geometry Component .
**Details**: [View Full Documentation](./COMP/Bone.md)

### Button

**Type**: COMP | **Category**: General
**Description**: The Button Component is used in panels to provide interactive on/off buttons, including toggle buttons, momentary buttons, and sets of radio buttons or exclusive buttons.
**Details**: [View Full Documentation](./COMP/Button.md)

### Camera

**Type**: COMP | **Category**: General
**Description**: The Camera Component is a 3D object that acts like real-world cameras. You view your scene through it and render from their point of view.
**Details**: [View Full Documentation](./COMP/Camera.md)

### Camera Blend

**Type**: COMP | **Category**: General
**Description**: The Camera Blend Component allows various effects by blending multiple Components together. It gives you some extra flexibility in setting up parent-child relationships.
**Details**: [View Full Documentation](./COMP/Camera_Blend.md)

### Container

**Type**: COMP | **Category**: General
**Description**: The Container Component groups together any number of button, slider, field, container and other Panel Components to build an interface.
**Details**: [View Full Documentation](./COMP/Container.md)

### Engine

**Type**: COMP | **Category**: General
**Description**: The Engine Component runs a .tox file (component) in a separate process.
**Details**: [View Full Documentation](./COMP/Engine.md)

### Field

**Type**: COMP | **Category**: General
**Description**: The Field Component lets you enter text strings and renders text generated with the Text TOP . Internally it contains a Text TOP which points to one cell of a DAT that contains the text to render.
**Details**: [View Full Documentation](./COMP/Field.md)

### Geometry

**Type**: COMP | **Category**: General
**Description**: The Geometry Component is a 3D surface that you see and render in TouchDesigner with a Render TOP . Lights, cameras and other Components affect the scene, but are not visible surfaces.
**Details**: [View Full Documentation](./COMP/Geometry.md)

### Handle

**Type**: COMP | **Category**: General
**Description**: The Handle Component is a new IK tool designed for manipulating groups of bones. Whereas the previous IK tools only allowed for a single end-affector per bone chain, this new method allows for several end-affectors per bone.
**Details**: [View Full Documentation](./COMP/Handle.md)

### Light

**Type**: COMP | **Category**: General
**Description**: The Light Components are objects which cast light into a 3D scene. With the light parameters you can control the color, brightness, and atmosphere of geometry lit by the light.
**Details**: [View Full Documentation](./COMP/Light.md)

### List

**Type**: COMP | **Category**: General
**Description**: The List Component lets you create large lists that are highly customizable via the List COMPs initialization and callback functions.
**Details**: [View Full Documentation](./COMP/List.md)

### Null

**Type**: COMP | **Category**: General
**Description**: The Null Component serves as a place-holder in a scene. It can be used to transform (translate, rotate, scale) Components attached to it.
**Details**: [View Full Documentation](./COMP/Null.md)

### OP Viewer

**Type**: COMP | **Category**: General
**Description**: The OP Viewer Component allows any operator viewer (CHOP Viewer, SOP Viewer etc) to be part of a panel with full interactivity.
**Details**: [View Full Documentation](./COMP/OP_Viewer.md)

### Replicator

**Type**: COMP | **Category**: General
**Description**: The Replicator Component creates a node for every row of a table, creating nodes (" replicants ") and deleting them as the table changes.
**Details**: [View Full Documentation](./COMP/Replicator.md)

### Select

**Type**: COMP | **Category**: General
**Description**: The Select Component selects a Panel Component from any other location. This allows a panel to appear in multiple other panels.
**Details**: [View Full Documentation](./COMP/Select.md)

### Shared Mem In

**Type**: COMP | **Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem In COMP will read transform data from a shared memory block.
**Details**: [View Full Documentation](./COMP/Shared_Mem_In.md)

### Shared Mem Out

**Type**: COMP | **Category**: General
**Description**: The Shared Mem In TOP is only available in TouchDesigner Commercial and Pro. The Shared Mem Out COMP will write transform data to a shared memory block.
**Details**: [View Full Documentation](./COMP/Shared_Mem_Out.md)

### Slider

**Type**: COMP | **Category**: General
**Description**: The Slider Component lets you build sliders in X, Y and XY, and outputs 1 or 2 channels from a Panel CHOP placed in the Slider component.
**Details**: [View Full Documentation](./COMP/Slider.md)

### Table

**Type**: COMP | **Category**: General
**Description**: The Table Component creates a grid of user interface gadgets.  These panels are laid out in a grid format where the contents of each cell are defined by DAT tables.
**Details**: [View Full Documentation](./COMP/Table.md)

### Time

**Type**: COMP | **Category**: General
**Description**: The Time Component allows each component to have its own timeline (clock). The Time Component contains a network of operators that can drive a Timeline, drive animations in Animation COMPs, or be used to drive any custom time-based system.
**Details**: [View Full Documentation](./COMP/Time.md)

### Window

**Type**: COMP | **Category**: General
**Description**: The Window Component allows you to create and maintain a separate floating window displaying the contents of any Panel or any other Node Viewer .
**Details**: [View Full Documentation](./COMP/Window.md)

---

## Family: MAT {#family-mat}

**Material Operators - Shading and material definitions**

**Total Operators**: 9

[View MAT Family Index](./MAT/MAT_INDEX.md)

### Constant

**Type**: MAT | **Category**: General
**Description**: Renders a constant color on a material. To apply a texture, use a Phong MAT and set the color for Diffuse and Specular parameters to (0,0,0), then use the Emit parameters to set color, and the Color Map if you want to apply a texture.
**Details**: [View Full Documentation](./MAT/Constant.md)

### Depth

**Type**: MAT | **Category**: General
**Description**: The Depth Only MAT can be used to prevent objects from being drawn by making an invisible barrier in Z.
**Details**: [View Full Documentation](./MAT/Depth.md)

### GLSL

**Type**: MAT | **Category**: General
**Description**: Allows you to write or import custom materials into TouchDesigner. When there are compile errors in a GLSL shader, a blue/red checkerboard error shader will be displayed.
**Details**: [View Full Documentation](./MAT/GLSL.md)

### Null

**Type**: MAT | **Category**: General
**Description**: Doesn't do much but comes in handy when building networks.
**Details**: [View Full Documentation](./MAT/Null.md)

### Phong

**Type**: MAT | **Category**: General
**Description**: Creates a material using the Phong Shading model. It has support for textures, reflections, bumps, cone lights, rim lights, alpha maps and more.
**Details**: [View Full Documentation](./MAT/Phong.md)

### Point Sprite

**Type**: MAT | **Category**: General
**Description**: Allows you to control some attributes of Point Sprites (creatable using the Particle SOP or DAT to SOP ).
**Details**: [View Full Documentation](./MAT/Point_Sprite.md)

### Select

**Type**: MAT | **Category**: General
**Description**: Grabs another material from any location in the project.
**Details**: [View Full Documentation](./MAT/Select.md)

### Switch

**Type**: MAT | **Category**: General
**Description**: Allows switching between multiple material inputs.
**Details**: [View Full Documentation](./MAT/Switch.md)

### Wireframe

**Type**: MAT | **Category**: General
**Description**: Renders the edges of polygons and curves as lines.
**Details**: [View Full Documentation](./MAT/Wireframe.md)

---

## Statistics

- **Total Operators**: 422
- **Families**: 6
- **Generated**: summaries_to_markdown.py

## Usage

Each operator has its own dedicated markdown file with:

- Complete description
- All parameters with types and descriptions  
- Usage examples and related operators
- Cross-references to similar functionality

Navigate using the family indexes or search for specific operators.
