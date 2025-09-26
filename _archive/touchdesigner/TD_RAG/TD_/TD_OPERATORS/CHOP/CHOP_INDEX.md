# CHOP - Channel Operators - Process and manipulate channel data

[← Back to All Operators](../OPERATORS_INDEX.md)

## Overview

Channel Operators - Process and manipulate channel data in TouchDesigner. This family contains 128 operators.

## All CHOP Operators

#### Analyze

**Category**: General
**Description**: Looks at the values of all the values of a channel, and outputs a single-number result into the output.
**Documentation**: [Full Details](./Analyze.md)
**Related**: _To be added_

#### Angle

**Category**: General
**Description**: Is a general purpose converter between degrees, radians, quaternions and vectors.  Different formats assume a specific ordering of input channels.
**Documentation**: [Full Details](./Angle.md)
**Related**: _To be added_

#### Attribute

**Category**: General
**Description**: Adds, removes or updates attributes of the input CHOP. Currently there is only one attribute type, a "quaternion".
**Documentation**: [Full Details](./Attribute.md)
**Related**: _To be added_

#### Audio Band EQ

**Category**: General
**Description**: Is a 16-band equalizer which filters audio input channels in the same way that a conventional band (graphic) equalizer uses a bank of sliders to filter fixed-frequency bands of sound.
**Documentation**: [Full Details](./Audio_Band_EQ.md)
**Related**: _To be added_

#### Audio Device In

**Category**: General
**Description**: Receives audio from any of the attached audio input devices using DirectSound or ASIO. It always outputs time sliced audio data.
**Documentation**: [Full Details](./Audio_Device_In.md)
**Related**: _To be added_

#### Audio Device Out

**Category**: General
**Description**: Sends audio to any of the attached audio output devices using DirectSound or ASIO. The audio channels can be routed to any speaker location.
**Documentation**: [Full Details](./Audio_Device_Out.md)
**Related**: _To be added_

#### Audio Dynamics

**Category**: General
**Description**: Is designed to control the dynamic range of an audio signal. Dynamic range refers to how loud and quiet the audio is over some period of time.
**Documentation**: [Full Details](./Audio_Dynamics.md)
**Related**: _To be added_

#### Audio File In

**Category**: General
**Description**: Reads audio from files on disk or at http:// addresses. File types .mp3, .aif, .aiff, .au, and .wav files are supported.
**Documentation**: [Full Details](./Audio_File_In.md)
**Related**: _To be added_

#### Audio Filter

**Category**: General
**Description**: Removes low frequencies, high frequencies, both low and high, or removes a mid-frequency range. A Low pass filter removes the higher frequencies of a sound, while a high pass filter reduces the bass of the sound.
**Documentation**: [Full Details](./Audio_Filter.md)
**Related**: _To be added_

#### Audio Movie

**Category**: General
**Description**: Plays the audio of a movie file that is played back with a Movie File In TOP . Make the Audio Movie TOP point to a Movie File In TOP via the Movie File In TOP parameter.
**Documentation**: [Full Details](./Audio_Movie.md)
**Related**: _To be added_

#### Audio Oscillator

**Category**: General
**Description**: Generates sounds in three ways. It repeats common waveforms (sine, triangle), it generates white noise (a random number for each sample), or it repeats a prepared incoming audio clip of any duration.
**Documentation**: [Full Details](./Audio_Oscillator.md)
**Related**: _To be added_

#### Audio Para EQ

**Category**: General
**Description**: (parametric equalizer ) applies up to 3 parametric filters to the incoming sound. The three filters are in series, where internally, the second filter takes its input from the output of the first filter, and so on.
**Documentation**: [Full Details](./Audio_Para_EQ.md)
**Related**: _To be added_

#### Audio Play

**Category**: General
**Description**: Plays back a sound file through any attached audio output device using DirectSound. It supports .aif, .
**Documentation**: [Full Details](./Audio_Play.md)
**Related**: _To be added_

#### Audio SDI In

**Category**: General
**Description**: Is a TouchDesigner Pro only operator. The Audio SDI In CHOP can capture the audio from any SDI In TOP .
**Documentation**: [Full Details](./Audio_SDI_In.md)
**Related**: _To be added_

#### Audio Spectrum

