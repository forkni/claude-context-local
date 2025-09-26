# DAT - Data Operators - Process and manipulate table/text data

[← Back to All Operators](../OPERATORS_INDEX.md)

## Overview

Data Operators - Process and manipulate table/text data in TouchDesigner. This family contains 57 operators.

## All DAT Operators

#### Art-Net

**Category**: General
**Description**: Polls and lists all devices on the network.
**Documentation**: [Full Details](./Art-Net.md)
**Related**: _To be added_

#### CHOP Execute

**Category**: General
**Description**: Will run its script when the values of a specified CHOP change. You can specify which channels to look at, and trigger based on their values changing in various ways.
**Documentation**: [Full Details](./CHOP_Execute.md)
**Related**: _To be added_

#### CHOP to

**Category**: General
**Description**: Allows you to get CHOP channel values into a DAT in table format.
**Documentation**: [Full Details](./CHOP_to.md)
**Related**: _To be added_

#### Clip

**Category**: General
**Description**: Contains information about motion clips that are manipulated by a Clip CHOP and Clip Blender CHOP . The Clip DAT can hold any command or script text, which can be triggered based on the settings on the Execute parameter page (This is where the Clip DAT and the Text DAT are different).
**Documentation**: [Full Details](./Clip.md)
**Related**: _To be added_

#### Convert

**Category**: General
**Description**: Changes the text format from simple text to table form and vice-versa.
**Documentation**: [Full Details](./Convert.md)
**Related**: _To be added_

#### DAT Execute

**Category**: General
**Description**: Monitors another DAT's contents and runs a script when those contents change. The other DAT is usually a table.
**Documentation**: [Full Details](./DAT_Execute.md)
**Related**: _To be added_

#### Error

**Category**: General
**Description**: Lists the most recent TouchDesigner errors in its FIFO (first in/first out) table. You can filter our messages using pattern matching on some of the columns like Severity, Type and path of the node containing the error.
**Documentation**: [Full Details](./Error.md)
**Related**: _To be added_

#### EtherDream

**Category**: General
**Description**: Polls and lists all EtherDream devices connected. See also: EtherDream CHOP, Scan CHOP.
**Documentation**: [Full Details](./EtherDream.md)
**Related**: _To be added_

#### Evaluate

**Category**: General
**Description**: Changes the cells of the incoming DAT using string-editing and math expressions. It outputs a table with the same number of rows and columns.
**Documentation**: [Full Details](./Evaluate.md)
**Related**: _To be added_

#### Examine

**Category**: General
**Description**: Lets you inspect an operator's python storage, locals, globals, expressions, and extensions.
**Documentation**: [Full Details](./Examine.md)
**Related**: _To be added_

#### Execute

**Category**: General
**Description**: Lets you edit scripts and run them based on conditions. It can be executed at the start or end of every frame, or at the start or end of the TouchDesigner process.
**Documentation**: [Full Details](./Execute.md)
**Related**: _To be added_

#### FIFO

**Category**: General
**Description**: The FIFO DAT maintains a user-set maximum number of rows in a table. You add rows using the appendRow() method found in DAT Class. When its capacity is reached, the first row is removed. After the maximum number of rows is reached, the oldest row is discarded when a new row is added.
**Documentation**: [Full Details](./FIFO.md)
**Related**: _To be added_

#### File In

**Category**: General
**Description**: Reads in .txt text files and .dat table files. It will attempt to read any other file as raw text. The file can be located on disk or on the web.
**Documentation**: [Full Details](./File_In.md)
**Related**: _To be added_

#### File Out

**Category**: General
**Description**: Allows you to write out DAT contents to a .dat file or a .txt file. A .dat file is one of the File Types of TouchDesigner that is used to hold the arrays of the Table DAT .
**Documentation**: [Full Details](./File_Out.md)
**Related**: _To be added_

#### Folder

**Category**: General
**Description**: Lists the files and subfolders found in a file system folder and monitors any changes. For each item found, a row is created in the table with optional columns for the following information: Name Extension Type Size Depth Folder Path Date Created Date Modified.
**Documentation**: [Full Details](./Folder.md)
**Related**: _To be added_

#### In

**Category**: General
**Description**: Is used to create a DAT input in a Component. Component inputs are positioned alphanumerically on the left side of the Component.
**Documentation**: [Full Details](./In.md)
**Related**: _To be added_

#### Indices

**Category**: General
**Description**: Creates a series of numbers in a table, ranging between the start and end values.  These values are suitable for display along a graph horizontal or vertical axis.
**Documentation**: [Full Details](./Indices.md)
**Related**: _To be added_

#### Info

**Category**: General
**Description**: Gives you string information about a node. Only some nodes contain additional string information which can be accessed by the Info DAT.
**Documentation**: [Full Details](./Info.md)
**Related**: _To be added_

#### Insert

**Category**: General
**Description**: Allows you to insert a row or column into an existing table.  If the input DAT is not a table, it will be converted to a table.
**Documentation**: [Full Details](./Insert.md)
**Related**: _To be added_

