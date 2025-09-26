# TouchDesigner Operators Reference Guide

## Content

- [Introduction](#introduction)
- [CHOP Operators (Channel Operators)](#chop-operators-channel-operators)
  - [Analysis & Information](#analysis--information)
  - [Audio Processing](#audio-processing)
  - [Control & Input](#control--input)
  - [Data Processing](#data-processing)
  - [File Operations](#file-operations)
  - [Generation](#generation)
  - [Logic & Math](#logic--math)
  - [Network Communication](#network-communication)
  - [Transform & Animation](#transform--animation)
  - [Utility](#utility)
  - [Pro/Commercial Only](#procommercial-only)
- [COMP Operators (Components)](#comp-operators-components)
  - [3D Scene Objects](#3d-scene-objects)
  - [Panel Components](#panel-components)
  - [System Components](#system-components)
  - [Pro/Commercial Only](#procommercial-only-1)
- [TOP Operators (Texture Operators)](#top-operators-texture-operators)
  - [Compositing](#compositing)
  - [Effects & Filters](#effects--filters)
  - [Generation](#generation-1)
  - [Input/Output](#inputoutput)
  - [Network Communication](#network-communication-1)
  - [Rendering](#rendering)
  - [Utility](#utility-1)
  - [Pro/Commercial Only](#procommercial-only-2)
- [MAT Operators (Materials)](#mat-operators-materials)
- [SOP Operators (Surface Operators)](#sop-operators-surface-operators)
  - [Creation & Generation](#creation--generation)
  - [Deformation & Animation](#deformation--animation)
  - [File Operations](#file-operations-1)
  - [Geometry Processing](#geometry-processing)
  - [Modeling Tools](#modeling-tools)
  - [Utility](#utility-2)
- [DAT Operators (Data Operators)](#dat-operators-data-operators)
  - [Data Processing](#data-processing-1)
  - [Execution & Scripting](#execution--scripting)
  - [File Operations](#file-operations-2)
  - [Input/Output](#inputoutput-1)
  - [Network Communication](#network-communication-2)
  - [System Information](#system-information)
  - [Utility](#utility-3)

## Introduction

TouchDesigner uses a node-based visual programming environment with different types of operators (OPs) for specific data types and functions. This reference guide covers all the major operator categories:

- **CHOP** - Channel Operators for numerical data streams
- **COMP** - Components for 3D objects and UI panels  
- **TOP** - Texture Operators for image processing
- **MAT** - Materials for 3D rendering
- **SOP** - Surface Operators for 3D geometry
- **DAT** - Data Operators for tables and text

---

## CHOP Operators (Channel Operators)

CHOPs work with channels of numerical data over time, commonly used for animation, audio processing, and control signals.

### Analysis & Information

#### Analyze

Looks at the values of all the values of a channel, and outputs a single-number result into the output.

#### Info

Gives you extra information about a node. All nodes contain extra inside information, and different types of nodes (TOPs, CHOPs, etc) contain different subsets of information.

### Audio Processing

#### Audio Device In

Receives audio from any of the attached audio input devices using DirectSound or ASIO. It always outputs time sliced audio data.

#### Audio Device Out

Sends audio to any of the attached audio output devices using DirectSound or ASIO. The audio channels can be routed to any speaker location.

#### Audio Dynamics

Is designed to control the dynamic range of an audio signal. Dynamic range refers to how loud and quiet the audio is over some period of time.

#### Audio Filter

Removes low frequencies, high frequencies, both low and high, or removes a mid-frequency range. A Low pass filter removes the higher frequencies of a sound, while a high pass filter reduces the bass of the sound.

#### Audio Stream In

Can stream audio into TouchDesigner from any rtsp server.

#### Audio Stream Out

Can stream audio out to any rtsp client such as VideoLAN's VLC media player and Apple's Quicktime. To access the stream in one of these players, open a "Network Stream" or "URL" under the File menu.

#### Audio Band EQ

Is a 16-band equalizer which filters audio input channels in the same way that a conventional band (graphic) equalizer uses a bank of sliders to filter fixed-frequency bands of sound.

#### Audio File In

Reads audio from files on disk or at `http://` addresses. File types `.mp3`, `.aif`, `.aiff`, `.au`, and `.wav` files are supported.

#### Audio Movie

Plays the audio of a movie file that is played back with a Movie File In TOP. Make the Audio Movie TOP point to a Movie File In TOP via the Movie File In TOP parameter.

#### Audio Oscillator

Generates sounds in three ways. It repeats common waveforms (sine, triangle), it generates white noise (a random number for each sample), or it repeats a prepared incoming audio clip of any duration.

#### Audio Para EQ

(parametric equalizer) applies up to 3 parametric filters to the incoming sound. The three filters are in series, where internally, the second filter takes its input from the output of the first filter, and so on.

#### Audio Play

Plays back a sound file through any attached audio output device using DirectSound. It supports `.aif` files.

#### Audio Spectrum

Calculates and displays the frequency spectrum of the input channels. In the default Visualization Mode the CHOP is set to display the spectrum in a more understandable way by emphasizing the higher frequency levels and the lower frequency ranges.

### Control & Input

#### Keyboard In

Receives ASCII input from the keyboard, and outputs channels for the number of keys specified. It creates a single-frame channel representing the current state of each key.

#### Mouse In

Outputs X and Y screen values for the mouse device and monitors the up/down state of the three mouse buttons.

#### Mouse Out

Forces the mouse position and button status to be driven from TouchDesigner using the incoming CHOP channels.

#### Tablet

Gets the Wacom tablet X and Y values, and also gets pen tip pressure, X tilt and Y tilt, and the various pen buttons.

### Data Processing

#### Angle

Is a general purpose converter between degrees, radians, quaternions and vectors. Different formats assume a specific ordering of input channels.

#### Attribute

Adds, removes or updates attributes of the input CHOP. Currently there is only one attribute type, a "quaternion".

#### Beat

Generates a variety of ramps, pulses and counters that are timed to the beats per minute and the sync produced by the Beat Dialog or the beat Command.

#### Blend

Combines two or more CHOPs in input 2, 3 and so on, by using a set of blending channels in input 1. The blending channels cause different strengths of the CHOPs to contribute to the output of the CHOP.

#### Clock

Generates channels that reflect the time of year, month, week, day, hour, minute, second and millisecond.

#### Composite

Layers (blends) the channels of one CHOP on the channels of another CHOP. The first input is the base input and the second is the layer input.

#### Constant

Creates up to forty new constant-value channels. Each channel can be named and assigned a different value.

#### Copy

Produces multiple copies of the second input along the timeline of the first input. The first input provides the trigger signals or the convolve levels.

#### Count

Counts the number of times a channel crosses a trigger or release threshold. It operates in either static or realtime ("Cook to Current Frame") mode.

#### Cross

Is a multi input OP that blends between 2 inputs at a time. This is similar to a Switch CHOP however the Cross CHOP allows for interpolation between the inputs.

#### Cycle

Creates cycles. It can repeat the channels any number of times before and after the original. It can also make a single cycle have a smooth transition from its end to its beginning, so it loops smoothly.

#### DAT to

Will create a set of CHOP channels with values derived from a DAT.

#### Delay

Delays the input. Multiple channels can be fed in to delay each separately and each channels can have a separate delay time.

#### Delete

Removes entire channels and/or individual samples of its input. A first method uses a text string to select channels by name or number ranges.

#### Envelope

Outputs the maximum amplitude in the vicinity of each sample of the input. It takes the absolute value of the input, and uses a sliding window of a number of samples to find the maximum amplitude near each sample.

#### Expression

Allows you to modify input channels by using math expressions. Up to six expressions are available. Each input channel is modified by exactly one expression, and the expressions are looped for multiple channels.

#### Extend

Only sets the "extend conditions" of a CHOP, which determines what values you get when sampling the CHOP before or after its interval.

#### Fan

Converts one channel out to many channels, or converts many channels down to one. Its first operation, Fan Out, takes one channel and generates 2 or more channels.

#### Feedback

Stores channels from the current frame to be used in a later frame, without forcing recooking back one frame.

#### Filter

Smooths or sharpens the input channels. It filters by combining each sample and a range of its neighbor samples to set the new value of that sample.

#### Function

Provides more complicated math functions than found in the Math CHOP: trigonometic functions, logarithmic functions and exponential functions, and also audio decibels (dB)-power-amplitude conversions.

#### Gesture

Records a short segment of the first input and loops this segment in time with options as specified in the Gesture Page.

#### Hold

Waits for a 0 to 1 step on its second input, at which time it reads the current values from the first input (one value per channel).

#### Interpolate

Treats its multiple-inputs as keyframes and interpolates between them. The inputs are usually single-frame CHOP channels like those produced by a Constant CHOP.

#### Join

Takes all its inputs and appends one CHOP after another. It is expected they all have the same channels.

#### Lag

Adds lag and overshoot to channels. It can also limit the velocity and acceleration of channels. Lag slows down rapid changes in the input channels.

#### LFO

(low frequency oscillator) generates waves in real-time in two ways. It synthesizes curves using a choice of common waveforms like Sine or Pulse, or it repeats a prepared incoming curve.

#### Limit

Can limit the values of the input channels to be between a minimum and maximum, and can quantize the input channels in time and/or value such that the value steps over time.

#### Logic

First converts channels of all its input CHOPs into binary (0 = off, 1 = on) channels and then combines the channels using a variety of logic operations.

#### Lookup

Outputs values from a lookup table. The first input (the Index Channel) is an index into the second input (the Lookup Table).

#### Math

Performs arithmetic operations on channels. The channels of a CHOP can be combined into one channel, and several CHOPs can be combined into one CHOP.

#### Merge

Takes multiple inputs and merges them into the output. All the channels of the input appear in the output.

#### Noise

Makes an irregular wave that never repeats, with values approximately in the range -1 to +1. It generates both smooth curves and noise that is random each sample.

#### Override

Lets you take inputs from several CHOP sources, and uses the most-recently changed input channels to determine the output.

#### Parameter

Gets parameter values, including custom parameters, from all OP types. (In Build 46000 or later. This replaces the Fetch CHOP.)

#### Pattern

Generates a sequence of samples in a channel. Unlike the Wave CHOP its purpose is generating arrays of samples that have no reference to time (seconds or frames).

#### Pulse

Generates pulses in one channel at regular intervals. The amplitude of each pulse can be edited with the CHOP sliders or with handles on the graph.

#### Record

Takes the channels coming in the first (Position) input, converts and records them internally, and outputs the stored channels as the CHOP output.

#### Rename

Renames channels. Channels names from the input CHOP are matched using the From pattern, and are renamed to the corresponding name in the To pattern.

#### Reorder

Re-orders the first input CHOP's channels by numeric or alphabetic patterns. Either a channel pattern specifies the new order, or a number sequence specifies the new order.

#### Replace

Can be used to replace channels very quickly. The output of channels in Input1 will be replaced by channels found in Input2 if a matching channel exists in Input2.

#### Resample

Resamples an input's channels to a new sample rate and/or start/end interval. In all cases, the entire input interval is resampled to match the output interval.

#### Script

Runs a script each time the Script CHOP cooks. By default, the Script CHOP is created with a docked DAT that contains three Python methods: `cook`, `onPulse`, and `setupParameters`.

#### Select

Selects and renames channels from other CHOPs of any CHOP network. You can select the channels from control panel gadgets like sliders and buttons.

#### Shift

Time-shifts a CHOP, changing the start and end of the CHOP's interval. However, the contents of the channels remain the same.

#### Shuffle

Reorganizes the samples in a set of channels. It is useful for transforming data received by the SOP to CHOP and TOP to CHOPs into channels containing only one row or column.

#### Slope

Calculates the slope (or "derivative" in math-speak) of the input channels. If the input CHOP represents position, the slope can be interpreted as speed.

#### Sort

Re-orders the inputs channels samples by value or by random. Specifying a channel to be sorted will reorder all remaining channels samples according to the new order.

#### Speed

Converts speed (units per second) to distance (units) over a time range. More generally, you give it a rate (the CHOP input) and it outputs a cumulative value.

#### Spring

Creates vibrations influenced by the input channels, as if a mass was attached to a spring. It acts as if, for every channel, there is a mass at the end of a spring, affected by a distance from the actual position (the output of the channel at the previous frame) to the desired position (the input channel at the current frame).

#### Stretch

Preserves the shape of channels and the sampling rate, but resamples the channels into a new interval.

#### Switch

Allows you to control the flow of channels through a CHOPnet. It selects one of the input CHOPs by index and copies it exactly.

#### Timer

Is an engine for running timed processes. It outputs channels such as timing fractions, counters, pulses and timer states, and it calls python functions (callbacks) when various timing events occur.

#### Timeline

Outputs time-based CHOP channels for a specific component. The time channels are defined by a Time Component whose Path can be determined using the expression `timepath()`.

#### Time Slice

Outputs a time slice of samples. It is used to generate smooth in-betweens when TouchDesigner cannot cook/draw fast enough and keep up with the animation's frames per second.

#### Trail

Displays a history of its input channels back in time. A window of time is displayed from the current frame back in time, the size of this window is set by the Window Length parameter.

#### Transform

Takes translate, rotate, and/or scale channels and transforms them using the transform parameters in the CHOP.

#### Trigger

Starts an audio-style attack/decay/sustain/release (ADSR) envelope to all trigger pulses in the input channels.

#### Trim

Shortens or lengthens the input's channels. A part of the interval can be preserved or removed. If the channels are being lengthened, the extend conditions of the channel will be used to get the new values.

#### Warp

Time-warps the channels of the first input (the Pre-Warp Channels) using one warping channel in the second input (the Warp Curve).

#### Wave

Makes repeating waves with a variety of shapes. It is by default 10-seconds of 1-second sine waves, a total of 600 frames.

### File Operations

#### File In

Reads in channel and audio files for use by CHOPs. The file can be read in from disk or from the web.

#### File Out

Writes CHOP channel data out to `.chan` files. The data can be written out every frame or at intervals (set by the Interval parameter) into a log file.

### Generation

#### Event

Manages the birth and life of overlapping events triggered by devices like a MIDI keyboard. It can be seen as a simple particle system designed for MIDI keyboards.

### Logic & Math

### Network Communication

#### DMX In

Receives channels from DMX or Art-Net devices. Channel values for DMX are 0-255. **NOTE:** In TouchDesigner Non-commercial, the DMX Out CHOP is limited to 32 channels.

#### DMX Out

Sends channels to DMX or Art-Net devices. Channel values for DMX are 0-255. The first channel you send into the DMX Out will correspond to the first DMX address (DMX channel) As you add channels to the DMX Out, you will access the next DMX channels in order.

#### LTC In

Reads SMPTE timecode data encoded into an audio signal. Read the overview Linear Timecode. First bring the audio signal into CHOPs using an Audio Device In CHOP.

#### LTC Out

Outputs "linear timecode" which is a SMPTE timecode data encoded into an audio signal. See also Linear Timecode.

#### MIDI In

Reads Note events, Controller events, Program Change events, System Exclusive messages and Timing events from both MIDI devices and files.

#### MIDI In Map

See first the MIDI In DAT. The MIDI In Map CHOP reads in specified channels from the MIDI Device Mapper which prepares slider channels starting from s1, s2, etc.

#### MIDI Out

Sends MIDI events to any available MIDI devices when its input channels change. More flexibly, the Python MidioutCHOP Class can be used to send any type of MIDI event to a MIDI device via an existing MIDI Out CHOP.

#### OSC In

Is used to accept Open Sound Control Messages. OSC In can be used to accept messages from either a 3rd party application which adheres to the Open Sound Control specification.

#### OSC Out

Sends all input channels to a specified network address and port. Each channel name and associated data is transmitted together to the specified location.

#### Pipe In

Allows users to input from custom devices into CHOPs. It is implemented as a TCP/IP network connection.

#### Pipe Out

Can be used to transmit data out of TouchDesigner to other processes running on a remote machine using a network connection.

#### Serial

Is used for serial communication through an external port, using the RS-232 protocol. These ports are usually a 9 pin connector, or a USB port on new machines.

#### Sync In

And Sync Out CHOP are used to keep timelines in two or more TouchDesigner processes within a single frame of each other.

#### Sync Out

The Sync In CHOP and Sync Out CHOP are used to keep timelines in two or more TouchDesigner processes within a single frame of each other.

#### Touch In

Can be used to create a high speed connection between two TouchDesigner processes via CHOPs. Data is sent over TCP/IP.

#### Touch Out

Can be used to create high speed connection between two TouchDesigner processes. Data is sent over TCP/IP.

### Transform & Animation

### Utility

#### Hog

Eats up CPU cycles (ie it's a CPU hog - oink!). This can be used to simulate performance on slower machines, or to artifically slow down a synth's frame rate.

#### In

Gets channels that are connected to one of the inputs of the component. For each In CHOP inside a component, there is one input connector added to the In CHOP's parent component.

#### Null

Is used as a place-holder and does not alter the data coming in. It is often used to Export channels to parameters, which allows you to experiment with the CHOPs that feed into the Null without having to un-export from one CHOP and re-export from another.

#### Out

Sends CHOP data from inside a components to other components or CHOPs. It sends channels to one of the outputs of the component.

#### Perform

Outputs many channels like frames-per-second, describing the current state of the TouchDesigner process.

### Pro/Commercial Only

#### Audio SDI In

Is a TouchDesigner Pro only operator. The Audio SDI In CHOP can capture the audio from any SDI In TOP.

#### Clip

Is a TouchDesigner Pro only operator.

#### Clip Blender

Is a TouchDesigner Pro only operator. It can be used as an animation system that blends between different animation clips, preserving rotation, changing target positions etc.

#### CPlusPlus

Allows you to make custom CHOP operators by writing your own `.dll` using C++. **Note:** The CPlusPlus CHOP is only available in TouchDesigner Commercial and TouchDesigner Pro.

#### EtherDream

Takes as input up to five channels interpreted as X and Y (horizontal and vertical) position values in the first 2 channels, and red, green and blue color values in the next 3 channels.

#### Handle

Is the "engine" which drives Inverse Kinematic solutions using the Handle COMP. The role of the Handle CHOP is to generate rotation values for the bones which will bring their attached handles as close to their targets as possible.

#### Inverse Curve

Calculates an inverse kinematics simulation for bone objects using a curve object. The Inverse Curve CHOP will stretch and position a set of bones to follow a curve defined by another set of objects (guide).

#### Inverse Kin

Calculates an inverse kinematics simulation for Bone objects.

#### Joystick

Outputs values for all 6 possible axes on any game controller (joysticks, game controllers, driving wheels, etc.).

#### Keyframe

Uses channel and keys data in an Animation COMP and creates channels of samples at a selectable sample rate (frames per second).

#### Kinect

Reads positional and skeletal tracking data from the Kinect and Kinect2 sensors. Up to 6 people's full skeletons can be tracked (2 on the original Kinect), and the center position of an addition 4 people in the camera view is tracked as well.

#### Leap Motion

Reads hand, finger, tool and gesture data from the Leap Motion controller. It outputs hand, finger and tool positions, rotations and 'tracking' channels that indicate if these values are currently being detected and updated.

#### NatNet In

The NatNet In CHOP.

#### Object

Compares two objects and outputs channels containing their raw or relative positions and orientations.

#### Oculus Audio

Uses the Oculus Audio SDK to take a mono sound channel and create a spatialized stereo pair or channels for that sound.

#### Oculus Rift

Connects to an Oculus Rift device and outputs several useful sets of channels that can be used to integrate the Oculus Rift into projects.

#### Panel

Reads Panel Values from Panel Components into CHOP channels. Panel values can also be accessed by using the `panel()` expression.

#### RealSense

Receives positional data from Intel's RealSense camera. See also RealSense TOP. Available in builds 50000 or later.

#### Render Pick

Samples a rendering (from a Render TOP or a Render Pass TOP) and returns 3D information from the geometry at that particular pick location.

#### Scan

Converts a SOP or TOP to oscilloscope or laser friendly control waves. The output is usually in the audible range and can be heard directly via an Audio Device Out CHOP, or used to drive the X and Y deflector inputs of an oscilloscope, recreating the imagery.

#### Shared Mem In

Is only available in TouchDesigner Commercial and Pro. The Shared Mem In CHOP receives CHOPs from a shared memory segment that is attached to a Shared Mem Out CHOP in another process or the same process.

#### Shared Mem Out

The Shared Mem Out TOP is only available in TouchDesigner Commercial and Pro. The Shared Mem Out CHOP sends CHOPs to a shared memory segment that is attached to a Shared Mem In CHOP in another process or the same process.

#### SOP to

Uses a geometry object to choose a SOP from which the channels will be created. The channels are created from the point attributes of a SOP, such as the X, Y and Z of the point position.

#### TOP to

Converts pixels in a TOP image to CHOP channels. It generates one CHOP channel per scanline (row) in the image and per pixel color element (RGBA).

---

## COMP Operators (Components)

COMPs are containers and 3D scene objects that can hold other operators and define UI panels or 3D transformations.

### 3D Scene Objects

#### Ambient Light

The Ambient Light Component controls the color and intensity of the environmental light in a given scene.

#### Bone

The Bone Component is the foundation of all of the Character Tools. It is a Component with most of the properties of a Geometry Component.

#### Camera

The Camera Component is a 3D object that acts like real-world cameras. You view your scene through it and render from their point of view.

#### Camera Blend

The Camera Blend Component allows various effects by blending multiple Components together. It gives you some extra flexibility in setting up parent-child relationships.

#### Geometry

The Geometry Component is a 3D surface that you see and render in TouchDesigner with a Render TOP. Lights, cameras and other Components affect the scene, but are not visible surfaces.

#### Handle

The Handle Component is a new IK tool designed for manipulating groups of bones. Whereas the previous IK tools only allowed for a single end-affector per bone chain, this new method allows for several end-affectors per bone.

#### Light

The Light Components are objects which cast light into a 3D scene. With the light parameters you can control the color, brightness, and atmosphere of geometry lit by the light.

#### Null

The Null Component serves as a place-holder in a scene. It can be used to transform (translate, rotate, scale) Components attached to it.

### Panel Components

#### Button

The Button Component is used in panels to provide interactive on/off buttons, including toggle buttons, momentary buttons, and sets of radio buttons or exclusive buttons.

#### Container

The Container Component groups together any number of button, slider, field, container and other Panel Components to build an interface.

#### Field

The Field Component lets you enter text strings and renders text generated with the Text TOP. Internally it contains a Text TOP which points to one cell of a DAT that contains the text to render.

#### List

The List Component lets you create large lists that are highly customizable via the List COMPs initialization and callback functions.

#### OP Viewer

The OP Viewer Component allows any operator viewer (CHOP Viewer, SOP Viewer etc) to be part of a panel with full interactivity.

#### Select

The Select Component selects a Panel Component from any other location. This allows a panel to appear in multiple other panels.

#### Slider

The Slider Component lets you build sliders in X, Y and XY, and outputs 1 or 2 channels from a Panel CHOP placed in the Slider component.

#### Table

The Table Component creates a grid of user interface gadgets. These panels are laid out in a grid format where the contents of each cell are defined by DAT tables.

#### Window

The Window Component allows you to create and maintain a separate floating window displaying the contents of any Panel or any other Node Viewer.

### System Components

#### Animation

The Animation Component is a special component used for creating keyframe animation channels. The component contains a pre-defined network utilizing a Keyframe CHOP and a number of Table DATs to define the animated CHOP channels.

#### Base

The Base Component has no panel parameters and no 3D object parameters. You would use it for a component that has no panel associated with it, nor any 3D, such as component that converted RGB channels to HSV channels.

#### Blend

The Blend Component allows various effects such as blended inputs, animating the parents of Components, sequencing, partial transformation inheritance, three-point orientation, and other effects.

#### Engine

The Engine Component runs a `.tox` file (component) in a separate process.

#### Replicator

The Replicator Component creates a node for every row of a table, creating nodes ("replicants") and deleting them as the table changes.

#### Time

The Time Component allows each component to have its own timeline (clock). The Time Component contains a network of operators that can drive a Timeline, drive animations in Animation COMPs, or be used to drive any custom time-based system.

### Pro/Commercial Only

#### Shared Mem In

Is only available in TouchDesigner Commercial and Pro. The Shared Mem In COMP will read transform data from a shared memory block.

#### Shared Mem Out

The Shared Mem In TOP is only available in TouchDesigner Commercial and Pro. The Shared Mem Out COMP will write transform data to a shared memory block.

---

## TOP Operators (Texture Operators)

TOPs work with 2D images and textures, handling everything from image processing to video input/output.

### Compositing

#### Add

Composites the input images together by adding the pixel values. `Output = Input1 + Input2`. It clamps a color channel if the sum exceeds 1.

#### Composite

Is a multi-input TOP that will perform a composite operation for each input. Select the composite operation using the Operation parameter on the Composite parameter page.

#### Difference

Performs a difference composite on its two input images.

#### Inside

Places Input1 'inside' Input2. The alpha of Input2 is used to determine what parts of the Input1 image are visible.

#### Matte

Composites input1 over input2 using the alpha channel of input3 as a matte. White (one) pixels in input3's alpha channel will draw input1 over input2, black (or zero) will make input1 transparent, leaving the input2 image at that pixel.

#### Multiply

Performs a multiply operation on Input1 and Input2.

#### Outside

Places Input1 'outside' Input2. Input1 is visible in the output wherever Input2's alpha is <1. This is the opposite operation to the Inside TOP.

#### Over

Places Input1 'over' Input2. The alpha of Input1 is used to determine what parts of the Input2 image are visible in the result.

#### Screen

Brightens the underlying layers depending on how bright the screened layer's pixels are. If the screened pixel is black, it will look completely transparent.

#### Subtract

Composites the input images together by subtracting the pixel values. `Output = Input1 - Input2`. The pixel values below 0 are clammped to 0.

#### Under

Places Input1 'under' Input2. The alpha of Input2 is used to determine what parts of the Input1 image are visible in the result.

### Effects & Filters

#### Blur

Blurs the image with various kernel filters and radii. It can do multi-pass blurs and can do horizontal-only or vertical-only blurs.

#### Channel Mix

Allows mixing of the input RGBA channels to any other color channel of the output. For example, the pixels in the blue channel of the input can be added to the output's red channel, added or subtracted by the amount in Red parameter's blue column.

#### Chroma Key

Pulls a key matte from the image using Hue, Saturation, and Value settings. If a pixel falls between the Min and Max parameters for all three settings, then it is included in the key.

#### Convolve

Uses a DAT table containing numeric coefficients. For each pixel, it combines its RGBA values and it's neighboring pixels' RGBA values by multiplying the values by the corresponding coefficients in the table, adding the results together.

#### Displace

Will cause one image to be warped by another image. A pixel of the output image at (Uo,Vo) gets its RGBA value from a different pixel (Ui, Vi) of the Source Image by using the second input image (the Displace Image).

#### Edge

Finds edges in an image and highlights them. For each pixel, it looks at the values at neighboring pixels, and where differences are greater than a threshold, the output's value is higher.

#### Emboss

Creates the effect that an image is embossed in a thin sheet of metal. Edges in the image will appear raised.

#### HSV Adjust

Adjust color values using hue, saturation, and value controls. If you change the Hue Offset, Saturation Multiplier and Value Multiplier without changing any of the other parameters then you will modify the color of all pixels in the image.

#### HSV to RGB

Converts an image from HSV color channels to RGB color channels.

#### Level

Adjusts image contrast, brightness, gamma, black level, color range, quantization, opacity and more.

#### Limit

Provides multiple methods of clamping the pixel values of the input image to fall between given minimum and maximum values and can quantize the pixels by value or position.

#### Lookup

Replaces color values in the TOP image connected to its first input with values derived from a lookup table created from its second intput or a lookup table created using the CHOP parameter.

#### Luma Blur

Blurs image on a per-pixel basis depending on the luminance or greyscale value of its second input. The image is blurred with separate parameters for white and black filter sizes, which correspond to the white and black luminance values of the second input.

#### Luma Level

Adjusts image brightness, gamma, black level, quantization, opacity and more. It has similar parameters to the Level TOP, but it maintains the hue and saturation more accurately when you use Gamma and Black Level.

#### Math

Performs specific mathematical operations on the pixels of the input image.

#### Monochrome

Changes an image to greyscale colors. You can choose from a number of different methods to convert the image to greyscale using the RGB and Alpha menus.

#### Normal Map

Takes an input image and creates a normal map by finding edges in the image. This can then be used for bump mapping (See Phong MAT).

#### RGB Key

Pulls a key from the image using Red, Green, and Blue channel settings. If a pixel falls between the Min and Max parameters for all three settings, then it is included in the key.

#### RGB to HSV

The RGV to HSV TOP converts the image from RGB to HSV colorspace. The R channel becomes Hue, the G channel becomes Saturation, and the B channel becomes Value.

#### Slope

Generates pixels that represent the difference between its value and its neighbouring pixels' values.

#### Threshold

Creates a matte with pixel values set to 0 for pixels below the threshold value, and 1 for pixels greater than or equal to the threshold value.

### Generation

#### Circle

Can be used to generate circles, ellipses and N-sided polygons. The shapes can be customized with different sizes, rotation and positioning.

#### Constant

Sets the red, green, blue, and alpha (r, g, b, and a) channels individually. It is commonly used to create a solid color TOP image.

#### Noise

Generates a variety of noise patterns including sparse, alligator and random. It currently runs on the CPU and passes its images to the GPU.

#### Ramp

Allows you to interactively create vertical, horizontal, radial, and circular ramps. Using the ramp bar and the color picker, you can add as many color tabs to the ramp as you like, each with its own color and alpha values.

#### Rectangle

Can be used to generate Rectangles with rounded corners. The shapes can be customized with different sizes, rotation and positioning.

#### Text

Displays text strings in an image. It allows for multiple fonts, sizes, colors, borders, character separation and line separation.

### Input/Output

#### Movie File In

Loads movies, still images, or a sequence of still images into TOPs. It will read images in `.jpg`, `.gif` formats.

#### Movie File Out

Saves a TOP stream out to a QuickTime or MP4 (`.mp4`) movie in a variety of formats, plus the Animation, Cineform and Hap Q video codecs.

#### Point File In

Loads 3D point data into TOPs from either a single file or a sequence of files. Points are composed of one or more floating point values such as XYZ positions, RGB color values, 3D normals, scanner intensity, etc. Supports OBJ, PLY, EXR, PTS, and more.

#### Point File Select

Creates additional output images from a point file loaded into a Point File In TOP. Useful when the point data file has more than 4 channels e.g. XYZ position and RGB colors.

#### Screen Grab

Turns the main screen output into a TOP image. It can be captured in real-time while you work.

#### Video Device In

Can be used to capture video from an external camera, capture card, or DV decoder connected to the system.

#### Video Stream In

Creates an RTSP client to receive video and audio across the network. The URL to connect to the RTSP server is in the form: `rtsp://<ipaddress>:<port>/<streamName>`.

#### Video Stream Out

Creates an RTSP server to send H.264 video and MP3 audio across the network. It uses Nvidia's hardware H264 encoder to achieve low-latency encoding.

### Network Communication

#### DirectX In

Brings DirectX textures from other applications into TouchDesigner. This feature is only available on Windows 7 or greater, accessed through the DirectX Sharing Resources feature.

#### DirectX Out

Creates textures that a DirectX application can access, or any instance of TouchDesigner with a DirectX In TOP.

#### Spout In

Will obtain its texture image via shared memory from other applications that support the Spout framework.

#### Spout Out

Will share its input texture with other applications that support the Spout framework. You can download a Spout setup package at <http://spout>.

#### Touch In

Will read in image data send over a TCP/IP network connection from a Touch Out TOP. The other TouchDesigner process can be on the same computer or from another computer anywhere on the connected network.

#### Touch Out

Sends a TOP image stream over TCP/IP to a Touch In TOP. The Touch In TOP can be in another TouchDesigner session on the same computer or on a computer anywhere on the connected network.

### Rendering

#### Cube Map

Builds a texture map in the Cube Map internal texture format. It accepts a vertical cross image, or 1 input per side of the cube.

#### Depth

Reads an image containing depth information from a scene described in a specified Render TOP. The resulting image is black (0) at pixels where the surface is at the near depth value (Camera's parameter "Near").

#### OP Viewer

Can display the Node Viewer for any other operator as a TOP image. If the operator source is a Panel Component, panel interaction through the TOP image is also supported.

#### Projection

Takes a Cube Map created with a Render TOP and converts that to a fisheye projection suitable for domes, and a "equirectangular" projection, where u-v is latitude-longitude, suitable for spheres.

#### Render

Is used to render all 3D scenes in TouchDesigner. You need to give it a Camera object and a Geometry object as a minimum.

#### Render Pass

Is used along with a Render TOP to achieve multipass rendering. It can build upon its inputs render by using the existing depth/color information in the framebuffers, or it can optionally clear one or both of the depth/color buffers before it does its render.

#### Render Select

Allows you to select one of the color buffers from any Render TOP.

#### SSAO

Performs Screen Space Ambient Occlusion on the output of a Render TOP or Render Pass TOP. Because this technique requires access to the Depth Buffer, no other TOP can be in between the Render/RenderPass TOP and the SSAO TOP.

#### Texture 3D

Creates a 3D texture map. It saves a series of images in one array of pixels. This TOP can be used with Time Machine TOP, as well as materials.

#### Time Machine

Combines pixels in a sequence of images stored in a Texture 3D TOP. Whereas "morphing" warps an image "spatially" (in xy), Time Machine warps images only in time.

### Utility

#### Analyze

Takes any image and determines various characteristics of it, such as the average pixel color, or the pixel with the maximum luminance.

#### Blob Track

Is implemented using source code from OpenCV, much of which was ported to the GPU for faster performance.

#### Cache

Stores a sequence of images into GPU memory. These cached images can be read by the graphics card much faster than an image cache in main memory or reading images off disk.

#### Cache Select

Grabs an image from a Cache TOP based on the index parameter. This gives direct, random access to any image stored in a Cache TOP.

#### CHOP to

Puts CHOP channels into a TOP image. The full 32-bit floating point numbers of a CHOP are converted to 32-bit floating point pixel values by setting the TOP's Pixel Format to 32-bit floats.

#### Corner Pin

Can perform two operations. The Extract page lets you specify a sub-section of the image to use by moving 4 points.

#### Crop

Crops an image by defining the position of the left, right, bottom, and top edges of the image. The cropped part of the image is discarded, thus reducing the resolution of the image.

#### Cross

Blends between the two input images based on the value of the Cross parameter (refered to as Cross_value below).

#### Feedback

Can be used to create feedback effects in TOPs. The Feedback TOP's input image will be passed through whenever Feedback is bypassed (by setting the Bypass Feedback parameter = 1).

#### Fit

Re-sizes its input to the resolution set on the Common Page using the method specified in the Fit parameter menu.

#### Flip

Will Flip an image in X and/or Y. It also offers a Flop option to turn each row of pixels into a column.

#### GLSL

Renders a GLSL shader into a TOP image. Use the Info DAT to check for compile errors in your shaders.

#### GLSL Multi

Renders a GLSL shader into a TOP image. Its parameters and functionality are identical to the [GLSL TOP].

#### In

Is used to create a TOP input in a Component. Component inputs are positioned alphanumerically on the left side of the Component.

#### Null

Has no effect on the image. It is an instance of the TOP connected to its input. The Null TOP is often used when making reference to a TOP network, allowing new TOPs to be added to the network (upstream) without the need to update the reference.

#### Out

Is used to create a TOP output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.

#### Pack

**Note:** Only in builds 48000 or later.

#### Point Transform

Treats the RGB values of the input image as a point cloud of XYZ positions or vectors and performs 3D transformations and alignments.

#### Remap

Uses the second input to warp the first input. For every pixel of the output, it uses the red channel and green channel of the second input to choose which pixel to pick from the first input.

#### Reorder

Is a multi-input TOP which lets you choose any of the input channels for the R, G, B, and A output. It also gives the option of outputting one, zero or the input luminance to any of the output channels.

#### Resolution

Changes the resolution of the TOP image. This can also be done on the Common page of most other TOPs.

#### Select

Allows you to reference a TOP from any other location in TouchDesigner. To save graphics memory, the Select TOP creates an instance of the TOP references.

#### Switch

Is a multi-input operator which lets you switch which input is passed through using the Input parameter.

#### Tile

Tiles images in a repeating pattern. It also has a Crop option which crops an image by defining the position of the left, right, bottom, and top edges of the image.

#### Transform

Applies 2D transformations to a TOP image like translate, scale, rotate, and multi-repeat tiling. The background can be filled with solid color and alpha.

### Pro/Commercial Only

#### Anti Alias

The Anti-Alias TOP uses a screen space antialiasing technique called `SMAA: Enhanced Subpixel Morphological Antialiasing`.

#### CPlusPlus

Allows you to make custom TOP operators by writing your own `.dll` using C++. **Note:** The CPlusPlus TOP is only available in TouchDesigner Commercial and TouchDesigner Pro.

#### CUDA

Runs a CUDA program on a NVIDIA GPU (8000 series and later, full list here). The use a CUDA TOP, you'll need to write a CUDA DLL.

#### Kinect

Captures video from the Kinect depth camera or RGB color camera. **NOTE:** This TOP works with the Kinect for Windows hardware and supports the Kinect2.

#### Leap Motion

Gets the image from the Leap Motion Controller's cameras. To enable this feature the option Allow Images must be turned on in the Leap Motion Control Panel.

#### Oculus Rift

**Note** - The Oculus SDK has changed a lot over since the DK1. The original DK1 used the Oculus Rift TOP to do the barrel distortion.

#### Photoshop In

Can stream the output from Photoshop CS6 into TouchDesigner. Photoshop can be running on the same computer as TouchDesigner or any other computer on the network.

#### RealSense

Connects to RealSense devices and outputs color, depth and IR data from it. See also RealSense CHOP.

#### Scalable Display

Lets you load calibration data retrieved from running the Scalable Display Calibration Software. Please refer to How-to calibrate your projector with Scalable Displays for a complete guide on TouchDesigners integration of the Scalable Displays SDK.

#### SDI In

Is a TouchDesigner Pro only operator. The SDI In TOP uses NVIDIA's SDI Capture Card to capture video frames directly into GPU memory.

#### SDI Out

Is a TouchDesigner Pro only operator. The SDI Out TOP uses Nvidia's SDI Output card to output video frames directly to the output card, avoid any issues involved with Windows such as vsync, desktop tearing etc.

#### SDI Select

The SDI In TOP is a TouchDesigner Pro only operator. The SDI Select TOP is used to select video from the 2-4 inputs in the SDI In TOP on the Nvidia SDI Capture card.

#### Shared Mem In

Is only available in TouchDesigner Commercial and Pro. The Shared Mem In TOP will read image data from a shared memory block.

#### Shared Mem Out

Is only available in TouchDesigner Commercial and Pro. The Shared Mem Out TOP will write image data out to a shared memory block for use by other TouchDesigner processes or other 3rd party applications.

#### Video Device Out

Routes video to output devices using their native driver libraries. Devices currently supported: Blackmagic Design devices The Video Device Out TOP is only available in Commercial and Pro.

---

## MAT Operators (Materials)

MATs define the surface properties and shading of 3D geometry.

#### Constant

Renders a constant color on a material. To apply a texture, use a Phong MAT and set the color for Diffuse and Specular parameters to (0,0,0), then use the Emit parameters to set color, and the Color Map if you want to apply a texture.

#### CPlusPlus

Allows you to make custom MAT operators by writing your own `.dll` using C++. **Note:** The CPlusPlus MAT is only available in TouchDesigner Commercial and TouchDesigner Pro.

#### Depth

The Depth Only MAT can be used to prevent objects from being drawn by making an invisible barrier in Z.

#### GLSL

Allows you to write or import custom materials into TouchDesigner. When there are compile errors in a GLSL shader, a blue/red checkerboard error shader will be displayed.

#### Null

Doesn't do much but comes in handy when building networks.

#### Phong

Creates a material using the Phong Shading model. It has support for textures, reflections, bumps, cone lights, rim lights, alpha maps and more.

#### Point Sprite

Allows you to control some attributes of Point Sprites (creatable using the Particle SOP or DAT to SOP).

#### Select

Grabs another material from any location in the project.

#### Switch

Allows switching between multiple material inputs.

#### Wireframe

Renders the edges of polygons and curves as lines.

---

## SOP Operators (Surface Operators)

SOPs work with 3D geometry, handling modeling, animation, and procedural generation of surfaces and curves.

### Creation & Generation

#### Add

Can both create new Points and Polygons on its own, or it can be used to add Points and Polygons to an existing input.

#### Box

Creates cuboids. These can be used as geometries by themselves, or they can be sub-divided for use with the Lattice SOP.

#### Circle

Creates open or closed arcs, circles and ellipses. If two NURBS circles that are non-rational (i.e. their X and Y radii are unequal) are skinned, more isoparms may be generated than expected.

#### Font

Allows you to create text in your model from Adobe Type 1 Postscript Fonts. To install fonts, copy the font files to the `$TFS/touch/fonts` directory of your installation path.

#### Grid

Allows you to create grids and rectangles using polygons, a mesh, Bzier and NURBS surfaces, or multiple lines using open polygons.

#### Iso Surface

Uses implicit functions to create 3D visualizations of isometric surfaces found in Grade 12 Functions and Relations textbooks.

#### Line

Creates straight lines.

#### LSystem

The Lsystem SOP implements L-systems (Lindenmayer-systems, named after Aristid Lindenmayer (1925-1989)), allow definition of complex shapes through the use of iteration.

#### Metaball

Creates metaballs and meta-superquadric surfaces. Metaballs can be thought of as spherical force fields whose surface is an implicit function defined at any point where the density of the force field equals a certain threshold.

#### Rectangle

Creates a 4-sided polygon. It is a planar surface.

#### Sphere

Generates spherical objects of different geometry types. It is capable of creating non-uniform scalable spheres of all geometry types.

#### Superquad

Generates an isoquadric surface. This produces a spherical shape that is similar to a metaball, with the difference that it doesn't change it's shape in response to what surrounds it.

#### Text

Creates text geometry from any TrueType font that is installed on the system, or any TrueType font file on disk.

#### Torus

Generates complete or specific sections of torus shapes (like a doughnut).

#### Tube

Generates open or closed tubes, cones, or pyramids along the X, Y or Z axes. It outputs as meshes, polygons or simply a tube primitive.

### Deformation & Animation

#### Blend

Provides 3D metamorphosis between shapes with the same topology. It can blend between sixteen input SOPs using the average weight of each input's respective channel.

#### Clay

Deforms faces and surfaces by pulling points that lie directly on them. As opposed to the Point SOP or other SOPs that manipulate control points (CVs), the Clay SOP operates on the primitive contours themselves, providing a direct, intuitive, and unconstrained way of reshaping geometry.

#### Creep

Lets you deform and animate Source Input geometry along the surface of the PathInput geometry.

#### Fractal

Allows you created jagged mountain-like divisions of the input geometry. It will create random-looking deviations and sub-divisions along either a specified normal vector (the Direction xyz fields) or the vertex normals of the input geometry.

#### Lattice

Allows you to create animated deformations of its input geometry by manipulating grids or a subdivided box that encloses the input source's geometry.

#### Magnet

Allows you to affect deformations of the input geometry with another object using a "magnetic field" of influence, defined by a metaball field.

#### Noise

Displaces geometry points using noise patterns. It uses the same math as the Noise CHOP.

#### Particle

Is used for creating and controlling motion of "particles" for particle systems simulations. Particle systems are often used to create simulations of natural events such as rain and snow, or effects such as fireworks and sparks.

#### Point

Allows you to get right down into the geometry and manipulate the position, color, texture coordinates, and normals of the points in the Source, and other attributes.

#### Spring

Deforms and moves the input geometry using spring "forces" on the edges of polygons and on masses attached to each point.

#### Trail

Takes an input SOP and makes a trail of each point of the input SOP over the past several frames, and connects the trails in different ways.

#### Transform

Translates, rotates and scales the input geometry in "object space" or local to the SOP. The Model Editor and the Transform SOP both work in "object space", and change the X Y Z positions of the points.

#### Twist

Performs non-linear deformations such as bend, linear taper, shear, squash and stretch, taper and twist.

### File Operations

#### File In

Allows you to read a geometry file that may have been previously created in the Model Editor, output geometry from a SOP, or generated from other software such as Houdini.

### Geometry Processing

#### Align

Aligns a group of primitives to each other or to an auxiliary input, by translating or rotating each primitive along any pivot point.

#### Attribute Create

Allows you to add normals or tangents to geometry.

#### Attribute

Allows you to manually rename and delete point and primitive attributes.

#### Basis

Provides a set of operations applicable to the parametric space of spline curves and surfaces. The parametric space, also known as the "domain" of a NURBS or Bzier primitive, is defined by one basis in the U direction and, if the primitive is a surface, another basis in the V direction.

#### Boolean

Takes two closed polygonal sets, A and B. Set these Sources to the SOPs with the 3D shapes that you wish to operate on.

#### Bridge

Is useful for skinning trimmed surfaces, holes, creating highly controllable joins between arms and body, branches or tube intersections.

#### Cap

Is used to close open areas with flat or rounded coverings. Meshes are capped by extending the mesh in either the U or V direction.

#### Carve

Works with any face or surface type, be that polygon, Bzier, or NURBS. It can be used to slice a primitive, cut it into multiple sections, or extract points or cross-sections from it.

#### Clip

Cuts and creases source geometry with a plane.

#### Convert

Converts geometry from one geometry type to another type. Types include polygon, mesh, Bezier patche, particle and sphere primitive.

#### Delete

Deletes input geometry as selected by a group specification or a geometry selection by using either of the three selection options: by entity number, by a bounding volume, and by entity (primitive/point) normals.

#### Divide

Divides incoming polygonal geometry. It will smooth input polygons, dividing polygons, as well as sub-divide input polygons using the Bricker option.

#### Extrude

Can be used for: Extruding and bevelling Text and other geometry Cusping the bevelled edges to get sharp edges Making primitives thicker or thinner In order to do so, it uses the normal of the surface to determine the direction of extrusion.

#### Facet

Lets you control the smoothness of faceting of a given object. It also lets you consolidate points or surface normals.

#### Fillet

Is used to create smooth bridging geometry between two curves / polygons or two surfaces / meshes. Filleting creates a new primitive between each input pair and never affects the original shapes.

#### Fit

Fits a Spline curve to a sequence of points or a Spline surface to an m X n mesh of points. Any type of face or surface represents a valid input.

#### Force

Adds force attributes to the input metaball field that is used by either Particle SOP or Spring SOP as attractor or repulsion force fields.

#### Group

Generates groups of points or primitives according to various criteria and allows you to act upon these groups.

#### Hole

Is for making holes where faces are enclosed, even if they are not in the same plane. It can also remove existing holes from the input geometry.

#### Join

Connects a sequence of faces or surfaces into a single primitive that inherits their attributes. Faces of different types can be joined together, and so can surfaces.

#### Joint

Will aid in the creation of circle-based skeletons by creating a series of circles between each pair of input circles.

#### Material

Allows the assignment of materials (MATs) to geometry at the SOP level. **Note:** The Material parameter in Object Components will override material attributes assigned to geometry using the Material SOP.

#### Merge

Merges geometry from multiple SOPs.

#### Polyloft

Generates meshes of triangles by connecting (i.e. lofting/stitching) the points of open or closed faces without adding any new points.

#### Polypatch

Creates a smooth polygonal patch from a mesh primitive or a set of faces (polygons, NURBS or Bezier curves).

#### Polyreduce

Reduces a high detail polygonal model into one consisting of fewer polygons. The second input's polygons represent feature edges.

#### Polyspline

Fits a spline curve to a polygon or hull and outputs a polygonal approximation of that spline. You can choose either to create divisions between the original points, or to ignore the position of the original points and divide the shape into segments of equal lengths.

#### Polystitch

Attempts to stitch polygonal surfaces together, thereby eliminating cracks that result from evaluating the surfaces at differing levels of detail.

#### Primitive

Is like the Point SOP but manipulates a primitive's position, size, orientation, color, alpha, in addition to primitive-specific attributes, such as reversing primitive normals.

#### Profile

Enables the extraction and manipulation of profiles. You will usually need a Trim SOP, Bridge SOP, or Profile SOP after a Project SOP.

#### Project

Creates curves on surface (also known as trim or profile curves) by projecting a 3D face onto a spline surface, much like a light casts a 2D shadow onto a 3D surface.

#### Rails

Generates surfaces by stretching cross-sections between two rails. This is similar to the Sweep SOP, but it gives more control over the orientation and scaling of the cross-sections.

#### Ray

Is used to project one surface onto another. Rays are projected from each point of the input geometry in the direction of its normal.

#### Refine

Allows you to increase the number of CVs in any NURBS, Bzier, or polygonal surface or face without changing its shape.

#### Resample

Will resample one or more primitives into even length segments. It only applies to polygons so when presented with a NURBS or Bzier curve input, it first converts it to polygons using the Level of Detail parameter.

#### Revolve

Revolves faces to create a surface of revolution. The revolution's direction and origin are represented by guide geometry that resembles a thick line with a cross hair at the centre.

#### Sequence Blend

Allows you do 3D Metamorphosis between shapes and Interpolate point position, colors, point normals, and texture coordinates between shapes.

#### Skin

Takes any number of faces and builds a skin surface over them. If given two or more surfaces, however, the SOP builds four skins, one for each set of boundary curves.

#### Sort

Allows you to sort points and primitives in different ways. Sometimes the primitives are arranged in the desired order, but the point order is not.

#### Stitch

Is used to stretch two curves or surfaces to cover a smooth area. It can also be used to create certain types of upholstered fabrics such as cushions and parachutes.

#### Subdivide

Takes an input polygon surface (which can be piped into one or both inputs), and divides each face to create a smoothed polygon surface using a Catmull-Clark subdivision algorithm.

#### Surfsect

Performs boolean operations with NURBS and Bezier surfaces, or only generates profiles where the surfaces intersect.

#### Sweep

Sweeps primitives in the Cross-section input along Backbone Source primitive(s), creating ribbon and tube-like shapes.

#### Texture

Assigns texture UV and W coordinates to the Source geometry for use in texture and bump mapping. It generates multi-layers of texture coordinates.

#### Trim

Cuts out parts of a spline surface, or uncuts previously cut pieces. When a portion of the surface is trimmed, it is not actually removed from the surface; instead, that part is made invisible.

#### Tristrip

Convert geometry into triangle strips. Triangle strips are faster to render than regular triangles or quads.

#### Vertex

Allows you to edit/create attributes on a per-vertex (rather than per-point) basis. It is similar to the Point SOP in this respect.

#### Wireframe

Converts edges to tubes and points to spheres, creating the look of a wire frame structure in renderings.

### Modeling Tools

#### Bone Group

Groups primitives by common bones (shared bones). For more information regarding using Bone Groups for deforming geometry, see this article: Deforming_Geometry_(Skinning).

#### Cache

Collects its input geometry in a cache for faster random-access playback of multiple SOPs. It should be used when cook times for a chain of SOPs is long and a quicker playback is needed.

#### Capture Region

Defines capture region (cregion), which is a type of primitive which can be thought of as a modified tube primitive (a tube with half a sphere on either end).

#### Capture

Is used to weight points in a geometry to capture regions. The weighting scheme is described in the next section, Capture Region SOP.

#### Copy

Lets you make copies of the geometry of other SOPs and apply a transformation to each copy. It also allows you to copy geometry to points on an input template.

#### Curveclay

Is similar to the Clay SOP in that you deform a spline surface not by modifying the CVs but by directly manipulating the surface.

#### Curvesect

Finds the intersections or the points of minimum distance between two or more faces (polygons, Bziers, and NURBS curves) or between faces and a polygonal or spline surface.

#### Deform

Takes geometry along with point weights (assigned by the Capture SOP) and deforms geometry as Capture Regions are moved.

#### LOD

Is unusual in so far as it does not actually alter any geometry. Instead it builds a level of detail cache for the input object.

#### Model

Holds the surface modeler in TouchDesigner. It is designed to hold raw model geometry constructed using the SOP Editor (aka Modeler).

#### Object Merge

Allows you to merge the geometry of several SOPs spanning different components.

#### Script

Runs a script each time the Script SOP cooks. By default, the Script SOP is created with a docked DAT that contains three Python methods: `cook`, `onPulse`, and `setupParameters`.

#### Trace

Reads an image file and automatically traces it, generating a set of faces around areas exceeding a certain brightness threshold.

### Utility

#### Arm

Creates all the necessary geometry for an arm, and provides a smooth, untwisted skin that connects the arm to the body.

#### CHOP to

Takes CHOP channels and generates 3D polygons in a SOP. It reads sample data from a CHOP and converts it into point positions and point attributes.

#### DAT to

Can be used to create geometry from DAT tables, or if a SOP input is specified, to modify attributes on existing geometry.

#### In

Creates a SOP input in a Component. Component inputs are positioned alphanumerically on the left side of the node.

#### Inverse Curve

Takes data from an Inverse Curve CHOP and builds a curve from it.

#### Limit

Creates geometry from samples fed to it by CHOPs. It creates geometry at every point in the sample.

#### Line Thick

Extrudes a surface from a curved line. The line can be of polygon, NURBS, or Bezier geometry type.

#### Null

Has no effect on the geometry. It is an instance of the SOP connected to its input. The Null SOP is often used when making reference to a SOP network, allowing new SOPs to be added to the network (upstream) without the need to update the reference.

#### Out

Is used to create a SOP output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.

#### Select

Allows you to reference a SOP from any other location in TouchDesigner. To save memory, the Select SOP creates an instance of the SOP references.

#### Sprite

Creates geometry (quad sprites) at point positions defined by the CHOP referenced in the XYZ CHOP parameter.

#### Switch

Switches between up to 9999 possible inputs. The output of this SOP is specified by the Select Input field.

---

## DAT Operators (Data Operators)

DATs handle text data, tables, and scripting functionality in TouchDesigner.

### Data Processing

#### Convert

Changes the text format from simple text to table form and vice-versa.

#### Evaluate

Changes the cells of the incoming DAT using string-editing and math expressions. It outputs a table with the same number of rows and columns.

#### FIFO

The FIFO DAT maintains a user-set maximum number of rows in a table. You add rows using the `appendRow()` method found in DAT Class. When its capacity is reached, the first row is removed. After the maximum number of rows is reached, the oldest row is discarded when a new row is added.

#### Indices

Creates a series of numbers in a table, ranging between the start and end values. These values are suitable for display along a graph horizontal or vertical axis.

#### Insert

Allows you to insert a row or column into an existing table. If the input DAT is not a table, it will be converted to a table.

#### Merge

The Merged DAT is a multi-input DAT which merges the text or tables from the input DATs together.

#### Reorder

Allows you to reorder the rows and columns of the input table. You can also use In Specified Order option to get duplicate copies of rows and columns.

#### Sort

Will sort table DAT data by row or column.

#### Substitute

Changes the cells of the incoming DAT using pattern matching and substitution strings. It outputs a table with the same number of rows and columns.

#### Transpose

Converts rows into columns. The number of rows becomes the number of columns, and vice versa.

### Execution & Scripting

#### CHOP Execute

Will run its script when the values of a specified CHOP change. You can specify which channels to look at, and trigger based on their values changing in various ways.

#### DAT Execute

Monitors another DAT's contents and runs a script when those contents change. The other DAT is usually a table.

#### Execute

Lets you edit scripts and run them based on conditions. It can be executed at the start or end of every frame, or at the start or end of the TouchDesigner process.

#### OP Execute

Runs a script when the state of an operator changes. OP Execute DATs are created with default python method placeholders.

#### Panel Execute

Will run its script when the values of a specified panel component changes. You can specify which Panel Values to monitor, and trigger scripts based on their values changing in various ways.

#### Parameter Execute

The Parm Execute DAT runs a script when a parameter of any node changes state. There are 4 ways a parameter can trigger the script: if its value, expression, export, or enable state changes.

#### Script

Runs a script each time the Script DAT cooks. By default, the Script DAT is created with a docked DAT that contains three Python methods: `cook`, `onPulse`, and `setupParameters`.

### File Operations

#### File In

Reads in `.txt` text files and `.dat` table files. It will attempt to read any other file as raw text. The file can be located on disk or on the web.

#### File Out

Allows you to write out DAT contents to a `.dat` file or a `.txt` file. A `.dat` file is one of the File Types of TouchDesigner that is used to hold the arrays of the Table DAT.

#### Folder

Lists the files and subfolders found in a file system folder and monitors any changes. For each item found, a row is created in the table with optional columns for the following information: Name Extension Type Size Depth Folder Path Date Created Date Modified.

#### Web

Fetches pages of data from a web connection. The data should be ASCII-readable. The Web DAT will automatically uncompress any gzip compressed page transfers.

#### XML

Can be used to parse arbitrary XML and SGML/HTML formatted data. Once formatted, selected sections of the text can be output for further processing.

### Input/Output

#### In

Is used to create a DAT input in a Component. Component inputs are positioned alphanumerically on the left side of the Component.

#### Out

Is used to create a DAT output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.

### Network Communication

#### OSC In

Receives and parses full Open Sound Control packets using UDP. Each packet is parsed and appended as a row in the DAT's table.

#### OSC Out

Is used for sending information over a OSC connection between remotely located computers. Use the send Command to initiate the data output.

#### Serial

Is used for serial communication through an external port, using the RS-232 protocol. These ports are usually a 9 pin connector, or a USB port on new machines.

#### TCP/IP

Is used for sending and receiving information over a TCP/IP connection between two remotely located computers.

#### Touch In

Receives full tables across the network from the Touch Out DAT, as opposed to messages with the other network based DATs.

#### Touch Out

Sends full DAT tables across the network to the Touch In DAT in another TouchDesigner process, as opposed to messages with the other network based DATs.

#### TUIO In

Receives and parses TUIO messages (received over network) into columns in the table. TUIO packets OSC bundles, so TUIO data can also be viewed in it's more raw form in an OSC In DAT.

#### UDP In

Is used for receiving information over a UDP connection between two remotely located computers. It captures all the messages without any queuing or buffering, and allows you to send it any messages you want.

#### UDP Out

Is used to send information over a UDP connection to/from a remotely-located computer. Use the send Command in a DAT script or the textport to initiate the data output.

#### UDT In

Is used for receiving information over a UDT connection between two remotely located computers. It captures all the messages without any queuing or buffering, and allows you to send it any messages you want.

#### UDT Out

Is used for sending information over a UDT connection between remotely located computers. Send messages using the `udtoutDAT_Class`.

#### WebSocket

Receives and parses WebSocket messages. WebSockets are fast an efficient two way communication protocol used by web servers and clients.

### System Information

#### Art-Net

Polls and lists all devices on the network.

#### Error

Lists the most recent TouchDesigner errors in its FIFO (first in/first out) table. You can filter our messages using pattern matching on some of the columns like Severity, Type and path of the node containing the error.

#### EtherDream

Polls and lists all EtherDream devices connected. See also: EtherDream CHOP, Scan CHOP.

#### Examine

Lets you inspect an operator's python storage, locals, globals, expressions, and extensions.

#### Info

Gives you string information about a node. Only some nodes contain additional string information which can be accessed by the Info DAT.

#### Keyboard In

Lists the most recent key events in its FIFO (first in/first out) table. There is one row for every key press down and every key-up, including Shift, Ctrl and Alt, with distinction between left and right side.

#### MIDI Event

Logs all MIDI messages coming into TouchDesigner from all MIDI devices. It outputs columns in a table format: message, type, channel, index, value.

#### MIDI In

Logs all MIDI messages coming into TouchDesigner from a specified MIDI device. It outputs columns in a table format - message, type, channel, index, value.

#### Monitors

Is a table of data about all currently detected monitors with information on the resolution, screen positioning, monitor name and description, and a flag indicating whether it is a primary monitor or not.

#### Multi Touch In

Is used for receiving messages and events from the Windows 7+ standard multi-touch API. It captures all the messages, where each new message changes the table it outputs.

#### OP Find

Traverses the component hierarchy starting at one component and looking at all nodes within that component, and outputs a table with one row per node that matches criteria the user chooses.

#### Perform

Logs various performance times in a Table DAT format. These benchmarks are similar to those reported by the Performance Monitor.

#### Render Pick

Allows you to do multi-touch on a 3D rendered scene. It samples a rendering (from a Render TOP or a Render Pass TOP) and returns 3D information from the geometry at the specified pick locations.

#### SOP to

Allows you to extract point and primitive data and attributes. Data is output in columns, with the first column being index.

### Utility

#### CHOP to

Allows you to get CHOP channel values into a DAT in table format.

#### Clip

Contains information about motion clips that are manipulated by a Clip CHOP and Clip Blender CHOP. The Clip DAT can hold any command or script text, which can be triggered based on the settings on the Execute parameter page (This is where the Clip DAT and the Text DAT are different).

#### Null

Has no effect on the data. It is an instance of the DAT connected to its input. The Null DAT is often used when making reference to a DAT network, allowing new DATs to be added to the network (upstream) without the need to update the reference.

#### Select

Allows you to fetch a DAT from any other location in TouchDesigner, and to select any subset of rows and columns if it is a table.

#### Switch

Is a multi-input operator which lets you choose which input is output by using the Input parameter.

#### Table

Lets you create a table of rows and columns of cells, each cell containing a text string. A "table" is one of the two forms of DATs (the other being simply lines of "free-form" text via the Text DAT).

#### Text

Lets you edit free-form, multi-line ASCII text. It is used for scripts, GLSL shaders, notes, XML and other purposes.

---

**Note:** Many operators marked as "Pro/Commercial Only" are restricted to TouchDesigner Commercial and Pro versions. Non-commercial versions may have limited functionality or channel restrictions for certain operators.