**Category**: General
**Description**: Calculates and displays the frequency spectrum of the input channels. In the default Visualization Mode the CHOP is set to display the spectrum in a more understandable way by emphasizing the higher frequency levels and the lower frequency ranges.
**Documentation**: [Full Details](./Audio_Spectrum.md)
**Related**: _To be added_

#### Audio Stream In

**Category**: General
**Description**: Can stream audio into TouchDesigner from any rtsp server.
**Documentation**: [Full Details](./Audio_Stream_In.md)
**Related**: _To be added_

#### Audio Stream Out

**Category**: General
**Description**: Can stream audio out to any rtsp client such as VideoLAN's VLC media player and Apple's Quicktime. To access the stream in one of these players, open a "Network Stream" or "URL" under the File menu.
**Documentation**: [Full Details](./Audio_Stream_Out.md)
**Related**: _To be added_

#### Beat

**Category**: General
**Description**: Generates a variety of ramps, pulses and counters that are timed to the beats per minute and the sync produced by the Beat Dialog or the beat Command .
**Documentation**: [Full Details](./Beat.md)
**Related**: _To be added_

#### Blend

**Category**: General
**Description**: Combines two or more CHOPs in input 2, 3 and so on, by using a set of blending channels in input 1. The blending channels cause different strengths of the CHOPs to contribute to the output of the CHOP.
**Documentation**: [Full Details](./Blend.md)
**Related**: _To be added_

#### CPlusPlus

**Category**: General
**Description**: Allows you to make custom CHOP operators by writing your own .dll using C++. Note : The CPlusPlus CHOP is only available in TouchDesigner Commercial and TouchDesigner Pro .
**Documentation**: [Full Details](./CPlusPlus.md)
**Related**: _To be added_

#### Clip

**Category**: General
**Description**: Is a TouchDesigner Pro only operator. See.
**Documentation**: [Full Details](./Clip.md)
**Related**: _To be added_

#### Clip Blender

**Category**: General
**Description**: Is a TouchDesigner Pro only operator.  It can be used as an animation system that blends between different animation clips, preserving rotation, changing target positions etc.
**Documentation**: [Full Details](./Clip_Blender.md)
**Related**: _To be added_

#### Clock

**Category**: General
**Description**: Generates channels that reflect the time of year, month, week, day, hour, minute, second and millisecond.
**Documentation**: [Full Details](./Clock.md)
**Related**: _To be added_

#### Composite

**Category**: General
**Description**: Layers (blends) the channels of one CHOP on the channels of another CHOP. The first input is the base input and the second is the layer input.
**Documentation**: [Full Details](./Composite.md)
**Related**: _To be added_

#### Constant

**Category**: General
**Description**: Creates up to forty new constant-value channels. Each channel can be named and assigned a different value.
**Documentation**: [Full Details](./Constant.md)
**Related**: _To be added_

#### Copy

**Category**: General
**Description**: Produces multiple copies of the second input along the timeline of the first input. The first input provides the trigger signals or the convolve levels.
**Documentation**: [Full Details](./Copy.md)
**Related**: _To be added_

#### Count

**Category**: General
**Description**: Counts the number of times a channel crosses a trigger or release threshold. It operates in either static or realtime ("Cook to Current Frame") mode.
**Documentation**: [Full Details](./Count.md)
**Related**: _To be added_

#### Cross

**Category**: General
**Description**: Is a multi input OP that blends between 2 inputs at a time. This is similar to a Switch CHOP however the Cross CHOP allows for interpolation between the inputs.
**Documentation**: [Full Details](./Cross.md)
**Related**: _To be added_

#### Cycle

**Category**: General
**Description**: Creates cycles. It can repeat the channels any number of times before and after the original. It can also make a single cycle have a smooth transition from its end to its beginning, so it loops smoothly.
**Documentation**: [Full Details](./Cycle.md)
**Related**: _To be added_

#### DAT to

**Category**: General
**Description**: Will create a set of CHOP channels with values derived from a DAT .
**Documentation**: [Full Details](./DAT_to.md)
**Related**: _To be added_

#### DMX In

**Category**: General
**Description**: Receives channels from DMX or Art-Net devices.  Channel values for DMX are 0-255. NOTE: In TouchDesigner Non-commercial, the DMX Out CHOP is limited to 32 channels.
**Documentation**: [Full Details](./DMX_In.md)
**Related**: _To be added_