#### Keyboard In

**Category**: General
**Description**: Lists the most recent key events in its FIFO (first in/first out) table. There is one row for every key press down and every key-up, including Shift, Ctrl and Alt, with distinction between left and right side.
**Documentation**: [Full Details](./Keyboard_In.md)
**Related**: _To be added_

#### MIDI Event

**Category**: General
**Description**: Logs all MIDI messages coming into TouchDesigner from all MIDI devices. It outputs columns in a table format: message, type, channel, index, value.
**Documentation**: [Full Details](./MIDI_Event.md)
**Related**: _To be added_

#### MIDI In

**Category**: General
**Description**: Logs all MIDI messages coming into TouchDesigner from a specified MIDI device. It outputs columns in a table format - message, type, channel, index, value.
**Documentation**: [Full Details](./MIDI_In.md)
**Related**: _To be added_

#### Merge

**Category**: General
**Description**: The Merged DAT is a multi-input DAT which merges the text or tables from the input DATs together.
**Documentation**: [Full Details](./Merge.md)
**Related**: _To be added_

#### Monitors

**Category**: General
**Description**: Is a table of data about all currently detected monitors with information on the resolution, screen positioning, monitor name and description, and a flag indicating whether it is a primary monitor or not.
**Documentation**: [Full Details](./Monitors.md)
**Related**: _To be added_

#### Multi Touch In

**Category**: General
**Description**: Is used for receiving messages and events from the Windows 7+ standard multi-touch API. It captures all the messages, where each new message changes the table it outputs.
**Documentation**: [Full Details](./Multi_Touch_In.md)
**Related**: _To be added_

#### Null

**Category**: General
**Description**: Has no effect on the data. It is an instance of the DAT connected to its input. The Null DAT is often used when making reference to a DAT network, allowing new DATs to be added to the network (upstream) without the need to update the reference.
**Documentation**: [Full Details](./Null.md)
**Related**: _To be added_

#### OP Execute

**Category**: General
**Description**: Runs a script when the state of an operator changes. OP Execute DATs are created with default python method placeholders.
**Documentation**: [Full Details](./OP_Execute.md)
**Related**: _To be added_

#### OP Find

**Category**: General
**Description**: Traverses the component hierarchy starting at one component and looking at all nodes within that component, and outputs a table with one row per node that matches criteria the user chooses.
**Documentation**: [Full Details](./OP_Find.md)
**Related**: _To be added_

#### OSC In

**Category**: General
**Description**: Receives and parses full Open Sound Control packets using UDP.  Each packet is parsed and appended as a row in the DAT's table.
**Documentation**: [Full Details](./OSC_In.md)
**Related**: _To be added_

#### OSC Out

**Category**: General
**Description**: Is used for sending information over a OSC connection between remotely located computers. Use the send Command to initiate the data output.
**Documentation**: [Full Details](./OSC_Out.md)
**Related**: _To be added_

#### Out

**Category**: General
**Description**: Is used to create a DAT output in a Component. Component outputs are positioned alphanumerically on the right side of the Component.
**Documentation**: [Full Details](./Out.md)
**Related**: _To be added_

#### Panel Execute

**Category**: General
**Description**: Will run its script when the values of a specified panel component changes. You can specify which Panel Values to monitor, and trigger scripts based on their values changing in various ways.
**Documentation**: [Full Details](./Panel_Execute.md)
**Related**: _To be added_

#### Parameter Execute

**Category**: General
**Description**: The Parm Execute DAT runs a  script when a parameter of any node changes state. There are 4 ways a parameter can trigger the script: if its value, expression, export, or enable state changes.
**Documentation**: [Full Details](./Parameter_Execute.md)
**Related**: _To be added_

#### Perform

**Category**: General
**Description**: Logs various performance times in a Table DAT format. These benchmarks are similar to those reported by the Performance Monitor .
**Documentation**: [Full Details](./Perform.md)
**Related**: _To be added_

#### Render Pick

**Category**: General
**Description**: Allows you to do multi-touch on a 3D rendered scene. It samples a rendering (from a Render TOP or a Render Pass TOP ) and returns 3D information from the geometry at the specified pick locations.
**Documentation**: [Full Details](./Render_Pick.md)
**Related**: _To be added_

#### Reorder

**Category**: General
**Description**: Allows you to reorder the rows and columns of the input table.  You can also use In Specified Order option to get duplicate copies of rows and columns.
**Documentation**: [Full Details](./Reorder.md)
**Related**: _To be added_

#### SOP to

**Category**: General
**Description**: Allows you to extract point and primitive data and attributes. Data is output in columns, with the first column being index.
**Documentation**: [Full Details](./SOP_to.md)
**Related**: _To be added_

#### Script

**Category**: General
**Description**: Runs a script each time the Script DAT cooks.  By default, the Script DAT is created with a docked DAT that contains three Python methods: cook, onPulse, and setupParameters .
**Documentation**: [Full Details](./Script.md)
**Related**: _To be added_