#### DMX Out

**Category**: General
**Description**: Sends channels to DMX or Art-Net devices.  Channel values for DMX are 0-255. The first channel you send into the DMX Out will correspond to the first DMX address (DMX channel) As you add channels to the DMX Out, you will access the next DMX channels in order.
**Documentation**: [Full Details](./DMX_Out.md)
**Related**: _To be added_

#### Delay

**Category**: General
**Description**: Delays the input. Multiple channels can be fed in to delay each separately and each channels can have a separate delay time.
**Documentation**: [Full Details](./Delay.md)
**Related**: _To be added_

#### Delete

**Category**: General
**Description**: Removes entire channels and/or individual samples of its input. A first method uses a text string to select channels by name or number ranges.
**Documentation**: [Full Details](./Delete.md)
**Related**: _To be added_

#### Envelope

**Category**: General
**Description**: Outputs the maximum amplitude in the vicinity of each sample of the input. It takes the absolute value of the input, and uses a sliding window of a number of samples to find the maximum amplitude near each sample.
**Documentation**: [Full Details](./Envelope.md)
**Related**: _To be added_

#### EtherDream

**Category**: General
**Description**: Takes as input up to five channels interpreted as X and Y (horizontal and vertical) position values in the first 2 channels, and red, green and blue color values in the next 3 channels.
**Documentation**: [Full Details](./EtherDream.md)
**Related**: _To be added_

#### Event

**Category**: General
**Description**: Manages the birth and life of overlapping events triggered by devices like a MIDI keyboard. It can be seen as a simple particle system designed for MIDI keyboards.
**Documentation**: [Full Details](./Event.md)
**Related**: _To be added_

#### Expression

**Category**: General
**Description**: Allows you to modify input channels by using math expressions. Up to six expressions are available. Each input channel is modified by exactly one expression, and the expressions are looped for multiple channels.
**Documentation**: [Full Details](./Expression.md)
**Related**: _To be added_

#### Extend

**Category**: General
**Description**: Only sets the "extend conditions" of a CHOP, which determines what values you get when sampling the CHOP before or after its interval.
**Documentation**: [Full Details](./Extend.md)
**Related**: _To be added_

#### Fan

**Category**: General
**Description**: Converts one channel out to many channels, or converts many channels down to one. Its first operation, Fan Out, takes one channel and generates 2 or more channels.
**Documentation**: [Full Details](./Fan.md)
**Related**: _To be added_

#### Feedback

**Category**: General
**Description**: Stores channels from the current frame to be used in a later frame, without forcing recooking back one frame.
**Documentation**: [Full Details](./Feedback.md)
**Related**: _To be added_

#### File In

**Category**: General
**Description**: Reads in channel and audio files for use by CHOPs. The file can be read in from disk or from the web.
**Documentation**: [Full Details](./File_In.md)
**Related**: _To be added_

#### File Out

**Category**: General
**Description**: Writes CHOP channel data out to .chan files. The data can be written out every frame or at intervals (set by the Interval parameter) into a log file.
**Documentation**: [Full Details](./File_Out.md)
**Related**: _To be added_

#### Filter

**Category**: General
**Description**: Smooths or sharpens the input channels. It filters by combining each sample and a range of its neighbor samples to set the new value of that sample.
**Documentation**: [Full Details](./Filter.md)
**Related**: _To be added_

#### Function

**Category**: General
**Description**: Provides more complicated math functions than found in the Math CHOP : trigonometic functions, logarithmic functions and exponential functions, and also audio decibels (dB)-power-amplitude conversions.
**Documentation**: [Full Details](./Function.md)
**Related**: _To be added_

#### Gesture

**Category**: General
**Description**: Records a short segment of the first input and loops this segment in time with options as specified in the Gesture Page.
**Documentation**: [Full Details](./Gesture.md)
**Related**: _To be added_

#### Handle

**Category**: General
**Description**: Is the "engine" which drives Inverse Kinematic solutions using the Handle COMP . The role of the Handle CHOP is to generate rotation values for the bones which will bring their attached handles as close to their respective targets as possible.
**Documentation**: [Full Details](./Handle.md)
**Related**: _To be added_

#### Hog

**Category**: General
**Description**: Eats up CPU cycles (ie it's a CPU hog - oink!). This can be used to simulate performance on slower machines, or to artifically slow down a synth's frame rate.
**Documentation**: [Full Details](./Hog.md)
**Related**: _To be added_

#### Hold

**Category**: General
**Description**: Waits for a 0 to 1 step on its second input, at which time it reads the current values from the first input (one value per channel).
**Documentation**: [Full Details](./Hold.md)
**Related**: _To be added_

#### In

**Category**: General
**Description**: Gets channels that are connected to one of the inputs of the component. For each In CHOP inside a component, there is one input connector added to the In CHOP's parent component.
**Documentation**: [Full Details](./In.md)
**Related**: _To be added_

#### Info

**Category**: General
**Description**: Gives you extra information about a node. All nodes contain extra inside information, and different types of nodes (TOPs, CHOPs, etc) contain different subsets of information.
**Documentation**: [Full Details](./Info.md)
**Related**: _To be added_

#### Interpolate

**Category**: General
**Description**: Treats its multiple-inputs as keyframes and interpolates between them. The inputs are usually single-frame CHOP channels like those produced by a Constant CHOP .
**Documentation**: [Full Details](./Interpolate.md)
**Related**: _To be added_

#### Inverse Curve

**Category**: General
**Description**: Calculates an inverse kinematics simulation for bone objects using a curve object. The Inverse Curve CHOP will stretch and position a set of bones to follow a curve defined by another set of objects (guide).
**Documentation**: [Full Details](./Inverse_Curve.md)
**Related**: _To be added_

#### Inverse Kin

**Category**: General
**Description**: Calculates an inverse kinematics simulation for Bone objects .
**Documentation**: [Full Details](./Inverse_Kin.md)
**Related**: _To be added_

#### Join

**Category**: General
**Description**: Takes all its inputs and appends one CHOP after another. It is expected they all have the same channels.
**Documentation**: [Full Details](./Join.md)
**Related**: _To be added_

#### Joystick

**Category**: General
**Description**: Outputs values for all 6 possible axes on any game controller (joysticks, game controllers, driving wheels, etc.
**Documentation**: [Full Details](./Joystick.md)
**Related**: _To be added_

#### Keyboard In

**Category**: General
**Description**: Receives ASCII input from the keyboard, and outputs channels for the number of keys specified. It creates a single-frame channel representing the current state of each key.
**Documentation**: [Full Details](./Keyboard_In.md)
**Related**: _To be added_

#### Keyframe

**Category**: General
**Description**: Uses channel and keys data in an Animation COMP and creates channels of samples at a selectable sample rate (frames per second).
**Documentation**: [Full Details](./Keyframe.md)
**Related**: _To be added_

#### Kinect

**Category**: General
**Description**: Reads positional and skeletal tracking data from the Kinect and Linect2 sensors.  Up to 6 people's full skeletons can be tracked (2 on the original Kinect), and the center position of an addition 4 people in the camera view is tracked as well.
**Documentation**: [Full Details](./Kinect.md)
**Related**: _To be added_

#### LFO

**Category**: General
**Description**: (low frequency oscillator) generates waves in real-time in two ways. It synthesizes curves using a choice of common waveforms like Sine or Pulse, or it repeats a prepared incoming curve.
**Documentation**: [Full Details](./LFO.md)
**Related**: _To be added_

#### LTC In

**Category**: General
**Description**: Reads SMPTE timecode data encoded into an audio signal.  Read the overview Linear Timecode . First bring the audio signal into CHOPs using an Audio Device In CHOP .
**Documentation**: [Full Details](./LTC_In.md)
**Related**: _To be added_

#### LTC Out

**Category**: General
**Description**: Outputs "linear timecode" which is a SMPTE timecode data encoded into an audio signal.  See also Linear Timecode .
**Documentation**: [Full Details](./LTC_Out.md)
**Related**: _To be added_

#### Lag

**Category**: General
**Description**: Adds lag and overshoot to channels. It can also limit the velocity and acceleration of channels. Lag slows down rapid changes in the input channels.
**Documentation**: [Full Details](./Lag.md)
**Related**: _To be added_

#### Leap Motion

**Category**: General
**Description**: Reads hand, finger, tool and gesture data from the Leap Motion controller. It outputs hand, finger and tool positions, rotations and 'tracking' channels that indicate if these values are currently being detected and updated.
**Documentation**: [Full Details](./Leap_Motion.md)
**Related**: _To be added_

#### Limit

**Category**: General
**Description**: Can limit the values of the input channels to be between a minimum and maximum, and can quantize the input channels in time and/or value such that the value steps over time.
**Documentation**: [Full Details](./Limit.md)
**Related**: _To be added_

#### Logic

**Category**: General
**Description**: First converts channels of all its input CHOPs into binary (0 = off, 1 = on) channels and then combines the channels using a variety of logic operations.
**Documentation**: [Full Details](./Logic.md)
**Related**: _To be added_

#### Lookup

**Category**: General
**Description**: Outputs values from a lookup table. The first input (the Index Channel) is an index into the second input (the Lookup Table).
**Documentation**: [Full Details](./Lookup.md)
**Related**: _To be added_

#### MIDI In

**Category**: General
**Description**: Reads Note events, Controller events, Program Change events, System Exclusive messages and Timing events from both MIDI devices and files.
**Documentation**: [Full Details](./MIDI_In.md)
**Related**: _To be added_

#### MIDI In Map

**Category**: General
**Description**: See first the MIDI In DAT . The MIDI In Map CHOP reads in specified channels from the MIDI Device Mapper which prepares slider channels starting from s1, s2, etc.
**Documentation**: [Full Details](./MIDI_In_Map.md)
**Related**: _To be added_

#### MIDI Out

**Category**: General
**Description**: Sends MIDI events to any available MIDI devices when its input channels change. More flexibly, the Python MidioutCHOP Class can be used to send any type of MIDI event to a MIDI device via an existing MIDI Out CHOP.
**Documentation**: [Full Details](./MIDI_Out.md)
**Related**: _To be added_

#### Math

**Category**: General
**Description**: Performs arithmetic operations on channels. The channels of a CHOP can be combined into one channel, and several CHOPs can be combined into one CHOP.
**Documentation**: [Full Details](./Math.md)
**Related**: _To be added_

#### Merge

**Category**: General
**Description**: Takes multiple inputs and merges them into the output. All the channels of the input appear in the output.
**Documentation**: [Full Details](./Merge.md)
**Related**: _To be added_

#### Mouse In

**Category**: General
**Description**: Outputs X and Y screen values for the mouse device and monitors the up/down state of the three mouse buttons.
**Documentation**: [Full Details](./Mouse_In.md)
**Related**: _To be added_

#### Mouse Out

**Category**: General
**Description**: Forces the mouse position and button status to be driven from TouchDesigner using the incoming CHOP channels.
**Documentation**: [Full Details](./Mouse_Out.md)
**Related**: _To be added_

#### NatNet In

**Category**: General
**Description**: The NatNet In CHOP.
**Documentation**: [Full Details](./NatNet_In.md)
**Related**: _To be added_

#### Noise

**Category**: General
**Description**: Makes an irregular wave that never repeats, with values approximately in the range -1 to +1. It generates both smooth curves and noise that is random each sample.
**Documentation**: [Full Details](./Noise.md)
**Related**: _To be added_

#### Null

**Category**: General
**Description**: Is used as a place-holder and does not alter the data coming in. It is often used to Export channels to parameters, which allows you to experiment with the CHOPs that feed into the Null without having to un-export from one CHOP and re-export from another.
**Documentation**: [Full Details](./Null.md)
**Related**: _To be added_

#### OSC In

**Category**: General
**Description**: Is used to accept Open Sound Control Messages. OSC In can be used to accept messages from either a 3rd party application which adheres to the Open Sound Control specification ( <http://www>.
**Documentation**: [Full Details](./OSC_In.md)
**Related**: _To be added_

#### OSC Out

**Category**: General
**Description**: Sends all input channels to a specified network address and port. Each channel name and associated data is transmitted together to the specified location.
**Documentation**: [Full Details](./OSC_Out.md)
**Related**: _To be added_

#### Object

**Category**: General
**Description**: Compares two objects and outputs channels containing their raw or relative positions and orientations.
**Documentation**: [Full Details](./Object.md)
**Related**: _To be added_

#### Oculus Audio

**Category**: General
**Description**: Uses the Oculus Audio SDK to take a mono sound channel and create a spatialized stereo pair or channels for that sound.
**Documentation**: [Full Details](./Oculus_Audio.md)
**Related**: _To be added_

#### Oculus Rift

**Category**: General
**Description**: Connects to an Oculus Rift device and outputs several useful sets of channels that can be used to integrate the Oculus Rift into projects.
**Documentation**: [Full Details](./Oculus_Rift.md)
**Related**: _To be added_

#### Out

**Category**: General
**Description**: Sends CHOP data from inside a components to other components or CHOPs. It sends channels to one of the outputs of the component.
**Documentation**: [Full Details](./Out.md)
**Related**: _To be added_

#### Override

**Category**: General
**Description**: Lets you take inputs from several CHOP sources, and uses the most-recently changed input channels to determine the output.
**Documentation**: [Full Details](./Override.md)
**Related**: _To be added_

#### Panel

**Category**: General
**Description**: Reads Panel Values from Panel Components into CHOP channels. Panel values can also be accessed by using the panel() expression.
**Documentation**: [Full Details](./Panel.md)
**Related**: _To be added_

#### Parameter

**Category**: General
**Description**: Gets parameter values, including custom parameters, from all OP types. ( In Build 46000 or later . This replaces the Fetch CHOP.
**Documentation**: [Full Details](./Parameter.md)
**Related**: _To be added_

#### Pattern

**Category**: General
**Description**: Generates a sequence of samples in a channel. Unlike the Wave CHOP its purpose is generating arrays of samples that have no reference to time (seconds or frames).
**Documentation**: [Full Details](./Pattern.md)
**Related**: _To be added_

#### Perform

**Category**: General
**Description**: Outputs many channels like frames-per-second, describing the current state of the TouchDesigner process.
**Documentation**: [Full Details](./Perform.md)
**Related**: _To be added_

#### Pipe In

**Category**: General
**Description**: Allows users to input from custom devices into CHOPs. It is implemented as a TCP/IP network connection.
**Documentation**: [Full Details](./Pipe_In.md)
**Related**: _To be added_

#### Pipe Out

**Category**: General
**Description**: Can be used to transmit data out of TouchDesigner to other processes running on a remote machine using a network connection.
**Documentation**: [Full Details](./Pipe_Out.md)
**Related**: _To be added_

#### Pulse

**Category**: General
**Description**: Generates pulses in one channel at regular intervals. The amplitude of each pulse can be edited with the CHOP sliders or with handles on the graph.
**Documentation**: [Full Details](./Pulse.md)
**Related**: _To be added_

#### RealSense

**Category**: General
**Description**: Receives positional data from Intel's RealSense camera. See also RealSense TOP Available in builds 50000 or later.
**Documentation**: [Full Details](./RealSense.md)
**Related**: _To be added_

#### Record

**Category**: General
**Description**: Takes the channels coming in the first (Position) input, converts and records them internally, and outputs the stored channels as the CHOP output.
**Documentation**: [Full Details](./Record.md)
**Related**: _To be added_

#### Rename

**Category**: General
**Description**: Renames channels. Channels names from the input CHOP are matched using the From pattern, and are renamed to the corresponding name in the To pattern.
**Documentation**: [Full Details](./Rename.md)
**Related**: _To be added_

#### Render Pick

**Category**: General
**Description**: Samples a rendering (from a Render TOP or a Render Pass TOP ) and returns 3D information from the geometry at that particular pick location.
**Documentation**: [Full Details](./Render_Pick.md)
**Related**: _To be added_

#### Reorder

**Category**: General
**Description**: Re-orders the first input CHOP's channels by numeric or alphabetic patterns. Either a channel pattern specifies the new order, or a number sequence specifies the new order.
**Documentation**: [Full Details](./Reorder.md)
**Related**: _To be added_

#### Replace

**Category**: General
**Description**: Can be used to replace channels very quickly. The output of channels in Input1 will be replaced by channels found in Input2 if a matching channel exists in Input2.
**Documentation**: [Full Details](./Replace.md)
**Related**: _To be added_

#### Resample

**Category**: General
**Description**: Resamples an input's channels to a new sample rate and/or start/end interval. In all cases, the entire input interval is resampled to match the output interval.
**Documentation**: [Full Details](./Resample.md)
**Related**: _To be added_

#### SOP to

**Category**: General
**Description**: Uses a geometry object to choose a SOP from which the channels will be created. The channels are created from the point attributes of a SOP, such as the X, Y and Z of the point position.
**Documentation**: [Full Details](./SOP_to.md)
**Related**: _To be added_

#### Scan

**Category**: General
**Description**: Converts a SOP or TOP to oscilloscope or laser friendly control waves.  The output is usually in the audible range and can be heard directly via an Audio Device Out CHOP, or used to drive the X and Y deflector inputs of an oscilloscope, recreating the imagery.
**Documentation**: [Full Details](./Scan.md)
**Related**: _To be added_

#### Script

**Category**: General
**Description**: Runs a script each time the Script CHOP cooks. By default, the Script CHOP is created with a docked DAT that contains three Python methods: cook, onPulse, and setupParameters .
**Documentation**: [Full Details](./Script.md)
**Related**: _To be added_

#### Select

**Category**: General
**Description**: Selects and renames channels from other CHOPs of any CHOP network. You can select the channels from control panel gadgets like sliders and buttons.
**Documentation**: [Full Details](./Select.md)
**Related**: _To be added_

#### Serial

**Category**: General
**Description**: Is used for serial communication through an external port, using the RS-232 protocol. These ports are usually a 9 pin connector, or a USB port on new machines.
**Documentation**: [Full Details](./Serial.md)
**Related**: _To be added_

#### Shared Mem In

**Category**: General
**Description**: Is only available in TouchDesigner Commercial and Pro. The Shared Mem In CHOP receives CHOPs from a shared memory segment that is attached to a Shared Mem Out CHOP in another process or the same process.
**Documentation**: [Full Details](./Shared_Mem_In.md)
**Related**: _To be added_

#### Shared Mem Out

**Category**: General
**Description**: The Shared Mem Out TOP is only available in TouchDesigner Commercial and Pro. The Shared Mem Out CHOP sends CHOPs to a shared memory segment that is attached to a Shared Mem In CHOP in another process or the same process.
**Documentation**: [Full Details](./Shared_Mem_Out.md)
**Related**: _To be added_

#### Shift

**Category**: General
**Description**: Time-shifts a CHOP, changing the start and end of the CHOP's interval. However, the contents of the channels remain the same.
**Documentation**: [Full Details](./Shift.md)
**Related**: _To be added_

#### Shuffle

**Category**: General
**Description**: Reorganizes the samples in a set of channels. It is useful for transforming data received by the SOP to CHOP and TOP to CHOPs into channels containing only one row or column.
**Documentation**: [Full Details](./Shuffle.md)
**Related**: _To be added_

#### Slope

**Category**: General
**Description**: Calculates the slope (or "derivative" in math-speak) of the input channels. If the input CHOP represents position, the slope can be interpreted as speed.
**Documentation**: [Full Details](./Slope.md)
**Related**: _To be added_

#### Sort

**Category**: General
**Description**: Re-orders the inputs channels samples by value or by random. Specifying a channel to be sorted will reorder all remaining channels samples according to the new order.
**Documentation**: [Full Details](./Sort.md)
**Related**: _To be added_

#### Speed

**Category**: General
**Description**: Converts speed (units per second) to distance (units) over a time range. More generally, you give it a rate (the CHOP input) and it outputs a cumulative value.
**Documentation**: [Full Details](./Speed.md)
**Related**: _To be added_

#### Spring

**Category**: General
**Description**: Creates vibrations influenced by the input channels, as if a mass was attached to a spring. It acts as if, for every channel, there is a mass at the end of a spring, affected by a distance from the actual position (the output of the channel at the previous frame) to the desired position (the input channel at the current frame).
**Documentation**: [Full Details](./Spring.md)
**Related**: _To be added_

#### Stretch

**Category**: General
**Description**: Preserves the shape of channels and the sampling rate, but resamples the channels into a new interval.
**Documentation**: [Full Details](./Stretch.md)
**Related**: _To be added_

#### Switch

**Category**: General
**Description**: Allows you to control the flow of channels through a CHOPnet. It selects one of the input CHOPs by index and copies it exactly.
**Documentation**: [Full Details](./Switch.md)
**Related**: _To be added_

#### Sync In

**Category**: General
**Description**: And Sync Out CHOP are used to keep timelines in two or more TouchDesigner processes within a single frame of each other.
**Documentation**: [Full Details](./Sync_In.md)
**Related**: _To be added_

#### Sync Out

**Category**: General
**Description**: The Sync In CHOP and Sync Out CHOP are used to keep timelines in two or more TouchDesigner processes within a single frame of each other.
**Documentation**: [Full Details](./Sync_Out.md)
**Related**: _To be added_

#### TOP to

**Category**: General
**Description**: Converts pixels in a TOP image to CHOP channels. It generates one CHOP channel per scanline (row) in the image and per pixel color element (RGBA).
**Documentation**: [Full Details](./TOP_to.md)
**Related**: _To be added_

#### Tablet

**Category**: General
**Description**: Gets the Wacom tablet X and Y values, and also gets pen tip pressure, X tilt and Y tilt, and the various pen buttons.
**Documentation**: [Full Details](./Tablet.md)
**Related**: _To be added_

#### Time Slice

**Category**: General
**Description**: Outputs a time slice of samples. It is used to generate smooth in-betweens when TouchDesigner cannot cook/draw fast enough and keep up with the animation's frames per second.
**Documentation**: [Full Details](./Time_Slice.md)
**Related**: _To be added_

#### Timeline

**Category**: General
**Description**: Outputs time-based CHOP channels for a specific component.  The time channels are defined by a Time Component whose Path can be determined using the expression timepath() .
**Documentation**: [Full Details](./Timeline.md)
**Related**: _To be added_

#### Timer

**Category**: General
**Description**: Is an engine for running timed processes. It outputs channels such as timing fractions, counters, pulses and timer states, and it calls python functions (callbacks) when various timing events occur.
**Documentation**: [Full Details](./Timer.md)
**Related**: _To be added_

#### Touch In

**Category**: General
**Description**: Can be used to create a high speed connection between two TouchDesigner processes via CHOPs. Data is sent over TCP/IP.
**Documentation**: [Full Details](./Touch_In.md)
**Related**: _To be added_

#### Touch Out

**Category**: General
**Description**: Can be used to create high speed connection between two TouchDesigner processes. Data is sent over TCP/IP.
**Documentation**: [Full Details](./Touch_Out.md)
**Related**: _To be added_

#### Trail

**Category**: General
**Description**: Displays a history of its input channels back in time. A window of time is displayed from the current frame back in time, the size of this window is set by the Window Length parameter.
**Documentation**: [Full Details](./Trail.md)
**Related**: _To be added_

#### Transform

**Category**: General
**Description**: Takes translate, rotate, and/or scale channels and transforms them using the transform parameters in the CHOP.
**Documentation**: [Full Details](./Transform.md)
**Related**: _To be added_

#### Trigger

**Category**: General
**Description**: Starts an audio-style attack/decay/sustain/release (ADSR) envelope to all trigger pulses in the input channels.
**Documentation**: [Full Details](./Trigger.md)
**Related**: _To be added_

#### Trim

**Category**: General
**Description**: Shortens or lengthens the input's channels. A part of the interval can be preserved or removed. If the channels are being lengthened, the extend conditions of the channel will be used to get the new values.
**Documentation**: [Full Details](./Trim.md)
**Related**: _To be added_

#### Warp

**Category**: General
**Description**: Time-warps the channels of the first input (the Pre-Warp Channels) using one warping channel in the second input (the Warp Curve).
**Documentation**: [Full Details](./Warp.md)
**Related**: _To be added_

#### Wave

**Category**: General
**Description**: Makes repeating waves with a variety of shapes. It is by default 10-seconds of 1-second sine waves, a total of 600 frames.
**Documentation**: [Full Details](./Wave.md)
**Related**: _To be added_

---

## Quick Stats

- **Total CHOP Operators**: 128
- **Family Type**: CHOP
- **Documentation**: Each operator has detailed parameter reference

## Navigation

- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation-by-family)

---
_Generated from TouchDesigner summaries.txt_