#### Select

**Category**: General
**Description**: Allows you to fetch a DAT from any other location in TouchDesigner, and to select any subset of rows and columns if it is a table.
**Documentation**: [Full Details](./Select.md)
**Related**: _To be added_

#### Serial

**Category**: General
**Description**: Is used for serial communication through an external port, using the RS-232 protocol.  These ports are usually a 9 pin connector, or a USB port on new machines.
**Documentation**: [Full Details](./Serial.md)
**Related**: _To be added_

#### Sort

**Category**: General
**Description**: Will sort table DAT data by row or column.
**Documentation**: [Full Details](./Sort.md)
**Related**: _To be added_

#### Substitute

**Category**: General
**Description**: Changes the cells of the incoming DAT using pattern matching and substitution strings. It outputs a table with the same number of rows and columns.
**Documentation**: [Full Details](./Substitute.md)
**Related**: _To be added_

#### Switch

**Category**: General
**Description**: Is a multi-input operator which lets you choose which input is output by using the Input parameter.
**Documentation**: [Full Details](./Switch.md)
**Related**: _To be added_

#### TCP/IP

**Category**: General
**Description**: Is used for sending and receiving information over a TCP/IP connection between two remotely located computers.
**Documentation**: [Full Details](./TCPIP.md)
**Related**: _To be added_

#### TUIO In

**Category**: General
**Description**: Receives and parses TUIO messages (received over network) into columns in the table. TUIO packets OSC bundles, so TUIO data can also be viewed in it's more raw form in an OSC In DAT.
**Documentation**: [Full Details](./TUIO_In.md)
**Related**: _To be added_

#### Table

**Category**: General
**Description**: Lets you create a table of rows and columns of cells, each cell containing a text string. A "table" is one of the two forms of DATs (the other being simply lines of "free-form" text via the Text DAT ).
**Documentation**: [Full Details](./Table.md)
**Related**: _To be added_

#### Text

**Category**: General
**Description**: Lets you edit free-form, multi-line ASCII text. It is used for scripts, GLSL shaders, notes, XML and other purposes.
**Documentation**: [Full Details](./Text.md)
**Related**: _To be added_

#### Touch In

**Category**: General
**Description**: Receives full tables across the network from the Touch Out DAT, as opposed to messages with the other network based DATs.
**Documentation**: [Full Details](./Touch_In.md)
**Related**: _To be added_

#### Touch Out

**Category**: General
**Description**: Sends full DAT tables across the network to the Touch In DAT in another TouchDesigner process, as opposed to messages with the other network based DATs.
**Documentation**: [Full Details](./Touch_Out.md)
**Related**: _To be added_

#### Transpose

**Category**: General
**Description**: Converts rows into columns. The number of rows becomes the number of columns, and vice versa.
**Documentation**: [Full Details](./Transpose.md)
**Related**: _To be added_

#### UDP In

**Category**: General
**Description**: Is used for receiving information over a UDP connection between two remotely located computers. It captures all the messages without any queuing or buffering, and allows you to send it any messages you want.
**Documentation**: [Full Details](./UDP_In.md)
**Related**: _To be added_

#### UDP Out

**Category**: General
**Description**: Is used to send information over a UDP connection to/from a remotely-located computer.  Use the send Command in a DAT script or the textport to initiate the data output.
**Documentation**: [Full Details](./UDP_Out.md)
**Related**: _To be added_

#### UDT In

**Category**: General
**Description**: Is used for receiving information over a UDT connection between two remotely located computers. It captures all the messages without any queuing or buffering, and allows you to send it any messages you want.
**Documentation**: [Full Details](./UDT_In.md)
**Related**: _To be added_

#### UDT Out

**Category**: General
**Description**: Is used for sending information over a UDT connection between remotely located computers. Send messages using the udtoutDAT_Class .
**Documentation**: [Full Details](./UDT_Out.md)
**Related**: _To be added_

#### Web

**Category**: General
**Description**: Fetches pages of data from a web connection. The data should be ASCII-readable. The Web DAT will automatically uncompress any gzip compressed page transfers.
**Documentation**: [Full Details](./Web.md)
**Related**: _To be added_

#### WebSocket

**Category**: General
**Description**: Receives and parses WebSocket messages.  WebSockets are fast an efficient two way communication protocol used by web servers and clients.
**Documentation**: [Full Details](./WebSocket.md)
**Related**: _To be added_

#### XML

**Category**: General
**Description**: Can be used to parse arbitrary XML and SGML/HTML formatted data. Once formatted, selected sections of the text can be output for further processing.
**Documentation**: [Full Details](./XML.md)
**Related**: _To be added_

---

## Quick Stats

- **Total DAT Operators**: 57
- **Family Type**: DAT
- **Documentation**: Each operator has detailed parameter reference

## Navigation

- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation-by-family)

---
_Generated from TouchDesigner summaries.txt_
